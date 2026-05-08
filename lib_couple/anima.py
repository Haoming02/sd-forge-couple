from functools import wraps

import torch

from backend.nn.anima import SelfCrossAttention
from lib_couple.logging import logger
from modules.devices import device, dtype

from .attention_masks import get_dit_mask, lcm_for_list


class AttentionCoupleAnima:

    @staticmethod
    @torch.inference_mode()
    def patch_dit(model, base_mask, width: int, height: int, kwargs: dict):
        dit = model.model.diffusion_model

        num_conds = len(kwargs) // 2 + 1

        mask = [base_mask] + [kwargs[f"mask_{i}"] for i in range(1, num_conds)]
        mask = torch.stack(mask, dim=0).to(device=device, dtype=dtype)

        if mask.sum(dim=0).min().item() <= 0.0:
            logger.error("Mask must be completely filled...")
            return None

        mask = mask / mask.sum(dim=0, keepdim=True)
        conds: list[torch.Tensor] = []

        for i in range(1, num_conds):
            c = kwargs[f"cond_{i}"]
            if isinstance(c, dict):
                c = c["crossattn"][0]
            else:
                c = c[0][0]
            conds.append(c.to(device=device, dtype=dtype))

        num_tokens = [cond.shape[1] for cond in conds]

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
            ctx_seq_len = context_3d.shape[-2]
            context_chunks = context_3d.chunk(num_chunks, dim=0)

            lcm_tokens = lcm_for_list(num_tokens + [ctx_seq_len])

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
    def unpatch():
        if hasattr(SelfCrossAttention, "couple_orig_forward"):
            if getattr(SelfCrossAttention.forward, "_couple", False):
                SelfCrossAttention.forward = SelfCrossAttention.couple_orig_forward
            del SelfCrossAttention.couple_orig_forward
