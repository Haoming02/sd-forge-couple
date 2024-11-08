from json.decoder import JSONDecodeError
from PIL import Image, ImageDraw
from json import dumps, loads
import gradio as gr

DEFAULT_MAPPING = [[0.0, 0.5, 0.0, 1.0, 1.0], [0.5, 1.0, 0.0, 1.0, 1.0]]
COLORS = ("red", "orange", "yellow", "green", "blue", "indigo", "violet")


def validate_mapping(data: list) -> bool:
    for x1, x2, y1, y2, w in data:

        if not all(0.0 <= v <= 1.0 for v in (x1, x2, y1, y2)):
            print("\n[Couple] Region range must be between 0.0 and 1.0...\n")
            return False

        if x2 < x1 or y2 < y1:
            print('\n[Couple] "to" value must be larger than "from" value...\n')
            return False

    return True


def visualize_mapping(mode: str, res: str, mapping: list) -> Image.Image:
    if mode != "Advanced":
        return gr.update()

    p_width, p_height = [int(v) for v in res.split("x")]

    while p_width > 1024 or p_height > 1024:
        p_width, p_height = p_width // 2, p_height // 2

    while p_width < 512 and p_height < 512:
        p_width, p_height = p_width * 2, p_height * 2

    matt = Image.new("RGBA", (p_width, p_height), (0, 0, 0, 64))

    if not (validate_mapping(mapping)):
        return matt

    line_width = int(max(min(p_width, p_height) / 128, 4.0))

    draw = ImageDraw.Draw(matt)

    for tile_index, (x1, x2, y1, y2, w) in enumerate(mapping):
        color_index = tile_index % len(COLORS)

        x_from = int(p_width * x1)
        x_to = int(p_width * x2)
        y_from = int(p_height * y1)
        y_to = int(p_height * y2)

        draw.rectangle(
            ((x_from, y_from), (x_to, y_to)),
            outline=COLORS[color_index],
            width=line_width,
        )

    return matt


def on_entry(data: str) -> list:
    if not data.strip():
        return gr.update()

    if ":" in data:
        print("\n[Couple] Old infotext is no longer supported...\n")
        return DEFAULT_MAPPING

    try:
        return loads(data)
    except JSONDecodeError:
        print("\n[Couple] Something went wrong while parsing advanced mapping...\n")
        return DEFAULT_MAPPING


def on_pull(data: dict) -> str:
    if not data:
        return ""

    try:
        return dumps(data)
    except JSONDecodeError:
        print("\n[Couple] Something went wrong while parsing advanced mapping...\n")
        return ""
