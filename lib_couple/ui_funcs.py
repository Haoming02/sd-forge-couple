from json.decoder import JSONDecodeError
from PIL import Image, ImageDraw
from json import loads
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


def visualize_mapping(mode: str, res: str, mapping: list) -> Image:
    if mode != "Advanced":
        return gr.update()

    p_WIDTH, p_HEIGHT = [int(v) for v in res.split("x")]

    while p_WIDTH > 1024 or p_HEIGHT > 1024:
        p_WIDTH, p_HEIGHT = p_WIDTH // 2, p_HEIGHT // 2

    while p_WIDTH < 512 and p_HEIGHT < 512:
        p_WIDTH, p_HEIGHT = p_WIDTH * 2, p_HEIGHT * 2

    matt = Image.new("RGBA", (p_WIDTH, p_HEIGHT), (0, 0, 0, 64))

    if not (validate_mapping(mapping)):
        return matt

    line_width = int(max(min(p_WIDTH, p_HEIGHT) / 128, 4.0))

    draw = ImageDraw.Draw(matt)

    for tile_index, (x1, x2, y1, y2, w) in enumerate(mapping):
        color_index = tile_index % len(COLORS)

        x_from = int(p_WIDTH * x1)
        x_to = int(p_WIDTH * x2)
        y_from = int(p_HEIGHT * y1)
        y_to = int(p_HEIGHT * y2)

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
