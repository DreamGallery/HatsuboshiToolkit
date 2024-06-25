import os
import json
import src.rich_console as console
from pathlib import Path
from google.protobuf.json_format import MessageToDict
from src.decrypt import decrypt_database_from_api
from src.warp_request import request_update


class DataManger:
    revision: int
    latest: bool = False
    _data_path: str = "cache"
    _local_db_filename: str = "OctoDatabase.json"
    _local_diff_filename: str = "OctoDiff.json"
    _local_db_path = os.path.join(_data_path, _local_db_filename)
    _local_diff_path = os.path.join(_data_path, _local_diff_filename)

    def __init__(self):
        self.get_revision_from_local_database()

    def get_revision_from_local_database(self) -> bool:
        self.revision = 0
        if Path(self._local_db_path).exists():
            try:
                with open(self._local_db_path, "r", encoding="utf8") as fp:
                    local_db_dict = json.load(fp)
                    self.revision = local_db_dict["revision"]
                return True
            except (json.JSONDecodeError, KeyError) as e:
                console.error(f"Failed to get revision from local database, error:{e}")
                return False
        else:
            return False

    def start_db_update(self, reset: bool = False, db_revision: int = 0):
        revision = db_revision if reset else self.revision
        downloaded_bytes = request_update(revision)
        self.update_db(downloaded_bytes, revision == 0)

    # Store whole database in OctoDatabase.json and the updated part in OctoDiff.json
    def update_db(self, downloaded_bytes: bytes, reset: bool):
        try:
            db = decrypt_database_from_api(downloaded_bytes)
        except TypeError:
            console.error("Failed to deserialize database from API")
            return

        if db.revision == self.revision and not reset:
            console.info(f"The database\[revision={self.revision}] is already up to date")
            self.latest = True
            return

        if self.revision == 0 or reset:
            self.revision = db.revision
            with open(self._local_db_path, "w", encoding="utf8") as fp:
                db_dict = MessageToDict(db, use_integers_for_enums=True, including_default_value_fields=True)
                json.dump(db_dict, fp, ensure_ascii=False, indent=2)
            console.info(f"Got the latest database\[revision={self.revision}] from API")
            return

        console.info(f"Database update available\[from revision {self.revision} to {db.revision}]")
        self.latest = False
        self.revision = db.revision
        with open(self._local_diff_path, "w", encoding="utf8") as fp:
            db_dict = MessageToDict(db, use_integers_for_enums=True, including_default_value_fields=True)
            json.dump(db_dict, fp, ensure_ascii=False, indent=2)
        self.start_db_update(reset=True)
