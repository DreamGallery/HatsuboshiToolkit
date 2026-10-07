import os
import shutil
from pathlib import Path


def file_store(data_bytes: bytes, file_name: str, root_path: str):
    """Keep original resource names in the caller's AssetBundle/Resource directory."""
    if not file_name or Path(file_name).name != file_name or file_name in (".", "..") or "\\" in file_name:
        raise ValueError("Resource name must be a single filename")
    directory = Path(root_path)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / file_name).write_bytes(data_bytes)


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
