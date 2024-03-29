from modules.prompt_parser import SdConditioning
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
    IS_SDXL: bool = hasattr(
        sd_model.forge_objects.unet.model.diffusion_model, "label_emb"
    )

    for tile in range(LINE_COUNT):
        mask = torch.zeros((HEIGHT, WIDTH))
        pos_cond = None

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
