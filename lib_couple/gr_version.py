from gradio import __version__ as gradio_version

is_gradio_4: bool = int(gradio_version.split(".")[0]) > 3


def js(func: str) -> dict:
    return {("js" if is_gradio_4 else "_js"): func}
