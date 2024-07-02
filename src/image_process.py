import json
import UnityPy
from PIL import Image
from pathlib import Path
import src.rich_console as console


def unpack_to_image(asset_bytes: bytes, dest_path: str):
    env = UnityPy.load(asset_bytes)
    for obj in env.objects:
        if obj.type.name == "Texture2D":
            data = obj.read()
            if data.name.startswith("env") or data.name.startswith("img"):
                try:
                    store_path = f"{Path(dest_path).parent}/image/Texture2D"
                    Path(store_path).mkdir(parents=True, exist_ok=True)
                    img = data.image
                    img.save(f"{store_path}/{data.name}.png")
                except:
                    console.error(f"Failed to convert '{data.name}' to image.")


def resize_image(inputs: str, output: str, size: tuple = (0, 0)):
    try:
        original_image = Image.open(inputs)
    except FileNotFoundError:
        console.error(f"No such file or directory: '{inputs}'")
        return
    resized_image = original_image.resize(size)
    resized_image.save(output)
    console.succeed(f"Img '{inputs}' has been successfully scaled")


def image_scale(source: str, dest: str):
    Path(dest).mkdir(exist_ok=True)
    with open("cache/OctoDiff.json") as fp:
        update_database_dict = json.load(fp)
    for asset in update_database_dict["assetBundleList"]:
        name = asset["name"]
        if (name.startswith("img_general_cidol-") and name.endswith("-full")) or name.startswith(
            "img_adv_still_"
        ):
            size = (1440, 2560)
        elif name.startswith("img_general_csprt-") and name.endswith("_full"):
            size = (2560, 1440)
        elif name.startswith("img_general_comic_"):
            size = (1024, 768)
        else:
            continue
        file = f"{source}/Texture2D/{name}.png"
        resize_image(inputs=file, output=f"{dest}/{name}.png", size=size)
