from importlib.metadata import version

is_neo: bool = not version("gradio").startswith("3")


def js(func: str) -> dict:
    return {("js" if is_neo else "_js"): func}
