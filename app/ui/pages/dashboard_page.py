from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

import customtkinter as ctk
from PIL import Image

from app.core.fonts import app_font
from app.ui.components.cards import PanelCard, StatCard


def format_compact_number(value) -> str:
    if value in (None, ""):
        return "--"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    for suffix, threshold in (("T", 1_000_000_000_000), ("B", 1_000_000_000), ("M", 1_000_000), ("K", 1_000)):
        if abs(number) >= threshold:
            return f"{number / threshold:.2f}{suffix}"
    return f"{number:.0f}"


class TrendChart(ctk.CTkCanvas):
    def __init__(self, master, theme: dict[str, str], **kwargs):
        super().__init__(
            master,
            height=140,
            bg=theme["panel"],
            highlightthickness=0,
            bd=0,
            **kwargs,
        )
        self.theme = theme

    def draw_series(self, values: list[float]) -> None:
        self.delete("all")
        width = max(self.winfo_width(), 320)
        height = max(self.winfo_height(), 140)
        self.create_rectangle(0, 0, width, height, fill=self.theme["panel"], outline=self.theme["panel"])
        if not values:
            self.create_text(20, 20, anchor="nw", fill=self.theme["text_muted"], text="No trend data yet")
            return
        max_value = max(values) or 1
        min_value = min(values)
        span = max(max_value - min_value, 1)
        points = []
        for index, value in enumerate(reversed(values[-12:])):
            x = 20 + index * ((width - 40) / max(1, len(values[-12:]) - 1))
            normalized = (value - min_value) / span
            y = height - 20 - normalized * (height - 40)
            points.extend([x, y])
            self.create_oval(x - 3, y - 3, x + 3, y + 3, fill=self.theme["accent"], outline="")
        if len(points) >= 4:
            self.create_line(*points, fill=self.theme["chart"], width=3, smooth=True)


