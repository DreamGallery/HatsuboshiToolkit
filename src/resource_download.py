import sys
import shutil
import json
import threading
import platform
import tarfile
import zipfile
from pathlib import Path
from concurrent.futures import (
    ThreadPoolExecutor,
    wait,
    ALL_COMPLETED,
)
from google.protobuf.json_format import MessageToDict
from src.config import UNITY_SIGNATURE, DOWNLOAD_PATH
import src.rich_console as console
import proto.octodb_pb2 as octop
from src.file_unpack import unpack_to_image, unpack_to_audio
from src.decrypt import crypt_by_string
from src.warp_request import send_request


_asset_count = 0
_resource_count = 0
_current_count = 0
lock = threading.Lock()

def filter_database(database: octop.Database):
    filtered_assets = [
        item for item in database.assetBundleList 
        if item.name.startswith(("img", "env"))
    ]
    del database.assetBundleList[:]
    database.assetBundleList.extend(filtered_assets)
    
    filtered_resources = [
        item for item in database.resourceList 
        if item.name.startswith(("img_general_music_jacket", "sud_vo_system", "sud_vo_adv")) or item.name.endswith(".mp3")
    ]
    del database.resourceList[:]
    database.resourceList.extend(filtered_resources)
    
    return database

def one_task(item: dict, _type: str, url_format: str, dest_path: str):
    global _current_count

    url = url_format.replace("{o}", item.objectName)
    obj = send_request(url, verify=True).content
    if obj.__len__() == 0:
        console.info(f"Empty object '{item.name}', skipping.")
        return

    if _type == "AssetBundle":
        try:
            if obj[0:5] != UNITY_SIGNATURE:
                asset_bytes = crypt_by_string(obj, item.name, 0, 0, 256)
            else:
                asset_bytes = obj
            if asset_bytes[0:5] != UNITY_SIGNATURE:
                console.error(f"'{item.name}' '{item.md5}' is not a unity asset.")
                raise
            # Converts an image asset to png, does nothing if asset is not texture2d/sprite
            unpack_to_image(asset_bytes, dest_path)
            lock.acquire()
            _current_count += 1
            console.succeed(
                f"({_current_count}/{_asset_count}) AssetBundle '{item.name}' has been successfully deobfuscated."
            )
            lock.release()
        except:
            lock.acquire()
            _current_count += 1
            console.error(f"{_current_count}/{_asset_count}) Failed to deobfuscate '{item.name}'.")
            console.error(sys.exc_info())
            lock.release()
    elif _type == "Resource":
        with open(f"{dest_path}/{item.name}", "wb") as f:
            f.write(obj)
        if item.name.startswith("img_general_music_jacket"):
            Path(f"{dest_path}/images/jacket").mkdir(parents=True, exist_ok=True)
            shutil.move(f"{dest_path}/{item.name}", f"{dest_path}/images/jacket/{item.name}")
        else:
            success = unpack_to_audio(item.name, dest_path)
            if not success:
                original_file = Path(f"{dest_path}/{item.name}")
                if original_file.exists():
                    original_file.unlink()
        
        lock.acquire()
        _current_count += 1
        if item.name.startswith("img_general_music_jacket") or success:
            console.succeed(
                f"({_current_count}/{_resource_count}) Resource '{item.name}' has been successfully processed."
            )
        else:
            console.error(
                f"({_current_count}/{_resource_count}) Failed to process resource '{item.name}'."
            )
        lock.release()


def download_resource(revision: int, database: octop.Database):
    global _asset_count
    global _resource_count
    global _current_count

    database = filter_database(database)
    with open(f"{DOWNLOAD_PATH}/OctoDiff_{revision}.json", "w", encoding="utf8") as f:
        f.write(json.dumps(MessageToDict(database), ensure_ascii=False, indent=2))

    urlFormat = database.urlFormat

    _asset_count = len(database.assetBundleList)
    _resource_count = len(database.resourceList)

    Path(DOWNLOAD_PATH).mkdir(parents=True, exist_ok=True)
    executor = ThreadPoolExecutor(max_workers=20)

    _current_count = 0
    asset_tasks = [
        executor.submit(one_task, item, "AssetBundle", urlFormat, DOWNLOAD_PATH)
        for item in database.assetBundleList
    ]
    wait(asset_tasks, return_when=ALL_COMPLETED)
    console.succeed("Assets of image has been successfully processed.")

    _current_count = 0
    resource_tasks = [
        executor.submit(one_task, item, "Resource", urlFormat, DOWNLOAD_PATH)
        for item in database.resourceList
    ]
    wait(resource_tasks, return_when=ALL_COMPLETED)
    console.succeed("Resources of sound and jacket has been successfully processed.")


def download_and_extract_vgmstream():
    """Download and extract vgmstream CLI"""
    base_url = "https://github.com/vgmstream/vgmstream-releases/releases/download/nightly/"
    vgmstream_dir = Path("vgmstream")
    vgmstream_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine the download file based on the system type
    system = platform.system().lower()
    if system == "linux":
        filename = "vgmstream-linux-cli.tar.gz"
        is_zip = False
    elif system == "darwin":
        filename = "vgmstream-mac-cli.tar.gz"
        is_zip = False
    elif system == "windows":
        filename = "vgmstream-win.zip"
        is_zip = True
    else:
        console.error(f"Unsupported system: {system}")
        return False
    
    download_url = base_url + filename
    file_path = vgmstream_dir / filename
    
    console.info(f"Downloading {filename}...")
    
    try:
        response = send_request(download_url, verify=True)
        
        with open(file_path, 'wb') as f:
            f.write(response.content)
        
        console.succeed(f"Download completed: {filename}")
        
        console.info(f"Extracting {filename}...")
        
        if is_zip:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(vgmstream_dir)
        else:
            with tarfile.open(file_path, 'r:gz') as tar_ref:
                tar_ref.extractall(vgmstream_dir)
        
        console.succeed(f"Extraction completed: {filename}")
        
        file_path.unlink()
        console.info(f"Temporary file deleted: {filename}")
        
        return True
        
    except Exception as e:
        console.error(f"Download or extract vgmstream failed: {e}")
        if file_path.exists():
            file_path.unlink()
        return False


def check_vgmstream_installed():
    """Check if vgmstream is installed"""
    vgmstream_dir = Path("vgmstream")
    
    if not vgmstream_dir.exists():
        return False
    
    system = platform.system().lower()
    if system == "windows":
        executable_pattern = "*.exe"
    else:
        executable_pattern = "*"
    
    executables = list(vgmstream_dir.rglob(executable_pattern))
    return len(executables) > 0


def ensure_vgmstream():
    """Ensure vgmstream is installed, if not, download it"""
    if not check_vgmstream_installed():
        console.info("vgmstream not found, downloading...")
        return download_and_extract_vgmstream()
    else:
        console.info("vgmstream already exists, skipping download.")
        return True
