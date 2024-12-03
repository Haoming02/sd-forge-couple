"""
Credit: logtd
https://github.com/logtd/ComfyUI-Fluxtapoz/blob/main/nodes/regional_cond_nodes.py

Modified by. Haoming02 to work with Forge
"""

from lib_flux.inject import ConfigureModifiedFluxNode
import torch


DEFAULT_REGIONAL_ATTN = {
    "double": [i for i in range(1, 19, 2)],
    "single": [i for i in range(1, 38, 2)],
}

# https://github.com/logtd/ComfyUI-Fluxtapoz/blob/main/example_workflows/example_flux_regional.json
OPTIMIZED_REGIONAL_ATTN = {
    "double": [0, 2, 4, 6, 8, 10, 12, 14],
    "single": [1, 3, 5, 7, 9, 11, 13, 15, 18, 20, 22],
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


class FluxRegionalConds:

    @staticmethod
    def convert(args: dict[str, torch.Tensor]) -> list[dict]:
        count = len(args.keys()) // 2
        regions = []

        for i in range(count):
            regions.append(
                {
                    "mask": args[f"mask_{i + 1}"],
                    "cond": args[f"cond_{i + 1}"],
                }
            )

        return regions[::-1]

    @staticmethod
    @torch.inference_mode()
    def patch(model, regions: list[dict[str, torch.Tensor]], height: int, width: int):
        new_model = ConfigureModifiedFluxNode.apply(model.clone())

        h = int((height / 8) / 2)
        w = int((width / 8) / 2)

        img_len = h * w

        regional_conditioning = torch.cat(
            [region_cond["cond"] for region_cond in regions], dim=1
        )

        text_len = 256 + regional_conditioning.shape[1]

        regional_mask = torch.zeros(
            (text_len + img_len, text_len + img_len), dtype=torch.bool
        )

        self_attend_masks = torch.zeros((img_len, img_len), dtype=torch.bool)
        union_masks = torch.zeros((img_len, img_len), dtype=torch.bool)

        regions = [
            {
                "mask": torch.ones((1, h, w), dtype=torch.float16),
                "cond": torch.ones((1, 256, 4096), dtype=torch.float16),
            },
            *regions,
        ]

        current_seq_len = 0
        for region_cond_dict in regions:
            region_cond = region_cond_dict["cond"]
            region_mask = 1 - region_cond_dict["mask"][0]
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
            regional_mask[
                current_seq_len:next_seq_len, current_seq_len:next_seq_len
            ] = True

            # txt attends to corresponding regional img
            regional_mask[current_seq_len:next_seq_len, text_len:] = (
                region_mask.transpose(-1, -2)
            )

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
                union_masks, torch.logical_or(img_size_masks, img_size_masks_transpose)
            )

            current_seq_len = next_seq_len

        background_masks = torch.logical_not(union_masks)
        background_and_self_attend_masks = torch.logical_or(
            background_masks, self_attend_masks
        )
        regional_mask[text_len:, text_len:] = background_and_self_attend_masks

        # Patch
        regional_conditioning = RegionalConditioning(regional_conditioning)
        new_model.set_model_patch(regional_conditioning, "regional_conditioning")

        regional_mask = RegionalMask(regional_mask)
        for block_idx in OPTIMIZED_REGIONAL_ATTN["double"]:
            new_model.set_model_patch_replace(
                regional_mask, f"double", "mask_fn", int(block_idx)
            )
        for block_idx in OPTIMIZED_REGIONAL_ATTN["single"]:
            new_model.set_model_patch_replace(
                regional_mask, f"single", "mask_fn", int(block_idx)
            )

        return new_model
