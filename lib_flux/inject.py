"""
Credit: logtd
https://github.com/logtd/ComfyUI-Fluxtapoz/blob/main/nodes/configure_modified_flux_node.py
"""

from .layers import inject_blocks
from .model import inject_flux


class ConfigureModifiedFluxNode:

    @staticmethod
    def apply(model):
        inject_flux(model.model.diffusion_model)
        inject_blocks(model.model.diffusion_model)
        return model
