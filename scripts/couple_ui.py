from PIL import Image, ImageDraw
import gradio as gr
import gradio.blocks

def create_region_canvas(aspect_ratio: str) -> Image:
    return Image.new("RGB", (int(float(aspect_ratio) * 512), 512), "black")

def couple_UI(script, title: str, is_img2img: bool) -> list[gradio.blocks.Block]:
    with gr.Accordion(label=title, open=False):
        with gr.Row():
            enable = gr.Checkbox(label="Enable", elem_id="fc_enable")

            mode = gr.Radio(
                ["Basic", "Advanced"],
                label="Region Assignment",
                value="Basic"
            )

            separator = gr.Textbox(
                label="Couple Separator",
                lines=1,
                max_lines=1,
                placeholder="Leave empty to use newline"
            )

        with gr.Group() as basic_settings:
            with gr.Row():
                basic_direction = gr.Radio(
                    ["Horizontal", "Vertical"],
                    label="Tile Direction",
                    value="Horizontal"
                )

                basic_background_type = gr.Radio(
                    ["None", "First Line", "Last Line"],
                    label="Global Effect",
                    value="None"
                )

        with gr.Group(visible = False, elem_id = "forge-couple--adv-group-" + ("img2img" if is_img2img else "txt2img")) as adv_settings:
            advanced_regions = gr.Textbox(
                label = "Regions",
                elem_id = "forge-couple--adv-regions-" + ("img2img" if is_img2img else "txt2img"),
                visible = False
            )
            advanced_regions.change(None, advanced_regions, _js = f"ForgeCouple.CustomRegionControl.refresh{is_img2img and 'Img2img' or 'Txt2img'}")

        def update_mode_group_visibility(choice: str):
            if choice == "Basic":
                return [
                    gr.Group.update(visible=True),
                    gr.Group.update(visible=False)
                ]
            else:
                return [
                    gr.Group.update(visible=False),
                    gr.Group.update(visible=True)
                ]

        mode.change(update_mode_group_visibility, mode, [basic_settings, adv_settings])
        mode.change(None, _js = f"ForgeCouple.CustomRegionControl.refresh{is_img2img and 'Img2img' or 'Txt2img'}")

        script.paste_field_names = []
        script.infotext_fields = [
            (enable, "forge_couple"),
            (basic_direction, "forge_couple_direction"),
            (basic_background_type, "forge_couple_background"),
            (separator, "forge_couple_separator"),
            (mode, "forge_couple_mode"),
            (advanced_regions, "forge_couple_regions")
        ]

        for comp, name in script.infotext_fields:
            comp.do_not_save_to_config = True
            script.paste_field_names.append(name)

        return [enable, basic_direction, basic_background_type, separator, mode, advanced_regions]
