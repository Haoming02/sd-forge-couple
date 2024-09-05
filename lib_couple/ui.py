from .ui_masks import CoupleMaskData
from .ui_adv import advanced_ui
from .gr_version import js

import gradio as gr


def couple_UI(script, is_img2img: bool, title: str):
    m: str = "i2i" if is_img2img else "t2i"

    with gr.Accordion(
        label=title,
        elem_id=f"forge_couple_{m}",
        open=False,
    ):
        with gr.Row():
            enable = gr.Checkbox(label="Enable", elem_classes="fc_enable", scale=2)

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
            preview_btn, preview_res, mapping_paste_field, mapping = advanced_ui(
                is_img2img, m, mode
            )

        with gr.Group(visible=False, elem_classes="fc_msk") as msk_settings:
            couple_mask = CoupleMaskData(is_img2img)
            couple_mask.mask_ui(preview_btn, preview_res, mode)
            script.get_mask = couple_mask.get_masks

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
            (mode, "forge_couple_mode"),
            (separator, "forge_couple_separator"),
            (direction, "forge_couple_direction"),
            (background, "forge_couple_background"),
            (background_weight, "forge_couple_background_weight"),
            (mapping_paste_field, "forge_couple_mapping"),
        ]

        for comp, name in script.infotext_fields:
            comp.do_not_save_to_config = True
            script.paste_field_names.append(name)

    return [
        enable,
        mode,
        separator,
        direction,
        background,
        background_weight,
        mapping,
    ]
