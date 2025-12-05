"""
Credit: laksjdjf
https://github.com/laksjdjf/cgem156-ComfyUI/blob/main/scripts/attention_couple/node.py
"""

import math

import torch
from torch.nn.functional import interpolate


def repeat_div(value: int, iterations: int) -> int:
    for _ in range(iterations):
        value = math.ceil(value / 2)

    return value


def get_mask(mask: torch.Tensor, batch_size: int, num_tokens: int, shape: tuple[int]):
    """
    Credit: hako-mikan
    https://github.com/hako-mikan/sd-webui-regional-prompter/blob/main/scripts/attention.py

    Issue Found/Fixed by. arcusmaximus & www
    https://github.com/arcusmaximus/sd-forge-couple/tree/draggable-box-ui
    """

    width, height = shape[3], shape[2]

    scale = math.ceil(math.log2(math.sqrt(height * width / num_tokens)))
    size = (repeat_div(height, scale), repeat_div(width, scale))

    num_conds = mask.shape[0]
    mask_downsample = interpolate(mask, size=size, mode="nearest")
    mask_downsample = mask_downsample.view(num_conds, num_tokens, 1).repeat_interleave(
        batch_size, dim=0
    )

    return mask_downsample


def lcm(a: int, b: int) -> int:
    return a * b // math.gcd(a, b)


def lcm_for_list(numbers: list[int]) -> int:
    current_lcm = numbers[0]
    for number in numbers[1:]:
        current_lcm = lcm(current_lcm, number)
    return current_lcm
