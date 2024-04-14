from PIL import Image, ImageDraw
import gradio as gr


DEFAULT_MAPPING = [["0.0:0.5", "0.0:1.0", "1.0"], ["0.5:1.0", "0.0:1.0", "1.0"]]
COLORS = ("red", "orange", "yellow", "green", "blue", "indigo", "violet")

T2I_W = None
T2I_H = None
I2I_W = None
I2I_H = None


def hook_component(component, id: str):
    global T2I_W, T2I_H, I2I_W, I2I_H

    if id == "txt2img_width":
        T2I_W = component
    elif id == "txt2img_height":
        T2I_H = component
    elif id == "img2img_width":
        I2I_W = component
    elif id == "img2img_height":
        I2I_H = component


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

    lnw = int(max(min(p_WIDTH, p_HEIGHT) / 128, 2.0))

    draw = ImageDraw.Draw(matt)

    mapping = parse_mapping(data)

    # print("\nAdv. Preview:")
    for tile_index in range(len(mapping)):
        color_index = tile_index % len(COLORS)

        (X, Y, W) = mapping[tile_index]
        x_from = int(p_WIDTH * X[0])
        x_to = int(p_WIDTH * X[1])
        y_from = int(p_HEIGHT * Y[0])
        y_to = int(p_HEIGHT * Y[1])
        weight = W

        # print(f"  [{y_from:4d}:{y_to:4d}, {x_from:4d}:{x_to:4d}] = {weight:.2f}")
        draw.rectangle(
            [(x_from, y_from), (x_to, y_to)], outline=COLORS[color_index], width=lnw
        )

    return matt


def reset_mapping() -> list:
    return DEFAULT_MAPPING, 2


def add_first_row(data: list) -> list:
    return [["0.0:1.0", "0.0:1.0", "1.0"]] + data, 0


def add_last_row(data: list) -> list:
    i = len(data)
    return data + [["0.25:0.75", "0.25:0.75", "1.0"]], i


def del_first_row(data: list) -> list:
    if len(data) == 1:
        return [["0.0:1.0", "0.0:1.0", "1.0"]], 0
    else:
        return data[1:], 0


def del_last_row(data: list) -> list:
    i = len(data)
    if len(data) == 1:
        return [["0.0:1.0", "0.0:1.0", "1.0"]], 0
    else:
        return data[:-1], i - 2


def del_sele_row(data: list, index: int) -> list:
    i = len(data) - 1
    try:
        if index == 0 and len(data) == 1:
            return [["0.0:1.0", "0.0:1.0", "1.0"]], 0
        del data[index]
        i -= 1
    except IndexError:
        pass

    return data, i


def manual_entry(data: list, new: str, index: int) -> list:
    v = [round(float(val), 2) for val in new.split(",")]

    if v[1] < v[0]:
        v[0], v[1] = v[1], v[0]
    if v[3] < v[2]:
        v[2], v[3] = v[3], v[2]

    try:
        data[index][0] = f"{v[0]}:{v[1]}"
        data[index][1] = f"{v[2]}:{v[3]}"
    except IndexError:
        data.append([f"{v[0]}:{v[1]}", f"{v[2]}:{v[3]}", "1.0"])

    return data


def couple_UI(script, is_img2img: bool, title: str):
    m: str = "i2i" if is_img2img else "t2i"
    preview_js: str = f'() => {{ ForgeCouple.preview("{m}"); }}'

    with gr.Accordion(
        label=title,
        elem_id=f"forge_couple_{m}",
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

                background_weight = gr.Slider(
                    minimum=0.1,
                    maximum=1.0,
                    step=0.1,
                    value=0.5,
                    label="Global Effect Weight",
                )

        with gr.Group(visible=False, elem_classes="fc_adv") as adv_settings:
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

            mapping.select(
                None, None, None, _js=f'() => {{ ForgeCouple.onSelect("{m}"); }}'
            )

            preview_img = gr.Image(
                value=Image.new("RGB", (1, 1), "black"),
                image_mode="RGB",
                label="Mapping Preview",
                type="pil",
                interactive=False,
                height=512,
            )

            preview_btn = gr.Button("Preview Mapping", elem_classes="fc_preview")
            preview_btn.click(
                visualize_mapping,
                [
                    I2I_W if is_img2img else T2I_W,
                    I2I_H if is_img2img else T2I_H,
                    mapping,
                ],
                preview_img,
            )

            with gr.Column(elem_classes="fc_map_btns"):
                with gr.Row():
                    add_first = gr.Button("New First Row")
                    add_last = gr.Button("New Last Row")
                    manual_btn = gr.Button("Click & Drag", elem_classes="fc_manual")

                with gr.Row():
                    del_first = gr.Button("Delete First Row")
                    del_last = gr.Button("Delete Last Row")
                    del_sele = gr.Button("Delete Selection")

                with gr.Row():
                    reset_map = gr.Button("Reset Mapping")
                    manual_idx = gr.Number(
                        label="Selected Row",
                        value=2,
                        interactive=True,
                        precision=0,
                        elem_classes="fc_index",
                    )

        add_first.click(add_first_row, mapping, [mapping, manual_idx]).success(
            None, None, None, _js=preview_js
        )
        add_last.click(add_last_row, mapping, [mapping, manual_idx]).success(
            None, None, None, _js=preview_js
        )
        del_first.click(del_first_row, mapping, [mapping, manual_idx]).success(
            None, None, None, _js=preview_js
        )
        del_last.click(del_last_row, mapping, [mapping, manual_idx]).success(
            None, None, None, _js=preview_js
        )
        del_sele.click(
            del_sele_row, [mapping, manual_idx], [mapping, manual_idx]
        ).success(None, None, None, _js=preview_js)
        reset_map.click(reset_mapping, None, [mapping, manual_idx]).success(
            None, None, None, _js=preview_js
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
        ).success(None, None, None, _js=preview_js)

        def on_mode_change(choice):
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

        mode.change(on_mode_change, mode, [basic_settings, adv_settings])

        script.paste_field_names = []
        script.infotext_fields = [
            (enable, "forge_couple"),
            (direction, "forge_couple_direction"),
            (background, "forge_couple_background"),
            (separator, "forge_couple_separator"),
            (mode, "forge_couple_mode"),
            (mapping, "forge_couple_mapping"),
            (background_weight, "forge_couple_background_weight"),
        ]

        for comp, name in script.infotext_fields:
            comp.do_not_save_to_config = True
            script.paste_field_names.append(name)

        for comp in (manual_idx, manual_field):
            comp.do_not_save_to_config = True

        return [
            enable,
            direction,
            background,
            separator,
            mode,
            mapping,
            background_weight,
        ]
