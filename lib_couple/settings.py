from modules.shared import OptionInfo, opts


def fc_settings():
    args = {"section": ("fc", "Forge Couple"), "category_id": "sd"}

    opts.add_option(
        "fc_no_presets",
        OptionInfo(
            False,
            "Disable the Presets Features in Advanced Mode",
            **args,
        ).needs_restart(),
    )

    opts.add_option(
        "fc_do_interrupt",
        OptionInfo(
            True,
            "Interrupt the generation on error",
            **args,
        )
        .info('if disabled, Forge Couple will simply "fail silently"')
        .needs_restart(),
    )
