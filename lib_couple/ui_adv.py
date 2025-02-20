from json import dumps

import gradio as gr
from modules.shared import opts
from modules.ui_components import ToolButton
from PIL import Image

from .gr_version import js
from .ui_funcs import DEFAULT_MAPPING, on_entry, visualize_mapping

show_presets = not getattr(opts, "fc_no_presets", False)

if show_presets:
    from .adv_presets import PresetManager

    PresetManager.load_presets()

    def __presets_ui() -> tuple[gr.components.Component]:
        with gr.Accordion("Presets", open=False):
            with gr.Row(elem_classes="style-rows"):
                preset_choice = gr.Dropdown(
                    label="Mapping Presets",
                    value=None,
                    choices=PresetManager.list_preset(),
                    scale=3,
                )
                apply_btn = gr.Button(value="Apply Preset", scale=2)
                refresh_btn = gr.Button(value="Refresh Presets", scale=2)

            with gr.Row(elem_classes="style-rows"):
                preset_name = gr.Textbox(label="Preset Name", max_lines=1, scale=3)
                save_btn = gr.Button(value="Save Preset", scale=2)
                delete_btn = gr.Button(value="Delete Preset", scale=2)

        comps = (
            preset_choice,
            apply_btn,
            refresh_btn,
            preset_name,
            save_btn,
            delete_btn,
        )

        for comp in comps:
            comp.do_not_save_to_config = True

        return comps


def advanced_ui(
    is_img2img: bool, m: str, mode: gr.Radio
) -> tuple[gr.components.Component]:
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
                    value="\U0001f195",
                    elem_id="fc_up_btn",
                    tooltip="Add a New Row above the Selected Row",
                )
                ToolButton(
                    value="\U0001f195",
                    elem_id="fc_dn_btn",
                    tooltip="Add a New Row below the Selected Row",
                )
            ToolButton(
                value="\U0000274c",
                elem_id="fc_del_btn",
                tooltip="Delete the Selected Row",
            )

    with gr.Column(elem_classes="fc_bg_btns"):
        ToolButton(
            value="\U0001f4c2",
            elem_id="fc_load_img_btn",
            tooltip="Load a background image for the mapping visualization",
        )
        if is_img2img:
            ToolButton(
                value="\U000023cf",
                elem_id="fc_load_i2i_img_btn",
                tooltip="Load the img2img image as the background image",
            )
        ToolButton(
            value="\U0001f5d1",
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

    msk_btn_pull = gr.Button(
        f"Pull from {'txt2img' if is_img2img else 'img2img'}", elem_classes="round-btn"
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
        msk_btn_pull,
    ):
        comp.do_not_save_to_config = True

    if not show_presets:
        return preview_btn, preview_res, mapping_paste_field, mapping, msk_btn_pull

    (
        preset_choice,
        apply_btn,
        refresh_btn,
        preset_name,
        save_btn,
        delete_btn,
    ) = __presets_ui()

    def _apply(name: str) -> dict:
        preset: dict = PresetManager.get_preset(name)
        if preset is None:
            return gr.skip()
        else:
            return gr.update(value=dumps(preset))

    apply_btn.click(
        fn=_apply,
        inputs=[preset_choice],
        outputs=[mapping_paste_field],
    )
    refresh_btn.click(
        fn=lambda: gr.update(choices=PresetManager.list_preset()),
        outputs=[preset_choice],
    )

    save_btn.click(
        fn=lambda *args: gr.update(choices=PresetManager.save_preset(*args)),
        inputs=[preset_name, mapping],
        outputs=[preset_choice],
    )
    delete_btn.click(
        fn=lambda name: PresetManager.delete_preset(name),
        inputs=[preset_name],
        outputs=[preset_choice],
    )

    return preview_btn, preview_res, mapping_paste_field, mapping, msk_btn_pull
