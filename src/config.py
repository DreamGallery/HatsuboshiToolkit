import os
import configparser


_BASE_PATH = os.path.abspath(os.path.dirname(__file__) + os.path.sep + "..")

config = configparser.ConfigParser(comment_prefixes="/", allow_no_value=True)
config.optionxform = lambda option: option
config.read(os.path.join(_BASE_PATH, "config.ini"), encoding="utf-8")

# Decryption settings
FILE_KEY = bytes.fromhex(config.get("Decryption settings", "FILE_KEY"))
FILE_IV = bytes.fromhex(config.get("Decryption settings", "FILE_IV"))

# Download settings
FILE_CHECK = config.getboolean("Download settings", "FILE_CHECK")
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
