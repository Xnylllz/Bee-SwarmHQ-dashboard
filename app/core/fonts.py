from __future__ import annotations

from dataclasses import dataclass

import customtkinter as ctk


@dataclass(frozen=True)
class FontPreset:
    label: str
    family: str
    category: str


FONT_PRESETS: dict[str, FontPreset] = {
    "System Sans": FontPreset("System Sans", "Helvetica", "basic"),
    "Avenir Next": FontPreset("Avenir Next", "Avenir Next", "basic"),
    "Helvetica": FontPreset("Helvetica", "Helvetica", "basic"),
    "Arial": FontPreset("Arial", "Arial", "basic"),
    "Georgia": FontPreset("Georgia", "Georgia", "basic"),
    "Baskerville": FontPreset("Baskerville", "Baskerville", "exotic"),
    "Didot": FontPreset("Didot", "Didot", "exotic"),
    "Optima": FontPreset("Optima", "Optima", "exotic"),
    "Palatino": FontPreset("Palatino", "Palatino", "exotic"),
}

DEFAULT_FONT_PRESET = "System Sans"
_active_preset = DEFAULT_FONT_PRESET


def font_preset_labels() -> list[str]:
    return list(FONT_PRESETS.keys())


def set_active_font_preset(label: str) -> str:
    global _active_preset
    _active_preset = label if label in FONT_PRESETS else DEFAULT_FONT_PRESET
    return _active_preset


def active_font_preset() -> str:
    return _active_preset


def active_font_family() -> str:
    return FONT_PRESETS.get(_active_preset, FONT_PRESETS[DEFAULT_FONT_PRESET]).family


def app_font(size: int, weight: str = "normal", slant: str = "roman") -> ctk.CTkFont:
    return ctk.CTkFont(
        family=active_font_family(),
        size=size,
        weight=weight,
        slant=slant,
    )
