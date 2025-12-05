import math
import re

import gradio as gr

from modules.script_callbacks import on_after_component

I2I_WIDTH: gr.Slider = None
I2I_HEIGHT: gr.Slider = None
I2I_SCALE: gr.HTML = None

pattern = re.compile(r"(\d+)x(\d+)")


def tile_ui() -> tuple[gr.components.Component]:
    gr.Markdown(
        """
        <h2 style="float: left;">Tile Mode</h2>
        <p style="float: right;"><b>experimental</b> ⚠️</p>
        """
    )

    with gr.Row():
        use_tile = gr.Checkbox(value=False, label="Enable Tile Mode", scale=1)
        debug = gr.Checkbox(value=False, label="Debug Tiles", scale=1)

        tile_threshold = gr.Slider(
            label="Inclusion Threshold",
            info="overlap % needed for region to be included",
            minimum=0.0,
            maximum=1.0,
            value=0.75,
            step=0.05,
            scale=4,
        )

    with gr.Row(elem_classes=["dim_calc"]):
        with gr.Column(scale=1):
            _width = gr.Number(value=-1, label="Final Width", interactive=False)
            _height = gr.Number(value=-1, label="Final Height", interactive=False)
        with gr.Column(scale=2):
            _scale = gr.Slider(
                label="Scale Factor",
                value=2.0,
                minimum=1.0,
                maximum=8.0,
                step=0.05,
                interactive=True,
            )
            _overlap = gr.Slider(
                label="Tile Overlap",
                value=64,
                minimum=0,
                maximum=256,
                step=16,
                interactive=True,
            )
        with gr.Column(scale=1):
            tile_h = gr.Number(value=-1, label="Column Count", interactive=False)
            tile_v = gr.Number(value=-1, label="Row Count", interactive=False)

        _calc = gr.Button("Calculate", variant="primary", scale=2)

    def calculate(w: int, h: int, dim: str, scale: float, overlap: int):
        if not (m := re.search(pattern, dim)):
            return [gr.update(value=-1)] * 4

        _w, _h = int(m.group(1)), int(m.group(2))

        new_width = int(_w * scale)
        new_height = int(_h * scale)
        tile_width = w - overlap
        tile_height = h - overlap

        rows = math.ceil((new_height - overlap) / tile_height)
        cols = math.ceil((new_width - overlap) / tile_width)

        return [
            gr.update(value=new_width),
            gr.update(value=new_height),
            gr.update(value=rows),
            gr.update(value=cols),
        ]

    _calc.click(
        fn=calculate,
        inputs=[I2I_WIDTH, I2I_HEIGHT, I2I_SCALE, _scale, _overlap],
        outputs=[_width, _height, tile_h, tile_v],
        show_progress="hidden",
        queue=False,
    )

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
    for comp in (_width, _height, _scale, _overlap, _calc):
        comp.do_not_save_to_config = True

    return comps


def setup_components(component: gr.components.Component, **kwargs):
    if not (_id := kwargs.get("elem_id", None)):
        return

    global I2I_WIDTH, I2I_HEIGHT, I2I_SCALE

    if _id == "img2img_width":
        I2I_WIDTH = component
    if _id == "img2img_height":
        I2I_HEIGHT = component
    if _id == "img2img_scale_resolution_preview":
        I2I_SCALE = component


on_after_component(setup_components)
