import UnityPy
from PIL import Image
from pathlib import Path
from typing import Optional
import proto.octodb_pb2 as octop
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


def resize_image(input: str, output: str, size: Optional[tuple] = None):
    try:
        original_image = Image.open(input)
    except FileNotFoundError:
        console.error(f"No such file or directory: '{input}'")
        return
    with original_image:
        if size is None:
            width, height = original_image.size
            # Restore the display ratio without changing the texture's orientation.
            if width == height:
                return
            size = (2560, 1440) if width > height else (1440, 2560)
        original_image.resize(size, Image.Resampling.LANCZOS).save(output)
    console.succeed(f"Img '{input}' has been successfully scaled")


def image_scale(database: octop.Database, source: str, dest: str):
    Path(dest).mkdir(exist_ok=True)
    for item in database.assetBundleList:
        name = item.name
        if ((name.startswith("img_general_cidol-") and name.endswith("-full"))
                or (name.startswith("img_general_csprt-") and name.endswith("_full"))
                or name.startswith("img_adv_still_")):
            size = None
        elif name.startswith("img_general_comic_"):
            size = (1024, 768)
        else:
            continue
        input_path = f"{source}/Texture2D/{name}.png"
        resize_image(input=input_path, output=f"{dest}/{name}.png", size=size)
