import time
import click
import shutil
import UnityPy.config
from src.config import config
from src.octo_manager import DataManger
from src.file_operation import file_operate
from src.resource_download import download_resource
from src.image_process import image_scale
from src.config import UPDATE_PATH, UNITY_VERSION, UPDATE_FLAG


UnityPy.config.FALLBACK_UNITY_VERSION = UNITY_VERSION


def after_download(revision: int):
    image_scale(f"{UPDATE_PATH}/{revision}/image", f"{UPDATE_PATH}/{revision}/stretch")
    if UPDATE_FLAG:
        file_operate("copy", f"{UPDATE_PATH}/{revision}", "cache", dirs_exist_ok=True)
    else:
        file_operate("move", f"{UPDATE_PATH}/{revision}", "cache")
        shutil.rmtree(f"{UPDATE_PATH}/{revision}", ignore_errors=True)
        config.set("Download settings", "UPDATE_FLAG", "True")
        with open("config.ini", "w", encoding="utf8") as config_file:
            config.write(config_file)


def once():
    octo_manager = DataManger()
    octo_manager.start_db_update()
    revision = octo_manager.revision
    if not octo_manager.latest:
        download_resource(revision)
        after_download(revision)


def loop():
    while True:
        octo_manager = DataManger()
        octo_manager.start_db_update()
        revision = octo_manager.revision
        if not octo_manager.latest:
            download_resource(revision)
            after_download(revision)
        time.sleep(60)


@click.command()
@click.option(
    "--mode",
    default="once",
    type=click.Choice(["once", "loop"]),
    help="Script mode, [once] for single run or [loop] for continuously check for updates",
)
def main(mode: str):
    if mode == "once":
        once()
    elif mode == "loop":
        loop()


if __name__ == "__main__":
    main()
