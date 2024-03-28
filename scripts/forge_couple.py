from modules.prompt_parser import SdConditioning
from modules import scripts, shared
import gradio as gr
import torch
import re

from scripts.attention_couple import AttentionCouple
forgeAttentionCouple = AttentionCouple()

VERSION = 1.2


class ForgeCouple(scripts.Script):

    def __init__(self):
        self.couples: list = None

    def title(self):
        return "Forge Couple"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, *args, **kwargs):
        with gr.Accordion(label=f"{self.title()} v{VERSION}", open=False):
            with gr.Row():
                enable = gr.Checkbox(label="Enable")

                direction = gr.Radio(
                    ["Horizontal", "Vertical"],
                    label="Tile Direction",
                    value="Horizontal",
                )

            with gr.Row():
                background = gr.Radio(
                    ["None", "First Line", "Last Line"],
                    label="Global Effect",
                    value="None",
                )

        self.paste_field_names = []
        self.infotext_fields = [
            (enable, "forge_couple"),
            (direction, "forge_couple_direction"),
            (background, "forge_couple_background"),
        ]

        for comp, name in self.infotext_fields:
            comp.do_not_save_to_config = True
            self.paste_field_names.append(name)

        return [enable, direction, background]

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
        *args,
        **kwargs,
    ):
        if not enable:
            return

        couples = []

        chunks = kwargs["prompts"][0].split("\n")
        for chunk in chunks:
            prompt = self.parse_networks(chunk).strip()

            if not prompt.strip():
                # Skip Empty Lines
                continue

            couples.append(prompt)

        if len(couples) < (3 if background != "None" else 2):
            print("\n[Couple] Not Enough Lines in Prompt...\n")
            self.couples = None
            return

        self.couples = couples

    def process_before_every_sampling(
        self,
        p,
        enable: bool,
        direction: str,
        background: str,
        *args,
        **kwargs,
    ):

        if not enable or not self.couples:
            return

        p.extra_generation_params["forge_couple"] = True
        p.extra_generation_params["forge_couple_direction"] = direction
        p.extra_generation_params["forge_couple_background"] = background

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

        assert len(ARGs.keys()) // 2 == LINE_COUNT

        base_mask = torch.zeros((HEIGHT, WIDTH)).unsqueeze(0)

        patched_unet = forgeAttentionCouple.patch_unet(unet, base_mask, ARGs)
        p.sd_model.forge_objects.unet = patched_unet
