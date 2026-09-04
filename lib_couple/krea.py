"""Krea 2 engine: regional prompting for a single-stream DiT through a joint-attention bias.

Krea 2 (backend/nn/krea.py) runs text and image tokens through one attention sequence, so
the batch-splitting trick used for SD / Anima has no cross-attention to hook. Instead every
prompt line is encoded on its own, the segments are joined into one text sequence, and an
additive attention bias (lib_couple/krea_bias.py) restricts each image token to the lines
whose regions cover it. All patches are class-level attribute swaps restored by unpatch();
krea.py itself is never edited.
"""

import math

import torch

from backend import attention as _attention
from backend.args import dynamic_args
from backend.nn import krea as _krea
from lib_couple.logging import logger
from modules.shared import opts

from . import krea_bias as _bias


class _State:
    def __init__(self):
        self.reset()

    def reset(self):
        self.active = False
        self.seg_lens: list[int] = []
        self.context: torch.Tensor | None = None  # (1, T, 12, 2560)
        self.spatial: torch.Tensor | None = None  # (N, H, W) float32, cpu
        self.is_global: list[bool] = []
        self.blend: float = 0.25
        # transient, per forward
        self.bias: torch.Tensor | None = None
        self.bias_gated: torch.Tensor | None = None
        self.n_self: int = 0
        self.block_counter: int = 0
        self.txt_split: list[int] | None = None
        self.txt_seg: int | None = None
        # caches / one-shot flags
        self.bias_cache: dict = {}
        self.warned_ref: bool = False


state = _State()
_originals: dict = {}


class AttentionCoupleKrea:

    @staticmethod
    @torch.inference_mode()
    def patch_dit(model, base_mask, width: int, height: int, kwargs: dict):
        AttentionCoupleKrea.unpatch()
        try:
            num_conds = len(kwargs) // 2 + 1
            masks = [kwargs[f"mask_{i}"] for i in range(1, num_conds)]
            spatial = torch.stack([m.reshape(m.shape[-2], m.shape[-1]).float() for m in masks], dim=0)
            segments = [kwargs[f"cond_{i}"][0][0] for i in range(1, num_conds)]

            state.seg_lens = [int(s.shape[0]) for s in segments]
            state.context = torch.cat([s.detach() for s in segments], dim=0).unsqueeze(0)
            state.spatial = spatial.detach().cpu()
            state.is_global = _bias.find_globals(state.spatial)
            state.blend = float(getattr(opts, "fc_krea_blend", 0.25))

            dit = model.model.diffusion_model
            _originals["dit_forward"] = _krea.SingleStreamDiT.forward
            _originals["block_forward"] = _krea.SingleStreamBlock.forward
            _originals["txt_forward"] = _krea.TextFusionTransformer.forward
            _originals["attention_function"] = _krea.attention_function
            _krea.SingleStreamDiT.forward = _dit_forward
            _krea.SingleStreamBlock.forward = _block_forward
            _krea.TextFusionTransformer.forward = _txt_forward
            _krea.attention_function = _attention.attention_pytorch  # attention_flash asserts mask is None
            state.active = True

            # Tell Forge's memory planner about the two attention biases plus the float32
            # build intermediate; without this Forge fills VRAM to the brim and pages.
            grid = 8 * dit.patch
            tokens = sum(state.seg_lens) + math.ceil(height / grid) * math.ceil(width / grid)
            model.add_extra_preserved_memory_during_sampling(int(4 * tokens * tokens * 2 + 64 * 1024 * 1024))

            logger.info(
                f"Krea 2: {num_conds - 1} lines ({sum(state.is_global)} global), "
                f"blend {state.blend} -> {int(round(state.blend * len(dit.blocks)))} gated blocks"
            )
            return model

        except Exception:
            logger.exception("Krea 2 patch failed...")
            AttentionCoupleKrea.unpatch()
            return None

    @staticmethod
    def unpatch():
        if "dit_forward" in _originals:
            _krea.SingleStreamDiT.forward = _originals.pop("dit_forward")
        if "block_forward" in _originals:
            _krea.SingleStreamBlock.forward = _originals.pop("block_forward")
        if "txt_forward" in _originals:
            _krea.TextFusionTransformer.forward = _originals.pop("txt_forward")
        if "attention_function" in _originals:
            _krea.attention_function = _originals.pop("attention_function")
        state.reset()


# ---------------------------------------------------------------- helpers


def _grid(x: torch.Tensor, patch: int) -> tuple[int, int]:
    return math.ceil(x.shape[-2] / patch), math.ceil(x.shape[-1] / patch)


