import gradio as gr


def validata_mapping(data: list) -> bool:
    try:
        for [X, Y, W] in data:
            assert len(X.split(":")) == 2
            assert len(Y.split(":")) == 2
            float(X.split(":")[0])
            float(X.split(":")[1])
            float(Y.split(":")[0])
            float(Y.split(":")[1])
            float(W)

        return True

    except AssertionError:
        print("\n\n[Couple] Incorrect number of : in Mapping...\n")
        return False
    except ValueError:
        print("\n\n[Couple] Non-Number in Mapping...\n")
        return False


def couple_UI(script, title: str):
    with gr.Accordion(label=title, open=False):
        with gr.Row():
            enable = gr.Checkbox(label="Enable")

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

        with gr.Group(visible=False) as adv_settings:
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
