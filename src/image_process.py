import UnityPy
from PIL import Image
from pathlib import Path
import proto.octodb_pb2 as octop
import src.rich_console as console


def unpack_to_image(asset_bytes: bytes, dest_path: str):
    env = UnityPy.load(asset_bytes)
    for obj in env.objects:
        if obj.type.name in ["Texture2D", "Sprite"]:
            try:
                store_path = f"{Path(dest_path).parent}/image/{obj.type.name}"
                Path(store_path).mkdir(parents=True, exist_ok=True)
                data = obj.read()
                img = data.image
                img.save(f"{store_path}/{data.name}.png")
            except:
                console.error(f"Failed to convert '{data.name}' to image.")


def resize_image(input: str, output: str, size: tuple = (0, 0)):
    try:
        original_image = Image.open(input)
    except FileNotFoundError:
        console.error(f"No such file or directory: '{input}'")
        return
    resized_image = original_image.resize(size)
    resized_image.save(output)
    console.succeed(f"Img '{input}' has been successfully scaled")


def image_scale(database: octop.Database, source: str, dest: str):
    Path(dest).mkdir(exist_ok=True)
    for item in database.assetBundleList:
        name = item.name
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
        input_path = f"{source}/Texture2D/{name}.png"
        resize_image(input=input_path, output=f"{dest}/{name}.png", size=size)
