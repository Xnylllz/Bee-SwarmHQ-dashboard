from __future__ import annotations

import customtkinter as ctk
from pathlib import Path

from PIL import Image

from app.core.fonts import app_font


class SidebarTabButton(ctk.CTkFrame):
    def __init__(self, master, theme: dict[str, str], tab_row, status_color: str, on_select, on_edit):
        super().__init__(
            master,
            fg_color=theme["panel"],
            border_color=theme["border"],
            border_width=1,
            corner_radius=14,
            height=72,
        )
        self.pack_propagate(False)
        self.tab_row = tab_row
        self.theme = theme
        self.on_select = on_select
        self.on_edit = on_edit
        self._avatar_ref = None

        self.dot = ctk.CTkFrame(self, width=10, height=10, corner_radius=5, fg_color=status_color)
        self.dot.pack(side="left", padx=(14, 10), pady=0)

        avatar_path = str(tab_row["roblox_avatar_path"] or "").strip()
        if avatar_path and Path(avatar_path).exists():
            try:
                image = Image.open(avatar_path)
                self._avatar_ref = ctk.CTkImage(light_image=image, dark_image=image, size=(40, 40))
                self.avatar = ctk.CTkLabel(self, text="", image=self._avatar_ref)
            except Exception:
                self.avatar = ctk.CTkLabel(self, text="RB", width=40, height=40, corner_radius=20, fg_color=theme["panel_alt"])
        else:
            self.avatar = ctk.CTkLabel(self, text="RB", width=40, height=40, corner_radius=20, fg_color=theme["panel_alt"])
        self.avatar.pack(side="left", padx=(0, 10))

        text_frame = ctk.CTkFrame(self, fg_color="transparent")
        text_frame.pack(side="left", fill="x", expand=True, padx=(0, 8), pady=10)

        self.title = ctk.CTkLabel(
            text_frame,
            text=tab_row["name"],
            anchor="w",
            text_color=theme["text"],
            font=app_font(14, weight="bold"),
        )
        self.title.pack(fill="x")

        subtitle = (
            tab_row["roblox_username"]
            or tab_row["account_name"]
            or (f"Channel {tab_row['channel_id']}" if tab_row["channel_id"] else "Unassigned")
        )
        self.subtitle = ctk.CTkLabel(
            text_frame,
            text=subtitle,
            anchor="w",
            text_color=theme["text_muted"],
            font=app_font(11),
        )
        self.subtitle.pack(fill="x")

        self.menu_button = ctk.CTkButton(
            self,
            text="Edit",
            width=56,
            height=30,
            corner_radius=12,
            fg_color=theme["panel_alt"],
            hover_color=theme["accent"],
            command=lambda: self.on_edit(tab_row),
        )
        self.menu_button.pack(side="right", padx=10)

        for widget in (self, self.dot, self.avatar, self.title, self.subtitle, text_frame):
            widget.bind("<Button-1>", lambda _event, row=tab_row: self.on_select(row["id"]))

    def set_active(self, active: bool) -> None:
        self.configure(fg_color=self.theme["panel_alt"] if active else self.theme["panel"])
        self.menu_button.configure(fg_color=self.theme["accent"] if active else self.theme["panel_alt"])
