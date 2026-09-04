"""Krea 2 (single-stream DiT) regional attention bias. Pure torch, no Forge imports.

Sequence layout is [seg_0 | ... | seg_{N-1} | img], image tokens row-major.
Bias is additive in the query dtype: 0 = attend, log(w) = soft weight w, NEG = blocked.
A "global" line is one whose mask is > 0 at every pixel (Couple's Global Effect, a
full-frame Advanced box, an all-white Mask layer): every text segment may read it, every
image token reads it at log(weight), and it never counts for image-to-image gating.
"""

import torch
from torch.nn.functional import interpolate

NEG: float = -1e4


def find_globals(spatial: torch.Tensor) -> list[bool]:
    return [bool((m > 0).all()) for m in spatial]


def resize_masks(spatial: torch.Tensor, h: int, w: int) -> torch.Tensor:
    n = spatial.shape[0]
    x = spatial.float().view(n, 1, spatial.shape[-2], spatial.shape[-1])
    x = interpolate(x, size=(h, w), mode="bilinear", align_corners=False)
    return x.view(n, h * w).clamp_(min=0.0)


def log_weight(m: torch.Tensor) -> torch.Tensor:
    return torch.where(m > 0, torch.log(m.clamp(min=1e-6)), torch.full_like(m, NEG))


def build_bias(
    seg_lens: list[int],
    masks: torch.Tensor,
    is_global: list[bool],
    gate_img: bool,
) -> torch.Tensor:
    n_lines = len(seg_lens)
    assert masks.shape[0] == n_lines == len(is_global)
    device = masks.device
    n = masks.shape[1]
    t = sum(seg_lens)
    total = t + n

    offsets = [0]
    for length in seg_lens:
        offsets.append(offsets[-1] + length)

    regional = [i for i in range(n_lines) if not is_global[i]]
    globals_ = [i for i in range(n_lines) if is_global[i]]

    if regional:
        covered = (masks[regional] > 0).any(dim=0)  # (N,)
    else:
        covered = torch.zeros(n, dtype=torch.bool, device=device)

    bias = torch.zeros(total, total, dtype=torch.float32, device=device)

    # ---- text -> text: block diagonal; everyone may read every global segment
    bias[:t, :t] = NEG
    for i in range(n_lines):
        bias[offsets[i] : offsets[i + 1], offsets[i] : offsets[i + 1]] = 0.0
    for g in globals_:
        bias[:t, offsets[g] : offsets[g + 1]] = 0.0

    # ---- text <-> image
    for i in range(n_lines):
        cols = slice(offsets[i], offsets[i + 1])
        lw = log_weight(masks[i])  # (N,)
        bias[t:, cols] = lw.unsqueeze(1)
        bias[cols, t:] = 0.0 if is_global[i] else lw.unsqueeze(0)

    # ---- image tokens covered by no regional line read every text token
    img_rows = torch.arange(t, total, device=device)[~covered]
    bias[img_rows, :t] = 0.0

    # ---- image -> image (only regional lines count as "shared")
    if gate_img and regional:
        present = (masks[regional] > 0).float()  # (R, N)
        share = (present.t() @ present) > 0  # (N, N)
        allow = share | (~covered).unsqueeze(1) | (~covered).unsqueeze(0)
        bias[t:, t:] = torch.where(allow, 0.0, NEG)

    return bias


def pad_aligned(bias: torch.Tensor, dtype: torch.dtype, device: torch.device) -> torch.Tensor:
    """(L, L) -> (1, 1, L, L) view over storage whose last dim is padded to a multiple of 8,
    so the memory-efficient SDPA kernel accepts it."""
    length = bias.shape[-1]
    padded = (length + 7) // 8 * 8
    out = torch.zeros(1, 1, length, padded, dtype=dtype, device=device)
    out[..., :length] = bias.to(dtype=dtype, device=device)
    return out[..., :length]
