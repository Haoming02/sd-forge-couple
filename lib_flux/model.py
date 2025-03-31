import torch
from backend.nn.flux import IntegratedFluxTransformer2DModel, timestep_embedding
from einops import rearrange, repeat


class Flux(IntegratedFluxTransformer2DModel):

    def inner_forward(self, img, img_ids, txt, txt_ids, timesteps, y, guidance=None, transformer_options={}):
        if img.ndim != 3 or txt.ndim != 3:
            raise ValueError("Input img and txt tensors must have 3 dimensions.")
        img = self.img_in(img)
        vec = self.time_in(timestep_embedding(timesteps, 256).to(img.dtype))
        if self.guidance_embed:
            if guidance is None:
                raise ValueError("Didn't get guidance strength for guidance distilled model.")
            vec = vec + self.guidance_in(timestep_embedding(guidance, 256).to(img.dtype))
        vec = vec + self.vector_in(y)
        txt = self.txt_in(txt)
        del y, guidance
        ids = torch.cat((txt_ids, img_ids), dim=1)
        del txt_ids, img_ids
        pe = self.pe_embedder(ids)
        del ids
        for block in self.double_blocks:
            img, txt = block(img=img, txt=txt, vec=vec, pe=pe, transformer_options=transformer_options)
        img = torch.cat((txt, img), 1)
        for block in self.single_blocks:
            img = block(img, vec=vec, pe=pe, transformer_options=transformer_options)
        del pe
        img = img[:, txt.shape[1] :, ...]
        del txt
        img = self.final_layer(img, vec)
        del vec
        return img

    def forward(self, x, timestep, context, y, guidance=None, transformer_options={}, **kwargs):
        bs, c, h, w = x.shape
        input_device = x.device
        input_dtype = x.dtype
        patch_size = 2
        pad_h = (patch_size - x.shape[-2] % patch_size) % patch_size
        pad_w = (patch_size - x.shape[-1] % patch_size) % patch_size
        x = torch.nn.functional.pad(x, (0, pad_w, 0, pad_h), mode="circular")

        transformer_options["original_shape"] = x.shape
        transformer_options["patch_size"] = patch_size

        img = rearrange(x, "b c (h ph) (w pw) -> b (h w) (c ph pw)", ph=patch_size, pw=patch_size)
        del x, pad_h, pad_w

        regional_conditioning = transformer_options.get("patches", {}).get("regional_conditioning", None)
        if regional_conditioning is not None:
            region_cond = regional_conditioning[0](transformer_options)
            if region_cond is not None:
                context = torch.cat([torch.zeros_like(context), region_cond.to(context.dtype)], dim=1)

        h_len = (h + (patch_size // 2)) // patch_size
        w_len = (w + (patch_size // 2)) // patch_size
        img_ids = torch.zeros((h_len, w_len, 3), device=input_device, dtype=input_dtype)
        img_ids[..., 1] = img_ids[..., 1] + torch.linspace(0, h_len - 1, steps=h_len, device=input_device, dtype=input_dtype)[:, None]
        img_ids[..., 2] = img_ids[..., 2] + torch.linspace(0, w_len - 1, steps=w_len, device=input_device, dtype=input_dtype)[None, :]
        img_ids = repeat(img_ids, "h w c -> b (h w) c", b=bs)
        txt_ids = torch.zeros((bs, context.shape[1], 3), device=input_device, dtype=input_dtype)
        del input_device, input_dtype

        transformer_options["txt_size"] = context.shape[1]

        out = self.inner_forward(img, img_ids, context, txt_ids, timestep, y, guidance, transformer_options=transformer_options)
        del img, img_ids, txt_ids, timestep, context

        out = rearrange(out, "b (h w) (c ph pw) -> b c (h ph) (w pw)", h=h_len, w=w_len, ph=2, pw=2)[:, :, :h, :w]
        del h_len, w_len, bs
        return out


def inject_model(diffusion_model: IntegratedFluxTransformer2DModel):
    diffusion_model.__class__ = Flux
    return diffusion_model
