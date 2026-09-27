from json import dumps, loads
from json.decoder import JSONDecodeError
from typing import Final

import gradio as gr
from PIL import Image, ImageDraw

from lib_couple.logging import logger

DEFAULT_MAPPING: Final[list[list[float]]] = [
    [0.0, 0.5, 0.0, 1.0, 1.0],
    [0.5, 1.0, 0.0, 1.0, 1.0],
]

COLORS: Final[tuple[str]] = (
    "red",
    "orange",
    "yellow",
    "green",
    "blue",
    "indigo",
    "violet",
)


def validate_mapping(data: list, log: bool = False) -> bool:
    if not data:
        return False

    for row in data:
        # A row can arrive as None (e.g. JSON `null` from an unfinished UI row)
        if not isinstance(row, (list, tuple)) or len(row) < 5:
            if log:
                logger.error("Each mapping row must be [x1, x2, y1, y2, w]...")
            return False

        x1, x2, y1, y2, w = row[:5]
        for v in (x1, x2, y1, y2, w):
            if not (isinstance(v, float) or isinstance(v, int)):
                if log:
                    logger.error('Mappings must be "float"...')
                return False

        if not all(0.0 <= v <= 1.0 for v in (x1, x2, y1, y2)):
            if log:
                logger.error("Region range must be between 0.0 and 1.0...")
            return False

        if x2 < x1 or y2 < y1:
            if log:
                logger.error('"to" value must be larger than "from" value...')
            return False

    return True


def visualize_mapping(mode: str, res: str, mapping: list) -> Image.Image:
    if mode != "Advanced":
        return gr.skip()

    p_width, p_height = [int(v) for v in res.split("x")]

    while p_width * p_height > 1024 * 1024:
        p_width, p_height = p_width // 2, p_height // 2

    while p_width * p_height < 512 * 512:
        p_width, p_height = p_width * 2, p_height * 2

    matt = Image.new("RGBA", (p_width, p_height), (0, 0, 0, 64))

    if not (validate_mapping(mapping)):
        return matt

    line_width = int(max(min(p_width, p_height) / 128, 4.0))

    draw = ImageDraw.Draw(matt)

    for tile_index, (x1, x2, y1, y2, w) in enumerate(mapping):
        x_from = int(p_width * x1)
        x_to = int(p_width * x2)
        y_from = int(p_height * y1)
        y_to = int(p_height * y2)

        color_index = tile_index % 7
        draw.rectangle(
            ((x_from, y_from), (x_to, y_to)),
            outline=COLORS[color_index],
            width=line_width,
        )

    return matt


def on_entry(data: str) -> list[list]:
    if not data or not data.strip():
        return gr.skip()

    try:
        result = loads(data)
    except JSONDecodeError:
        logger.error("Something went wrong while parsing advanced mapping...")
        return DEFAULT_MAPPING

    # `loads("null")` → None; also reject non-list payloads
    if not isinstance(result, list):
        logger.error("Advanced mapping must be a list of rows...")
        return DEFAULT_MAPPING

    return result


def on_pull(data: dict) -> str:
    if not data:
        return ""

    try:
        return dumps(data)
    except (TypeError, ValueError):
        logger.error("Something went wrong while parsing advanced mapping...")
        return ""
