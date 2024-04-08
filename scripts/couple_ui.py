from PIL import Image, ImageDraw
import gradio as gr


DEFAULT_MAPPING = [["0.0:0.5", "0.0:1.0", "1.0"], ["0.5:1.0", "0.0:1.0", "1.0"]]


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

            assert len(X.split(":")) == 2
            assert len(Y.split(":")) == 2

            val = []

            val.append(float(X.split(":")[0]))
            val.append(float(X.split(":")[1]))
            val.append(float(Y.split(":")[0]))
            val.append(float(Y.split(":")[1]))
            float(W)

            for v in val:
                if v < 0.0 or v > 1.0:
                    raise OverflowError

            if val[1] < val[0] or val[3] < val[2]:
                raise IndexError

        return True

    except AssertionError:
        print("\n\n[Couple] Incorrect number of : in Mapping...\n\n")
        return False
    except ValueError:
        print("\n\n[Couple] Non-Number in Mapping...\n\n")
        return False
    except OverflowError:
        print("\n\n[Couple] Range must be between 0.0 and 1.0...\n\n")
        return False
    except IndexError:
        print('\n\n[Couple] "to" value must be larger than "from" value...\n\n')
        return False


def visualize_mapping(p_WIDTH: int, p_HEIGHT: int, data: list) -> Image:
    matt = Image.new("RGB", (p_WIDTH, p_HEIGHT), "black")

    if not (validata_mapping(data)):
        return matt

    COLORS = ("red", "orange", "yellow", "green", "blue", "violet", "purple")
    lnw = int(max(min(p_WIDTH, p_HEIGHT) / 256, 2.0))

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
            [(x_from, y_from), (x_to, y_to)], outline=COLORS[color_index], width=lnw
        )

    return matt


def reset_mapping() -> list:
    return DEFAULT_MAPPING


def add_first_row(data: list) -> list:
    return [["0.0:1.0", "0.0:1.0", "1.0"]] + data


def add_last_row(data: list) -> list:
    return data + [["0.0:1.0", "0.0:1.0", "1.0"]]


def del_first_row(data: list) -> list:
    return data[1:]


def del_last_row(data: list) -> list:
    return data[:-1]


def manual_entry(data: list, new: str, index: int) -> list:
    v = [round(float(val), 2) for val in new.split(",")]

    if v[1] < v[0]:
        v[0], v[1] = v[1], v[0]
    if v[3] < v[2]:
        v[2], v[3] = v[3], v[2]

    try:
        data[index] = [f"{v[0]}:{v[1]}", f"{v[2]}:{v[3]}", "1.0"]
    except IndexError:
        data.append([f"{v[0]}:{v[1]}", f"{v[2]}:{v[3]}", "1.0"])

    return data


def couple_UI(script, is_img2img: bool, title: str):
    mode = "i2i" if is_img2img else "t2i"
    m = f'"{mode}"'

    with gr.Accordion(
        label=title,
        elem_id=f"forge_couple_{mode}",
        open=False,
    ):
        with gr.Row():
            enable = gr.Checkbox(label="Enable", elem_classes="fc_enable")

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

        with gr.Group(visible=False, elem_classes="fc_adv") as adv_settings:
            mapping = gr.Dataframe(
                label="Mapping",
                headers=["x", "y", "weight"],
                datatype="str",
                row_count=(2, "dynamic"),
                col_count=(3, "fixed"),
                interactive=True,
                type="array",
                value=DEFAULT_MAPPING,
            )

            preview_img = gr.Image(
                value=Image.new("RGB", (1, 1), "black"),
                image_mode="RGB",
                label="Mapping Preview",
                type="pil",
                interactive=False,
                height=512,
            )

            with gr.Row():
                preview_width = gr.Number(value=1024, label="Width", precision=0)
                preview_height = gr.Number(value=1024, label="Height", precision=0)

            preview_btn = gr.Button("Preview Mapping", elem_classes="fc_preview")

            preview_btn.click(
                visualize_mapping,
                [preview_width, preview_height, mapping],
                preview_img,
            )

            with gr.Column(elem_classes="fc_map_btns"):
                with gr.Row():
                    with gr.Column():
                        add_first = gr.Button("New First Row")
                        add_first.click(add_first_row, mapping, mapping).success(
                            None, None, None, _js=f"() => {{ FCMCD.preview({m}); }}"
                        )
                        add_last = gr.Button("New Last Row")
                        add_last.click(add_last_row, mapping, mapping).success(
                            None, None, None, _js=f"() => {{ FCMCD.preview({m}); }}"
                        )
                    with gr.Column():
                        del_first = gr.Button("Delete First Row")
                        del_first.click(del_first_row, mapping, mapping).success(
                            None, None, None, _js=f"() => {{ FCMCD.preview({m}); }}"
                        )
                        del_last = gr.Button("Delete Last Row")
                        del_last.click(del_last_row, mapping, mapping).success(
                            None, None, None, _js=f"() => {{ FCMCD.preview({m}); }}"
                        )

                    reset_map = gr.Button("Reset Mapping")
                    reset_map.click(reset_mapping, None, mapping).success(
                        None, None, None, _js=f"() => {{ FCMCD.preview({m}); }}"
                    )

                with gr.Row():
                    manual_btn = gr.Button("Click & Drag", elem_classes="fc_manual")
                    manual_idx = gr.Number(
                        label="Row Index", value=-100, interactive=True, precision=0
                    )

        manual_field = gr.Textbox(
            lines=1,
            max_lines=1,
            visible=False,
            interactive=True,
            elem_classes="fc_manual_field",
        )

        manual_field.input(
            manual_entry, [mapping, manual_field, manual_idx], mapping
        ).success(None, None, None, _js=f"() => {{ FCMCD.preview({m}); }}")

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

        for comp in (preview_width, preview_height, manual_idx, manual_field):
            comp.do_not_save_to_config = True

        return [enable, direction, background, separator, mode, mapping]
