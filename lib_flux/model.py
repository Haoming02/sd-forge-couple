import torch


def inject_flux(diffusion_model):
    if hasattr(diffusion_model, "_old_forward"):
        return diffusion_model

    diffusion_model._old_forward = diffusion_model.forward

    def new_forward(x, timestep, context, y, guidance, control=None, transformer_options={}, **kwargs):
        regional_conditioning = transformer_options.get("patches", {}).get("regional_conditioning", None)
        if regional_conditioning is not None:
            region_cond = regional_conditioning[0](transformer_options)
            if region_cond is not None:
                context = torch.cat([torch.zeros_like(context), region_cond.to(context.dtype)], dim=1)

        transformer_options["txt_size"] = context.shape[1]
        return diffusion_model._old_forward(x, timestep, context, y, guidance, control=None, transformer_options={}, **kwargs)

    diffusion_model.forward = new_forward
    return diffusion_model
