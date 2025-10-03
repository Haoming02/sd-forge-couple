"""
Credit: laksjdjf
https://github.com/laksjdjf/cgem156-ComfyUI/blob/main/scripts/attention_couple/node.py

Modified by. Haoming02 to work with Forge
"""

from functools import wraps
from typing import Callable

import torch
from modules.devices import device, dtype

from lib_couple.logging import logger

from .attention_masks import get_mask, lcm_for_list


class AttentionCouple:
    def __init__(self):
        self.batch_size: int
        self.patches: dict[str, Callable] = {}
        self.manual: dict[str, list]
        self.checked: bool

    @torch.inference_mode()
    def patch_unet(
        self,
        model: torch.nn.Module,
        base_mask,
        kwargs: dict,
        *,
        isA1111: bool,
        width: int,
        height: int,
    ):
        num_conds = len(kwargs) // 2 + 1

        mask = [base_mask] + [kwargs[f"mask_{i}"] for i in range(1, num_conds)]
        mask = torch.stack(mask, dim=0).to(device=device, dtype=dtype)

        if mask.sum(dim=0).min().item() <= 0.0:
            logger.error("Image must contain weights on all pixels...")
            return None

        mask = mask / mask.sum(dim=0, keepdim=True)

        conds = [
            kwargs[f"cond_{i}"][0][0].to(device=device, dtype=dtype)
            for i in range(1, num_conds)
        ]
        num_tokens = [cond.shape[1] for cond in conds]

        if isA1111:
            self.manual = {
                "original_shape": [2, 4, height // 8, width // 8],
                "cond_or_uncond": [0, 1],
            }
            self.checked = False

        @torch.inference_mode()
        def attn2_patch(q, k, v, extra_options=None):
            assert torch.allclose(k, v), "k and v should be the same"
            if extra_options is None:
                if not self.checked:
                    self.manual["original_shape"][0] = k.size(0)
                    self.manual["cond_or_uncond"] = list(range(k.size(0)))
                    self.checked = True

                extra_options = self.manual

            cond_or_unconds = extra_options["cond_or_uncond"]
            num_chunks = len(cond_or_unconds)
            self.batch_size = q.shape[0] // num_chunks
            q_chunks = q.chunk(num_chunks, dim=0)
            k_chunks = k.chunk(num_chunks, dim=0)
            lcm_tokens = lcm_for_list(num_tokens + [k.shape[1]])
            conds_tensor = torch.cat(
                [
                    cond.repeat(self.batch_size, lcm_tokens // num_tokens[i], 1)
                    for i, cond in enumerate(conds)
                ],
                dim=0,
            )

            qs, ks = [], []
            for i, cond_or_uncond in enumerate(cond_or_unconds):
                k_target = k_chunks[i].repeat(1, lcm_tokens // k.shape[1], 1)
                if cond_or_uncond == 1:  # uncond
                    qs.append(q_chunks[i])
                    ks.append(k_target)
                else:
                    qs.append(q_chunks[i].repeat(num_conds, 1, 1))
                    ks.append(torch.cat([k_target, conds_tensor], dim=0))

            qs = torch.cat(qs, dim=0).to(q)
            ks = torch.cat(ks, dim=0).to(k)

            if qs.size(0) % 2 == 1:
                empty = torch.zeros_like(qs[0]).unsqueeze(0)
                qs = torch.cat((qs, empty), dim=0)
                empty = torch.zeros_like(ks[0]).unsqueeze(0)
                ks = torch.cat((ks, empty), dim=0)

            return qs, ks, ks

        @torch.inference_mode()
        def attn2_output_patch(out, extra_options=None):
            if extra_options is None:
                self.checked = False
                extra_options = self.manual

            cond_or_unconds = extra_options["cond_or_uncond"]
            mask_downsample = get_mask(
                mask, self.batch_size, out.shape[1], extra_options["original_shape"]
            )
            outputs = []
            pos = 0
            for cond_or_uncond in cond_or_unconds:
                if cond_or_uncond == 1:  # uncond
                    outputs.append(out[pos : pos + self.batch_size])
                    pos += self.batch_size
                else:
                    masked_output = (
                        out[pos : pos + num_conds * self.batch_size] * mask_downsample
                    ).view(num_conds, self.batch_size, out.shape[1], out.shape[2])
                    masked_output = masked_output.sum(dim=0)
                    outputs.append(masked_output)
                    pos += num_conds * self.batch_size
            return torch.cat(outputs, dim=0)

        if isA1111:

            def patch_attn2(layer: str, module: torch.nn.Module):
                f: Callable = module.forward
                self.patches[layer] = f

                @wraps(f)
                def _f(x, context, *args, **kwargs):
                    q = x
                    k = v = context
                    _q, _k, _v = attn2_patch(q, k, v)
                    return f(_q, context=_k, *args, **kwargs)

                module.forward = _f

            def patch_attn2_out(layer: str, module: torch.nn.Module):
                f: Callable = module.forward
                self.patches[layer] = f

                @wraps(f)
                def _f(*args, **kwargs):
                    _o = f(*args, **kwargs)
                    return attn2_output_patch(_o)

                module.forward = _f

            for layer_name, module in model.named_modules():
                if "attn2" not in layer_name:
                    continue

                if layer_name.endswith("2"):
                    patch_attn2(layer_name, module)

                if layer_name.endswith("to_out"):
                    patch_attn2_out(layer_name, module)

            return True

        else:
            model.set_model_attn2_patch(attn2_patch)
            model.set_model_attn2_output_patch(attn2_output_patch)

            return model

    @torch.no_grad()
    def unpatch(self, model: torch.nn.Module):
        if not self.patches:
            return

        for layer_name, module in model.named_modules():
            if "attn2" not in layer_name:
                continue

            if layer_name.endswith(("attn2", "to_out")):
                module.forward = self.patches.pop(layer_name)
