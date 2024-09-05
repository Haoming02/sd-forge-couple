from modules.ui_components import ToolButton
from .ui_funcs import DEFAULT_MAPPING, visualize_mapping, on_entry
from .gr_version import js

from PIL import Image
import gradio as gr


def advanced_ui(
    is_img2img: bool, m: str, mode: gr.Radio
) -> list[gr.components.Component]:

    with gr.Row(elem_classes="fc_mapping_btns"):
        gr.Button("Default Mapping", elem_classes="fc_reset_btn")

    gr.HTML('<div class="fc_mapping"></div>')

    mapping = gr.JSON(value=DEFAULT_MAPPING, visible=False)

    mapping_paste_field = gr.Textbox(visible=False, elem_classes="fc_paste_field")
    mapping_paste_field.change(
        on_entry, mapping_paste_field, mapping, show_progress="hidden"
    ).success(None, **js(f'() => {{ ForgeCouple.onPaste("{m}"); }}'))

    mapping_entry_field = gr.Textbox(visible=False, elem_classes="fc_entry_field")
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
        [mode, preview_res, mapping],
        preview_img,
        show_progress="hidden",
    ).success(None, **js(f'() => {{ ForgeCouple.updateColors("{m}"); }}'))

    for comp in (
        mapping,
        mapping_entry_field,
        preview_img,
        preview_res,
        preview_btn,
    ):
        comp.do_not_save_to_config = True

    return preview_btn, preview_res, mapping_paste_field, mapping
