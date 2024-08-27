from modules.prompt_parser import SdConditioning

from base64 import b64decode as decode
from io import BytesIO as bIO
from PIL import Image
import numpy as np
import torch
from typing import List, Union, Tuple


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
    IS_SDXL: bool = hasattr(
        sd_model.forge_objects.unet.model.diffusion_model, "label_emb"
    )

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


def safe_eval(formula: str, X: torch.Tensor, Y: torch.Tensor) -> torch.Tensor:
    safe_dict = {
        "sin": torch.sin,
        "cos": torch.cos,
        "tan": torch.tan,
        "exp": torch.exp,
        "log": torch.log,
        "sqrt": torch.sqrt,
        "abs": torch.abs,
        "max": torch.max,
        "min": torch.min,
    }
    return eval(formula, {"__builtins__": None}, {**safe_dict, "x": X, "y": Y})


def create_formula_mask(formula: str, width: int, height: int, x1: float, x2: float, y1: float, y2: float) -> torch.Tensor:
    try:
        x = torch.linspace(0, 1, width)
        y = torch.linspace(0, 1, height)
        X, Y = torch.meshgrid(x, y, indexing='xy')

        mask = safe_eval(formula, X, Y)

        full_mask = torch.zeros((height, width))
        x_from, x_to = int(width * x1), int(width * x2)
        y_from, y_to = int(height * y1), int(height * y2)
        full_mask[y_from:y_to, x_from:x_to] = mask[y_from:y_to, x_from:x_to]

        return full_mask
    except Exception as e:
        print(f"Error evaluating formula '{formula}': {str(e)}")
        return torch.zeros((height, width))


def advanced_mapping(sd_model, couples: List[str], WIDTH: int, HEIGHT: int, mapping: List[List[Union[float, str]]]) -> dict:
    assert len(couples) == len(mapping), "Number of couples must match number of mappings"

    ARGs: dict = {}
    IS_SDXL: bool = hasattr(sd_model.forge_objects.unet.model.diffusion_model, "label_emb")

    for tile_index, mapping_entry in enumerate(mapping):
        if len(mapping_entry) != 5:
            raise ValueError(f"Invalid mapping entry for tile {tile_index}. Expected 5 values, got {len(mapping_entry)}")

        x1, x2, y1, y2, w = mapping_entry

        try:
            x1, x2, y1, y2 = map(float, (x1, x2, y1, y2))
        except ValueError as e:
            raise ValueError(f"Invalid coordinate values for tile {tile_index}: {x1}, {x2}, {y1}, {y2}. Error: {str(e)}")

        if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
            raise ValueError(f"Invalid coordinate range for tile {tile_index}: {x1}, {x2}, {y1}, {y2}. Must be 0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1")

        # ===== Cond =====
        texts = SdConditioning([couples[tile_index]], False, WIDTH, HEIGHT, None)
        cond = sd_model.get_learned_conditioning(texts)
        pos_cond = [[cond["crossattn"]]] if IS_SDXL else [[cond]]
        # ===== Cond =====

        # ===== Mask =====
        if isinstance(w, str) and w.startswith('='):
            mask = create_formula_mask(w[1:], WIDTH, HEIGHT, x1, x2, y1, y2)
        else:
            try:
                w_float = float(w)
            except ValueError:
                raise ValueError(f"Weight must be a numeric value or a formula string starting with =. Got: {w}")

            mask = torch.zeros((HEIGHT, WIDTH))
            x_from, x_to = int(WIDTH * x1), int(WIDTH * x2)
            y_from, y_to = int(HEIGHT * y1), int(HEIGHT * y2)
            mask[y_from:y_to, x_from:x_to] = w_float
        # ===== Mask =====

        ARGs[f"cond_{tile_index + 1}"] = pos_cond
        ARGs[f"mask_{tile_index + 1}"] = mask.unsqueeze(0)

    return ARGs


@torch.inference_mode()
def b64image2tensor(img: str, WIDTH: int, HEIGHT: int) -> torch.Tensor:
    image_bytes = decode(img)
    image = Image.open(bIO(image_bytes)).convert("L")

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
    IS_SDXL: bool = hasattr(
        sd_model.forge_objects.unet.model.diffusion_model, "label_emb"
    )

    for layer in range(LINE_COUNT):
        mask = torch.zeros((HEIGHT, WIDTH))

        # ===== Cond =====
        texts = SdConditioning([couples[layer]], False, WIDTH, HEIGHT, None)
        cond = sd_model.get_learned_conditioning(texts)
        pos_cond = [[cond["crossattn"]]] if IS_SDXL else [[cond]]
        # ===== Cond =====

        # ===== Mask =====
        if background == "First Line":
            if layer == 0:
                mask = torch.ones((HEIGHT, WIDTH)) * BG_WEIGHT
            else:
                mask = mapping[layer - 1]
        else:
            mask = mapping[layer]
        # ===== Mask =====

        ARGs[f"cond_{layer + 1}"] = pos_cond
        ARGs[f"mask_{layer + 1}"] = mask.unsqueeze(0) if mask.dim() == 2 else mask

    if background == "Last Line":
        ARGs[f"mask_{LINE_COUNT}"] = (
            torch.ones((HEIGHT, WIDTH)) * BG_WEIGHT
        ).unsqueeze(0)

    return ARGs
