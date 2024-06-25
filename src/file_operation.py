import os
import shutil
from pathlib import Path
from src.config import CLASSIFY


def file_store(data_bytes: bytes, file_name: str, root_path: str, _type: str):
    if _type == "AssetBundle" and "shader" in file_name:
        sub_path = CLASSIFY[_type]["shader"]
    else:
        sub_path = CLASSIFY[_type]["other"]
        for index, split_part in enumerate(file_name.split("_")):
            if index > 1:
                break
            if split_part in CLASSIFY[_type].keys():
                sub_path = CLASSIFY[_type][split_part]
                break

    store_path = f"{root_path}/{sub_path}"
    Path(store_path).mkdir(parents=True, exist_ok=True)
    with open(f"{store_path}/{file_name}", "wb") as fp:
        fp.write(data_bytes)


def file_operate(mode: str, source_path: str, dest_path: str, **kwargs):
    if mode == "copy":
        shutil.copytree(source_path, dest_path, **kwargs)
    elif mode == "move":
        for root, _, files in os.walk(source_path):
            dest_dir = root.replace(source_path, dest_path, 1)
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir)
            for file in files:
                src_file = os.path.join(root, file)
                dest_file = os.path.join(dest_dir, file)
                if os.path.exists(dest_file):
                    if os.path.samefile(src_file, dest_file):
                        continue
                    os.remove(dest_file)
                shutil.move(src_file, dest_dir)
