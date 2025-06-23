import time
import click
import UnityPy.config
from src.octo_manager import DataManger
from src.resource_download import download_resource, ensure_vgmstream
from src.config import UNITY_VERSION
import src.rich_console as console


UnityPy.config.FALLBACK_UNITY_VERSION = UNITY_VERSION


def once(reset: bool, init_download: bool):
    octo_manager = DataManger()
    octo_manager.start_db_update(reset)
    revision = octo_manager.revision
    database = octo_manager.get_diff_and_check_legal(init_download)
    if database:
        download_resource(
            revision,
            database,
        )


def loop(reset: bool, init_download: bool, loop_interval: int = 600):
    once(reset, init_download)
    while True:
        time.sleep(loop_interval)
        octo_manager = DataManger()
        octo_manager.start_db_update()
        revision = octo_manager.revision
        database = octo_manager.get_diff_and_check_legal()
        if database:
            download_resource(
                revision,
                database
            )


@click.command()
@click.option(
    "--mode",
    default="once",
    type=click.Choice(["once", "loop"]),
    help="Script mode, once for single run and loop for continuously check for updates.",
)
@click.option(
    "--reset",
    default=False,
    type=bool,
    help="Used to reset local database.",
)
@click.option(
    "--init_download",
    default=False,
    type=bool,
    help="Whether to download the full resource on first use.",
)
@click.option(
    "--loop_interval",
    default=600,
    type=int,
    help="The interval between each check, in seconds.",
)
def main(
    mode: str,
    reset: bool = False,
    init_download: bool = False,
    download_type: str = "ALL",
    loop_interval: int = 600,
):
    if not ensure_vgmstream():
        console.error("vgmstream initialization failed, program exit.")
        return
    
    if mode == "once":
        once(reset, init_download)
    elif mode == "loop":
        loop(reset, init_download, loop_interval)


if __name__ == "__main__":
    main()
