from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.nn.flux import IntegratedFluxTransformer2DModel

import torch
from backend.attention import attention_function
from backend.nn.flux import DoubleStreamBlock, SingleStreamBlock, apply_rope
from backend.utils import fp16_fix


def attention(q, k, v, pe, mask=None):
    q, k = apply_rope(q, k, pe)
    x = attention_function(q, k, v, q.shape[1], skip_reshape=True, mask=mask)
    return x


class DoubleBlock(DoubleStreamBlock):
    def forward(self, img, txt, vec, pe, transformer_options={}):
        img_mod1_shift, img_mod1_scale, img_mod1_gate, img_mod2_shift, img_mod2_scale, img_mod2_gate = self.img_mod(vec)

        img_modulated = self.img_norm1(img)
        img_modulated = (1 + img_mod1_scale) * img_modulated + img_mod1_shift
        del img_mod1_shift, img_mod1_scale
        img_qkv = self.img_attn.qkv(img_modulated)
        del img_modulated

        B, L, _ = img_qkv.shape
        H = self.num_heads
        D = img_qkv.shape[-1] // (3 * H)
        img_q, img_k, img_v = img_qkv.view(B, L, 3, H, D).permute(2, 0, 3, 1, 4)
        del img_qkv

        img_q, img_k = self.img_attn.norm(img_q, img_k, img_v)

        txt_mod1_shift, txt_mod1_scale, txt_mod1_gate, txt_mod2_shift, txt_mod2_scale, txt_mod2_gate = self.txt_mod(vec)
        del vec

        txt_modulated = self.txt_norm1(txt)
        txt_modulated = (1 + txt_mod1_scale) * txt_modulated + txt_mod1_shift
        del txt_mod1_shift, txt_mod1_scale
        txt_qkv = self.txt_attn.qkv(txt_modulated)
        del txt_modulated

        B, L, _ = txt_qkv.shape
        txt_q, txt_k, txt_v = txt_qkv.view(B, L, 3, H, D).permute(2, 0, 3, 1, 4)
        del txt_qkv

        txt_q, txt_k = self.txt_attn.norm(txt_q, txt_k, txt_v)

        q = torch.cat((txt_q, img_q), dim=2)
        del txt_q, img_q
        k = torch.cat((txt_k, img_k), dim=2)
        del txt_k, img_k
        v = torch.cat((txt_v, img_v), dim=2)
        del txt_v, img_v

        mask_fn = transformer_options.get("patches_replace", {}).get("double", {}).get(("mask_fn", self.idx), None)
        mask = None
        if mask_fn is not None:
            mask = mask_fn(q, transformer_options, txt.shape[1])

        attn = attention(q, k, v, pe=pe, mask=mask)
        del pe, q, k, v
        txt_attn, img_attn = attn[:, : txt.shape[1]], attn[:, txt.shape[1] :]
        del attn

        img = img + img_mod1_gate * self.img_attn.proj(img_attn)
        del img_attn, img_mod1_gate
        img = img + img_mod2_gate * self.img_mlp((1 + img_mod2_scale) * self.img_norm2(img) + img_mod2_shift)
        del img_mod2_gate, img_mod2_scale, img_mod2_shift

        txt = txt + txt_mod1_gate * self.txt_attn.proj(txt_attn)
        del txt_attn, txt_mod1_gate
        txt = txt + txt_mod2_gate * self.txt_mlp((1 + txt_mod2_scale) * self.txt_norm2(txt) + txt_mod2_shift)
        del txt_mod2_gate, txt_mod2_scale, txt_mod2_shift

        txt = fp16_fix(txt)

        return img, txt


class SingleBlock(SingleStreamBlock):
    def forward(self, x, vec, pe, transformer_options={}):
        mod_shift, mod_scale, mod_gate = self.modulation(vec)
        del vec
        x_mod = (1 + mod_scale) * self.pre_norm(x) + mod_shift
        del mod_shift, mod_scale
        qkv, mlp = torch.split(self.linear1(x_mod), [3 * self.hidden_size, self.mlp_hidden_dim], dim=-1)
        del x_mod

        qkv = qkv.view(qkv.size(0), qkv.size(1), 3, self.num_heads, self.hidden_size // self.num_heads)
        q, k, v = qkv.permute(2, 0, 3, 1, 4)
        del qkv

        mask_fn = transformer_options.get("patches_replace", {}).get("single", {}).get(("mask_fn", self.idx), None)
        mask = None
        if mask_fn is not None:
            mask = mask_fn(q, transformer_options, transformer_options["txt_size"])

        q, k = self.norm(q, k, v)
        attn = attention(q, k, v, pe=pe, mask=mask)
        del q, k, v, pe
        output = self.linear2(torch.cat((attn, self.mlp_act(mlp)), dim=2))
        del attn, mlp

        x = x + mod_gate * output
        del mod_gate, output

        x = fp16_fix(x)

        return x


def inject_blocks(diffusion_model: "IntegratedFluxTransformer2DModel"):
    for i, block in enumerate(diffusion_model.double_blocks):
        block.__class__ = DoubleBlock
        block.idx = i

    for i, block in enumerate(diffusion_model.single_blocks):
        block.__class__ = SingleBlock
        block.idx = i

    return diffusion_model
