from modules import scripts
from json import dumps
import re

from couple.mapping import (
    empty_tensor,
    basic_mapping,
    advanced_mapping,
    mask_mapping,
)

from couple.ui import couple_UI
from couple.ui_funcs import validate_mapping, parse_mapping

from couple.attention_couple import AttentionCouple
forgeAttentionCouple = AttentionCouple()

VERSION = "1.6.R"

from couple.gr_version import js


class ForgeCouple(scripts.Script):

    def __init__(self):
        self.couples: list = None

    def title(self):
        return "Forge Couple"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, is_img2img):
        return couple_UI(self, is_img2img, f"{self.title()} v{VERSION}")

    def after_component(self, component, **kwargs):
        if kwargs.get("elem_id") in (
            "img2img_image",
            "img2img_sketch",
            "inpaint_sketch",
            "img_inpaint_base",
        ):
            component.change(
                None, component, None, **js("(img) => { ForgeCouple.preview(img); }")
            )

    def parse_networks(self, prompt: str) -> str:
        """LoRAs are already parsed"""
        pattern = re.compile(r"<.*?>")
        cleaned = re.sub(pattern, "", prompt)

        return cleaned

    def after_extra_networks_activate(
        self,
        p,
        enable: bool,
        mode: str,
        separator: str,
        direction: str,
        background: str,
        background_weight: float,
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

        match mode:
            case "Basic":
                if len(couples) < (3 if background != "None" else 2):
                    print(
                        f"\n\n[Couple] Not Enough Lines in Prompt...\nCurrent: {len(couples)} / Required: {3 if background != 'None' else 2}\n\n"
                    )

            case "Mask":
                if not mapping or len(mapping) != len(couples) - int(
                    background in ("First Line", "Last Line")
                ):
                    print(
                        f"\n\n[Couple] Number of Couples and Masks is not the same...\nCurrent: {len(couples)} / Required: {len(mapping) + int(background in ('First Line', 'Last Line'))}\n\n"
                    )
                    self.couples = None
                    return

            case "Advanced":
                if not validate_mapping(mapping):
                    self.couples = None
                    return

                if not mapping or (len(parse_mapping(mapping)) != len(couples)):
                    print(
                        f"\n\n[Couple] Number of Couples and Mapping is not the same...\nCurrent: {len(couples)} / Required: {len(parse_mapping(mapping))}\n\n"
                    )
                    self.couples = None
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
            p.extra_generation_params["forge_couple_background_weight"] = (
                background_weight
            )
        elif mode == "Advanced":
            p.extra_generation_params["forge_couple_mapping"] = dumps(mapping)
        # ===== Infotext =====

        self.couples = couples

    def process_before_every_sampling(
        self,
        p,
        enable: bool,
        mode: str,
        separator: str,
        direction: str,
        background: str,
        background_weight: float,
        mapping: list,
        *args,
        **kwargs,
    ):

        if not enable or not self.couples:
            return

        # ===== Init =====
        unet = p.sd_model.forge_objects.unet

        WIDTH: int = p.width
        HEIGHT: int = p.height
        IS_HORIZONTAL: bool = direction == "Horizontal"

        LINE_COUNT: int = len(self.couples)

        if mode in ("Basic", "Mask"):
            BG_WEIGHT: float = (
                0.0
                if (background not in ("First Line", "Last Line"))
                else max(0.1, background_weight)
            )

        if mode == "Basic":
            TILE_COUNT: int = LINE_COUNT - int(
                background in ("First Line", "Last Line")
            )
            TILE_WEIGHT: float = (
                1.25 if (background not in ("First Line", "Last Line")) else 1.0
            )
            TILE_SIZE: int = (
                (WIDTH if IS_HORIZONTAL else HEIGHT) - 1
            ) // TILE_COUNT + 1
        # ===== Init =====

        # ===== Tiles =====
        match mode:
            case "Basic":
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

            case "Mask":
                ARGs = mask_mapping(
                    p.sd_model,
                    self.couples,
                    WIDTH,
                    HEIGHT,
                    LINE_COUNT,
                    mapping,
                    background,
                    BG_WEIGHT,
                )

            case "Advanced":
                ARGs = advanced_mapping(
                    p.sd_model, self.couples, WIDTH, HEIGHT, mapping
                )
        # ===== Tiles =====

        assert len(ARGs.keys()) // 2 == LINE_COUNT

        base_mask = empty_tensor(HEIGHT, WIDTH)
        patched_unet = forgeAttentionCouple.patch_unet(unet, base_mask, ARGs)
        p.sd_model.forge_objects.unet = patched_unet
