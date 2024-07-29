import gradio as gr

is_gradio_4: bool = 4 == int(str(gr.__version__).split(".")[0])


def js(func: str) -> dict:
    if is_gradio_4:
        return {"js": func}
    else:
        return {"_js": func}
