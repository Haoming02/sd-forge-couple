from modules import scripts
import re

from scripts.couple_mapping import empty_tensor, basic_mapping, advanced_mapping
from scripts.couple_ui import couple_UI, validata_mapping, parse_mapping, hook_component

from scripts.attention_couple import AttentionCouple
forgeAttentionCouple = AttentionCouple()

VERSION = "1.3.5"


class ForgeCouple(scripts.Script):

    def __init__(self):
        self.couples: list = None

    def title(self):
        return "Forge Couple"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, is_img2img):
        return couple_UI(self, is_img2img, f"{self.title()} {VERSION}")

    def after_component(self, component, **kwargs):
        if "elem_id" in kwargs:
            hook_component(component, kwargs["elem_id"])

    def parse_networks(self, prompt: str) -> str:
        """LoRAs are already parsed"""
        pattern = re.compile(r"<.*?>")
        cleaned = re.sub(pattern, "", prompt)

        return cleaned

    def after_extra_networks_activate(
        self,
        p,
        enable: bool,
        direction: str,
        background: str,
        separator: str,
        mode: str,
        mapping: list,
        *args,
        **kwargs,
    ):
        if not enable:
            return

        separator = "\n" if not separator.strip() else separator.strip()

        couples = []

        chunks = kwargs["prompts"][0].split(separator)
        for chunk in chunks:
            prompt = self.parse_networks(chunk).strip()

            if not prompt.strip():
                # Skip Empty Lines
                continue

            couples.append(prompt)

        if (mode == "Basic") and len(couples) < (3 if background != "None" else 2):
            print(
                f"\n\n[Couple] Not Enough Lines in Prompt...\nCurrent: {len(couples)} / Required: {3 if background != 'None' else 2}\n\n"
            )
            self.couples = None
            return

        if (mode == "Advanced") and not validata_mapping(mapping):
            self.couples = None
            return

        if (mode == "Advanced") and (len(couples) != len(parse_mapping(mapping))):
            print(
                f"\n\n[Couple] Number of Couples and Mapping is not the same...\nCurrent: {len(couples)} / Required: {len(parse_mapping(mapping))}\n\n"
            )
            self.couples = None
            return

        self.couples = couples

    def process_before_every_sampling(
        self,
        p,
        enable: bool,
        direction: str,
        background: str,
        separator: str,
        mode: str,
        mapping: list,
        *args,
        **kwargs,
    ):

        if not enable or not self.couples:
            return

        # ===== Infotext =====
        p.extra_generation_params["forge_couple"] = True
        p.extra_generation_params["forge_couple_separator"] = (
            "\n" if not separator.strip() else separator.strip()
        )
        p.extra_generation_params["forge_couple_mode"] = mode
        if mode == "Basic":
            p.extra_generation_params["forge_couple_direction"] = direction
            p.extra_generation_params["forge_couple_background"] = background
        else:
            p.extra_generation_params["forge_couple_mapping"] = mapping
        # ===== Infotext =====

        # ===== Init =====
        unet = p.sd_model.forge_objects.unet

        WIDTH: int = p.width
        HEIGHT: int = p.height
        IS_HORIZONTAL: bool = direction == "Horizontal"

        LINE_COUNT: int = len(self.couples)
        TILE_COUNT: int = LINE_COUNT - (background != "None")

        if mode == "Basic":
            TILE_WEIGHT: float = 1.25 if background == "None" else 1.0
            BG_WEIGHT: float = 0.0 if background == "None" else 0.5

            TILE_SIZE: int = (
                (WIDTH if IS_HORIZONTAL else HEIGHT) - 1
            ) // TILE_COUNT + 1
        # ===== Init =====

        # ===== Tiles =====
        if mode == "Basic":
            ARGs = basic_mapping(
                p.sd_model,
                self.couples,
                WIDTH,
                HEIGHT,
                LINE_COUNT,
                IS_HORIZONTAL,
                background,
                TILE_SIZE,
                TILE_WEIGHT,
                BG_WEIGHT,
            )

        else:
            ARGs = advanced_mapping(p.sd_model, self.couples, WIDTH, HEIGHT, mapping)
        # ===== Tiles =====

        assert len(ARGs.keys()) // 2 == LINE_COUNT

        base_mask = empty_tensor(HEIGHT, WIDTH)
        patched_unet = forgeAttentionCouple.patch_unet(unet, base_mask, ARGs)
        p.sd_model.forge_objects.unet = patched_unet
