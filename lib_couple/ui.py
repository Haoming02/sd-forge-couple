from typing import Optional

import gradio as gr

from .gr_version import js
from .ui_adv import advanced_ui
from .ui_funcs import on_pull
from .ui_masks import CoupleMaskData


class CoupleDataTransfer:
    """Handle sending data from t2i/i2i to i2i/t2i"""

    T2I_MASK: Optional[CoupleMaskData] = None
    I2I_MASK: Optional[CoupleMaskData] = None

    T2I_ADV_DATA: Optional[gr.JSON] = None
    T2I_ADV_PASTE: Optional[gr.Textbox] = None
    T2I_ADV_PULL: Optional[gr.Button] = None

    I2I_ADV_DATA: Optional[gr.JSON] = None
    I2I_ADV_PASTE: Optional[gr.Textbox] = None
    I2I_ADV_PULL: Optional[gr.Button] = None

    A_HOOKED: bool = False
    M_HOOKED: bool = False

    @classmethod
    def hook_adv(cls):
        assert not any(
            [
                cls.T2I_ADV_DATA is None,
                cls.T2I_ADV_PASTE is None,
                cls.T2I_ADV_PULL is None,
                cls.I2I_ADV_DATA is None,
                cls.I2I_ADV_PASTE is None,
                cls.I2I_ADV_PULL is None,
            ]
        )

        cls.I2I_ADV_PULL.click(
            fn=on_pull, inputs=cls.T2I_ADV_DATA, outputs=cls.I2I_ADV_PASTE
        )

        cls.T2I_ADV_PULL.click(
            fn=on_pull, inputs=cls.I2I_ADV_DATA, outputs=cls.T2I_ADV_PASTE
        )

        cls.A_HOOKED = True

    @classmethod
    def hook_mask(cls):
        assert cls.T2I_MASK is not None
        assert cls.I2I_MASK is not None

        cls.T2I_MASK.opposite = cls.I2I_MASK
        cls.I2I_MASK.opposite = cls.T2I_MASK

        cls.M_HOOKED = True

    @classmethod
    def webui_setup_done(cls) -> bool:
        return cls.A_HOOKED and cls.M_HOOKED


def couple_ui(script, is_img2img: bool, title: str):
    m: str = "i2i" if is_img2img else "t2i"

    with gr.Accordion(
        label=title,
        elem_id=f"forge_couple_{m}",
        open=False,
    ):
        with gr.Row():
            with gr.Column(elem_classes="fc-checkbox", scale=2):
                enable = gr.Checkbox(False, label="Enable")
                disable_hr = gr.Checkbox(True, label="Compatibility")

            mode = gr.Radio(
                ["Basic", "Advanced", "Mask"],
                label="Region Assignment",
                value="Basic",
                scale=3,
            )

            separator = gr.Textbox(
                value="",
                label="Couple Separator",
                lines=1,
                max_lines=1,
                placeholder="\\n",
                elem_classes="fc_separator",
                scale=1,
            )

        with gr.Group(visible=True, elem_classes="fc_bsc") as basic_settings:
            with gr.Row():
                direction = gr.Radio(
                    ["Horizontal", "Vertical"],
                    label="Tile Direction",
                    value="Horizontal",
                    scale=2,
                )

                placeholder = gr.Group(visible=False, elem_classes="fc_placeholder")
                placeholder.do_not_save_to_config = True

                background = gr.Radio(
                    ["None", "First Line", "Last Line"],
                    label="Global Effect",
                    value="None",
                    scale=3,
                    elem_classes="fc_global_effect",
                )

                background_weight = gr.Slider(
                    minimum=0.1,
                    maximum=1.0,
                    step=0.1,
                    value=0.5,
                    label="Global Effect Weight",
                    scale=1,
                    interactive=False,
                )

            def on_background_change(choice: str):
                return gr.update(interactive=(choice != "None"))

            background.change(
                on_background_change,
                background,
                background_weight,
                show_progress="hidden",
            ).success(None, **js(f'() => {{ ForgeCouple.onBackgroundChange("{m}"); }}'))

        with gr.Group(visible=False, elem_classes="fc_adv") as adv_settings:
            preview_btn, preview_res, mapping_paste_field, mapping, pull_btn = (
                advanced_ui(is_img2img, m, mode)
            )

            if not CoupleDataTransfer.webui_setup_done():
                if is_img2img:
                    CoupleDataTransfer.I2I_ADV_DATA = mapping
                    CoupleDataTransfer.I2I_ADV_PASTE = mapping_paste_field
                    CoupleDataTransfer.I2I_ADV_PULL = pull_btn
                    CoupleDataTransfer.hook_adv()  # img2img always happens after txt2img

                else:
                    CoupleDataTransfer.T2I_ADV_DATA = mapping
                    CoupleDataTransfer.T2I_ADV_PASTE = mapping_paste_field
                    CoupleDataTransfer.T2I_ADV_PULL = pull_btn

        with gr.Group(visible=False, elem_classes="fc_msk") as msk_settings:
            couple_mask = CoupleMaskData(is_img2img)
            couple_mask.mask_ui(preview_btn, preview_res, mode)

            if not CoupleDataTransfer.webui_setup_done():
                script.get_mask = couple_mask.get_masks
                if is_img2img:
                    CoupleDataTransfer.I2I_MASK = couple_mask
                    CoupleDataTransfer.hook_mask()  # img2img always happens after txt2img
                else:
                    CoupleDataTransfer.T2I_MASK = couple_mask

        with gr.Accordion(
            label="Common Prompts",
            elem_id=f"forge_couple_cmp_{m}",
            open=False,
        ):
            with gr.Row():
                common_parser = gr.Radio(
                    ("off", "{ }", "< >"), label="Syntax", value="{ }", scale=4
                )
                common_debug = gr.Checkbox(False, label="Debug", scale=1)
                common_debug.do_not_save_to_config = True

        def on_mode_change(choice: str):
            return [
                gr.update(visible=(choice in ("Basic", "Mask"))),
                gr.update(visible=(choice == "Basic")),
                gr.update(visible=(choice == "Advanced")),
                gr.update(visible=(choice == "Mask")),
                gr.update(visible=(choice == "Mask")),
            ]

        mode.change(
            on_mode_change,
            mode,
            [basic_settings, direction, adv_settings, msk_settings, placeholder],
            show_progress="hidden",
        ).success(fn=None, **js(f'() => {{ ForgeCouple.preview("{m}"); }}'))

        script.paste_field_names = []
        script.infotext_fields = [
            (enable, "forge_couple"),
            (disable_hr, "forge_couple_compatibility"),
            (mode, "forge_couple_mode"),
            (separator, "forge_couple_separator"),
            (direction, "forge_couple_direction"),
            (background, "forge_couple_background"),
            (background_weight, "forge_couple_background_weight"),
            (mapping_paste_field, "forge_couple_mapping"),
            (common_parser, "forge_couple_common_parser"),
        ]

        for comp, name in script.infotext_fields:
            comp.do_not_save_to_config = True
            script.paste_field_names.append(name)

    return [
        enable,
        disable_hr,
        mode,
        separator,
        direction,
        background,
        background_weight,
        mapping,
        common_parser,
        common_debug,
    ]
