"""
Credit: logtd
https://github.com/logtd/ComfyUI-Fluxtapoz/blob/main/nodes/regional_cond_nodes.py
Modified by. Haoming02 to work with Forge
"""

import torch

DEFAULT_REGIONAL_ATTN = {
    "double": [i for i in range(1, 19, 2)],
    "single": [i for i in range(1, 38, 2)],
}


class RegionalMask(torch.nn.Module):
    def __init__(self, mask: torch.Tensor):
        super().__init__()
        self.register_buffer("mask", mask)

    def __call__(self, *args, **kwargs):
        return self.mask


class RegionalConditioning(torch.nn.Module):
    def __init__(self, region_cond: torch.Tensor):
        super().__init__()
        self.register_buffer("region_cond", region_cond)

    def __call__(self, *args, **kwargs):
        return self.region_cond


def ConvertConds(args: dict) -> list[dict]:
    count = len(args.keys()) // 2
    regions = []

    for i in range(count):
        regions.append(
            {
                "mask": 1.0 - args[f"mask_{i + 1}"],
                "cond": args[f"cond_{i + 1}"],
            }
        )

    return regions


def ApplyRegionalConds(model, region_conds: list[dict], width: int, height: int, attn_override=DEFAULT_REGIONAL_ATTN):
    w = width // 16
    h = height // 16

    img_len = h * w

    regional_conditioning = torch.cat([region_cond["cond"] for region_cond in region_conds], dim=1)
    text_len = 256 + regional_conditioning.shape[1]

    regional_mask = torch.zeros((text_len + img_len, text_len + img_len), dtype=torch.bool)

    self_attend_masks = torch.zeros((img_len, img_len), dtype=torch.bool)
    union_masks = torch.zeros((img_len, img_len), dtype=torch.bool)

    region_conds = [
        {
            "mask": torch.ones((1, h, w), dtype=torch.float16),
            "cond": torch.ones((1, 256, 4096), dtype=torch.float16),
        },
        *region_conds,
    ]

    current_seq_len = 0
    for region_cond_dict in region_conds:
        region_cond = region_cond_dict["cond"]
        region_mask = 1 - region_cond_dict["mask"][0]
        region_mask = torch.nn.functional.interpolate(region_mask[None, None, :, :], (h, w), mode="nearest-exact").flatten().unsqueeze(1).repeat(1, region_cond.size(1))
        next_seq_len = current_seq_len + region_cond.shape[1]

        regional_mask[current_seq_len:next_seq_len, current_seq_len:next_seq_len] = True

        regional_mask[current_seq_len:next_seq_len, text_len:] = region_mask.transpose(-1, -2)

        regional_mask[text_len:, current_seq_len:next_seq_len] = region_mask

        img_size_masks = region_mask[:, :1].repeat(1, img_len)
        img_size_masks_transpose = img_size_masks.transpose(-1, -2)
        self_attend_masks = torch.logical_or(
            self_attend_masks,
            torch.logical_and(img_size_masks, img_size_masks_transpose),
        )

        union_masks = torch.logical_or(union_masks, torch.logical_or(img_size_masks, img_size_masks_transpose))

        current_seq_len = next_seq_len

    background_masks = torch.logical_not(union_masks)
    background_and_self_attend_masks = torch.logical_or(background_masks, self_attend_masks)
    regional_mask[text_len:, text_len:] = background_and_self_attend_masks

    regional_mask = RegionalMask(regional_mask)
    regional_conditioning = RegionalConditioning(regional_conditioning)

    model.set_model_patch(regional_conditioning, "regional_conditioning")

    for block_idx in attn_override["double"]:
        model.set_model_patch_replace(regional_mask, "double", "mask_fn", int(block_idx))

    for block_idx in attn_override["single"]:
        model.set_model_patch_replace(regional_mask, "single", "mask_fn", int(block_idx))

    return model
