from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scripts.forge_couple import ForgeCouple
    from PIL import Image

from lib_couple.logging import logger
from modules.upscaler import NEAREST
import numpy as np


SIZE = 1024  # image size used for overlap calculation


def _include(
    x: int,
    h: int,
    y: int,
    v: int,
    mappings: list["Image.Image"],
    threshold: float,
) -> list[int]:
    include: list[int] = []

    tile_width = SIZE // h
    tile_height = SIZE // v

    x1 = x * tile_width
    y1 = y * tile_height

    x2 = SIZE if x == h - 1 else (x + 1) * tile_width
    y2 = SIZE if y == v - 1 else (y + 1) * tile_height

    tile_mask = np.zeros((SIZE, SIZE), dtype=np.uint8)
    tile_mask[y1:y2, x1:x2] = 1

    for i, m in enumerate(mappings):
        m = m.resize((SIZE, SIZE), NEAREST)
        mask = np.asarray(m, dtype=np.uint8)

        overlap = np.sum((tile_mask == 1) & (mask == 1))
        total = np.sum((mask == 1))

        if (overlap / total) >= threshold:
            include.append(i)

    return include


def _process_replacements(replace: str) -> dict[str, str]:
    replacements = {}

    for line in replace.split("\n"):
        goal, sauce = line.split(":")
        tags = sauce.split(",")

        for tag in tags:
            replacements[tag.strip()] = goal.strip()

    return replacements


def calculate_tiles(self: "ForgeCouple", args: tuple) -> bool:
    self.tiles.clear()

    enable: bool = args[1]
    use_tile: bool = args[11]
    if not (enable and use_tile):
        return False

    mode: str = args[3]
    if mode != "Mask":
        logger.error("Tile Mode only supports Mask Regions currently...")
        return None

    tile_h = int(args[12])
    tile_v = int(args[13])

    if tile_h * tile_v == 1:
        logger.error("Invalid number of Tiles...")
        return None

    prompt: str = args[0].prompt
    self.after_extra_networks_activate(*args, prompts=[prompt])
    if not self.valid:
        return None

    prompts: list[str] = self.couples
    bg: str = None
    background: str = args[6]
    if background == "First Line":
        bg, *prompts = prompts
    if background == "Last Line":
        *prompts, bg = prompts

    mapping: list[dict] = self.get_mask()
    assert len(mapping) == len(prompts)

    mappings: list = [m["mask"] for m in mapping]
    tile_threshold: float = args[14]
    tile_replace: str = args[15]
    replacements = _process_replacements(tile_replace)

    for y in range(tile_v):
        for x in range(tile_h):
            _prompt = [bg] if bg else []

            idx = _include(x, tile_h, y, tile_v, mappings, tile_threshold)
            for i in idx:
                p = prompts[i]
                for k, v in replacements.items():
                    p = p.replace(k, v)
                _prompt.append(p)

            self.tiles.append("\n".join(_prompt))

    assert len(self.tiles) == tile_h * tile_v
    return True
