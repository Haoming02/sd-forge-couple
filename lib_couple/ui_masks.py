from PIL import Image
import gradio as gr
import numpy as np

from .gr_version import is_gradio_4
from .ui_funcs import COLORS


class CoupleMaskData:

    def __init__(self):
        self.masks: list[Image.Image] = []

    def get_masks(self) -> list[Image.Image]:
        return self.masks

    def mask_ui(self, btn: gr.Button, res: gr.Textbox):
        return self._mask_ui_4(btn, res) if is_gradio_4 else self._mask_ui_3(btn, res)

    def _mask_ui_3(self, btn, res) -> list[gr.components.Component]:

        msk_btn_empty = gr.Button("Create Empty Image", elem_classes="round-btn")

        msk_canvas = gr.Image(
            label="Mask Canvas",
            show_label=True,
            source="upload",
            interactive=True,
            type="pil",
            tool="sketch",
            image_mode="L",
            brush_color="#ffffff",
        )

        mask_index = gr.Number(value=0, visible=False)

        with gr.Row():
            msk_btn_save = gr.Button("Save", elem_classes="round-btn")
            msk_btn_delete = gr.Button("Delete", elem_classes="round-btn")

        gr.HTML('<div class="fc_masks"></div>')

        msk_preview = gr.Image(
            label="Mask Preview",
            image_mode="RGB",
            type="pil",
            show_label=True,
            show_download_button=False,
            interactive=False,
        )

        msk_gallery = gr.Gallery(
            label="Stored Masks",
            show_label=True,
            show_share_button=False,
            show_download_button=False,
            interactive=False,
            visible=False,
        )

        msk_btn_reset = gr.Button("Reset All Masks", elem_classes="round-btn")

        msk_btn_empty.click(fn=self._create_empty, inputs=[res], outputs=[msk_canvas])

        msk_btn_save.click(
            fn=self._write_mask,
            inputs=[msk_canvas],
            outputs=[msk_gallery, msk_preview],
        )

        msk_btn_reset.click(fn=self._reset_masks, outputs=[msk_gallery, msk_preview])

        for comp in (
            msk_btn_empty,
            msk_canvas,
            mask_index,
            msk_btn_save,
            msk_btn_delete,
            msk_preview,
            msk_gallery,
            msk_btn_reset,
        ):
            comp.do_not_save_to_config = True

        btn.click(
            fn=self._refresh_resolution,
            inputs=[res],
            outputs=[msk_gallery, msk_preview],
        )

    def _mask_ui_4(self, btn, res) -> list[gr.components.Component]:
        raise NotImplementedError

    @staticmethod
    def _create_empty(resolution: str) -> Image.Image:
        w, h = [int(v) for v in resolution.split("x")]
        return Image.new("L", (w, h), "black")

    def _generate_preview(self) -> Image.Image:
        if not self.masks:
            return Image.new(("RGB"), (64, 64))

        res: tuple[int, int] = self.masks[0].size
        bg = Image.new("RGBA", res, "black")

        for i, mask in enumerate(self.masks):
            color = Image.new("RGB", res, COLORS[i % 7])
            alpha = Image.fromarray(np.asarray(mask).astype(np.uint8) * 128)
            rgba = Image.merge("RGBA", [*color.split(), alpha.convert("L")])
            bg.paste(rgba, (0, 0), rgba)

        return bg

    def _refresh_resolution(
        self, resolution: str
    ) -> list[list[Image.Image], Image.Image]:

        if not self.masks:
            return [gr.update(), gr.update()]

        w, h = [int(v) for v in resolution.split("x")]
        ow, oh = self.masks[0].size

        if w != ow and h != oh:
            new_list: list[Image.Image] = []
            for mask in self.masks:
                new_list.append(mask.resize((w, h)))
            self.masks = new_list

        preview = self._generate_preview()
        return [self.masks, preview]

    def _reset_masks(self) -> list[list[Image.Image], Image.Image]:
        self.masks.clear()
        preview = self._generate_preview()
        return [self.masks, preview]

    def _delete_mask(self, index) -> list[Image.Image]:
        return self.masks

    def _write_mask(
        self, img: None | dict | Image.Image
    ) -> list[list[Image.Image], Image.Image]:

        if img is None:
            return [self.masks, gr.update()]

        if isinstance(img, dict):
            img = img.get("mask", None)

        assert isinstance(img, Image.Image)

        if not bool(img.getbbox()):
            return [self.masks, gr.update()]

        self.masks.append(img.convert("1"))

        preview = self._generate_preview()
        return [self.masks, preview]
