import os
import sys
import json
from pathlib import Path
from google.protobuf.json_format import MessageToDict
from src.decrypt import decrypt_octo_database
from src.config import FILE_CHECK, ASSET_PATH, RESOURCE_PATH


def get_local_files(asset_path: str = ASSET_PATH, resource_path: str = RESOURCE_PATH) -> dict:
    local_asset_list = []
    if Path(asset_path).exists():
        for _, _, files in os.walk(asset_path):
            local_asset_list.extend(files)

    local_resource_list = []
    if Path(resource_path).exists():
        for _, _, files in os.walk(resource_path):
            local_resource_list.extend(files)

    local_files = {"assetBundleList": local_asset_list, "resourceList": local_resource_list}
    return local_files


def update_octo_database(raw_cache: bytes):
    """Store whole database in OctoManifest.json and the updated part in OctoDiff.json
    """
    new_database = MessageToDict(
        decrypt_octo_database(raw_cache), use_integers_for_enums=True, including_default_value_fields=True
    )
    update_flag = 0
    if Path("cache/OctoManifest.json").exists():
        update_database = {}
        with open(f"cache/OctoManifest.json", "r", encoding="utf8") as fp:
            local_database = json.load(fp)
        local_files = get_local_files()
        for key in new_database.keys():
            if isinstance(new_database[key], list):
                update_database[key] = []
                for item in new_database[key]:
                    if item not in local_database[key] or (
                        FILE_CHECK and item['name'] not in local_files[key]
                    ):
                        update_database[key].append(item)
                        update_flag += 1
            else:
                update_database[key] = new_database[key]
                if new_database[key] != local_database[key]:
                    update_flag += 1
    else:
        update_flag = -1
        update_database = new_database

    if update_flag != 0:
        with open(f"cache/OctoManifest.json", "w", encoding="utf8") as fp:
            json.dump(new_database, fp, ensure_ascii=False, indent=2)
        with open(f"cache/OctoDiff.json", "w", encoding="utf8") as fp:
            json.dump(update_database, fp, ensure_ascii=False, indent=2)
    else:
        print("The database is already up to date.")
        sys.exit(0)
