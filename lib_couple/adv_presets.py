import os
from json import dump, load

import gradio as gr

from lib_couple.logging import logger
from modules import scripts

PRESET_FILE = os.path.join(scripts.basedir(), "presets.json")


class PresetManager:
    presets: dict[str, dict] = {}

    @classmethod
    def load_presets(cls):
        if os.path.isfile(PRESET_FILE):
            try:
                with open(PRESET_FILE, "r", encoding="utf-8") as json_file:
                    cls.presets = load(json_file)
            except Exception:
                logger.error("Failed to load Adv. Presets...")
            else:
                logger.info("Loaded Adv. Presets...")
        else:
            with open(PRESET_FILE, "w+", encoding="utf-8") as json_file:
                dump({}, json_file)
            logger.info("Creating new empty Adv. Presets...")

    @classmethod
    def list_preset(cls) -> list[str]:
        return list(cls.presets.keys())

    @classmethod
    def get_preset(cls, preset_name: str) -> None | dict:
        if (preset := cls.presets.get(preset_name, None)) is None:
            logger.error(f'Preset "{preset_name}" was not found...')
            return None

        return preset

    @classmethod
    def save_preset(cls, preset_name: str, mapping: dict) -> list[str]:
        if not preset_name.strip():
            logger.error("Invalid Preset Name...")
            return cls.list_preset()

        cls.presets.update({preset_name: mapping})

        with open(PRESET_FILE, "w", encoding="utf-8") as json_file:
            dump(cls.presets, json_file)

        logger.info(f'Preset "{preset_name}" Saved!')
        return cls.list_preset()

    @classmethod
    def delete_preset(cls, preset_name: str) -> dict:
        if preset_name not in cls.presets:
            logger.error(f'Preset "{preset_name}" was not found...')
            return gr.skip()

        del cls.presets[preset_name]

        with open(PRESET_FILE, "w", encoding="utf-8") as json_file:
            dump(cls.presets, json_file)

        logger.info(f'Preset "{preset_name}" Deleted!')
        return gr.update(choices=cls.list_preset())
