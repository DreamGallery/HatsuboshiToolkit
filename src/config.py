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
UPDATE_FLAG = config.getboolean("Download settings", "UPDATE_FLAG")
MAX_RETRIES = config.getint("Download settings", "MAX_RETRIES")

# Path settings
ASSET_PATH = config.get("Path settings", "ASSET_PATH")
RESOURCE_PATH = config.get("Path settings", "RESOURCE_PATH")
UPDATE_PATH = config.get("Path settings", "UPDATE_PATH")

# Unity settings
UNITY_SIGNATURE = bytes(config.get("Unity settings", "UNITY_SIGNATURE"), encoding="utf8")
UNITY_VERSION = config.get("Unity settings", "UNITY_VERSION")

# Asset/Resource classify settings
ASSET_CLASSIFY = {
    key: config["Asset classify settings"].get(key) for key in config["Asset classify settings"]
}
RESOURCE_CLASSIFY = {
    key: config["Resource classify settings"].get(key) for key in config["Resource classify settings"]
}
CLASSIFY = {"AssetBundle": ASSET_CLASSIFY, "Resource": RESOURCE_CLASSIFY}
