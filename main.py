import shutil
import UnityPy.config
from pathlib import Path
from src.config import config
from src.file_operation import file_operate
from src.octo_manager import update_octo_database
from src.resource_download import download_resource
from src.image_process import image_scale
from src.config import UPDATE_PATH, UNITY_VERSION, UPDATE_FLAG


def main():
    UnityPy.config.FALLBACK_UNITY_VERSION = UNITY_VERSION
    enc_bytes = Path("cache/octocacheevai").read_bytes()
    update_octo_database(enc_bytes)
    revision = download_resource()
    image_scale(f"{UPDATE_PATH}/{revision}/image", f"{UPDATE_PATH}/{revision}/stretch")
    if UPDATE_FLAG:
        file_operate("copy", f"{UPDATE_PATH}/{revision}", "cache", dirs_exist_ok=True)
    else:
        file_operate("move", f"{UPDATE_PATH}/{revision}", "cache")
        shutil.rmtree(f"{UPDATE_PATH}/{revision}", ignore_errors=True)
        config.set("Download settings", "UPDATE_FLAG", "True")
        with open("config.ini", "w", encoding="utf8") as config_file:
            config.write(config_file)


if __name__ == "__main__":
    main()
