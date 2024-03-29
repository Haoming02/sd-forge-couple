from modules.prompt_parser import SdConditioning
from modules import scripts, shared
import torch
import re

from scripts.attention_couple import AttentionCouple
from scripts.couple_ui import couple_UI, validata_mapping

forgeAttentionCouple = AttentionCouple()

VERSION = "1.2.1"


class ForgeCouple(scripts.Script):

    def __init__(self):
        self.couples: list = None

    def title(self):
        return "Forge Couple"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, *args, **kwargs):
        return couple_UI(self, f"{self.title()} {VERSION}")

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

        if not separator.strip():
            separator = "\n"

        couples = []

        chunks = kwargs["prompts"][0].split(separator)
        for chunk in chunks:
            prompt = self.parse_networks(chunk).strip()

            if not prompt.strip():
                # Skip Empty Lines
                continue

            couples.append(prompt)

        if len(couples) < (3 if background != "None" else 2):
            print("\n\n[Couple] Not Enough Lines in Prompt...\n")
            self.couples = None
            return

        if (mode == "Advanced") and (len(couples) != len(mapping)):
            print("\n\n[Couple] Number of Couples and Mapping is not the same...\n")
            self.couples = None
            return

        if (mode == "Advanced") and not validata_mapping(mapping):
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
        if not separator.strip():
            p.extra_generation_params["forge_couple_separator"] = "\n"
        p.extra_generation_params["forge_couple_mode"] = mode
        if mode == "Basic":
            p.extra_generation_params["forge_couple_direction"] = direction
            p.extra_generation_params["forge_couple_background"] = background
        else:
            p.extra_generation_params["forge_couple_mapping"] = mapping
        # ===== Infotext =====

        # ===== Init =====
        unet = p.sd_model.forge_objects.unet
        IS_SDXL: bool = hasattr(unet.model.diffusion_model, "label_emb")

        WIDTH: int = p.width
        HEIGHT: int = p.height
        IS_HORIZONTAL: bool = direction == "Horizontal"

        LINE_COUNT: int = len(self.couples)
        TILE_COUNT: int = LINE_COUNT - (background != "None")

        TILE_WEIGHT: float = 1.25 if background == "None" else 1.0
        BG_WEIGHT: float = 0.0 if background == "None" else 0.5

        TILE_SIZE: int = ((WIDTH if IS_HORIZONTAL else HEIGHT) - 1) // TILE_COUNT + 1

        ARGs: dict = {}
        # ===== Init =====

        # ===== Tiles =====
        for T in range(LINE_COUNT):
            mask = torch.zeros((HEIGHT, WIDTH))
            pos_cond = None

            # ===== Cond =====
            texts = SdConditioning([self.couples[T]], False, WIDTH, HEIGHT, None)
            cond = shared.sd_model.get_learned_conditioning(texts)
            pos_cond = [[cond["crossattn"]]] if IS_SDXL else [[cond]]
            # ===== Cond =====

            # ===== Mask =====
            if background == "First Line":
                if T == 0:
                    mask = torch.ones((HEIGHT, WIDTH)) * BG_WEIGHT
                else:
                    if IS_HORIZONTAL:
                        mask[:, (T - 1) * TILE_SIZE : T * TILE_SIZE] = TILE_WEIGHT
                    else:
                        mask[(T - 1) * TILE_SIZE : T * TILE_SIZE, :] = TILE_WEIGHT
            else:
                if IS_HORIZONTAL:
                    mask[:, T * TILE_SIZE : (T + 1) * TILE_SIZE] = TILE_WEIGHT
                else:
                    mask[T * TILE_SIZE : (T + 1) * TILE_SIZE, :] = TILE_WEIGHT
            # ===== Mask =====

            ARGs[f"cond_{T + 1}"] = pos_cond
            ARGs[f"mask_{T + 1}"] = mask.unsqueeze(0)

        if background == "Last Line":
            ARGs[f"mask_{LINE_COUNT}"] = (
                torch.ones((HEIGHT, WIDTH)) * BG_WEIGHT
            ).unsqueeze(0)
        # ===== Tiles =====

        assert len(ARGs.keys()) // 2 == LINE_COUNT

        base_mask = torch.zeros((HEIGHT, WIDTH)).unsqueeze(0)
        patched_unet = forgeAttentionCouple.patch_unet(unet, base_mask, ARGs)
        p.sd_model.forge_objects.unet = patched_unet
