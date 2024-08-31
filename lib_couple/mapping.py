from modules.prompt_parser import SdConditioning

from base64 import b64decode as decode
from io import BytesIO as bIO
from PIL import Image
import numpy as np
import torch


def empty_tensor(H: int, W: int):
    return torch.zeros((H, W)).unsqueeze(0)


def basic_mapping(
    sd_model,
    couples: list,
    WIDTH: int,
    HEIGHT: int,
    LINE_COUNT: int,
    IS_HORIZONTAL: bool,
    background: str,
    TILE_SIZE: int,
    TILE_WEIGHT: float,
    BG_WEIGHT: float,
):

    ARGs: dict = {}
    IS_SDXL: bool = sd_model.is_sdxl

    for tile in range(LINE_COUNT):
        mask = torch.zeros((HEIGHT, WIDTH))

        # ===== Cond =====
        texts = SdConditioning([couples[tile]], False, WIDTH, HEIGHT, None)
        cond = sd_model.get_learned_conditioning(texts)
        pos_cond = [[cond["crossattn"]]] if IS_SDXL else [[cond]]
        # ===== Cond =====

        # ===== Mask =====
        if background == "First Line":
            if tile == 0:
                mask = torch.ones((HEIGHT, WIDTH)) * BG_WEIGHT
            else:
                if IS_HORIZONTAL:
                    mask[:, (tile - 1) * TILE_SIZE : tile * TILE_SIZE] = TILE_WEIGHT
                else:
                    mask[(tile - 1) * TILE_SIZE : tile * TILE_SIZE, :] = TILE_WEIGHT
        else:
            if IS_HORIZONTAL:
                mask[:, tile * TILE_SIZE : (tile + 1) * TILE_SIZE] = TILE_WEIGHT
            else:
                mask[tile * TILE_SIZE : (tile + 1) * TILE_SIZE, :] = TILE_WEIGHT
        # ===== Mask =====

        ARGs[f"cond_{tile + 1}"] = pos_cond
        ARGs[f"mask_{tile + 1}"] = mask.unsqueeze(0)

    if background == "Last Line":
        ARGs[f"mask_{LINE_COUNT}"] = (
            torch.ones((HEIGHT, WIDTH)) * BG_WEIGHT
        ).unsqueeze(0)

    return ARGs


def advanced_mapping(sd_model, couples: list, WIDTH: int, HEIGHT: int, mapping: list):
    assert len(couples) == len(mapping)

    ARGs: dict = {}
    IS_SDXL: bool = sd_model.is_sdxl

    for tile_index, (x1, x2, y1, y2, w) in enumerate(mapping):
        mask = torch.zeros((HEIGHT, WIDTH))

        x_from = int(WIDTH * x1)
        x_to = int(WIDTH * x2)
        y_from = int(HEIGHT * y1)
        y_to = int(HEIGHT * y2)

        # ===== Cond =====
        texts = SdConditioning([couples[tile_index]], False, WIDTH, HEIGHT, None)
        cond = sd_model.get_learned_conditioning(texts)
        pos_cond = [[cond["crossattn"]]] if IS_SDXL else [[cond]]
        # ===== Cond =====

        # ===== Mask =====
        mask[y_from:y_to, x_from:x_to] = w
        # ===== Mask =====

        ARGs[f"cond_{tile_index + 1}"] = pos_cond
        ARGs[f"mask_{tile_index + 1}"] = mask.unsqueeze(0)

    return ARGs


@torch.inference_mode()
def b64image2tensor(img: str | Image.Image, WIDTH: int, HEIGHT: int) -> torch.Tensor:
    if isinstance(img, str):
        image_bytes = decode(img)
        image = Image.open(bIO(image_bytes)).convert("L")
    else:
        image = img.convert("L")

    if image.width != WIDTH or image.height != HEIGHT:
        image = image.resize((WIDTH, HEIGHT), resample=Image.Resampling.NEAREST)

    image = np.array(image).astype(np.float32) / 255.0
    image = torch.from_numpy(image).unsqueeze(0)

    return image


def mask_mapping(
    sd_model,
    couples: list,
    WIDTH: int,
    HEIGHT: int,
    LINE_COUNT: int,
    mapping: list[dict],
    background: str,
    BG_WEIGHT: float,
):

    mapping = [
        b64image2tensor(m["mask"], WIDTH, HEIGHT) * float(m["weight"]) for m in mapping
    ]

    ARGs: dict = {}
    IS_SDXL: bool = sd_model.is_sdxl

    for layer in range(LINE_COUNT):
        mask = torch.zeros((HEIGHT, WIDTH))

        # ===== Cond =====
        texts = SdConditioning([couples[layer]], False, WIDTH, HEIGHT, None)
        cond = sd_model.get_learned_conditioning(texts)
        pos_cond = [[cond["crossattn"]]] if IS_SDXL else [[cond]]
        # ===== Cond =====

        # ===== Mask =====
        if background == "First Line":
            mask = (
                mapping[layer - 1]
                if layer > 0
                else torch.ones((HEIGHT, WIDTH)) * BG_WEIGHT
            )
        elif background == "Last Line":
            mask = (
                mapping[layer]
                if layer < LINE_COUNT - 1
                else torch.ones((HEIGHT, WIDTH)) * BG_WEIGHT
            )
        else:
            mask = mapping[layer]
        # ===== Mask =====

        ARGs[f"cond_{layer + 1}"] = pos_cond
        ARGs[f"mask_{layer + 1}"] = mask.unsqueeze(0) if mask.dim() == 2 else mask

    return ARGs
