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

    # Flatten spatial dims, then pad/crop so the token count always matches
    # exactly. The log2/repeat_div heuristic above can be off by a few tokens
    # (non-multiple-of-64 sizes, hires fix, extra attn tokens, ...), which
    # previously crashed with "shape '[X, Y, 1]' is invalid for input of size Z"
    # and surfaced as TypeError: 'NoneType' object is not iterable via Gradio.
    spatial = mask_downsample.shape[-2] * mask_downsample.shape[-1]
    flat = mask_downsample.reshape(num_conds, spatial, 1)

    if spatial < num_tokens:
        pad = flat.new_zeros(num_conds, num_tokens - spatial, 1)
        flat = torch.cat([flat, pad], dim=1)
    elif spatial > num_tokens:
        flat = flat[:, :num_tokens, :]

    return flat.repeat_interleave(batch_size, dim=0)


def get_dit_mask(mask: torch.Tensor, seq_len: int, w: int, h: int, patch_size: int = 2):
    """Dynamically resizes and flattens the 2D mask to match the DiT's sequence length"""

    num_conds = mask.shape[0]

    h_p = max(h // (8 * patch_size), 1)
    w_p = max(w // (8 * patch_size), 1)
    spatial = h_p * w_p

    mask_for_interp = mask.view(num_conds, 1, mask.shape[-2], mask.shape[-1])

    mask_resized = interpolate(
        mask_for_interp, size=(h_p, w_p), mode="bilinear", align_corners=False
    )

    mask_flattened = mask_resized.reshape(num_conds, 1, spatial)

    # Cover seq_len even when it is not an exact multiple of the patch grid
    reps = math.ceil(seq_len / spatial) if spatial else 1
    mask_flattened = mask_flattened.repeat(1, reps, 1)[:, :, :seq_len]

    return mask_flattened.reshape(num_conds, 1, seq_len, 1)


def lcm(a: int, b: int) -> int:
    return a * b // math.gcd(a, b)


def lcm_for_list(numbers: list[int]) -> int:
    current_lcm = numbers[0]
    for number in numbers[1:]:
        current_lcm = lcm(current_lcm, number)
    return current_lcm
