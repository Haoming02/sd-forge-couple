import gradio as gr

version = int(str(gr.__version__).split(".", 1)[0])
is_gradio4: bool = version == 4


def is_4() -> bool:
    return is_gradio4


def javascript(func: str) -> dict:
    if is_gradio4:
        return {"js": func}
    else:
        return {"_js": func}
