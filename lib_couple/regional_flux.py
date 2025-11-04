"""
Credit: logtd
https://github.com/logtd/ComfyUI-Fluxtapoz/blob/main/nodes/regional_cond_nodes.py

Modified by. Haoming02 to work with Forge
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.patcher.unet import UnetPatcher

import torch
from lib_flux.layers import inject_blocks
from lib_flux.model import inject_model

ATTN_BLOCKS: dict[str, tuple[int]] = {
    "double": tuple((int(i) for i in range(19))),
    "single": tuple((int(i) for i in range(38))),
}


class RegionalMask(torch.nn.Module):
    def __init__(self, mask: torch.Tensor) -> None:
        super().__init__()
        self.register_buffer("mask", mask)

    def __call__(self, *args, **kwargs):
        return self.mask


class RegionalConditioning(torch.nn.Module):
    def __init__(self, region_cond: torch.Tensor) -> None:
        super().__init__()
        self.register_buffer("region_cond", region_cond)

    def __call__(self, *args, **kwargs):
        return self.region_cond


def convert_conds(args: dict) -> list[dict]:
    count = len(args.keys()) // 2
    regions = []

    for i in range(count):
        regions.append(
            {
                "mask": args[f"mask_{i + 1}"],
                "cond": args[f"cond_{i + 1}"],
            }
        )

    return regions


@torch.inference_mode()
def patch_flux(model: "UnetPatcher", region_conds: list[dict], height: int, width: int):
    model = model.clone()

    h = height // 16
    w = width // 16
    img_len = h * w

    regional_conditioning = torch.cat(
        [region_cond["cond"] for region_cond in region_conds],
        dim=1,
    )

    text_len = 256 + regional_conditioning.shape[1]

    regional_mask = torch.zeros(
        (text_len + img_len, text_len + img_len),
        dtype=torch.bool,
    )

    self_attend_masks = torch.zeros((img_len, img_len), dtype=torch.bool)
    union_masks = torch.zeros((img_len, img_len), dtype=torch.bool)

    region_conds = [
        {
            "mask": torch.zeros((1, h, w), dtype=torch.float16),
            "cond": torch.ones((1, 256, 4096), dtype=torch.float16),
        },
        *region_conds,
    ]

    current_seq_len = 0
    for region_cond_dict in region_conds:
        region_cond = region_cond_dict["cond"]
        region_mask = region_cond_dict["mask"][0]
        region_mask = (
            torch.nn.functional.interpolate(
                region_mask[None, None, :, :], (h, w), mode="nearest-exact"
            )
            .flatten()
            .unsqueeze(1)
            .repeat(1, region_cond.size(1))
        )

        next_seq_len = current_seq_len + region_cond.shape[1]

        # txt attends to itself
        regional_mask[current_seq_len:next_seq_len, current_seq_len:next_seq_len] = True

        # txt attends to corresponding regional img
        t = region_mask.transpose(-1, -2)
        regional_mask[current_seq_len:next_seq_len, text_len:] = t

        # regional img attends to corresponding txt
        regional_mask[text_len:, current_seq_len:next_seq_len] = region_mask

        # regional img attends to corresponding regional img
        img_size_masks = region_mask[:, :1].repeat(1, img_len)
        img_size_masks_transpose = img_size_masks.transpose(-1, -2)

        self_attend_masks = torch.logical_or(
            self_attend_masks,
            torch.logical_and(img_size_masks, img_size_masks_transpose),
        )

        # update union
        union_masks = torch.logical_or(
            union_masks,
            torch.logical_or(img_size_masks, img_size_masks_transpose),
        )

        current_seq_len = next_seq_len

    background_masks = torch.logical_not(union_masks)
    regional_mask[text_len:, text_len:] = torch.logical_or(
        background_masks,
        self_attend_masks,
    )

    regional_mask = RegionalMask(regional_mask)
    regional_conditioning = RegionalConditioning(regional_conditioning)

    model.set_model_patch(regional_conditioning, "regional_conditioning")

    for block_idx in ATTN_BLOCKS["double"]:
        model.set_model_patch_replace(regional_mask, "double", "mask_fn", block_idx)

    for block_idx in ATTN_BLOCKS["single"]:
        model.set_model_patch_replace(regional_mask, "single", "mask_fn", block_idx)

    inject_model(model.model.diffusion_model)
    inject_blocks(model.model.diffusion_model)

    return model
