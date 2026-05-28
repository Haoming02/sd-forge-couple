from modules.shared import OptionHTML, OptionInfo, options_templates, opts


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


def fc_anima_settings():
    from gradio import Slider

    from modules.options import OptionRow, options_section

    options_templates.update(
        options_section(
            ("fc", "Forge Couple", "sd"),
            {
                "anima_explanation": OptionHTML("""
Enable the following options to additionally process the latent for <b>Anima</b><br>
This enforces the conditioning separation, but reduces the coherence of the overall image, sometimes even leaving a harsh line in the middle<br>
<b>Note:</b> This also slows down the generation based on the number of regions
<ul>
    <li><b>Recommended Values:</b> start with 0.1 for both</li>
</ul>
"""),
                "anima_1": OptionRow(),
                "fc_anima_strength": OptionInfo(
                    default=0.0,
                    label="[Anima] Separation Bias",
                    component=Slider,
                    component_args={"minimum": 0.0, "maximum": 1.0, "step": 0.05},
                ).info("effect strength"),
                "fc_anima_steps": OptionInfo(
                    default=0.0,
                    label="[Anima] Separation Timestep",
                    component=Slider,
                    component_args={"minimum": 0.0, "maximum": 1.0, "step": 0.05},
                ).info("percentage of steps to process"),
                "anima_0": OptionRow(),
            },
        )
    )
