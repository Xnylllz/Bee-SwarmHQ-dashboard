from __future__ import annotations

import customtkinter as ctk

from app.core.fonts import app_font


class TabEditorDialog(ctk.CTkToplevel):
    ACCENT_PRESETS = ["#58c4ff", "#ff4f82", "#ff6a5f", "#8dff8a", "#ffc65c"]

    def __init__(self, master, theme: dict[str, str], initial_values: dict[str, str], on_save):
        super().__init__(master)
        self.theme = theme
        self.on_save = on_save
        self.title("Edit Tab")
        self.geometry("560x760")
        self.transient(master)
        self.grab_set()
        self.configure(fg_color=theme["bg"])

        ctk.CTkLabel(self, text="Tab Settings", font=app_font(22, weight="bold"), text_color=theme["text"]).pack(anchor="w", padx=24, pady=(24, 8))
        ctk.CTkLabel(
            self,
            text="Keep it simple: link the Discord update channel, optionally lock the tab to one source bot, and add a Roblox username for the circular profile image.",
            text_color=theme["text_muted"],
            wraplength=500,
            justify="left",
        ).pack(anchor="w", padx=24, pady=(0, 16))

        scroller = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroller.pack(fill="both", expand=True, padx=18)

        self.entries: dict[str, ctk.CTkEntry] = {}
        self.menus: dict[str, ctk.CTkOptionMenu] = {}
        self.switches: dict[str, ctk.CTkSwitch] = {}

        account = self._section(scroller, "Account")
        self._entry(account, "name", "Tab Name", initial_values)
        self._entry(account, "account_name", "Account Label", initial_values)
        self._entry(account, "roblox_username", "Roblox Username", initial_values)

        discord = self._section(scroller, "Discord Routing")
        self._entry(discord, "channel_id", "Update Channel ID", initial_values)
        self._entry(discord, "source_author_filter", "Source Bot Name or User ID", initial_values)
        self._switch(discord, "ingest_bots_only", "Only Ingest Bot Messages", initial_values, default=True)
        self._entry(discord, "command_channel_id", "Command Channel ID", initial_values)
        self._entry(discord, "announcement_channel_id", "Announcement Channel ID", initial_values)

        appearance = self._section(scroller, "Appearance")
        self._entry(appearance, "accent_color", "Accent Color (#58c4ff)", initial_values)
        self._color_presets(appearance, "accent_color", "Quick Accent Colors")
        self._entry(appearance, "background_override", "Per-Tab Background Override Path", initial_values)
        self._option(appearance, "layout_preference", "Layout Preference", ["overview", "focus", "compact"], initial_values)

        button_row = ctk.CTkFrame(self, fg_color="transparent")
        button_row.pack(fill="x", padx=24, pady=18)
        ctk.CTkButton(button_row, text="Cancel", fg_color=theme["panel_alt"], command=self.destroy).pack(side="right", padx=(10, 0))
        ctk.CTkButton(button_row, text="Save", fg_color=theme["accent"], command=self._handle_save).pack(side="right")

    def _section(self, master, title: str):
        frame = ctk.CTkFrame(master, fg_color=self.theme["panel"], border_color=self.theme["border"], border_width=1, corner_radius=18)
        frame.pack(fill="x", padx=6, pady=(0, 14))
        ctk.CTkLabel(frame, text=title, font=app_font(16, weight="bold"), text_color=self.theme["text"]).pack(anchor="w", padx=18, pady=(16, 10))
        return frame

    def _entry(self, master, key: str, label: str, initial_values: dict[str, str]) -> None:
        ctk.CTkLabel(master, text=label, text_color=self.theme["text_muted"]).pack(anchor="w", padx=18, pady=(0, 6))
        entry = ctk.CTkEntry(master, height=38)
        entry.insert(0, initial_values.get(key, ""))
        entry.pack(fill="x", padx=18, pady=(0, 12))
        self.entries[key] = entry

    def _option(self, master, key: str, label: str, values: list[str], initial_values: dict[str, str]) -> None:
        ctk.CTkLabel(master, text=label, text_color=self.theme["text_muted"]).pack(anchor="w", padx=18, pady=(0, 6))
        menu = ctk.CTkOptionMenu(master, values=values, fg_color=self.theme["panel_alt"], button_color=self.theme["accent"])
        initial = initial_values.get(key, values[0]) or values[0]
        menu.set(initial)
        menu.pack(anchor="w", padx=18, pady=(0, 12))
        self.menus[key] = menu

    def _switch(self, master, key: str, label: str, initial_values: dict[str, str], default: bool = False) -> None:
        raw = str(initial_values.get(key, "1" if default else "0")).strip().lower()
        switch = ctk.CTkSwitch(master, text=label, text_color=self.theme["text"], onvalue="1", offvalue="0")
        if raw in {"1", "true", "yes", "on"}:
            switch.select()
        else:
            switch.deselect()
        switch.pack(anchor="w", padx=18, pady=(0, 12))
        self.switches[key] = switch

    def _color_presets(self, master, key: str, label: str) -> None:
        ctk.CTkLabel(master, text=label, text_color=self.theme["text_muted"]).pack(anchor="w", padx=18, pady=(0, 6))
        row = ctk.CTkFrame(master, fg_color="transparent")
        row.pack(anchor="w", padx=18, pady=(0, 12))
        for color in self.ACCENT_PRESETS:
            ctk.CTkButton(
                row,
                text="",
                width=30,
                height=30,
                corner_radius=15,
                fg_color=color,
                hover_color=color,
                command=lambda value=color: self._set_entry_value(key, value),
            ).pack(side="left", padx=(0, 8))

    def _set_entry_value(self, key: str, value: str) -> None:
        entry = self.entries[key]
        entry.delete(0, "end")
        entry.insert(0, value)

    def _handle_save(self) -> None:
        payload = {key: entry.get().strip() for key, entry in self.entries.items()}
        for key, menu in self.menus.items():
            payload[key] = menu.get().strip()
        for key, switch in self.switches.items():
            payload[key] = switch.get().strip()
        self.on_save(payload)
        self.destroy()
