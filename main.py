import time
import click
import UnityPy.config
from src.octo_manager import DataManger
from src.resource_download import download_resource, ensure_vgmstream
from src.r2_sync import sync_to_r2
from src.config import UNITY_VERSION, ENABLE_R2_SYNC
import src.rich_console as console


UnityPy.config.FALLBACK_UNITY_VERSION = UNITY_VERSION


def once(reset: bool, init_download: bool, force_upload: bool):
    octo_manager = DataManger()
    octo_manager.start_db_update(reset)
    database = octo_manager.get_diff_and_check_legal(init_download)
    if database:
        download_resource(database)
        
        if ENABLE_R2_SYNC:
            console.info("Starting R2 synchronization...")
            if sync_to_r2(force_upload=force_upload):
                console.succeed("R2 synchronization completed successfully.")
            else:
                console.error("R2 synchronization failed.")
        else:
            console.info("R2 sync is disabled.")


def loop(reset: bool, init_download: bool, loop_interval: int = 600, force_upload: bool = False):
    once(reset, init_download, force_upload)
    while True:
        time.sleep(loop_interval)
        octo_manager = DataManger()
        octo_manager.start_db_update()
        database = octo_manager.get_diff_and_check_legal()
        if database:
            download_resource(database)
            
            if ENABLE_R2_SYNC:
                console.info("Starting R2 synchronization...")
                if sync_to_r2(force_upload=force_upload):
                    console.succeed("R2 synchronization completed successfully.")
                else:
                    console.error("R2 synchronization failed.")
            else:
                console.info("R2 sync is disabled.")


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
@click.option(
    "--sync_only",
    default=False,
    type=bool,
    help="Only sync existing cache to R2 without downloading new resources.",
)
@click.option(
    "--force_upload",
    default=False,
    type=bool,
    help="Force upload all files to R2.",
)
def main(
    mode: str,
    reset: bool = False,
    init_download: bool = False,
    loop_interval: int = 600,
    sync_only: bool = False,
    force_upload: bool = False,
):
    if not ensure_vgmstream():
        console.error("vgmstream initialization failed, program exit.")
        return
    
    if sync_only:
        console.info("Running in sync-only mode...")
        if sync_to_r2(force_upload=force_upload):
            console.succeed("R2 synchronization completed successfully.")
        else:
            console.error("R2 synchronization failed.")
        return
    
    if mode == "once":
        once(reset, init_download, force_upload)
    elif mode == "loop":
        loop(reset, init_download, loop_interval, force_upload)


if __name__ == "__main__":
    main()
