import os
import sys
import threading
from pathlib import Path
from concurrent.futures import (
    ThreadPoolExecutor,
    wait,
    ALL_COMPLETED,
)
from src.config import (
    UNITY_SIGNATURE,
    ASSET_PATH,
    RESOURCE_PATH,
    UPDATE_PATH,
)
import src.rich_console as console
import proto.octodb_pb2 as octop
from src.image_process import unpack_to_image
from src.decrypt import crypt_by_string
from src.warp_request import send_request
from src.file_operation import file_store


_asset_count = 0
_resource_count = 0
_current_count = 0
lock = threading.Lock()


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
            file_store(asset_bytes, item.name, dest_path, _type)
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
        file_store(obj, item.name, dest_path, _type)
        lock.acquire()
        _current_count += 1
        console.succeed(
            f"{_current_count}/{_resource_count}) Resource '{item.name}' has been successfully renamed."
        )
        lock.release()


def download_resource(revision: int, database: octop.Database, download_type: str = "ALL"):
    global _asset_count
    global _resource_count
    global _current_count

    urlFormat = database.urlFormat

    _asset_count = len(database.assetBundleList)
    _resource_count = len(database.resourceList)

    # set update path
    asset_store_path = f"{UPDATE_PATH}/{revision}/{os.path.basename(ASSET_PATH)}"
    resource_store_path = f"{UPDATE_PATH}/{revision}/{os.path.basename(RESOURCE_PATH)}"
    Path(asset_store_path).mkdir(parents=True, exist_ok=True)
    Path(resource_store_path).mkdir(parents=True, exist_ok=True)

    executor = ThreadPoolExecutor(max_workers=20)

    if download_type in ["ALL", "ab"]:
        # Asset download/update
        _current_count = 0
        asset_tasks = [
            executor.submit(one_task, item, "AssetBundle", urlFormat, asset_store_path)
            for item in database.assetBundleList
        ]
        wait(asset_tasks, return_when=ALL_COMPLETED)
        console.succeed("All AssetBundle tasks has been successfully processed.")

    if download_type in ["ALL", "resource"]:
        # Resource download/update
        _current_count = 0
        resource_tasks = [
            executor.submit(one_task, item, "Resource", urlFormat, resource_store_path)
            for item in database.resourceList
        ]
        wait(resource_tasks, return_when=ALL_COMPLETED)
        console.succeed("All resource tasks has been successfully processed.")
