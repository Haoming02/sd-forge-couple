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

        conds = [
            kwargs[f"cond_{i}"][0][0].to(device=device, dtype=dtype).squeeze(1)
            for i in range(1, num_conds)
        ]
        num_tokens = [cond.shape[1] for cond in conds]

        SelfCrossAttention.orig_forward = SelfCrossAttention.forward

        @wraps(SelfCrossAttention.orig_forward)
        @torch.inference_mode()
        def custom_forward(
            self, x, context=None, rope_emb=None, transformer_options=None
        ):
            if transformer_options is None:
                transformer_options = {}

            cond_or_unconds = transformer_options.get("cond_or_uncond", [])

            if context is None or not cond_or_unconds:
                return self.orig_forward(
                    x=x,
                    context=context,
                    rope_emb=rope_emb,
                    transformer_options=transformer_options,
                )

            num_chunks = len(cond_or_unconds)
            batch_size = x.shape[0] // num_chunks

            x_chunks = x.chunk(num_chunks, dim=0)

            assert context is not None
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
                if cond_or_uncond == 1:
                    new_x.append(x_chunks[idx])
                    c_target = context_chunks[idx].repeat(
                        1, lcm_tokens // ctx_seq_len, 1
                    )
                    new_context.append(c_target)
                else:
                    new_x.append(x_chunks[idx].repeat(num_conds, 1, 1))
                    c_target = context_chunks[idx].repeat(
                        1, lcm_tokens // ctx_seq_len, 1
                    )
                    new_context.append(torch.cat([c_target, conds_tensor], dim=0))

            x_in = torch.cat(new_x, dim=0)
            ctx_in = torch.cat(new_context, dim=0).unsqueeze(1)

            out = self.orig_forward(
                x_in,
                context=ctx_in,
                rope_emb=rope_emb,
                transformer_options=transformer_options,
            )

            seq_len = out.shape[1]

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

        SelfCrossAttention.forward = custom_forward

        return model

    @staticmethod
    def unpatch():
        if hasattr(SelfCrossAttention, "orig_forward"):
            SelfCrossAttention.forward = SelfCrossAttention.orig_forward
            del SelfCrossAttention.orig_forward
