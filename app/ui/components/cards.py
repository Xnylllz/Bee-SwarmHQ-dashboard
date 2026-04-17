from __future__ import annotations

import customtkinter as ctk

from app.core.fonts import app_font


class PanelCard(ctk.CTkFrame):
    def __init__(self, master, theme: dict[str, str], title: str = "", **kwargs):
        super().__init__(
            master,
            fg_color=theme["panel"],
            border_color=theme["border"],
            border_width=1,
            corner_radius=18,
            **kwargs,
        )
        self.theme = theme
        if title:
            self.title_label = ctk.CTkLabel(
                self,
                text=title,
                font=app_font(15, weight="bold"),
                text_color=theme["text"],
            )
            self.title_label.pack(anchor="w", padx=18, pady=(16, 8))


class StatCard(PanelCard):
    def __init__(self, master, theme: dict[str, str], label: str, value: str, accent: str | None = None):
        super().__init__(master, theme, width=180, height=110)
        self.pack_propagate(False)
        accent_color = accent or theme["accent"]
        ctk.CTkLabel(
            self,
            text=label.upper(),
            text_color=theme["text_muted"],
            font=app_font(11, weight="bold"),
        ).pack(anchor="w", padx=18, pady=(16, 4))
        self.value_label = ctk.CTkLabel(
            self,
            text=value,
            text_color=accent_color,
            font=app_font(24, weight="bold"),
        )
        self.value_label.pack(anchor="w", padx=18)

    def set_value(self, value: str, color: str | None = None) -> None:
        self.value_label.configure(text=value)
        if color:
            self.value_label.configure(text_color=color)
