from __future__ import annotations

from pathlib import Path
from tkinter import colorchooser

import customtkinter as ctk
from PIL import Image, ImageColor

from app.core.fonts import app_font, font_preset_labels, set_active_font_preset
from app.ui.components.cards import PanelCard


class SettingsPage(ctk.CTkScrollableFrame):
    ACCENT_PRESETS = ["#58c4ff", "#ff4f82", "#ff6a5f", "#8dff8a", "#ffc65c"]
    GRADIENT_PRESETS = [
        ("Black Ice", "#090909", "#161a22"),
        ("Dark Red", "#120509", "#28111b"),
        ("Deep Ember", "#120b0b", "#2d1616"),
        ("Ocean Night", "#07121b", "#123048"),
    ]

    def __init__(self, master, theme: dict[str, str], callbacks: dict[str, callable], **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.theme = theme
        self.callbacks = callbacks
        self._image_ref = None

        self.header = ctk.CTkLabel(
            self,
            text="Settings",
            font=app_font(28, weight="bold"),
            text_color=theme["text"],
        )
        self.header.pack(anchor="w", padx=12, pady=(8, 18))

        self.appearance = self._section("Appearance")
        self.background = self._section("Background")
        self.discord = self._section("Discord")
        self.tabs = self._section("Tabs")
        self.data = self._section("Data")
        self.advanced = self._section("Advanced")

        ctk.CTkLabel(
            self.appearance,
            text="Choose a base look, then fine-tune the accent, panels, and background below.",
            text_color=theme["text_muted"],
            wraplength=880,
            justify="left",
        ).pack(anchor="w", padx=18, pady=(0, 12))
        self.theme_preset = self._option_menu(self.appearance, "Theme Preset", ["black", "dark", "ember", "crimson"])
        self.font_preset = self._option_menu(self.appearance, "Font Preset", font_preset_labels())
        ctk.CTkLabel(
            self.appearance,
            text="Basic: System Sans, Avenir Next, Helvetica, Arial, Georgia. Exotic: Baskerville, Didot, Optima, Palatino.",
            text_color=theme["text_muted"],
            wraplength=880,
            justify="left",
        ).pack(anchor="w", padx=18, pady=(0, 10))
        self.accent_color = self._entry(self.appearance, "Accent Color", "#58c4ff")
        self._inline_action_buttons(self.appearance, [("Pick Accent", lambda: self._pick_color(self.accent_color, refresh_preview=False))])
        self._color_presets(self.appearance, self.accent_color, self.ACCENT_PRESETS, refresh_preview=False)
        self.transparent_mode = self._switch(self.appearance, "Transparent Panels")
        self.panel_opacity = self._slider(self.appearance, "Panel Opacity", 0.55, 1.0)
        self.background_dim = self._slider(self.appearance, "Background Dimming", 0.0, 0.85)
        self.blur_amount = self._slider(self.appearance, "Blur Amount", 0, 20)
        self.font_preview = ctk.CTkLabel(
            self.appearance,
            text="Font preview: Honey, Hourly, Announcements, Dashboard",
            text_color=theme["text_muted"],
            font=app_font(14),
        )
        self.font_preview.pack(anchor="w", padx=18, pady=(0, 12))

        ctk.CTkLabel(
            self.background,
            text="Use your own image, or build a gradient background for a cleaner dashboard style.",
            text_color=theme["text_muted"],
            wraplength=880,
            justify="left",
        ).pack(anchor="w", padx=18, pady=(0, 12))
        self.background_preview = ctk.CTkLabel(self.background, text="No background selected", text_color=theme["text_muted"])
        self.background_preview.pack(anchor="w", padx=18, pady=(0, 10))
        self.background_image_path = self._entry(self.background, "Background Image Path", "")
        self.gradient_enabled = self._switch(self.background, "Use Generated Gradient When No Image Is Set")
        self.gradient_start = self._entry(self.background, "Gradient Start Color", "#090909")
        self.gradient_end = self._entry(self.background, "Gradient End Color", "#161a22")
        self._inline_action_buttons(
            self.background,
            [
                ("Pick Start", lambda: self._pick_color(self.gradient_start, refresh_preview=True)),
                ("Pick End", lambda: self._pick_color(self.gradient_end, refresh_preview=True)),
            ],
        )
        self.gradient_direction = self._option_menu(self.background, "Gradient Direction", ["diagonal", "vertical", "horizontal"])
        self._gradient_presets(self.background)
        self.tab_override_toggle = self._switch(self.background, "Allow Per-Tab Background Override")
        self._button_row(
            self.background,
            [
                ("Choose Image", self.callbacks["choose_background"]),
                ("Remove Image", self.callbacks["remove_background"]),
                ("Save Theme", self.callbacks["save_settings"]),
            ],
        )

        self.discord_token = self._entry(self.discord, "Bot Token", "", masked=True)
        self.watched_channels = self._entry(self.discord, "Watched Channel IDs (comma-separated)", "")
        self.announcement_channels = self._entry(self.discord, "Announcement Channel IDs (comma-separated)", "")
        self.command_prefix = self._entry(self.discord, "Macro Command Prefix", "?")
        self._button_row(
            self.discord,
            [
                ("Save Discord Settings", self.callbacks["save_settings"]),
                ("Test Connection", self.callbacks["test_discord"]),
            ],
        )

        self.tab_hint = ctk.CTkLabel(
            self.tabs,
            text="Use the sidebar Edit buttons or + New Tab to manage account tabs.",
            text_color=theme["text_muted"],
        )
        self.tab_hint.pack(anchor="w", padx=18, pady=(0, 14))
        self._button_row(
            self.tabs,
            [
                ("Create Tab", self.callbacks["create_tab"]),
                ("Duplicate Selected", self.callbacks["duplicate_tab"]),
                ("Delete Selected", self.callbacks["delete_tab"]),
            ],
        )

        self._button_row(
            self.data,
            [
                ("Export CSV", self.callbacks["export_csv"]),
                ("Export App Config", self.callbacks["export_config"]),
                ("Import App Config", self.callbacks["import_config"]),
                ("Clear History", self.callbacks["clear_history"]),
            ],
        )

        self.debug_logging = self._switch(self.advanced, "Enable Debug Logging")
        self.refresh_interval = self._entry(self.advanced, "Refresh Interval (ms)", "1200")
        self.startup_backfill_hours = self._entry(self.advanced, "Catch Up Missed Updates On Launch (hours)", "12")
        self.offline_timeout = self._entry(self.advanced, "Offline Timeout (minutes)", "10")
        self.run_in_background_on_close = self._switch(self.advanced, "Keep Running In Background When Window Closes")
        self.enable_menubar_helper = self._switch(self.advanced, "Enable macOS Menu Bar Helper If Available")
        self.desktop_notifications = self._switch(self.advanced, "Enable macOS Desktop Notifications")
        self.launch_at_login = self._switch(self.advanced, "Launch Bee HQ At Login")
        ctk.CTkLabel(
            self.advanced,
            text="When the app opens again, it can pull recent Discord messages from your linked channels and place them into the right tabs. This does not replay old system notifications while the app was closed, but it can sync the missed hourly posts into the app.",
            text_color=self.theme["text_muted"],
            wraplength=880,
            justify="left",
        ).pack(anchor="w", padx=18, pady=(0, 12))
        self._button_row(
            self.advanced,
            [
                ("Save All Settings", self.callbacks["save_settings"]),
            ],
        )
        self._bind_live_preview_events()

    def _section(self, title: str) -> PanelCard:
        card = PanelCard(self, self.theme, title)
        card.pack(fill="x", padx=10, pady=(0, 14))
        return card

    def _entry(self, master, label: str, placeholder: str, masked: bool = False):
        ctk.CTkLabel(master, text=label, text_color=self.theme["text_muted"]).pack(anchor="w", padx=18, pady=(0, 6))
        entry = ctk.CTkEntry(master, height=38, placeholder_text=placeholder, show="*" if masked else "")
        entry.pack(fill="x", padx=18, pady=(0, 12))
        return entry

    def _option_menu(self, master, label: str, values: list[str]):
        ctk.CTkLabel(master, text=label, text_color=self.theme["text_muted"]).pack(anchor="w", padx=18, pady=(0, 6))
        option = ctk.CTkOptionMenu(master, values=values, fg_color=self.theme["panel_alt"], button_color=self.theme["accent"], command=self._handle_option_change)
        option.pack(anchor="w", padx=18, pady=(0, 12))
        return option

    def _switch(self, master, label: str):
        switch = ctk.CTkSwitch(master, text=label, text_color=self.theme["text"])
        switch.pack(anchor="w", padx=18, pady=(0, 12))
        return switch

    def _slider(self, master, label: str, minimum: float, maximum: float):
        ctk.CTkLabel(master, text=label, text_color=self.theme["text_muted"]).pack(anchor="w", padx=18, pady=(0, 6))
        slider = ctk.CTkSlider(master, from_=minimum, to=maximum, number_of_steps=20)
        slider.pack(fill="x", padx=18, pady=(0, 12))
        return slider

    def _button_row(self, master, buttons: list[tuple[str, callable]]) -> None:
        row = ctk.CTkFrame(master, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(0, 14))
        for label, command in buttons:
            ctk.CTkButton(row, text=label, command=command, fg_color=self.theme["accent"]).pack(side="left", padx=(0, 10))

    def _inline_action_buttons(self, master, buttons: list[tuple[str, callable]]) -> None:
        row = ctk.CTkFrame(master, fg_color="transparent")
        row.pack(anchor="w", padx=18, pady=(0, 12))
        for label, command in buttons:
            ctk.CTkButton(
                row,
                text=label,
                command=command,
                fg_color=self.theme["panel_alt"],
                hover_color=self.theme["accent"],
                width=110,
            ).pack(side="left", padx=(0, 8))

    def _color_presets(self, master, entry: ctk.CTkEntry, colors: list[str], refresh_preview: bool) -> None:
        ctk.CTkLabel(master, text="Quick Accent Colors", text_color=self.theme["text_muted"]).pack(anchor="w", padx=18, pady=(0, 6))
        row = ctk.CTkFrame(master, fg_color="transparent")
        row.pack(anchor="w", padx=18, pady=(0, 12))
        for color in colors:
            ctk.CTkButton(
                row,
                text="",
                width=30,
                height=30,
                corner_radius=15,
                fg_color=color,
                hover_color=color,
                command=lambda value=color: self._set_entry_and_refresh(entry, value, refresh_preview),
            ).pack(side="left", padx=(0, 8))

    def _gradient_presets(self, master) -> None:
        ctk.CTkLabel(master, text="Gradient Presets", text_color=self.theme["text_muted"]).pack(anchor="w", padx=18, pady=(0, 6))
        row = ctk.CTkFrame(master, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(0, 12))
        for label, start, end in self.GRADIENT_PRESETS:
            ctk.CTkButton(
                row,
                text=label,
                fg_color=start,
                hover_color=end,
                command=lambda s=start, e=end: self._apply_gradient_preset(s, e),
            ).pack(side="left", padx=(0, 8))

    def _apply_gradient_preset(self, start: str, end: str) -> None:
        self._set_entry_and_refresh(self.gradient_start, start, True)
        self._set_entry_and_refresh(self.gradient_end, end, True)

    def _set_entry_and_refresh(self, entry: ctk.CTkEntry, value: str, refresh_preview: bool) -> None:
        entry.delete(0, "end")
        entry.insert(0, value)
        if refresh_preview:
            self._load_preview(self.background_image_path.get().strip())

    def _pick_color(self, entry: ctk.CTkEntry, refresh_preview: bool) -> None:
        initial = entry.get().strip() or "#58c4ff"
        _, selected = colorchooser.askcolor(color=initial, title="Choose Color")
        if not selected:
            return
        self._set_entry_and_refresh(entry, selected, refresh_preview)

    def _bind_live_preview_events(self) -> None:
        for entry in (self.background_image_path, self.gradient_start, self.gradient_end):
            entry.bind("<KeyRelease>", lambda _event: self._load_preview(self.background_image_path.get().strip()))
            entry.bind("<FocusOut>", lambda _event: self._load_preview(self.background_image_path.get().strip()))

    def _handle_option_change(self, _value: str) -> None:
        if hasattr(self, "font_preset"):
            set_active_font_preset(self.font_preset.get())
        if hasattr(self, "font_preview"):
            self.font_preview.configure(font=app_font(14))
        self._load_preview(self.background_image_path.get().strip())

    def load_settings(self, settings: dict[str, str]) -> None:
        self.theme_preset.set(settings.get("theme_preset", "black"))
        self.font_preset.set(settings.get("font_preset", "System Sans"))
        self._replace_entry(self.accent_color, settings.get("accent_color", "#58c4ff"))
        self.transparent_mode.select() if settings.get("transparent_mode", "0") == "1" else self.transparent_mode.deselect()
        self.panel_opacity.set(float(settings.get("panel_opacity", 0.9)))
        self.background_dim.set(float(settings.get("background_dim", 0.42)))
        self.blur_amount.set(float(settings.get("blur_amount", 8)))
        self._replace_entry(self.background_image_path, settings.get("background_image", ""))
        self.gradient_enabled.select() if settings.get("gradient_enabled", "1") == "1" else self.gradient_enabled.deselect()
        self._replace_entry(self.gradient_start, settings.get("gradient_start", "#090909"))
        self._replace_entry(self.gradient_end, settings.get("gradient_end", "#161a22"))
        self.gradient_direction.set(settings.get("gradient_direction", "diagonal"))
        self._replace_entry(self.discord_token, settings.get("discord_token", ""))
        self._replace_entry(self.watched_channels, settings.get("watched_channels", ""))
        self._replace_entry(self.announcement_channels, settings.get("announcement_channels", ""))
        self._replace_entry(self.command_prefix, settings.get("command_prefix", "?"))
        self.debug_logging.select() if settings.get("debug_logging", "0") == "1" else self.debug_logging.deselect()
        self._replace_entry(self.refresh_interval, settings.get("refresh_interval", "1200"))
        self._replace_entry(self.startup_backfill_hours, settings.get("startup_backfill_hours", "12"))
        self._replace_entry(self.offline_timeout, settings.get("offline_timeout_minutes", "10"))
        self.run_in_background_on_close.select() if settings.get("run_in_background_on_close", "1") == "1" else self.run_in_background_on_close.deselect()
        self.enable_menubar_helper.select() if settings.get("enable_menubar_helper", "1") == "1" else self.enable_menubar_helper.deselect()
        self.desktop_notifications.select() if settings.get("desktop_notifications", "1") == "1" else self.desktop_notifications.deselect()
        self.launch_at_login.select() if settings.get("launch_at_login", "0") == "1" else self.launch_at_login.deselect()
        set_active_font_preset(settings.get("font_preset", "System Sans"))
        self.font_preview.configure(font=app_font(14))
        self._load_preview(settings.get("background_image", ""))

    def collect_settings(self) -> dict[str, str]:
        return {
            "theme_preset": self.theme_preset.get(),
            "font_preset": self.font_preset.get(),
            "accent_color": self.accent_color.get().strip() or "#58c4ff",
            "transparent_mode": "1" if self.transparent_mode.get() else "0",
            "panel_opacity": str(round(float(self.panel_opacity.get()), 2)),
            "background_dim": str(round(float(self.background_dim.get()), 2)),
            "blur_amount": str(int(float(self.blur_amount.get()))),
            "background_image": self.background_image_path.get().strip(),
            "gradient_enabled": "1" if self.gradient_enabled.get() else "0",
            "gradient_start": self.gradient_start.get().strip() or "#090909",
            "gradient_end": self.gradient_end.get().strip() or "#161a22",
            "gradient_direction": self.gradient_direction.get(),
            "discord_token": self.discord_token.get().strip(),
            "watched_channels": self.watched_channels.get().strip(),
            "announcement_channels": self.announcement_channels.get().strip(),
            "command_prefix": self.command_prefix.get().strip() or "?",
            "debug_logging": "1" if self.debug_logging.get() else "0",
            "refresh_interval": self.refresh_interval.get().strip() or "1200",
            "startup_backfill_hours": self.startup_backfill_hours.get().strip() or "12",
            "offline_timeout_minutes": self.offline_timeout.get().strip() or "10",
            "run_in_background_on_close": "1" if self.run_in_background_on_close.get() else "0",
            "enable_menubar_helper": "1" if self.enable_menubar_helper.get() else "0",
            "desktop_notifications": "1" if self.desktop_notifications.get() else "0",
            "launch_at_login": "1" if self.launch_at_login.get() else "0",
        }

    def set_background_path(self, path: str) -> None:
        self._replace_entry(self.background_image_path, path)
        self._load_preview(path)

    def _replace_entry(self, entry: ctk.CTkEntry, value: str) -> None:
        entry.delete(0, "end")
        entry.insert(0, value)

    def _load_preview(self, path: str) -> None:
        if not path or not Path(path).exists():
            if hasattr(self, "gradient_enabled") and self.gradient_enabled.get():
                preview = self._build_gradient_preview(
                    self.gradient_start.get().strip() or "#090909",
                    self.gradient_end.get().strip() or "#161a22",
                    self.gradient_direction.get() if hasattr(self, "gradient_direction") else "diagonal",
                )
                self._image_ref = ctk.CTkImage(light_image=preview, dark_image=preview, size=(320, 180))
                self.background_preview.configure(text="", image=self._image_ref)
            else:
                self.background_preview.configure(text="No background selected", image=None)
                self._image_ref = None
            return
        try:
            image = Image.open(path)
            self._image_ref = ctk.CTkImage(light_image=image, dark_image=image, size=(320, 180))
            self.background_preview.configure(text="", image=self._image_ref)
        except Exception:
            self.background_preview.configure(text="Preview unavailable", image=None)
            self._image_ref = None

    def _build_gradient_preview(self, start_color: str, end_color: str, direction: str) -> Image.Image:
        size = (320, 180)
        image = Image.new("RGB", size)
        pixels = image.load()
        try:
            start_rgb = ImageColor.getrgb(start_color)
            end_rgb = ImageColor.getrgb(end_color)
        except ValueError:
            start_rgb = ImageColor.getrgb("#090909")
            end_rgb = ImageColor.getrgb("#161a22")
        width, height = size
        for y in range(height):
            for x in range(width):
                if direction == "horizontal":
                    ratio = x / max(1, width - 1)
                elif direction == "vertical":
                    ratio = y / max(1, height - 1)
                else:
                    ratio = (x + y) / max(1, (width - 1) + (height - 1))
                color = tuple(
                    int(start_rgb[index] * (1 - ratio) + end_rgb[index] * ratio)
                    for index in range(3)
                )
                pixels[x, y] = color
        return image
