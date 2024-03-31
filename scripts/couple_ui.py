from PIL import Image, ImageDraw
import gradio as gr


def parse_mapping(data: list) -> list:
    mapping = []

    for [X, Y, W] in data:
        if not X.strip():
            continue

        mapping.append(
            (
                (float(X.split(":")[0]), float(X.split(":")[1])),
                (float(Y.split(":")[0]), float(Y.split(":")[1])),
                float(W),
            )
        )

    return mapping


def validata_mapping(data: list) -> bool:
    try:
        for [X, Y, W] in data:
            if not X.strip():
                continue

            float(X.split(":")[0])
            float(X.split(":")[1])
            float(Y.split(":")[0])
            float(Y.split(":")[1])
            float(W)

        return True

    except AssertionError:
        print("\n\n[Couple] Incorrect number of : in Mapping...\n\n")
        return False
    except ValueError:
        print("\n\n[Couple] Non-Number in Mapping...\n\n")
        return False


def visualize_mapping(p_WIDTH: int, p_HEIGHT: int, data: list) -> Image:
    if not (validata_mapping(data)):
        return None

    COLORS = ("red", "orange", "yellow", "green", "blue", "violet", "purple", "white")

    matt = Image.new("RGB", (p_WIDTH, p_HEIGHT), "black")
    draw = ImageDraw.Draw(matt)

    mapping = parse_mapping(data)

    print("\nAdv. Preview:")
    for tile_index in range(len(mapping)):
        color_index = tile_index % len(COLORS)

        (X, Y, W) = mapping[tile_index]
        x_from = int(p_WIDTH * X[0])
        x_to = int(p_WIDTH * X[1])
        y_from = int(p_HEIGHT * Y[0])
        y_to = int(p_HEIGHT * Y[1])
        weight = W

        print(f"  [{y_from:4d}:{y_to:4d}, {x_from:4d}:{x_to:4d}] = {weight:.2f}")
        draw.rectangle(
            [(x_from, y_from), (x_to, y_to)], outline=COLORS[color_index], width=2
        )

    return matt


def couple_UI(script, title: str):
    with gr.Accordion(label=title, open=False):
        with gr.Row():
            enable = gr.Checkbox(label="Enable", elem_id="fc_enable")

            mode = gr.Radio(
                ["Basic", "Advanced"],
                label="Region Assignment",
                value="Basic",
            )

            separator = gr.Textbox(
                label="Couple Separator",
                lines=1,
                max_lines=1,
                placeholder="Leave empty to use newline",
            )

        with gr.Group() as basic_settings:
            with gr.Row():
                direction = gr.Radio(
                    ["Horizontal", "Vertical"],
                    label="Tile Direction",
                    value="Horizontal",
                )

                background = gr.Radio(
                    ["None", "First Line", "Last Line"],
                    label="Global Effect",
                    value="None",
                )

        with gr.Group(visible=False, elem_id="fc_adv") as adv_settings:
            mapping = gr.Dataframe(
                label="Mapping",
                headers=["x", "y", "weight"],
                datatype="str",
                row_count=(2, "dynamic"),
                col_count=(3, "fixed"),
                interactive=True,
                type="array",
                value=[["0:0.5", "0.0:1.0", "1.0"], ["0.5:1.0", "0.0:1.0", "1.0"]],
            )

            preview_img = gr.Image(
                image_mode="RGB",
                label="Mapping Preview",
                type="pil",
                interactive=False,
                height=512,
            )

            with gr.Row():
                preview_width = gr.Number(value=1024, label="Width", precision=0)
                preview_height = gr.Number(value=1024, label="Height", precision=0)

            preview_btn = gr.Button("Preview Mapping", elem_id="fc_preview")

            preview_btn.click(
                visualize_mapping,
                [preview_width, preview_height, mapping],
                preview_img,
            )

        def on_radio_change(choice):
            if choice == "Basic":
                return [
                    gr.Group.update(visible=True),
                    gr.Group.update(visible=False),
                ]
            else:
                return [
                    gr.Group.update(visible=False),
                    gr.Group.update(visible=True),
                ]

        mode.change(on_radio_change, mode, [basic_settings, adv_settings])

        script.paste_field_names = []
        script.infotext_fields = [
            (enable, "forge_couple"),
            (direction, "forge_couple_direction"),
            (background, "forge_couple_background"),
            (separator, "forge_couple_separator"),
            (mode, "forge_couple_mode"),
            (mapping, "forge_couple_mapping"),
        ]

        for comp, name in script.infotext_fields:
            comp.do_not_save_to_config = True
            script.paste_field_names.append(name)

        return [enable, direction, background, separator, mode, mapping]
