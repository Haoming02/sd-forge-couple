"""
Credit: laksjdjf
https://github.com/laksjdjf/cgem156-ComfyUI/blob/main/scripts/attention_couple/node.py
"""

import torch.nn.functional as F
import math


def repeat_div(value: int, iterations: int) -> int:
    for _ in range(iterations):
        value = math.ceil(value / 2)

    return value


def get_mask(mask, batch_size, num_tokens, original_shape):
    """
    Credit: hako-mikan
    https://github.com/hako-mikan/sd-webui-regional-prompter/blob/main/scripts/attention.py

    Issue Found/Fixed by. arcusmaximus & www
    https://github.com/arcusmaximus/sd-forge-couple/tree/draggable-box-ui
    """

    image_width: int = original_shape[3]
    image_height: int = original_shape[2]

    scale = math.ceil(math.log2(math.sqrt(image_height * image_width / num_tokens)))
    size = (repeat_div(image_height, scale), repeat_div(image_width, scale))

    num_conds = mask.shape[0]
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