class DashboardPage(ctk.CTkFrame):
    def __init__(self, master, theme: dict[str, str], callbacks: dict[str, callable], **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.theme = theme
        self.callbacks = callbacks
        self._image_refs = []
        self._profile_ref = None

        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", padx=10, pady=(8, 12))

        self.identity_frame = ctk.CTkFrame(self.header, fg_color="transparent")
        self.identity_frame.pack(side="left")
        self.profile_label = ctk.CTkLabel(
            self.identity_frame,
            text="RB",
            width=56,
            height=56,
            corner_radius=28,
            fg_color=theme["panel_alt"],
            text_color=theme["text"],
        )
        self.profile_label.pack(side="left", padx=(0, 12))
        identity_text = ctk.CTkFrame(self.identity_frame, fg_color="transparent")
        identity_text.pack(side="left")
        self.title_label = ctk.CTkLabel(
            identity_text,
            text="Dashboard",
            font=app_font(28, weight="bold"),
            text_color=theme["text"],
        )
        self.title_label.pack(anchor="w")
        self.profile_username = ctk.CTkLabel(
            identity_text,
            text="No Roblox profile linked",
            text_color=theme["text_muted"],
            font=app_font(12),
        )
        self.profile_username.pack(anchor="w")

        self.status_label = ctk.CTkLabel(
            self.header,
            text="Waiting for updates",
            text_color=theme["text_muted"],
            font=app_font(12),
        )
        self.status_label.pack(side="right")

        self.helper_panel = PanelCard(self, theme, "Quick Setup")
        self.helper_panel.pack(fill="x", padx=8, pady=(0, 12))
        self.helper_text = ctk.CTkLabel(
            self.helper_panel,
            text="Link a bot token, update channel, command channel, and optional announcement channel to unlock the full dashboard.",
            text_color=theme["text_muted"],
            justify="left",
            wraplength=1180,
        )
        self.helper_text.pack(anchor="w", padx=18, pady=(0, 18))

        self.stats_row = ctk.CTkFrame(self, fg_color="transparent")
        self.stats_row.pack(fill="x", padx=8, pady=(0, 12))

        self.stat_cards: dict[str, StatCard] = {}
        for key, label in (
            ("honey", "Honey"),
            ("pollen", "Pollen"),
            ("honey_per_second", "Honey / Sec"),
            ("hourly_rate", "Hourly"),
            ("backpack_percent", "Backpack"),
            ("session_total", "Session"),
        ):
            card = StatCard(self.stats_row, theme, label, "--")
            card.pack(side="left", padx=8, fill="both", expand=True)
            self.stat_cards[key] = card

        self.content_row = ctk.CTkFrame(self, fg_color="transparent")
        self.content_row.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.left_column = ctk.CTkFrame(self.content_row, fg_color="transparent")
        self.left_column.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.right_column = ctk.CTkFrame(self.content_row, fg_color="transparent", width=340)
        self.right_column.pack(side="right", fill="y")
        self.right_column.pack_propagate(False)

        self.controls_panel = PanelCard(self.right_column, theme, "Macro Controls")
        self.controls_panel.pack(fill="x", pady=(0, 12))
        self.command_status = ctk.CTkLabel(
            self.controls_panel,
            text="Ready to send commands",
            text_color=theme["text_muted"],
        )
        self.command_status.pack(anchor="w", padx=18, pady=(0, 10))
        buttons_row_1 = ctk.CTkFrame(self.controls_panel, fg_color="transparent")
        buttons_row_1.pack(fill="x", padx=18, pady=(0, 8))
        buttons_row_2 = ctk.CTkFrame(self.controls_panel, fg_color="transparent")
        buttons_row_2.pack(fill="x", padx=18, pady=(0, 10))
        ctk.CTkButton(buttons_row_1, text="Start", fg_color=theme["success"], command=lambda: self.callbacks["send_command"]("start")).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(buttons_row_1, text="Pause", fg_color=theme["warning"], text_color="#111111", command=lambda: self.callbacks["send_command"]("pause")).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(buttons_row_2, text="Stop", fg_color=theme["danger"], command=lambda: self.callbacks["send_command"]("stop")).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(buttons_row_2, text="Request HR", fg_color=theme["accent"], command=lambda: self.callbacks["send_command"]("hr")).pack(side="left", fill="x", expand=True)
        self.command_log = ctk.CTkTextbox(
            self.controls_panel,
            height=90,
            fg_color=theme["panel_alt"],
            text_color=theme["text"],
            border_width=0,
        )
        self.command_log.pack(fill="x", padx=18, pady=(0, 18))

        self.history_panel = PanelCard(self.left_column, theme, "Recent Update History")
        self.history_panel.pack(fill="both", expand=True, pady=(0, 12))
        self.history_search = ctk.CTkEntry(self.history_panel, placeholder_text="Search raw messages...")
        self.history_search.pack(fill="x", padx=18, pady=(0, 10))
        self.history_box = ctk.CTkTextbox(
            self.history_panel,
            fg_color=theme["panel_alt"],
            text_color=theme["text"],
            border_width=0,
        )
        self.history_box.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        self.trend_panel = PanelCard(self.left_column, theme, "Hourly Trend")
        self.trend_panel.pack(fill="x")
        self.chart = TrendChart(self.trend_panel, theme)
        self.chart.pack(fill="x", padx=18, pady=(0, 18))

        self.overview_panel = PanelCard(self.right_column, theme, "Account Overview")
        self.overview_panel.pack(fill="x", pady=(0, 12))
        self.overview_text = ctk.CTkTextbox(self.overview_panel, height=170, fg_color=theme["panel_alt"], text_color=theme["text"], border_width=0)
        self.overview_text.pack(fill="x", padx=18, pady=(0, 18))

        self.announcement_panel = PanelCard(self.right_column, theme, "Announcements")
        self.announcement_panel.pack(fill="x", pady=(0, 12))
        self.announcement_filter = ctk.CTkOptionMenu(
            self.announcement_panel,
            values=["all", "system", "macro", "update", "event", "general"],
            fg_color=theme["panel_alt"],
            button_color=theme["accent"],
            command=lambda _value: self.callbacks["refresh_dashboard"](),
        )
        self.announcement_filter.pack(anchor="w", padx=18, pady=(0, 10))
        self.announcement_box = ctk.CTkTextbox(
            self.announcement_panel,
            height=180,
            fg_color=theme["panel_alt"],
            text_color=theme["text"],
            border_width=0,
        )
        self.announcement_box.pack(fill="x", padx=18, pady=(0, 18))

        self.gallery_panel = PanelCard(self.right_column, theme, "Recent Screenshots")
        self.gallery_panel.pack(fill="both", expand=True)
        self.gallery_grid = ctk.CTkFrame(self.gallery_panel, fg_color="transparent")
        self.gallery_grid.pack(fill="both", expand=True, padx=18, pady=(0, 18))

    def set_theme(self, theme: dict[str, str]) -> None:
        self.theme = theme

    def render(self, tab_row, summary: dict, messages: list, search_term: str = "") -> None:
        latest = summary.get("latest")
        latest_message = summary.get("latest_message")
        self.title_label.configure(text=tab_row["name"])
        self._render_setup_hint(tab_row, latest_message)
        self._render_profile(tab_row)

        if latest_message:
            self.status_label.configure(text=f"Last message: {latest_message['created_at']}")
        else:
            self.status_label.configure(text="No messages yet")

        latest_values = latest if latest is not None else {}
        mapping = {
            "honey": format_compact_number(latest_values["honey"]) if latest else "--",
            "pollen": format_compact_number(latest_values["pollen"]) if latest else "--",
            "honey_per_second": format_compact_number(latest_values["honey_per_second"]) if latest else "--",
            "hourly_rate": format_compact_number(latest_values["hourly_rate"]) if latest else "--",
            "backpack_percent": f"{int(latest_values['backpack_percent'])}%" if latest and latest["backpack_percent"] is not None else "--",
            "session_total": format_compact_number(latest_values["session_total"]) if latest else "--",
        }
        for key, value in mapping.items():
            self.stat_cards[key].set_value(value)

        self.history_box.delete("1.0", "end")
        if messages:
            for row in messages:
                snippet = row["content"] or "[embed or attachment]"
                self.history_box.insert("end", f"{row['created_at']}  {row['author_name']}\n{snippet}\n\n")
        else:
            placeholder = "No message history yet." if not search_term else f'No messages match "{search_term}".'
            self.history_box.insert("end", placeholder)

        overview_lines = [
            f"Account: {tab_row['account_name'] or 'Unassigned'}",
            f"Update channel: {tab_row['channel_id'] or 'Not linked'}",
            f"Source filter: {tab_row['source_author_filter'] or 'Any author in channel'}",
            f"Bots only: {'on' if int(tab_row['ingest_bots_only'] or 1) == 1 else 'off'}",
            f"Command channel: {tab_row['command_channel_id'] or tab_row['channel_id'] or 'Not linked'}",
            f"Announcement channel: {tab_row['announcement_channel_id'] or 'Global feed'}",
            "Hourly requests: manual only",
            f"Layout: {tab_row['layout_preference'] or 'overview'}",
            f"Accent: {tab_row['accent_color'] or 'default'}",
        ]
        if latest:
            created_at = latest["created_at"]
            try:
                stamp = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                delta = datetime.now(timezone.utc) - stamp.astimezone(timezone.utc)
                overview_lines.append(f"Time since last stat: {int(delta.total_seconds() // 60)} min")
            except ValueError:
                overview_lines.append(f"Last stat: {created_at}")
            overview_lines.append(f"Status: {latest['online_status']}")
            overview_lines.append(f"Convert: {latest['convert_status'] or 'Unknown'}")
            overview_lines.append(f"Summary: {latest['raw_summary']}")
        self.overview_text.delete("1.0", "end")
        self.overview_text.insert("end", "\n".join(overview_lines))

        trend_values = [
            float(row["hourly_rate"])
            for row in summary.get("recent", [])
            if row["hourly_rate"] is not None
        ]
        self._render_commands(summary.get("recent_commands", []))
        self._render_announcements(summary.get("recent_announcements", []))
        self.chart.draw_series(trend_values)
        self._render_gallery(summary.get("recent_images", []))

    def set_command_status(self, text: str, color: str | None = None) -> None:
        self.command_status.configure(text=text, text_color=color or self.theme["text_muted"])

    def _render_commands(self, commands: list) -> None:
        self.command_log.delete("1.0", "end")
        if not commands:
            self.command_log.insert("end", "No commands sent yet.")
            return
        for row in commands:
            line = f"{row['requested_at']}  {row['command_text']}  [{row['status']}]\n{row['detail']}\n\n"
            self.command_log.insert("end", line)

    def _render_announcements(self, announcements: list) -> None:
        self.announcement_box.delete("1.0", "end")
        selected_filter = self.announcement_filter.get()
        if selected_filter != "all":
            announcements = [row for row in announcements if row["category"] == selected_filter]
        if not announcements:
            self.announcement_box.insert("end", "No announcements found for this account yet.")
            return
        for row in announcements:
            line = (
                f"[{row['category'].upper()} | {row['relevance_score']}]\n"
                f"{row['title']}\n"
                f"{row['created_at']}\n"
                f"{row['body'][:220]}\n\n"
            )
            self.announcement_box.insert("end", line)

    def _render_setup_hint(self, tab_row, latest_message) -> None:
        missing_steps = []
        if not tab_row["channel_id"]:
            missing_steps.append("set an update channel")
        if not tab_row["command_channel_id"] and not tab_row["channel_id"]:
            missing_steps.append("set a command channel")
        if not tab_row["announcement_channel_id"]:
            missing_steps.append("optionally link an announcement channel")
        if latest_message is None:
            missing_steps.append("wait for the first Discord message")
        if missing_steps:
            self.helper_panel.pack(fill="x", padx=8, pady=(0, 12), before=self.stats_row)
            self.helper_text.configure(text="To finish setup: " + ", ".join(missing_steps) + ".")
        else:
            self.helper_panel.pack_forget()

    def _render_profile(self, tab_row) -> None:
        avatar_path = str(tab_row["roblox_avatar_path"] or "").strip()
        username = str(tab_row["roblox_username"] or "").strip()
        display_name = str(tab_row["roblox_display_name"] or "").strip()
        if avatar_path and Path(avatar_path).exists():
            try:
                image = Image.open(avatar_path)
                self._profile_ref = ctk.CTkImage(light_image=image, dark_image=image, size=(56, 56))
                self.profile_label.configure(text="", image=self._profile_ref)
            except Exception:
                self.profile_label.configure(text="RB", image=None)
                self._profile_ref = None
        else:
            self.profile_label.configure(text="RB", image=None)
            self._profile_ref = None
        if username:
            line = f"@{username}"
            if display_name and display_name.lower() != username.lower():
                line = f"{display_name}  ·  @{username}"
            self.profile_username.configure(text=line)
        else:
            self.profile_username.configure(text="No Roblox profile linked")

    def _render_gallery(self, image_paths: list[str]) -> None:
        for child in self.gallery_grid.winfo_children():
            child.destroy()
        self._image_refs.clear()
        if not image_paths:
            ctk.CTkLabel(self.gallery_grid, text="No images cached yet", text_color=self.theme["text_muted"]).pack(anchor="w")
            return
        for index, image_path in enumerate(image_paths[:6]):
            row = index // 2
            column = index % 2
            frame = ctk.CTkFrame(
                self.gallery_grid,
                fg_color=self.theme["panel_alt"],
                corner_radius=14,
                border_width=1,
                border_color=self.theme["border"],
            )
            frame.grid(row=row, column=column, padx=6, pady=6, sticky="nsew")
            self.gallery_grid.grid_columnconfigure(column, weight=1)
            try:
                image = Image.open(Path(image_path))
                preview = ctk.CTkImage(light_image=image, dark_image=image, size=(135, 90))
                self._image_refs.append(preview)
                ctk.CTkLabel(frame, text="", image=preview).pack(padx=8, pady=(8, 4))
            except Exception:
                ctk.CTkLabel(frame, text="Image unavailable", text_color=self.theme["text_muted"]).pack(padx=8, pady=(16, 8))
            ctk.CTkLabel(frame, text=Path(image_path).name, text_color=self.theme["text_muted"], wraplength=120).pack(padx=8, pady=(0, 8))
