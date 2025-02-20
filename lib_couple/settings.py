from modules.shared import OptionInfo, opts


def fc_settings():
    section = ("fc", "Forge Couple")

    opts.add_option(
        "fc_no_presets",
        OptionInfo(
            False,
            "Disable the Presets Features in Advanced Mode",
            section=section,
            category_id="sd",
        ).needs_restart(),
    )
