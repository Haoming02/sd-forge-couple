import math
from functools import partial, wraps
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.nn.anima import Anima
    from modules.processing import StableDiffusionProcessing

import torch

from backend.nn.anima import SelfCrossAttention
from backend.operations import scaled_dot_product_attention
from lib_couple.logging import logger
from modules.devices import device, dtype
from modules.shared import opts

from .attention_masks import get_dit_mask, lcm_for_list

orig_attention = SelfCrossAttention.torch_attention_op


def _use_bias(sigmas: torch.Tensor, sigma: torch.Tensor) -> bool:
    threshold: float = getattr(opts, "fc_anima_steps", 0.0)
    steps: int = sigmas.size(0)
    step: int = (sigmas == sigma).int().argmax()
    return (step / steps) < threshold


@wraps(orig_attention)
def masked_attn_op(
    q: torch.Tensor,
    k: torch.Tensor,
    v: torch.Tensor,
    transformer_options: dict,
    *,
    attn_bias: torch.Tensor = None,
):
    if not _use_bias(
        sigmas=transformer_options["sampling_sigmas"],
        sigma=transformer_options["sigmas"],
    ):
        return orig_attention(q, k, v, transformer_options)

    B, S, H, D = q.shape

    q_b = q.permute(0, 2, 1, 3)
    k_b = k.permute(0, 2, 1, 3)
    v_b = v.permute(0, 2, 1, 3)
    bias = attn_bias.to(device=q.device, dtype=q.dtype)

    out = scaled_dot_product_attention(q_b, k_b, v_b, attn_mask=bias)

    return out.permute(0, 2, 1, 3).reshape(B, S, H * D)


