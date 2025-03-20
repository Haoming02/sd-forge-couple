from gradio import __version__ as gradio_version

is_gradio_4: bool = str(gradio_version).startswith("4")


def js(func: str) -> dict:
    return {("js" if is_gradio_4 else "_js"): func}
