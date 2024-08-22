from PIL import Image
import gradio as gr
import numpy as np

from .gr_version import js, is_gradio_4
from .ui_funcs import COLORS


class CoupleMaskData:

    def __init__(self, is_img2img: bool):
        self.masks: list[Image.Image] = []
        self.mode: str = "i2i" if is_img2img else "t2i"

    def get_masks(self) -> list[Image.Image]:
        return self.masks

    def mask_ui(self, *args):
        return self._mask_ui_4(*args) if is_gradio_4 else self._mask_ui_3(*args)

    def _mask_ui_3(self, btn, res, mode) -> list[gr.components.Component]:

        msk_btn_empty = gr.Button("Create Empty Canvas", elem_classes="round-btn")

        gr.HTML(
            """
            <h2 align="center"><ins>Mask Canvas</ins></h2>
            <p align="center"><b>[Important]</b> Do <b>NOT</b> upload / paste an image to here...</p>
            """
        )

        msk_canvas = gr.Image(
            show_label=False,
            source="upload",
            interactive=True,
            type="pil",
            tool="color-sketch",
            image_mode="RGB",
            brush_color="#ffffff",
            elem_classes="fc_msk_canvas",
        )

        msk_canvas.change(
            fn=None,
            **js(f'() => {{ ForgeCouple.hideButtons("{self.mode}"); }}'),
        )

        mask_index = gr.Number(value=0, visible=False)

        with gr.Row():
            msk_btn_save = gr.Button("Save", elem_classes="round-btn")
            msk_btn_delete = gr.Button("Delete", elem_classes="round-btn")

        gr.HTML('<div class="fc_masks"></div>')

        gr.HTML('<h2 align="center"><ins>Mask Preview</ins></h2>')

        msk_preview = gr.Image(
            show_label=False,
            image_mode="RGB",
            type="pil",
            interactive=False,
            show_download_button=False,
            elem_classes="fc_msk_preview",
        )

        msk_gallery = gr.Gallery(
            show_label=False,
            show_share_button=False,
            show_download_button=False,
            interactive=False,
            visible=False,
            elem_classes="fc_msk_gal",
        )

        msk_btn_reset = gr.Button("Reset All Masks", elem_classes="round-btn")

        msk_btn_empty.click(fn=self._create_empty, inputs=[res], outputs=[msk_canvas])

        msk_btn_save.click(
            fn=self._write_mask,
            inputs=[msk_canvas],
            outputs=[msk_gallery, msk_preview],
        ).success(
            fn=None,
            **js(f'() => {{ ForgeCouple.populateMasks("{self.mode}"); }}'),
        )

        msk_btn_reset.click(
            fn=self._reset_masks, outputs=[msk_gallery, msk_preview]
        ).success(
            fn=None,
            **js(f'() => {{ ForgeCouple.populateMasks("{self.mode}"); }}'),
        )

        [
            setattr(comp, "do_not_save_to_config", True)
            for comp in (
                msk_btn_empty,
                msk_canvas,
                mask_index,
                msk_btn_save,
                msk_btn_delete,
                msk_preview,
                msk_gallery,
                msk_btn_reset,
            )
        ]

        btn.click(
            fn=self._refresh_resolution,
            inputs=[res, mode],
            outputs=[msk_gallery, msk_preview, msk_canvas],
        ).success(
            fn=None,
            **js(f'() => {{ ForgeCouple.populateMasks("{self.mode}"); }}'),
        )

    def _mask_ui_4(self, btn, res, mode) -> list[gr.components.Component]:
        raise NotImplementedError

    @staticmethod
    def _parse_resolution(resolution: str) -> tuple[int, int]:
        w, h = [int(v) for v in resolution.split("x")]
        while w * h > 1024 * 1024:
            w //= 2
            h //= 2

        return (w, h)

    @staticmethod
    def _create_empty(resolution: str) -> Image.Image:
        w, h = CoupleMaskData._parse_resolution(resolution)
        return Image.new("RGB", (w, h))

    def _generate_preview(self) -> Image.Image:
        if not self.masks:
            return None

        res: tuple[int, int] = self.masks[0].size
        bg = Image.new("RGBA", res, "black")

        for i, mask in enumerate(self.masks):
            color = Image.new("RGB", res, COLORS[i % 7])
            alpha = Image.fromarray(np.asarray(mask).astype(np.uint8) * 192)
            rgba = Image.merge("RGBA", [*color.split(), alpha.convert("L")])
            bg.paste(rgba, (0, 0), rgba)

        return bg

    def _refresh_resolution(
        self, resolution: str, mode: str
    ) -> list[list[Image.Image], Image.Image, Image.Image]:
        canvas = self._create_empty(resolution)

        if not self.masks or mode != "Mask":
            return [gr.update(), gr.update(), canvas]

        w, h = self._parse_resolution(resolution)

        self.masks = [mask.resize((w, h), Image.NEAREST) for mask in self.masks]

        preview = self._generate_preview()
        return [self.masks, preview, canvas]

    def _reset_masks(self) -> list[list[Image.Image], Image.Image]:
        self.masks.clear()
        preview = self._generate_preview()
        return [self.masks, preview]

    def _delete_mask(self, index: int) -> list[list[Image.Image], Image.Image]:
        if index >= len(self.masks):
            return [gr.update(), gr.update()]

        self.masks.pop(index)
        preview = self._generate_preview()
        return [self.masks, preview]

    def _write_mask(
        self, img: None | dict | Image.Image
    ) -> list[list[Image.Image], Image.Image]:

        if img is None:
            return [self.masks, gr.update()]

        if isinstance(img, dict):
            img = img.get("mask")

        assert isinstance(img, Image.Image)

        if not bool(img.getbbox()):
            return [self.masks, gr.update()]

        self.masks.append(img.convert("1"))

        preview = self._generate_preview()
        return [self.masks, preview]