def _biases_for(h: int, w: int, dtype: torch.dtype, device: torch.device):
    key = (h, w, str(dtype), str(device))
    if key not in state.bias_cache:
        masks = _bias.resize_masks(state.spatial.to(device), h, w)
        plain = _bias.build_bias(state.seg_lens, masks, state.is_global, False)
        gated = _bias.build_bias(state.seg_lens, masks, state.is_global, True)
        state.bias_cache[key] = (
            _bias.pad_aligned(plain, dtype, device),
            _bias.pad_aligned(gated, dtype, device),
        )
    return state.bias_cache[key]


def _cond_rows(transformer_options: dict, rows: int) -> torch.Tensor:
    cond_mark = transformer_options.get("cond_mark", None)
    if cond_mark is None:
        return torch.ones(rows, dtype=torch.bool)
    return cond_mark.flatten()[:rows].cpu() < 0.5


# ---------------------------------------------------------------- patched forwards


def _run_regional(self, x, timesteps, context, attention_mask, transformer_options, kwargs):
    orig = _originals["dit_forward"]
    rows = x.shape[0]
    h, w = _grid(x, self.patch)
    ctx = state.context.to(device=x.device, dtype=context.dtype).expand(rows, -1, -1, -1)
    state.bias, state.bias_gated = _biases_for(h, w, x.dtype, x.device)
    state.n_self = int(round(state.blend * len(self.blocks)))
    state.block_counter = 0
    state.txt_split = list(state.seg_lens)
    try:
        return orig(self, x, timesteps, ctx, attention_mask, transformer_options, **kwargs)
    finally:
        state.bias = None
        state.bias_gated = None
        state.txt_split = None


def _dit_forward(self, x, timesteps, context, attention_mask=None, transformer_options={}, **kwargs):
    orig = _originals["dit_forward"]
    if not state.active or state.context is None:
        return orig(self, x, timesteps, context, attention_mask, transformer_options, **kwargs)

    if dynamic_args.ref_latents:
        if not state.warned_ref:
            state.warned_ref = True
            logger.warning("Krea 2 edit / reference mode is not supported; generating without regions")
        return orig(self, x, timesteps, context, attention_mask, transformer_options, **kwargs)

    try:
        rows = x.shape[0]
        is_cond = _cond_rows(transformer_options, rows)

        if bool(is_cond.all()):
            return _run_regional(self, x, timesteps, context, attention_mask, transformer_options, kwargs)
        if not bool(is_cond.any()):
            return orig(self, x, timesteps, context, attention_mask, transformer_options, **kwargs)

        # mixed cond / uncond rows in one batch: run the two halves separately
        idx_c = is_cond.nonzero().flatten().to(x.device)
        idx_u = (~is_cond).nonzero().flatten().to(x.device)

        def _rows(t, idx):
            return t[idx] if torch.is_tensor(t) and t.shape[0] == rows else t

        out_c = _run_regional(
            self, x[idx_c], _rows(timesteps, idx_c), context[idx_c], attention_mask, transformer_options, kwargs
        )
        out_u = orig(
            self, x[idx_u], _rows(timesteps, idx_u), context[idx_u], attention_mask, transformer_options, **kwargs
        )
        out = torch.empty((rows, *out_c.shape[1:]), dtype=out_c.dtype, device=out_c.device)
        out[idx_c] = out_c
        out[idx_u] = out_u
        return out

    except Exception:
        logger.exception("Krea 2 regional forward failed; generating without regions")
        AttentionCoupleKrea.unpatch()
        return orig(self, x, timesteps, context, attention_mask, transformer_options, **kwargs)


def _block_forward(self, x, vec, freqs, mask=None, transformer_options={}):
    if mask is None and state.bias is not None:
        i = state.block_counter
        state.block_counter += 1
        if state.bias.dtype != x.dtype:
            state.bias = state.bias.to(x.dtype)
            state.bias_gated = state.bias_gated.to(x.dtype)
        mask = state.bias_gated if i < state.n_self else state.bias
    return _originals["block_forward"](self, x, vec, freqs, mask, transformer_options=transformer_options)


def _txt_forward(self, x, mask=None, transformer_options={}):
    orig = _originals["txt_forward"]
    split = state.txt_split
    if split is None or x.shape[1] != sum(split):
        return orig(self, x, mask, transformer_options=transformer_options)
    parts = x.split(split, dim=1)
    outs = []
    try:
        for i, part in enumerate(parts):
            state.txt_seg = i
            outs.append(orig(self, part.contiguous(), None, transformer_options=transformer_options))
    finally:
        state.txt_seg = None
    return torch.cat(outs, dim=1)
