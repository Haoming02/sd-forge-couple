from modules import scripts
from typing import Callable
from json import dumps
import re

from lib_couple.mapping import (
    empty_tensor,
    basic_mapping,
    advanced_mapping,
    mask_mapping,
)

from lib_couple.ui import couple_UI
from lib_couple.ui_funcs import validate_mapping
from lib_couple.attention_couple import AttentionCouple
from lib_couple.gr_version import js


VERSION = "3.2.1"


class ForgeCouple(scripts.Script):
    forgeAttentionCouple = AttentionCouple()

    def __init__(self):
        self.couples: list = None
        self.get_mask: Callable = None

    def title(self):
        return "Forge Couple"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, is_img2img):
        return couple_UI(self, is_img2img, f"{self.title()} v{VERSION}")

    def after_component(self, component, **kwargs):
        if not (elem_id := kwargs.get("elem_id", None)):
            return

        if elem_id in ("txt2img_width", "txt2img_height"):
            component.change(None, **js('() => { ForgeCouple.preview("t2i"); }'))

        elif elem_id in ("img2img_width", "img2img_height"):
            component.change(None, **js('() => { ForgeCouple.preview("i2i"); }'))

    @staticmethod
    def strip_networks(prompt: str) -> str:
        """LoRAs are already parsed thus no longer needed"""
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
        prepend_cmp: str,
        prepend_ignore: str,
        append_cmp: str,
        append_ignore: str,
        *args,
        **kwargs,
    ):
        if not enable:
            return

        separator = (
            "\n"
            if not separator.strip()
            else "\n".join(
                [part.strip() for part in (separator.replace("\\n", "\n").split("\n"))]
            )
        )

        raw_separator = separator.replace("\n", "\\n")

        # Webui & API Usages...
        if mode == "Mask":
            mapping: list = self.get_mask() or mapping
            assert isinstance(mapping[0], dict)

        couples: list[str] = []

        chunks = kwargs["prompts"][0].split(separator)
        for chunk in chunks:
            prompt = self.strip_networks(chunk).strip()
            couples.append(prompt)

        match mode:
            case "Basic":
                if len(couples) < (3 - int(background == "None")):
                    print("\n[Couple] Not Enough Lines in Prompt...")
                    print(f"\t[{len(couples)} / {3 - int(background == 'None')}]\n")
                    self.couples = None
                    return

            case "Mask":
                if not mapping:
                    print("\n[Couple] No Mapping...?\n")
                    self.couples = None
                    return

                required: int = len(mapping) + int(background != "None")
                if len(couples) != required:
                    print("\n[Couple] Number of Couples and Masks is not the same...")
                    print(f"\t[{len(couples)} / {required}]\n")
                    self.couples = None
                    return

            case "Advanced":
                if not mapping:
                    print("\n[Couple] No Mapping...?\n")
                    self.couples = None
                    return

                if not validate_mapping(mapping):
                    self.couples = None
                    return

                if len(couples) != len(mapping):
                    print("\n[Couple] Number of Couples and Mapping is not the same...")
                    print(f"\t[{len(couples)} / {len(mapping)}]\n")
                    self.couples = None
                    return

        # ===== Infotext =====
        p.extra_generation_params["forge_couple"] = True
        p.extra_generation_params["forge_couple_separator"] = raw_separator
        p.extra_generation_params["forge_couple_mode"] = mode

        if mode == "Advanced":
            p.extra_generation_params["forge_couple_mapping"] = dumps(mapping)

        else:
            p.extra_generation_params.update(
                {
                    "forge_couple_background": background,
                    "forge_couple_background_weight": background_weight,
                }
            )

            if mode == "Basic":
                p.extra_generation_params["forge_couple_direction"] = direction

        prepend_cmp: str = prepend_cmp.strip()
        append_cmp: str = append_cmp.strip()
        l = len(couples)

        if prepend_cmp:
            p_ig: list[int] = [int(v) for v in prepend_ignore.split(",") if v.strip()]
            for i in range(l):
                if i not in p_ig:
                    couples[i] = f"{prepend_cmp}{couples[i]}"
            p.extra_generation_params["forge_couple_prepend_prompt"] = prepend_cmp
            p.extra_generation_params["forge_couple_prepend_ignore"] = prepend_ignore

        if append_cmp:
            a_ig: list[int] = [int(v) for v in append_ignore.split(",") if v.strip()]
            for i in range(l):
                if i not in a_ig:
                    couples[i] = f"{couples[i]}{append_cmp}"
            p.extra_generation_params["forge_couple_append_prompt"] = append_cmp
            p.extra_generation_params["forge_couple_append_ignore"] = append_ignore
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
        NO_BACKGROUND: bool = background == "None"

        LINE_COUNT: int = len(self.couples)

        if mode != "Advanced":
            BG_WEIGHT: float = 0.0 if NO_BACKGROUND else max(0.1, background_weight)

        if mode == "Basic":
            TILE_COUNT: int = LINE_COUNT - int(not NO_BACKGROUND)
            TILE_WEIGHT: float = 1.25 if NO_BACKGROUND else 1.0
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
                mapping: list[dict] = self.get_mask() or mapping

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
        patched_unet = self.forgeAttentionCouple.patch_unet(unet, base_mask, ARGs)
        p.sd_model.forge_objects.unet = patched_unet
