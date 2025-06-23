import UnityPy
from pathlib import Path
import platform
import re
import shutil
import subprocess
import src.rich_console as console
from src.config import DOWNLOAD_PATH


def unpack_to_image(asset_bytes: bytes, dest_path: str = DOWNLOAD_PATH):
    env = UnityPy.load(asset_bytes)
    for obj in env.objects:
        if obj.type.name == "Texture2D":
            data = obj.read()
            if data.name.startswith(("env", "img")):
                store_path = f"{dest_path}/images"                  
                if data.name.startswith("env"):
                    store_path = f"{dest_path}/images/environment"
                elif data.name.startswith("img_general_"):
                    match = re.match(r'img_general_([^_-]+)', data.name)
                    if match:
                        store_path = f"{dest_path}/images/{match.group(1)}"
                elif data.name.startswith("img_"):
                    match = re.match(r'img_([^_-]+)', data.name)
                    if match:
                        store_path = f"{dest_path}/images/{match.group(1)}"
                try:
                    Path(store_path).mkdir(parents=True, exist_ok=True)
                    img = data.image
                    img.save(f"{store_path}/{data.name}.png")
                    console.info(f"Saved image: {store_path}/{data.name}.png")
                except Exception as e:
                    console.error(f"Failed to convert '{data.name}' to image: {e}")
            else:
                continue


def unpack_to_audio(filename: str, dest_path: str = DOWNLOAD_PATH) -> bool:
    try:
        if filename.endswith(".mp3"):
            store_path = f"{dest_path}/music"
            Path(store_path).mkdir(parents=True, exist_ok=True)
            shutil.move(f"{dest_path}/{filename}", f"{store_path}/{filename}")
            return True
        else:
            vgmstream_dir = Path("vgmstream")
            system = platform.system().lower()
            if system == "windows":
                binary_pattern = "*.exe"
            else:
                binary_pattern = "*"
            binaries = list(vgmstream_dir.rglob(binary_pattern))
            if len(binaries) == 0:
                console.error("VGMStream is not installed. Please install it first.")
                return False
            binary = binaries[0]
            store_path = f"{dest_path}/sound"
            if filename.startswith(("sud_vo_system", "sud_vo_adv")):
                if filename.startswith("sud_vo_system"):
                    match = re.match(r'sud_vo_system_(.+?)(?:\.[^.]+)?$', filename)
                    if match:
                        store_path = f"{dest_path}/sound/system/{match.group(1)}"
                else:
                    match = re.match(r'sud_vo_adv_(.+?)(?:\.[^.]+)?$', filename)
                    if match:
                        store_path = f"{dest_path}/sound/adv/{match.group(1)}"
            Path(store_path).mkdir(parents=True, exist_ok=True)
            command = f"{binary} -S 0 -o {store_path}/?n.wav {dest_path}/{filename}"
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                original_file = Path(f"{dest_path}/{filename}")
                if original_file.exists():
                    original_file.unlink()
                return True
            else:
                console.error(f"VGMStream conversion failed for {filename}: {result.stderr}")
                return False
    except Exception as e:
        console.error(f"Failed to process audio file {filename}: {e}")
        return False