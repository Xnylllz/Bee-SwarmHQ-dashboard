from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

import customtkinter as ctk
from PIL import Image

from app.core.fonts import app_font
from app.ui.components.cards import PanelCard


class HourlyReportsPage(ctk.CTkScrollableFrame):
    def __init__(self, master, theme: dict[str, str], **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.theme = theme
        self._image_refs = []
        self._viewer_ref = None

        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", padx=10, pady=(8, 12))

        self.title_label = ctk.CTkLabel(
            self.header,
            text="Hourly Reports",
            font=app_font(28, weight="bold"),
            text_color=theme["text"],
        )
        self.title_label.pack(side="left")

        self.status_label = ctk.CTkLabel(
            self.header,
            text="Waiting for hourly images",
            text_color=theme["text_muted"],
            font=app_font(12),
        )
        self.status_label.pack(side="right")

        self.hero_card = PanelCard(self, theme, "Latest Hourly")
        self.hero_card.pack(fill="x", padx=10, pady=(0, 14))
        self.hero_image = ctk.CTkLabel(self.hero_card, text="No hourly image yet", text_color=theme["text_muted"])
        self.hero_image.pack(padx=18, pady=(0, 10))
        self.hero_meta = ctk.CTkLabel(self.hero_card, text="", text_color=theme["text_muted"], justify="left")
        self.hero_meta.pack(anchor="w", padx=18, pady=(0, 18))

        self.feed_card = PanelCard(self, theme, "Recent Hourly Feed")
        self.feed_card.pack(fill="both", expand=True, padx=10, pady=(0, 18))
        self.feed = ctk.CTkFrame(self.feed_card, fg_color="transparent")
        self.feed.pack(fill="both", expand=True, padx=18, pady=(0, 18))

    def render(self, tab_row, reports: list) -> None:
        self.title_label.configure(text=f"Hourly Reports · {tab_row['name']}")
        self._render_latest(reports[0] if reports else None)
        self._render_feed(reports)

    def _render_latest(self, report) -> None:
        if not report:
            self.hero_image.configure(text="No hourly image yet", image=None)
            self.hero_meta.configure(text="When Natro sends an hourly report image, it will show up here.")
            self.status_label.configure(text="No hourly reports captured yet")
            return
        attachment_paths = json.loads(report["attachment_paths"] or "[]")
        first_image_path = attachment_paths[0] if attachment_paths else ""
        sent_time = self._format_local_timestamp(report["created_at"])
        self.status_label.configure(text=f"Last hourly: {sent_time}")
        if first_image_path and Path(first_image_path).exists():
            image = Image.open(first_image_path)
            preview = ctk.CTkImage(light_image=image, dark_image=image, size=(760, 420))
            self._image_refs.append(preview)
            self.hero_image.configure(text="", image=preview)
            self.hero_image.bind("<Button-1>", lambda _event, path=first_image_path, title=report["title"] or "Hourly Report": self._open_fullscreen(path, title))
        else:
            self.hero_image.configure(text="Hourly image unavailable", image=None)
        meta_lines = [
            report["title"] or "Hourly Report",
            f"Report time: {report['report_time_label'] or sent_time}",
            f"Captured in app: {sent_time}",
        ]
        self.hero_meta.configure(text="\n".join(meta_lines))

    def _render_feed(self, reports: list) -> None:
        for child in self.feed.winfo_children():
            child.destroy()
        self._image_refs.clear()
        if not reports:
            ctk.CTkLabel(self.feed, text="No hourly reports stored for this account yet.", text_color=self.theme["text_muted"]).pack(anchor="w")
            return
        for report in reports:
            card = ctk.CTkFrame(
                self.feed,
                fg_color=self.theme["panel"],
                border_color=self.theme["border"],
                border_width=1,
                corner_radius=18,
            )
            card.pack(fill="x", pady=8)
            attachment_paths = json.loads(report["attachment_paths"] or "[]")
            first_image_path = attachment_paths[0] if attachment_paths else ""
            if first_image_path and Path(first_image_path).exists():
                try:
                    image = Image.open(first_image_path)
                    preview = ctk.CTkImage(light_image=image, dark_image=image, size=(300, 165))
                    self._image_refs.append(preview)
                    thumb = ctk.CTkLabel(card, text="", image=preview)
                    thumb.pack(side="left", padx=14, pady=14)
                    thumb.bind("<Button-1>", lambda _event, path=first_image_path, title=report["title"] or "Hourly Report": self._open_fullscreen(path, title))
                except Exception:
                    ctk.CTkLabel(card, text="Image unavailable", text_color=self.theme["text_muted"]).pack(side="left", padx=14, pady=14)
            text_block = ctk.CTkFrame(card, fg_color="transparent")
            text_block.pack(fill="both", expand=True, padx=(0, 14), pady=14)
            ctk.CTkLabel(text_block, text=report["title"] or "Hourly Report", anchor="w", text_color=self.theme["text"], font=app_font(16, weight="bold")).pack(fill="x")
            sent_time = self._format_local_timestamp(report["created_at"])
            subtitle = f"{report['report_time_label'] or sent_time} · synced {sent_time}"
            ctk.CTkLabel(text_block, text=subtitle, anchor="w", text_color=self.theme["text_muted"]).pack(fill="x", pady=(4, 8))
            ctk.CTkLabel(text_block, text=report["body"][:260] or "Embedded hourly image captured.", anchor="w", justify="left", wraplength=520, text_color=self.theme["text_muted"]).pack(fill="x")
            ctk.CTkButton(
                text_block,
                text="Open Full Size",
                fg_color=self.theme["accent"],
                command=lambda path=first_image_path, title=report["title"] or "Hourly Report": self._open_fullscreen(path, title),
            ).pack(anchor="w", pady=(10, 0))

    def _format_local_timestamp(self, raw_value: str) -> str:
        try:
            parsed = datetime.fromisoformat(str(raw_value).replace("Z", "+00:00"))
        except ValueError:
            return str(raw_value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        local_value = parsed.astimezone()
        return local_value.strftime("%b %d, %Y · %I:%M %p").replace(" 0", " ")

    def _open_fullscreen(self, image_path: str, title: str) -> None:
        if not image_path or not Path(image_path).exists():
            return
        viewer = ctk.CTkToplevel(self)
        viewer.title(title)
        viewer.geometry("1200x880")
        viewer.configure(fg_color=self.theme["bg"])
        frame = ctk.CTkScrollableFrame(viewer, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=18, pady=18)
        image = Image.open(image_path)
        width, height = image.size
        max_width = 1120
        scale = min(1.0, max_width / max(1, width))
        display_size = (max(1, int(width * scale)), max(1, int(height * scale)))
        self._viewer_ref = ctk.CTkImage(light_image=image, dark_image=image, size=display_size)
        ctk.CTkLabel(frame, text="", image=self._viewer_ref).pack(padx=12, pady=12)
