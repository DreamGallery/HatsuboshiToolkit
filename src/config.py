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
TXT_PATH = config.get("Path settings", "TXT_PATH")
