from modules.ui_components import FormRow, ToolButton
from PIL import Image
import gradio as gr

from .ui_funcs import (
    DEFAULT_MAPPING,
    visualize_mapping,
    add_row_above,
    add_row_below,
    del_row_select,
    reset_mapping,
    manual_entry,
    on_paste,
)

from .gr_version import js, is_gradio_4


def couple_UI(script, is_img2img: bool, title: str):
    m: str = "i2i" if is_img2img else "t2i"
    preview_js: str = f'() => {{ ForgeCouple.preview("{m}"); }}'

    with gr.Accordion(
        label=title,
        elem_id=f"forge_couple_{m}",
        open=False,
    ):
        with gr.Row():
            enable = gr.Checkbox(label="Enable", elem_classes="fc_enable", scale=2)

            mode = gr.Radio(
                ["Basic", "Advanced"],
                label="Region Assignment",
                value="Basic",
                scale=3,
                interactive=(not is_gradio_4),
            )

            separator = gr.Textbox(
                label="Couple Separator",
                lines=1,
                max_lines=1,
                placeholder="Default: Newline",
                elem_classes="fc_separator",
                scale=1,
            )

        with gr.Group() as basic_settings:
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

            with FormRow(elem_classes="fc_map_btns"):
                new_btn = gr.Button("New Row")
                ref_btn = gr.Button("Default Mapping")

            with gr.Group(elem_classes="fc_row_btns"):
                with gr.Row():
                    with gr.Column():
                        new_btn_up = ToolButton(
                            value="\U0001F195",
                            elem_id="fc_up_btn",
                            tooltip="Add a New Row above the Selected Row",
                        )
                        new_btn_dn = ToolButton(
                            value="\U0001F195",
                            elem_id="fc_dn_btn",
                            tooltip="Add a New Row below the Selected Row",
                        )
                    del_btn = ToolButton(
                        value="\U0000274C",
                        elem_id="fc_del_btn",
                        tooltip="Delete the Selected Row",
                    )

            mapping = gr.Dataframe(
                label="Mapping",
                headers=["x", "y", "weight"],
                datatype="str",
                row_count=(1, "dynamic"),
                col_count=(3, "fixed"),
                interactive=True,
                type="array",
                value=DEFAULT_MAPPING,
                elem_classes="fc_mapping",
            )

            preview_img = gr.Image(
                value=Image.new("RGB", (1, 1), "black"),
                image_mode="RGBA",
                label="Mapping Preview",
                type="pil",
                interactive=False,
                height=512,
                show_download_button=False,
            )

            with gr.Column(elem_classes="fc_bg_btns"):
                load_btn = ToolButton(
                    value="\U0001F4C2",
                    elem_id="fc_load_img_btn",
                    tooltip="Load a background image for the mapping visualization",
                )

                if is_img2img:
                    load_i2i_btn = ToolButton(
                        value="\U000023CF",
                        elem_id="fc_load_i2i_img_btn",
                        tooltip="Load the img2img image as the background image",
                    )

                clear_btn = ToolButton(
                    value="\U0000274C",
                    elem_id="fc_clear_img_btn",
                    tooltip="Remove the background image",
                )

            preview_btn = gr.Button("Preview Mapping", elem_classes="fc_preview")
            preview_btn.click(None, **js(preview_js))

            preview_res = gr.Textbox(
                lines=1,
                max_lines=1,
                visible=False,
                interactive=True,
                elem_classes="fc_preview_res",
            )

            real_preview_btn = gr.Button(
                visible=False,
                interactive=True,
                elem_classes="fc_preview_real",
            )

            real_preview_btn.click(
                visualize_mapping,
                [
                    preview_res,
                    mapping,
                ],
                preview_img,
            ).success(None, **js(f'() => {{ ForgeCouple.updateColors("{m}"); }}'))

            mapping.select(None, **js(f'() => {{ ForgeCouple.onSelect("{m}"); }}'))
            mapping.input(None, **js(preview_js))

            gr.Markdown(
                """
                <p align="center">
                    <a href="https://github.com/Haoming02/sd-forge-couple#advanced-mapping">[How to Use]</a>
                </p>
                """
            )

        manual_idx = gr.Number(
            label="Selected Row",
            value=-1,
            interactive=True,
            visible=False,
            precision=0,
            elem_classes="fc_index",
        )

        new_btn.click(add_row_below, mapping, mapping, show_progress="hidden").success(
            None, **js(preview_js)
        )

        new_btn_up.click(
            add_row_above, [mapping, manual_idx], mapping, show_progress="hidden"
        ).success(None, **js(preview_js))

        new_btn_dn.click(
            add_row_below, [mapping, manual_idx], mapping, show_progress="hidden"
        ).success(None, **js(preview_js))

        del_btn.click(
            del_row_select,
            [mapping, manual_idx],
            mapping,
            show_progress="hidden",
        ).success(None, **js(preview_js))

        ref_btn.click(reset_mapping, None, mapping, show_progress="hidden").success(
            None, **js(preview_js)
        )

        manual_field = gr.Textbox(
            lines=1,
            max_lines=1,
            visible=False,
            interactive=True,
            elem_classes="fc_manual_field",
        )

        manual_field.input(
            manual_entry,
            [mapping, manual_field, manual_idx],
            mapping,
            show_progress="hidden",
        ).success(None, **js(preview_js))

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

        mapping_paste_field = gr.Textbox(visible=False)
        mapping_paste_field.change(
            on_paste, mapping_paste_field, mapping, show_progress="hidden"
        ).success(None, **js(preview_js))

        script.paste_field_names = []
        script.infotext_fields = [
            (enable, "forge_couple"),
            (direction, "forge_couple_direction"),
            (background, "forge_couple_background"),
            (separator, "forge_couple_separator"),
            (mode, "forge_couple_mode"),
            (mapping_paste_field, "forge_couple_mapping"),
            (background_weight, "forge_couple_background_weight"),
        ]

        for comp, name in script.infotext_fields:
            comp.do_not_save_to_config = True
            script.paste_field_names.append(name)

        for comp in (manual_idx, manual_field, mapping):
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
