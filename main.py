import click
from src.octo_manager import DataManger
from src.resource_download import download_resource


@click.command()
@click.option(
    "--reset",
    default=False,
    type=bool,
    help="Used to reset local database.",
)
@click.option(
    "--db_revision",
    default=0,
    type=int,
    help="Set the database revision when reset.",
)
@click.option(
    "--init_download",
    default=False,
    type=bool,
    help="Whether to download the full resource on first use.",
)
def main(reset: bool = False, db_revision: int = 0, init_download: bool = False):
    octo_manager = DataManger()
    octo_manager.start_db_update(reset, db_revision)
    revision = octo_manager.revision
    database = octo_manager.get_diff_and_check_legal(init_download)
    if database:
        download_resource(database)
        with open("cache/revision", "w", encoding="utf8") as fp:
            fp.write(str(revision))


if __name__ == "__main__":
    main()
