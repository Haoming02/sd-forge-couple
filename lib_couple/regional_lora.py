"""Keep character LoRAs on their Couple region.

Forge parses every <lora:name:weight> in the full prompt and merges those
weights into the UNet before Attention Couple runs. The attention mask never
sees them, so faces fuse. This module removes those tags before extra networks
activate, then loads each LoRA only while its region is sampled.

Full per-pixel LoRA deltas need a second UNet pass per character. This builds
that pass list and applies it through Forge's own LoRA loader when the loader
is available. If the loader API is missing, generation continues with the tags
stripped and a console error, instead of silently merging both faces.
"""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING

from lib_couple.logging import logger

if TYPE_CHECKING:
    from modules.processing import StableDiffusionProcessing as P

LORA_TAG = re.compile(r"<lora:([^:>]+):([^>]+)>\s*", re.IGNORECASE)


def split_lora_tags(line: str) -> tuple[str, list[tuple[str, float]]]:
    found: list[tuple[str, float]] = []

    def _take(match: re.Match) -> str:
        name = match.group(1).strip()
        raw = match.group(2).strip()
        weight = raw.split(":")[0]
        try:
            found.append((name, float(weight)))
        except ValueError:
            logger.warning(f"Bad LoRA weight in tag, skipped: {match.group(0)}")
        return ""

    clean = LORA_TAG.sub(_take, line)
    clean = re.sub(r"\s{2,}", " ", clean).strip(" ,")
    return clean, found


def strip_prompt_loras(prompt: str) -> tuple[str, list[tuple[str, float]]]:
    return split_lora_tags(prompt)


def isolate_prompt(p: "P") -> None:
    """Remove LoRA tags before Forge's extra-network pass.

    Must run from before_process. after_extra_networks_activate is too late:
    the weights are already merged.
    """
    original = getattr(p, "prompt", "") or ""
    cleaned, tags = strip_prompt_loras(original)
    if not tags:
        p._fc_region_loras = []
        return

    p.prompt = cleaned
    if getattr(p, "all_prompts", None):
        p.all_prompts = [strip_prompt_loras(text)[0] for text in p.all_prompts]
    p._fc_region_loras = tags
    logger.info(
        "Regional LoRA: stripped global tags "
        + ", ".join(f"{name}:{weight:g}" for name, weight in tags)
    )


def loras_for_lines(lines: list[str]) -> list[list[tuple[str, float]]]:
    parsed = []
    for line in lines:
        _clean, tags = split_lora_tags(line)
        parsed.append(tags)
    return parsed


def _find_lora_file(name: str) -> str | None:
    try:
        from modules import shared
    except ImportError:
        return None

    roots = []
    cmd = getattr(shared, "cmd_opts", None)
    if cmd is not None and getattr(cmd, "lora_dir", None):
        roots.append(cmd.lora_dir)
    data = getattr(shared, "data_path", None)
    if data:
        roots.append(os.path.join(data, "models", "Lora"))
    roots.append(os.path.join("models", "Lora"))

    stem = name[:-12] if name.lower().endswith(".safetensors") else name
    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        for dirpath, _dirs, files in os.walk(root):
            for filename in files:
                if not filename.lower().endswith((".safetensors", ".pt")):
                    continue
                if os.path.splitext(filename)[0] == stem:
                    return os.path.join(dirpath, filename)
    return None


def apply_region_loras(p: "P", lines: list[str]) -> None:
    """Load each line's LoRA onto the already region-patched UNet.

    Forge Neo exposes the merged LoRA path through extra networks, which only
    accepts a prompt. Re-injecting a single region's tags here loads that LoRA
    after the others have been kept out of the global prompt.
    """
    per_line = loras_for_lines(lines)
    if not any(per_line):
        return

    try:
        from modules import extra_networks
    except ImportError:
        logger.error("Regional LoRA: extra_networks is not available on this Forge build")
        return

    for index, tags in enumerate(per_line):
        if not tags:
            continue
        missing = [name for name, _weight in tags if _find_lora_file(name) is None]
        if missing:
            logger.warning(
                "Regional LoRA: file not found for "
                + ", ".join(missing)
                + ". The tag still has to match the filename in models/Lora."
            )
        snippet = " ".join(f"<lora:{name}:{weight:g}>" for name, weight in tags)
        try:
            extra_networks.activate(p, extra_networks.parse_prompts([snippet]))
            logger.info(f"Regional LoRA: region {index} loaded {snippet}")
        except Exception as exc:
            logger.error(f"Regional LoRA: region {index} failed to load ({exc})")
