"""
Credit: laksjdjf
https://github.com/laksjdjf/cgem156-ComfyUI/blob/main/scripts/attention_couple/node.py
"""

import torch.nn.functional as F
import math


def get_mask(mask, batch_size, num_tokens, original_shape):
    num_conds = mask.shape[0]

    if original_shape[2] * original_shape[3] == num_tokens:
        down_sample_rate = 1
    elif (original_shape[2] // 2) * (original_shape[3] // 2) == num_tokens:
        down_sample_rate = 2
    elif (original_shape[2] // 4) * (original_shape[3] // 4) == num_tokens:
        down_sample_rate = 4
    else:
        down_sample_rate = 8

    size = (
        original_shape[2] // down_sample_rate,
        original_shape[3] // down_sample_rate,
    )
    mask_downsample = F.interpolate(mask, size=size, mode="nearest")
    mask_downsample = mask_downsample.view(num_conds, num_tokens, 1).repeat_interleave(
        batch_size, dim=0
    )

    return mask_downsample


def lcm(a, b):
    return a * b // math.gcd(a, b)


def lcm_for_list(numbers):
    current_lcm = numbers[0]
    for number in numbers[1:]:
        current_lcm = lcm(current_lcm, number)
    return current_lcm
