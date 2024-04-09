"""
Credit: laksjdjf
https://github.com/laksjdjf/cgem156-ComfyUI/blob/main/scripts/attention_couple/node.py

As well as hako-mikan
https://github.com/hako-mikan/sd-webui-regional-prompter/blob/main/scripts/attention.py
"""

from torch import Tensor
import torch.nn.functional as F
import math

def downsample_mask(mask: Tensor, batch_size: int, num_tokens: int, image_width: int, image_height: int) -> Tensor:
    power = math.ceil(math.log2(math.sqrt(image_height * image_width / num_tokens)))
    size = (repeat_div(image_height, power), repeat_div(image_width, power))

    num_conds = mask.shape[0]
    mask_downsample: Tensor = F.interpolate(mask, size=size, mode="nearest")
    mask_downsample = mask_downsample.view(num_conds, num_tokens, 1).repeat_interleave(
        batch_size, dim=0
    )

    return mask_downsample

def repeat_div(value: int, iterations: int) -> int:
    for _ in range(iterations):
        value = math.ceil(value / 2)

    return value

def lcm(a, b):
    return a * b // math.gcd(a, b)


def lcm_for_list(numbers):
    current_lcm = numbers[0]
    for number in numbers[1:]:
        current_lcm = lcm(current_lcm, number)
    return current_lcm
