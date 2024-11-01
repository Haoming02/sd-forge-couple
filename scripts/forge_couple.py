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


VERSION = "3.3.0"


class ForgeCouple(scripts.Script):
    forgeAttentionCouple = AttentionCouple()

    def __init__(self):
        self.couples: list = None
        self.get_mask: Callable = None
        self.is_hr: bool = False

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

    def setup(self, *args, **kwargs):
        self.is_hr = False

    def before_hr(self, *args, **kwargs):
        self.is_hr = True

    @staticmethod
    def parse_common_prompt(prompt: str, brackets: tuple[str]) -> str:
        common_prompts: dict[str, str] = {}
        op, cs = brackets

        pattern = rf"{op}([^{op}{cs}]+?):([^{op}{cs}]+?){cs}"
        matches = list(re.finditer(pattern, prompt))
        for m in matches:
            key: str = m.group(1).strip()
            val: str = m.group(2).strip()
            prompt = prompt.replace(m.group(0), val)
            common_prompts.update({key: val})

        pattern = rf"{op}([^{op}{cs}]+?){cs}"
        matches = list(re.finditer(pattern, prompt))
        for m in matches:
            key: str = m.group(1).strip()
            if key in common_prompts:
                prompt = prompt.replace(m.group(0), common_prompts[key])

        return prompt

    def after_extra_networks_activate(
        self,
        p,
        enable: bool,
        disable_hr: bool,
        mode: str,
        separator: str,
        direction: str,
        background: str,
        background_weight: float,
        mapping: list,
        common_parser: str,
        common_debug: bool,
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

        prompts: str = kwargs["prompts"][0]

        if common_parser != "off":
            prompts = self.parse_common_prompt(prompts, common_parser.split(" "))

            if common_debug:
                print("\n\n[Forge Couple] Common Prompts Applied:")
                print(prompts)
                print("\n")

        couples: list[str] = [chunk.strip() for chunk in prompts.split(separator)]
        self.couples = None

        match mode:
            case "Basic":
                if len(couples) < (3 - int(background == "None")):
                    raise RuntimeError(
                        "[Forge Couple] Not Enough Lines in Prompt... "
                        + f"[{len(couples)} / {3 - int(background == 'None')}]"
                    )

            case "Mask":
                if not mapping:
                    raise RuntimeError("[Forge Couple] No Mapping...?")

                required: int = len(mapping) + int(background != "None")
                if len(couples) != required:
                    raise RuntimeError(
                        "[Forge Couple] Number of Couples and Masks is not the same... "
                        + f"[{len(couples)} / {required}]"
                    )

            case "Advanced":
                if not mapping:
                    raise RuntimeError("[Forge Couple] No Mapping...?")

                if not validate_mapping(mapping):
                    return

                if len(couples) != len(mapping):
                    raise RuntimeError(
                        "[Forge Couple] Number of Couples and Mapping is not the same... "
                        + f"[{len(couples)} / {len(mapping)}]"
                    )

        # ===== Infotext =====
        fc_param: dict = {}

        fc_param["forge_couple"] = True
        fc_param["forge_couple_compatibility"] = disable_hr
        fc_param["forge_couple_mode"] = mode
        fc_param["forge_couple_separator"] = raw_separator
        if mode == "Basic":
            fc_param["forge_couple_direction"] = direction
        if mode == "Advanced":
            fc_param["forge_couple_mapping"] = dumps(mapping)
        else:
            fc_param["forge_couple_background"] = background
            fc_param["forge_couple_background_weight"] = background_weight
        fc_param["forge_couple_common_parser"] = common_parser

        p.extra_generation_params.update(fc_param)
        # ===== Infotext =====

        self.couples = couples

    def process_before_every_sampling(
        self,
        p,
        enable: bool,
        disable_hr: bool,
        mode: str,
        separator: str,
        direction: str,
        background: str,
        background_weight: float,
        mapping: list,
        *args,
        **kwargs,
    ):

        if not enable or self.couples is None:
            return

        if disable_hr and self.is_hr:
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
