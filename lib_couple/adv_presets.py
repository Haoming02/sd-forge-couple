from modules import scripts
from json import load, dump
import gradio as gr
import os


PRESET_FILE = os.path.join(scripts.basedir(), "presets.json")


class PresetManager:
    presets: dict[str, dict] = {}

    @classmethod
    def load_presets(cls):
        if os.path.isfile(PRESET_FILE):
            with open(PRESET_FILE, "r", encoding="utf-8") as json_file:
                cls.presets = load(json_file)
                print("[Forge Couple] Presets Loaded...")

        else:
            with open(PRESET_FILE, "w+", encoding="utf-8") as json_file:
                json_file.write("{}")
            print("[Forge Couple] Creating Empty Presets...")

    @classmethod
    def list_preset(cls) -> list[str]:
        return list(cls.presets.keys())

    @classmethod
    def get_preset(cls, preset_name: str) -> None | dict:
        preset: dict = cls.presets.get(preset_name, None)

        if preset is None:
            print(f'\n[Error] Preset "{preset_name}" was not found...\n')
            return None

        return preset

    @classmethod
    def save_preset(cls, preset_name: str, mapping: dict) -> list[str]:
        if not preset_name.strip():
            print("\n[Error] Invalid Preset Name...\n")
            return cls.list_preset()

        cls.presets.update({preset_name: mapping})

        with open(PRESET_FILE, "w", encoding="utf-8") as json_file:
            dump(cls.presets, json_file)

        print(f'\nPreset "{preset_name}" Saved!\n')
        return cls.list_preset()

    @classmethod
    def delete_preset(cls, preset_name: str) -> dict:
        if preset_name not in cls.presets:
            print(f'\n[Error] Preset "{preset_name}" was not found...\n')
            return gr.skip()

        del cls.presets[preset_name]

        with open(PRESET_FILE, "w", encoding="utf-8") as json_file:
            dump(cls.presets, json_file)

        print(f'\nPreset "{preset_name}" Deleted!\n')
        return gr.update(choices=cls.list_preset())
