import os
import hashlib
import configparser


_BASE_PATH = os.path.abspath(os.path.dirname(__file__) + os.path.sep + "..")

config = configparser.ConfigParser(comment_prefixes="/", allow_no_value=True)
config.optionxform = lambda option: option
config.read(os.path.join(_BASE_PATH, "config.ini"), encoding="utf-8")

# Octo settings
APP_ID = config.getint("Octo settings", "APP_ID")
CLIENT_SECRET_KEY = config.get("Octo settings", "CLIENT_SECRET_KEY")
VERSION = config.get("Octo settings", "VERSION")
URL = config.get("Octo settings", "URL")
API_KEY = hashlib.sha256(config.get("Octo settings", "A").encode("utf8")).digest()

# Download settings
MAX_RETRIES = config.getint("Download settings", "MAX_RETRIES")

# Path settings
DOWNLOAD_PATH = config.get("Path settings", "DOWNLOAD_PATH")

# Unity settings
UNITY_SIGNATURE = bytes(config.get("Unity settings", "UNITY_SIGNATURE"), encoding="utf8")
UNITY_VERSION = config.get("Unity settings", "UNITY_VERSION")

# R2 settings
R2_ACCOUNT_ID = config.get("R2 settings", "R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = config.get("R2 settings", "R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = config.get("R2 settings", "R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = config.get("R2 settings", "R2_BUCKET_NAME")
R2_ENDPOINT_URL = config.get("R2 settings", "R2_ENDPOINT_URL")
ENABLE_R2_SYNC = config.getboolean("R2 settings", "ENABLE_R2_SYNC")
