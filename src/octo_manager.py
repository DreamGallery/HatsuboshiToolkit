import os
import json
import proto.octodb_pb2 as octop
import src.rich_console as console
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from src.config import API_KEY
from pathlib import Path
from google.protobuf.json_format import MessageToDict, ParseDict
from src.warp_request import request_update


def decrypt_database_from_api(enc_data: bytes, key: bytes = API_KEY, offset: int = 16) -> octop.Database:
    iv = enc_data[:offset]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    dec_data = unpad(cipher.decrypt(enc_data[offset:]), block_size=16, style="pkcs7")
    database = octop.Database.FromString(dec_data)
    return database


class DataManger:
    revision: int
    _latest: bool
    _has_error: bool
    _data_path: str = "cache"
    _local_db_filename: str = "OctoManifest.json"
    _local_diff_filename: str = "OctoDiff.json"
    _local_db_path = os.path.join(_data_path, _local_db_filename)
    _local_diff_path = os.path.join(_data_path, _local_diff_filename)

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset object's revision, _latest and _has_error to default value"""
        self.get_revision_from_local_database()
        self._latest = False
        self._has_error = False

    def get_revision_from_local_database(self) -> int:
        """Set self.revision to local database revision if available or 0

        Return:
          self.revision
        """
        self.revision = 0
        if Path(self._local_db_path).exists():
            try:
                with open(self._local_db_path, "r", encoding="utf8") as fp:
                    local_db_dict = json.load(fp)
                    self.revision = local_db_dict["revision"]
            except (json.JSONDecodeError, KeyError) as e:
                console.error(f"Failed to get revision from local database, error:{e}")
        else:
            console.info("No local database found")
        return self.revision

    def start_db_update(self, reset: bool = False, db_revision: int = 0):
        """Download database from API with specified revision

        Args:
          reset: If True, set revision as db_revision, else self.revision
          db_revision: Database revision when reset
        """
        revision = db_revision if reset else self.revision
        downloaded_bytes = request_update(revision)
        self.update_db(downloaded_bytes, revision == 0)

    def update_db(self, downloaded_bytes: bytes, reset: bool):
        """Store whole database in OctoManifest.json and the updated part in OctoDiff.json

        Args:
          download_bytes: Octo database bytes stream get from API
          reset: If True (revision == 0) , reset local OctoManifest.json file

        Also set self._has_error as True when meet TypeError caused by some requests error,
        set self._latest by whether the database is up to date and set self.revision to
        API revision
        """
        try:
            db = decrypt_database_from_api(downloaded_bytes)
        except TypeError:
            self._has_error = True
            console.error("Failed to deserialize database from API")
            return

        if db.revision == self.revision and not reset:
            console.info(f"The database\\[revision={self.revision}] is already up to date")
            self._latest = True
            return

        self._latest = False
        if self.revision == 0 or reset:
            self.revision = db.revision
            with open(self._local_db_path, "w", encoding="utf8") as fp:
                db_dict = MessageToDict(db, use_integers_for_enums=True, including_default_value_fields=True)
                json.dump(db_dict, fp, ensure_ascii=False, indent=2)
            console.info(f"Got the latest database\\[revision={self.revision}] from API")
            return

        console.info(f"Database update available\\[from revision {self.revision} to {db.revision}]")
        self.revision = db.revision
        with open(self._local_diff_path, "w", encoding="utf8") as fp:
            db_dict = MessageToDict(db, use_integers_for_enums=True, including_default_value_fields=True)
            json.dump(db_dict, fp, ensure_ascii=False, indent=2)
        self.start_db_update(reset=True)

    def get_status(self) -> bool:
        """Return True when no error and not latest."""
        return not (self._has_error or self._latest)

    def get_diff_and_check_legal(self, init: bool = False) -> octop.Database | None:
        """Deserialize database diff from OctoDiff.json if exist,
        or deserialize database from OctoManifest.json if `init = True`
        
        Return:
          octo database object if available
        """
        if not self.get_status():
            return

        if Path(self._local_diff_path).exists() and not init:
            json_file_path = self._local_diff_path
        elif init:
            json_file_path = self._local_db_path
        else:
            return

        try:
            with open(json_file_path, "r", encoding="utf8") as fp:
                db = ParseDict(json.load(fp), octop.Database(), ignore_unknown_fields=True)
            return db
        except Exception as e:
            console.error(f"Failed to deserialize database from local json file, error:{e}")
