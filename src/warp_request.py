import sys
import requests
import src.rich_console as console
from os import _exit as exit
from src.config import MAX_RETRIES


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
