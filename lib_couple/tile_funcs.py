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
    mappings: list[np.ndarray],
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

    for i, mask in enumerate(mappings):
        overlap = np.sum((tile_mask == 1) & (mask == 1))
        total = np.sum((mask == 1))

        if (overlap / total) >= threshold:
            include.append(i)

    return include


def _prepare_mappings_basic(is_vertical: bool, count: int) -> list[np.ndarray]:
    mappings = []

    for i in range(count):
        mask = np.zeros((SIZE, SIZE), dtype=np.uint8)

        a = int(SIZE * (i / count))
        b = int(SIZE * ((i + 1) / count))

        if is_vertical:
            mask[a:b, 0:SIZE] = 1
        else:
            mask[0:SIZE, a:b] = 1

        mappings.append(mask)

    return mappings


def _prepare_mappings_adv(mapping: list[list[float]]) -> list[np.ndarray]:
    mappings = []

    for x1, x2, y1, y2, _ in mapping:
        x1 = int(x1 * SIZE)
        x2 = int(x2 * SIZE)
        y1 = int(y1 * SIZE)
        y2 = int(y2 * SIZE)

        mask = np.zeros((SIZE, SIZE), dtype=np.uint8)
        mask[y1:y2, x1:x2] = 1

        mappings.append(mask)

    return mappings


def _prepare_mappings_mask(mapping: list[dict[str, "Image.Image"]]) -> list[np.ndarray]:
    mappings = []

    for m in mapping:
        m = m["mask"].resize((SIZE, SIZE), NEAREST)
        mappings.append(np.asarray(m, dtype=np.uint8))

    return mappings


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

    tile_h = int(args[12])
    tile_v = int(args[13])

    if tile_h * tile_v < 2:
        logger.error(f"Invalid Tile Count: {tile_h * tile_v}...")
        return None

    prompt: str = args[0].prompt
    self.after_extra_networks_activate(*args, prompts=[prompt])
    if not self.valid:
        return None

    mode: str = args[3]
    prompts: list[str] = self.couples
    bg: str = None

    if mode != "Advanced":
        background: str = args[6]
        if background == "First Line":
            bg, *prompts = prompts
        if background == "Last Line":
            *prompts, bg = prompts

    if mode == "Basic":
        direction: str = args[5]
        mappings: list = _prepare_mappings_basic(direction == "Vertical", len(prompts))

    if mode == "Advanced":
        mapping: list[list[float]] = args[8]
        assert len(mapping) == len(prompts)
        mappings: list = _prepare_mappings_adv(mapping)

    if mode == "Mask":
        mapping: list[dict] = self.get_mask()
        assert len(mapping) == len(prompts)
        mappings: list = _prepare_mappings_mask(mapping)

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
