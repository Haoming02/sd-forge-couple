from importlib.metadata import version

is_gradio_4: bool = not version("gradio").startswith("3")


def js(func: str) -> dict:
    return {("js" if is_gradio_4 else "_js"): func}
