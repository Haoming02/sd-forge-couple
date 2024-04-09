from typing import Any, NamedTuple

import torch
from torch import Tensor
from modules.prompt_parser import SdConditioning

class MaskedConditioning(NamedTuple):
    conditioning: Tensor
    mask: Tensor

class Region(NamedTuple):
    x: float
    y: float
    width: float
    height: float
    prompt: str
    weight: float

    @staticmethod
    def deserialize(data: str) -> list["Region"]:
        regions: list[Region] = []
        for line in data.split('\n'):
            parts = line.strip().split(',')
            enabled = int(parts.pop(0)) != 0
            x = float(parts.pop(0))
            y = float(parts.pop(0))
            width = float(parts.pop(0))
            height = float(parts.pop(0))
            weight = float(parts.pop(0))
            prompt = ','.join(parts)
            if enabled:
                regions.append(Region(x, y, width, height, prompt, weight))
        
        return regions

def get_masked_conditionings_advanced(
    sd_model,
    background_prompt: str,
    background_weight: float,
    image_width: int,
    image_height: int,
    serialized_regions: str
) -> list[MaskedConditioning]:
    regions = Region.deserialize(serialized_regions)
    masked_conds: list[MaskedConditioning] = []

    background_masked_cond = make_masked_cond(
        sd_model,
        image_width,
        image_height,
        background_prompt or "_",
        0,
        0,
        image_width,
        image_height,
        background_weight
    )

    for region in regions:
        left = int(region.x * image_width)
        top = int(region.y * image_height)
        right = int((region.x + region.width) * image_width)
        bottom = int((region.y + region.height) * image_height)
        masked_conds.append(
            make_masked_cond(
                sd_model,
                image_width,
                image_height,
                region.prompt,
                left,
                top,
                right,
                bottom,
                region.weight
            )
        )

        if not background_prompt:
            background_masked_cond.mask[top:bottom, left:right] = 0

    if background_masked_cond.mask.max() > 0:
        masked_conds.append(background_masked_cond)
    
    return masked_conds

def get_masked_conditionings_basic(
    sd_model,
    image_width: int,
    image_height: int,
    prompts: list[str],
    background_type: str,
    background_weight: float,
    is_horizontal: bool,
    region_size: int,
    region_weight: float,
) -> list[MaskedConditioning]:
    masked_conds: list[MaskedConditioning] = []
    region_idx = 0
    for prompt_idx in range(len(prompts)):
        if (background_type == "First Line" and prompt_idx == 0) or \
           (background_type == "Last Line"  and prompt_idx == len(prompts) - 1):
            left = 0
            right = image_width
            top = 0
            bottom = image_height
            weight = background_weight
        else:
            if is_horizontal:
                left = region_idx * region_size
                right = (region_idx + 1) * region_size
                top = 0
                bottom = image_height
            else:
                left = 0
                right = image_width
                top = region_idx * region_size
                bottom = (region_idx + 1) * region_size
            
            weight = region_weight
            region_idx += 1
        
        masked_conds.append(
            make_masked_cond(
                sd_model,
                image_width,
                image_height,
                prompts[prompt_idx],
                left,
                top,
                right,
                bottom,
                weight
            )
        )

    return masked_conds

def make_masked_cond(
    sd_model: Any,
    image_width: int,
    image_height: int,
    prompt: str,
    left: int,
    top: int,
    right: int,
    bottom: int,
    weight: float
) -> MaskedConditioning:
    is_sdxl: bool = hasattr(
        sd_model.forge_objects.unet.model.diffusion_model, "label_emb"
    )
    texts = SdConditioning([prompt], False, image_width, image_height, None)
    cond = sd_model.get_learned_conditioning(texts)
    pos_cond: Tensor = cond["crossattn"] if is_sdxl else cond

    mask = torch.zeros((image_height, image_width))
    mask[top:bottom, left:right] = weight

    return MaskedConditioning(pos_cond, mask.unsqueeze(0))

def empty_tensor(H: int, W: int):
    return torch.zeros((H, W)).unsqueeze(0)
