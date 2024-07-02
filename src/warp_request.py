import sys
import requests
import src.rich_console as console
from os import _exit as exit
from urllib.parse import urljoin
from src.config import (
    APP_ID,
    CLIENT_SECRET_KEY,
    URL,
    VERSION,
    MAX_RETRIES,
)


def send_request(
    url: str, data=None, headers=None, verify: bool = True, retries: int = 0
) -> requests.Response:
    if retries >= MAX_RETRIES:
        console.error(f"Get {url} failed. Stopping process.")
        exit(-1)
    try:
        response = requests.get(url, data=data, headers=headers, verify=verify)
        if response.status_code != 200:
            raise f"Abnormal status code {response.status_code}."
    except:
        console.error(f"An error occurred during send request to {url}.")
        console.error(f"ErrInfo: {sys.exc_info()[0]}.")
        console.error(f"Retries({retries + 1}/{MAX_RETRIES}).")
        response = send_request(url, data, headers, verify, retries + 1)
    return response


def request_update(db_revision: int = 0) -> requests.Response | None:
    aes_api_list_format = f"v2/pub/a/{APP_ID}/v/{VERSION}/list"
    headers = {
        "Accept": f"application/x-protobuf,x-octo-app/{APP_ID}",
        "X-OCTO-KEY": f"{CLIENT_SECRET_KEY}",
    }
    try:
        url = urljoin(URL, aes_api_list_format + f"/{db_revision}")
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.content
    except:
        console.error(f"An error occurred during send request to {url}.")
        console.error(f"ErrInfo: {sys.exc_info()[0]}.")
    return None
