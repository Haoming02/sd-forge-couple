import gradio as gr


def tile_ui() -> tuple[gr.components.Component]:

    gr.Markdown(
        """
        <h2 style="float: left;">Tile Mode</h2>
        <p style="float: right;"><b>experimental</b> ⚠️</p>
        """
    )

    with gr.Row():
        with gr.Column():
            use_tile = gr.Checkbox(value=False, label="Enable Tile Mode")
            debug = gr.Checkbox(value=False, label="Debug Tiles")

        tile_threshold = gr.Slider(
            label="Inclusion Threshold",
            info="overlap % needed for region to be included",
            minimum=0.0,
            maximum=1.0,
            value=0.75,
            step=0.05,
        )

    with gr.Row():
        tile_h = gr.Number(value=5, label="Horizontal Tile Count")
        tile_v = gr.Number(value=4, label="Vertical Tile Count")

    tile_replace = gr.Textbox(
        value=None,
        lines=6,
        max_lines=6,
        label="Subject Replacement",
        placeholder="1boy: 2boys, multiple boys\n1girl: 2girls, multiple girls",
    )

    comps = (use_tile, tile_h, tile_v, tile_threshold, tile_replace, debug)

    for comp in comps:
        comp.do_not_save_to_config = True

    return comps