def get_attn_bias(mask: torch.Tensor, w: int, h: int, patch_size: int, _str: float):
    seq_len = (w // 8) * (h // 8) // (patch_size * patch_size)
    penalty = -12.0 * _str

    mask_downsample = get_dit_mask(mask, seq_len, w, h, patch_size)
    mask_bool = mask_downsample.squeeze(1).squeeze(-1) > 0.5

    allowed = torch.zeros((seq_len, seq_len), device=mask.device, dtype=torch.bool)
    for i in range(mask_bool.shape[0]):
        m = mask_bool[i]
        allowed |= m[:, None] & m[None, :]

    allowed |= torch.eye(seq_len, device=mask.device, dtype=torch.bool)
    dd = dict(device=mask.device, dtype=mask.dtype)

    bias = torch.where(
        allowed,
        torch.zeros((seq_len, seq_len), **dd),
        torch.full((seq_len, seq_len), penalty, **dd),
    )

    if _str >= 1.0:
        bias[~allowed] = float("-inf")

    return bias.unsqueeze(0).unsqueeze(0)


class AttentionCoupleAnima:

    @staticmethod
    @torch.inference_mode()
    def patch_dit(model, base_mask, width: int, height: int, kwargs: dict):
        dit: "Anima" = model.model.diffusion_model

        num_conds = len(kwargs) // 2 + 1

        mask = [base_mask] + [kwargs[f"mask_{i}"] for i in range(1, num_conds)]
        mask = torch.stack(mask, dim=0).to(device=device, dtype=dtype)

        if mask.sum(dim=0).min().item() <= 0.0:
            logger.error("Mask must be completely filled...")
            return None

        mask = mask / mask.sum(dim=0, keepdim=True)
        conds: list[torch.Tensor] = []

        for i in range(1, num_conds):
            c = kwargs[f"cond_{i}"][0][0].to(device=device, dtype=dtype)
            if (dim := math.ceil(c.shape[0] / 512) * 512) > 512:
                c = torch.nn.functional.pad(c, (0, 0, 0, dim - c.shape[0]))
            conds.append(c)

        num_tokens = [cond.shape[1] for cond in conds]

        strength = getattr(opts, "fc_anima_strength", 0.0)
        threshold = getattr(opts, "fc_anima_steps", 0.0)

        if (strength * threshold) > 0.0:
            self_attn_bias = get_attn_bias(
                mask,
                width,
                height,
                dit.patch_spatial,
                strength,
            )

            func = partial(masked_attn_op, attn_bias=self_attn_bias)
            func._couple = True

            for block in dit.blocks:
                attn: "SelfCrossAttention" = block.self_attn
                attn.torch_attention_op = func

        SelfCrossAttention.couple_orig_forward = SelfCrossAttention.forward

        @wraps(SelfCrossAttention.couple_orig_forward)
        @torch.inference_mode()
        def couple_forward(
            self: "SelfCrossAttention",
            x: torch.Tensor,
            context: torch.Tensor,
            rope_emb: torch.Tensor,
            transformer_options: dict = {},
        ):
            if self.is_SelfAttn:
                return self.couple_orig_forward(
                    x=x,
                    context=context,
                    rope_emb=rope_emb,
                    transformer_options=transformer_options,
                )

            cond_or_unconds = transformer_options.get("cond_or_uncond", None)

            if context is None or not cond_or_unconds:
                return self.couple_orig_forward(
                    x=x,
                    context=context,
                    rope_emb=rope_emb,
                    transformer_options=transformer_options,
                )

            num_chunks = len(cond_or_unconds)
            batch_size = x.shape[0] // num_chunks

            x_chunks = x.chunk(num_chunks, dim=0)

            context_3d = context.squeeze(1)
            if (dim := math.ceil(context_3d.shape[1] / 512) * 512) > 512:
                context_3d = torch.nn.functional.pad(
                    context_3d,
                    (0, 0, 0, dim - context_3d.shape[1]),
                )

            ctx_seq_len = context_3d.shape[-2]
            context_chunks = context_3d.chunk(num_chunks, dim=0)

            lcm_tokens = lcm_for_list(num_tokens + [ctx_seq_len])
            assert lcm_tokens in (512, 1024), "Your prompt is way too long..."

            conds_tensor = torch.cat(
                [
                    cond.repeat(batch_size, lcm_tokens // cond.shape[-2], 1)
                    for cond in conds
                ],
                dim=0,
            )

            new_x = []
            new_context = []

            for idx, cond_or_uncond in enumerate(cond_or_unconds):
                c_target = context_chunks[idx].repeat(1, lcm_tokens // ctx_seq_len, 1)
                if cond_or_uncond == 1:
                    new_x.append(x_chunks[idx])
                    new_context.append(c_target)
                else:
                    new_x.append(x_chunks[idx].repeat(num_conds, 1, 1))
                    new_context.append(torch.cat([c_target, conds_tensor], dim=0))

            x_in = torch.cat(new_x, dim=0)
            ctx_in = torch.cat(new_context, dim=0).to(dtype=x_in.dtype)

            out = self.couple_orig_forward(
                x_in,
                context=ctx_in,
                rope_emb=rope_emb,
                transformer_options=transformer_options,
            )

            seq_len: int = out.shape[1]

            mask_downsample = get_dit_mask(
                mask, seq_len, width, height, patch_size=dit.patch_spatial
            )

            outputs = []
            pos = 0

            for idx, cond_or_uncond in enumerate(cond_or_unconds):
                if cond_or_uncond == 1:
                    outputs.append(out[pos : pos + batch_size])
                    pos += batch_size
                else:
                    chunk = out[pos : pos + num_conds * batch_size]
                    chunk = chunk.view(num_conds, batch_size, seq_len, -1)

                    masked_output = (chunk * mask_downsample).sum(dim=0)
                    outputs.append(masked_output)
                    pos += num_conds * batch_size

            return torch.cat(outputs, dim=0)

        couple_forward._couple = True
        SelfCrossAttention.forward = couple_forward

        return model

    @staticmethod
    def unpatch(p: "StableDiffusionProcessing"):
        if hasattr(SelfCrossAttention, "couple_orig_forward"):
            if getattr(SelfCrossAttention.forward, "_couple", False):
                SelfCrossAttention.forward = SelfCrossAttention.couple_orig_forward
            del SelfCrossAttention.couple_orig_forward

        dit: "Anima" = p.sd_model.forge_objects.unet.model.diffusion_model

        for block in dit.blocks:
            attn: "SelfCrossAttention" = block.self_attn
            if getattr(attn.torch_attention_op, "_couple", False):
                attn.torch_attention_op = orig_attention
