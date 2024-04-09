from modules import scripts
import re
from modules.processing import StableDiffusionProcessing

from scripts.couple_mapping import empty_tensor, get_masked_conditionings_basic, get_masked_conditionings_advanced
from scripts.couple_ui import couple_UI

from scripts.attention_couple import AttentionCouple
forgeAttentionCouple = AttentionCouple()

VERSION = "1.4.0"


class ForgeCouple(scripts.Script):
    prompts: list[str]

    def __init__(self):
        self.prompts = None

    def title(self):
        return "Forge Couple"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, is_img2img):
        return couple_UI(self, f"{self.title()} {VERSION}", is_img2img)

    def after_extra_networks_activate(
        self,
        p: StableDiffusionProcessing,
        enable: bool,
        basic_direction: str,
        basic_background_type: str,
        separator: str,
        mode: str,
        advanced_regions: str,
        *args,
        prompts: list[str],
        **kwargs,
    ):
        self.prompts = None
        if not enable:
            return

        separator = separator.strip()
        if not separator:
            separator = "\n"

        region_prompts: list[str] = []
        for region_prompt in prompts[0].split(separator):
            region_prompt = re.sub(r"<.*?>", "", region_prompt)
            if not region_prompt.strip():
                # Skip Empty Lines
                continue

            region_prompts.append(region_prompt)

        if mode == "Basic" and len(region_prompts) < (3 if basic_background_type != "None" else 2):
            print("\n\n[Couple] Not Enough Lines in Prompt...\n\n")
            return

        # ===== Infotext =====
        p.extra_generation_params["forge_couple"] = True
        p.extra_generation_params["forge_couple_separator"] = "\n" if not separator.strip() else separator
        p.extra_generation_params["forge_couple_mode"] = mode
        if mode == "Basic":
            p.extra_generation_params["forge_couple_direction"] = basic_direction
            p.extra_generation_params["forge_couple_background"] = basic_background_type
        else:
            p.extra_generation_params["forge_couple_regions"] = advanced_regions
        # ===== Infotext =====
        
        self.prompts = region_prompts

    def process_before_every_sampling(
        self,
        p: StableDiffusionProcessing,
        enable: bool,
        basic_direction: str,
        basic_background_type: str,
        separator: str,
        mode: str,
        advanced_regions: str,
        *args,
        **kwargs,
    ):
        if not enable:
            return
        
        if mode == "Basic" and not self.prompts:
            return
        
        if mode == "Advanced" and not advanced_regions:
            return

        # ===== Init =====
        unet = p.sd_model.forge_objects.unet

        image_width: int = p.width
        image_height: int = p.height
        basic_mapping_horizontal: bool = basic_direction == "Horizontal"

        num_prompts: int = len(self.prompts)

        if mode == "Basic":
            num_basic_regions: int = num_prompts - (basic_background_type != "None")
            basic_region_size: int = (
                (image_width if basic_mapping_horizontal else image_height) - 1
            ) // num_basic_regions + 1
            basic_region_weight: float = 1.25 if basic_background_type == "None" else 1.0
            basic_background_weight: float = 0.0 if basic_background_type == "None" else 0.5
        # ===== Init =====

        # ===== Tiles =====
        if mode == "Basic":
            masked_conds = get_masked_conditionings_basic(
                p.sd_model,
                image_width,
                image_height,
                self.prompts,
                basic_background_type,
                basic_background_weight,
                basic_mapping_horizontal,
                basic_region_size,
                basic_region_weight
            )
        else:
            masked_conds = get_masked_conditionings_advanced(
                p.sd_model,
                separator.join(self.prompts),
                0.5,
                image_width,
                image_height,
                advanced_regions
            )
        # ===== Tiles =====

        base_mask = empty_tensor(image_height, image_width)
        patched_unet = forgeAttentionCouple.patch_unet(unet, image_width, image_height, base_mask, masked_conds)
        p.sd_model.forge_objects.unet = patched_unet
