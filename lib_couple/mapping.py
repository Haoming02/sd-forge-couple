from base64 import b64decode as decode
from io import BytesIO as bIO

import numpy as np
import torch
from modules.prompt_parser import SdConditioning
from PIL import Image


def empty_tensor(h: int, w: int):
    return torch.zeros((h, w)).unsqueeze(0)


def basic_mapping(
    sd_model,
    couples: list,
    width: int,
    height: int,
    line_count: int,
    is_horizontal: bool,
    background: str,
    tile_size: int,
    tile_weight: float,
    bg_weight: float,
) -> dict:
    fc_args: dict = {}

    for tile in range(line_count):
        # ===== Cond =====
        texts = SdConditioning([couples[tile]], False, width, height, None)
        cond = sd_model.get_learned_conditioning(texts)
        pos_cond = [[cond["crossattn"]]] if sd_model.is_sdxl else [[cond]]
        fc_args[f"cond_{tile + 1}"] = pos_cond
        # ===== Cond =====

        # ===== Mask =====
        mask = torch.zeros((height, width))

        if background == "First Line":
            if tile == 0:
                mask = torch.ones((height, width)) * bg_weight
            else:
                if is_horizontal:
                    mask[:, (tile - 1) * tile_size : tile * tile_size] = tile_weight
                else:
                    mask[(tile - 1) * tile_size : tile * tile_size, :] = tile_weight
        else:
            if is_horizontal:
                mask[:, tile * tile_size : (tile + 1) * tile_size] = tile_weight
            else:
                mask[tile * tile_size : (tile + 1) * tile_size, :] = tile_weight

        fc_args[f"mask_{tile + 1}"] = mask.unsqueeze(0)
        # ===== Mask =====

    if background == "Last Line":
        fc_args[f"mask_{line_count}"] = (
            torch.ones((height, width)) * bg_weight
        ).unsqueeze(0)

    return fc_args


def advanced_mapping(
    sd_model, couples: list, width: int, height: int, mapping: list
) -> dict:
    fc_args: dict = {}
    assert len(couples) == len(mapping)

    for tile_index, (x1, x2, y1, y2, w) in enumerate(mapping):
        # ===== Cond =====
        texts = SdConditioning([couples[tile_index]], False, width, height, None)
        cond = sd_model.get_learned_conditioning(texts)
        pos_cond = [[cond["crossattn"]]] if sd_model.is_sdxl else [[cond]]
        fc_args[f"cond_{tile_index + 1}"] = pos_cond
        # ===== Cond =====

        # ===== Mask =====
        x_from = int(width * x1)
        x_to = int(width * x2)
        y_from = int(height * y1)
        y_to = int(height * y2)

        mask = torch.zeros((height, width))
        mask[y_from:y_to, x_from:x_to] = w
        fc_args[f"mask_{tile_index + 1}"] = mask.unsqueeze(0)
        # ===== Mask =====

    return fc_args


@torch.no_grad()
def b64image2tensor(img: str | Image.Image, width: int, height: int) -> torch.Tensor:
    if isinstance(img, str):
        image_bytes = decode(img)
        image = Image.open(bIO(image_bytes)).convert("L")
    else:
        image = img.convert("L")

    if image.size != (width, height):
        image = image.resize((width, height), resample=Image.Resampling.NEAREST)

    image = np.asarray(image, dtype=np.float32) / 255.0
    image = torch.from_numpy(image).unsqueeze(0)

    return image


def mask_mapping(
    sd_model,
    couples: list,
    width: int,
    height: int,
    line_count: int,
    mapping: list[dict],
    background: str,
    bg_weight: float,
) -> dict:
    fc_args: dict = {}

    mapping: list[torch.Tensor] = [
        b64image2tensor(m["mask"], width, height) * float(m["weight"]) for m in mapping
    ]

    for layer in range(line_count):
        # ===== Cond =====
        texts = SdConditioning([couples[layer]], False, width, height, None)
        cond = sd_model.get_learned_conditioning(texts)
        pos_cond = [[cond["crossattn"]]] if sd_model.is_sdxl else [[cond]]
        fc_args[f"cond_{layer + 1}"] = pos_cond
        # ===== Cond =====

        # ===== Mask =====
        mask = torch.zeros((height, width))

        if background == "First Line":
            mask = (
                mapping[layer - 1]
                if layer > 0
                else torch.ones((height, width)) * bg_weight
            )
        elif background == "Last Line":
            mask = (
                mapping[layer]
                if layer < line_count - 1
                else torch.ones((height, width)) * bg_weight
            )
        else:
            mask = mapping[layer]

        fc_args[f"mask_{layer + 1}"] = mask.unsqueeze(0) if mask.dim() == 2 else mask
        # ===== Mask =====

    return fc_args
