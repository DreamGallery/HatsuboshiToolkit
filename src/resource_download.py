import threading
from pathlib import Path
from concurrent.futures import (
    ThreadPoolExecutor,
    wait,
    ALL_COMPLETED,
)
from src.config import TXT_PATH
import src.rich_console as console
import proto.octodb_pb2 as octop
from src.warp_request import send_request

_adv_txt_count = 0
_current_count = 0
lock = threading.Lock()


def one_task(item: dict, url_format: str, dest_path: str):
    global _current_count

    url = url_format.replace("{o}", item.objectName)
    obj = send_request(url, verify=True).content
    if obj.__len__() == 0:
        console.info(f"Empty object '{item.name}', skipping.")
        return
    
    with open(f"{dest_path}/{item.name}", "wb") as fp:
        fp.write(obj)
    lock.acquire()
    _current_count += 1
    console.succeed(
        f"{_current_count}/{_adv_txt_count}) Resource '{item.name}' has been successfully renamed."
    )
    lock.release()


def download_resource(database: octop.Database):
    global _adv_txt_count
    global _current_count

    urlFormat = database.urlFormat

    adv_txt_list = [item for item in database.resourceList if str(item.name).endswith(".txt")]
    _adv_txt_count = len(adv_txt_list)

    Path(TXT_PATH).mkdir(parents=True, exist_ok=True)

    executor = ThreadPoolExecutor(max_workers=20)

    _current_count = 0
    adv_txt_tasks = [
        executor.submit(one_task, item, urlFormat, TXT_PATH)
        for item in adv_txt_list
    ]
    wait(adv_txt_tasks, return_when=ALL_COMPLETED)
    console.succeed("All resource tasks has been successfully processed.")
