from modules.prompt_parser import SdConditioning
from scripts.couple_ui import parse_mapping
import torch


def empty_tensor(H: int, W: int):
    return torch.zeros((H, W)).unsqueeze(0)


def advanced_mapping(sd_model, couples: list, WIDTH: int, HEIGHT: int, mapping: list):
    data = parse_mapping(mapping)
    assert len(couples) == len(data)

    ARGs: dict = {}
    IS_SDXL: bool = hasattr(
        sd_model.forge_objects.unet.model.diffusion_model, "label_emb"
    )

    for tile_index in range(len(data)):
        mask = torch.zeros((HEIGHT, WIDTH))

        (X, Y, W) = data[tile_index]
        x_from = int(WIDTH * X[0])
        x_to = int(WIDTH * X[1])
        y_from = int(HEIGHT * Y[0])
        y_to = int(HEIGHT * Y[1])
        weight = W

        # ===== Cond =====
        texts = SdConditioning([couples[tile_index]], False, WIDTH, HEIGHT, None)
        cond = sd_model.get_learned_conditioning(texts)
        pos_cond = [[cond["crossattn"]]] if IS_SDXL else [[cond]]
        # ===== Cond =====

        # ===== Mask =====
        mask[y_from:y_to, x_from:x_to] = weight
        # ===== Mask =====

        ARGs[f"cond_{tile_index + 1}"] = pos_cond
        ARGs[f"mask_{tile_index + 1}"] = mask.unsqueeze(0)

    return ARGs


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
