from modules.ui_components import ToolButton
from PIL import Image
import gradio as gr

from .ui_funcs import DEFAULT_MAPPING, visualize_mapping, on_entry
from .gr_version import js


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
                ["Basic", "Advanced"], label="Region Assignment", value="Basic", scale=3
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

                background = gr.Radio(
                    ["None", "First Line", "Last Line"],
                    label="Global Effect",
                    value="None",
                    scale=3,
                )

                background_weight = gr.Slider(
                    minimum=0.1,
                    maximum=1.0,
                    step=0.1,
                    value=0.5,
                    label="Global Effect Weight",
                    scale=1,
                )

        with gr.Group(visible=False, elem_classes="fc_adv") as adv_settings:
            with gr.Row(elem_classes="fc_mapping_btns"):
                gr.Button("Default Mapping", elem_classes="fc_reset_btn")

            gr.HTML('<div class="fc_mapping"></div>')

            mapping = gr.JSON(value=DEFAULT_MAPPING, visible=False)

            mapping_paste_field = gr.Textbox(
                visible=False, elem_classes="fc_paste_field"
            )
            mapping_paste_field.change(
                on_entry, mapping_paste_field, mapping, show_progress="hidden"
            ).success(None, **js(f'() => {{ ForgeCouple.onPaste("{m}"); }}'))

            mapping_entry_field = gr.Textbox(
                visible=False, elem_classes="fc_entry_field"
            )
            mapping_entry_field.change(
                on_entry, mapping_entry_field, mapping, show_progress="hidden"
            ).success(None, **js(f'() => {{ ForgeCouple.preview("{m}"); }}'))

            with gr.Group(elem_classes="fc_row_btns"):
                with gr.Row():
                    with gr.Column():
                        ToolButton(
                            value="\U0001F195",
                            elem_id="fc_up_btn",
                            tooltip="Add a New Row above the Selected Row",
                        )
                        ToolButton(
                            value="\U0001F195",
                            elem_id="fc_dn_btn",
                            tooltip="Add a New Row below the Selected Row",
                        )
                    ToolButton(
                        value="\U0000274C",
                        elem_id="fc_del_btn",
                        tooltip="Delete the Selected Row",
                    )

            with gr.Column(elem_classes="fc_bg_btns"):
                ToolButton(
                    value="\U0001F4C2",
                    elem_id="fc_load_img_btn",
                    tooltip="Load a background image for the mapping visualization",
                )
                if is_img2img:
                    ToolButton(
                        value="\U000023CF",
                        elem_id="fc_load_i2i_img_btn",
                        tooltip="Load the img2img image as the background image",
                    )
                ToolButton(
                    value="\U0001F5D1",
                    elem_id="fc_clear_img_btn",
                    tooltip="Remove the background image",
                )

            preview_img = gr.Image(
                value=Image.new("RGB", (1, 1), "black"),
                image_mode="RGBA",
                label="Mapping Preview",
                elem_classes="fc_preview_img",
                type="pil",
                interactive=False,
                height=512,
                show_download_button=False,
                show_label=False,
            )

            preview_res = gr.Textbox(
                lines=1,
                max_lines=1,
                visible=False,
                interactive=True,
                elem_classes="fc_preview_res",
            )

            preview_btn = gr.Button(
                visible=False,
                interactive=True,
                elem_classes="fc_preview",
            )

            preview_btn.click(
                visualize_mapping,
                [preview_res, mapping],
                preview_img,
                show_progress="hidden",
            ).success(None, **js(f'() => {{ ForgeCouple.updateColors("{m}"); }}'))

        def on_mode_change(choice):
            if choice == "Basic":
                return [
                    gr.update(visible=True),
                    gr.update(visible=False),
                ]
            else:
                return [
                    gr.update(visible=False),
                    gr.update(visible=True),
                ]

        mode.change(on_mode_change, mode, [basic_settings, adv_settings])

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

        for comp in (mapping, preview_res):
            comp.do_not_save_to_config = True

    return [
        enable,
        mode,
        separator,
        direction,
        background,
        background_weight,
        mapping,
    ]
