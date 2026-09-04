import gradio as gr

from modules.script_callbacks import on_ui_settings
from modules.shared import OptionInfo, opts


def fc_settings():
    args = {"section": ("fc", "Forge Couple"), "category_id": "sd"}

    opts.add_option(
        "fc_do_interrupt",
        OptionInfo(
            True,
            "Interrupt on Error",
            **args,
        )
        .info('if disabled, Forge Couple will simply "fail silently"')
        .needs_restart(),
    )

    opts.add_option(
        "fc_no_presets",
        OptionInfo(
            False,
            "Disable the Presets feature in Advanced mode",
            **args,
        ).needs_reload_ui(),
    )

    opts.add_option(
        "fc_no_tile",
        OptionInfo(
            False,
            "Disable the Tile mode in img2img",
            **args,
        ).needs_reload_ui(),
    )

    opts.add_option(
        "fc_adv_newline",
        OptionInfo(
            False,
            "Keep newline characters in Advanced mode dataframe",
            **args,
        ).info('newlines would be shown as "\\n" literals'),
    )

    opts.add_option(
        "fc_krea_blend",
        OptionInfo(
            0.25,
            "[Krea 2] Region Blend",
            gr.Slider,
            {"minimum": 0.0, "maximum": 1.0, "step": 0.05},
            **args,
        ).info(
            "fraction of blocks in which image tokens of unrelated regions cannot read each other; "
            "above 0.4 tends to cause seams or duplicated subjects"
        ),
    )


on_ui_settings(fc_settings)
