import time
import click
import shutil
import UnityPy.config
import proto.octodb_pb2 as octop
from src.config import config
from src.octo_manager import DataManger
from src.file_operation import file_operate
from src.resource_download import download_resource
from src.image_process import image_scale
from src.config import UPDATE_PATH, UNITY_VERSION, UPDATE_FLAG


UnityPy.config.FALLBACK_UNITY_VERSION = UNITY_VERSION


def after_download(revision: int, database: octop.Database):
    image_scale(database, f"{UPDATE_PATH}/{revision}/image", f"{UPDATE_PATH}/{revision}/stretch")
    if UPDATE_FLAG:
        file_operate("copy", f"{UPDATE_PATH}/{revision}", "cache", dirs_exist_ok=True)
    else:
        file_operate("move", f"{UPDATE_PATH}/{revision}", "cache")
        shutil.rmtree(f"{UPDATE_PATH}/{revision}", ignore_errors=True)
        config.set("Download settings", "UPDATE_FLAG", "True")
        with open("config.ini", "w", encoding="utf8") as config_file:
            config.write(config_file)


def once(reset: bool, init_download: bool, download_type: str):
    octo_manager = DataManger()
    octo_manager.start_db_update(reset)
    revision = octo_manager.revision
    database = octo_manager.get_diff_and_check_legal(init_download)
    if database:
        download_resource(
            revision,
            database,
            download_type,
        )
        after_download(revision, database)


def loop(reset: bool, init_download: bool, download_type: str):
    once(reset, init_download, download_type)
    time.sleep(60)
    while True:
        octo_manager = DataManger()
        octo_manager.start_db_update()
        revision = octo_manager.revision
        database = octo_manager.get_diff_and_check_legal()
        if database:
            download_resource(
                revision,
                database,
                download_type,
            )
            after_download(revision, database)
        time.sleep(60)


@click.command()
@click.option(
    "--mode",
    default="once",
    type=click.Choice(["once", "loop"]),
    help="Script mode, once for single run and loop for continuously check for updates",
)
@click.option(
    "--reset",
    default=False,
    type=bool,
    help="Used to reset local database",
)
@click.option(
    "--init_download",
    default=False,
    type=bool,
    help="Whether to download the full resource on first use",
)
@click.option(
    "--download_type",
    default="ALL",
    type=click.Choice(["ALL", "ab", "resource"]),
    help="Specify the type to download, ab for assetBundle, resource for resource and ALL for both",
)
def main(mode: str, reset: bool = False, init_download: bool = False, download_type: str = "ALL"):
    if mode == "once":
        once(reset, init_download, download_type)
    elif mode == "loop":
        loop(reset, init_download, download_type)


if __name__ == "__main__":
    main()
