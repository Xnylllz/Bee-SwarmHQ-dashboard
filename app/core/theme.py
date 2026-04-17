from __future__ import annotations

from dataclasses import dataclass
import re


HEX_COLOR_RE = re.compile(r"^#?[0-9a-fA-F]{6}$")


@dataclass
class ThemePalette:
    name: str
    bg: str
    bg_alt: str
    panel: str
    panel_alt: str
    text: str
    text_muted: str
    border: str
    accent: str
    success: str
    warning: str
    danger: str
    chart: str


THEMES: dict[str, ThemePalette] = {
    "dark": ThemePalette(
        name="dark",
        bg="#111315",
        bg_alt="#16191d",
        panel="#1a1d22",
        panel_alt="#20252b",
        text="#f5f7fb",
        text_muted="#97a1af",
        border="#2c333b",
        accent="#4cc2ff",
        success="#69d08c",
        warning="#ffc65c",
        danger="#ff6b6b",
        chart="#6dd3ff",
    ),
    "black": ThemePalette(
        name="black",
        bg="#080808",
        bg_alt="#0f1012",
        panel="#131416",
        panel_alt="#1a1c1f",
        text="#f6f6f6",
        text_muted="#9ca3af",
        border="#24272d",
        accent="#58c4ff",
        success="#69d08c",
        warning="#f1b94f",
        danger="#ff7d7d",
        chart="#7ad8ff",
    ),
    "ember": ThemePalette(
        name="ember",
        bg="#120b0b",
        bg_alt="#191010",
        panel="#221414",
        panel_alt="#2b1818",
        text="#f9f2f2",
        text_muted="#c2a6a6",
        border="#3a2323",
        accent="#ff6a5f",
        success="#72d38f",
        warning="#ffbf5f",
        danger="#ff7c73",
        chart="#ff837a",
    ),
    "crimson": ThemePalette(
        name="crimson",
        bg="#15070b",
        bg_alt="#1d0d12",
        panel="#261016",
        panel_alt="#32131c",
        text="#fff4f6",
        text_muted="#d1a8b2",
        border="#44202b",
        accent="#ff4f82",
        success="#7dd89d",
        warning="#ffc56a",
        danger="#ff6c8d",
        chart="#ff7aa0",
    ),
}


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def normalize_hex(value: str, fallback: str) -> str:
    raw = str(value or "").strip()
    if not HEX_COLOR_RE.match(raw):
        return fallback
    return raw if raw.startswith("#") else f"#{raw}"


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def blend(color_a: str, color_b: str, ratio: float) -> str:
    ratio = clamp(ratio)
    a = hex_to_rgb(color_a)
    b = hex_to_rgb(color_b)
    mixed = tuple(int(a[i] * (1 - ratio) + b[i] * ratio) for i in range(3))
    return rgb_to_hex(mixed)


def build_theme(settings: dict[str, object]) -> dict[str, str]:
    preset = str(settings.get("theme_preset", "black")).lower()
    base = THEMES.get(preset, THEMES["black"])
    accent = normalize_hex(str(settings.get("accent_color", base.accent) or base.accent), base.accent)
    transparent = bool(int(settings.get("transparent_mode", 0)))
    panel_opacity = float(settings.get("panel_opacity", 0.92))
    dim = float(settings.get("background_dim", 0.45))

    panel = blend(base.panel, base.bg, 1.0 - panel_opacity)
    panel_alt = blend(base.panel_alt, base.bg_alt, 1.0 - panel_opacity)
    if transparent:
        panel = blend(panel, "#ffffff", 0.06)
        panel_alt = blend(panel_alt, "#ffffff", 0.04)

    return {
        "bg": blend(base.bg, "#000000", dim * 0.25),
        "bg_alt": base.bg_alt,
        "panel": panel,
        "panel_alt": panel_alt,
        "text": base.text,
        "text_muted": base.text_muted,
        "border": base.border,
        "accent": accent,
        "success": base.success,
        "warning": base.warning,
        "danger": base.danger,
        "chart": accent if accent else base.chart,
        "glass_highlight": blend("#ffffff", accent, 0.15),
    }
