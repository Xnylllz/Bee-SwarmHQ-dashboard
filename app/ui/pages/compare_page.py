from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import customtkinter as ctk
from PIL import Image

from app.core.fonts import app_font
from app.ui.components.cards import PanelCard
from app.ui.pages.dashboard_page import format_compact_number


class MiniTrend(ctk.CTkCanvas):
    def __init__(self, master, theme: dict[str, str], **kwargs):
        super().__init__(master, height=60, bg=theme["panel_alt"], highlightthickness=0, bd=0, **kwargs)
        self.theme = theme

    def draw(self, values: list[float]) -> None:
        self.delete("all")
        width = max(self.winfo_width(), 180)
        height = max(self.winfo_height(), 60)
        self.create_rectangle(0, 0, width, height, fill=self.theme["panel_alt"], outline=self.theme["panel_alt"])
        if not values:
            self.create_text(12, height / 2, anchor="w", fill=self.theme["text_muted"], text="No trend")
            return
        max_value = max(values) or 1.0
        min_value = min(values)
        span = max(max_value - min_value, 1.0)
        coords: list[float] = []
        subset = values[-10:]
        for index, value in enumerate(subset):
            x = 12 + index * ((width - 24) / max(1, len(subset) - 1))
            y = height - 10 - ((value - min_value) / span) * (height - 20)
            coords.extend([x, y])
        if len(coords) >= 4:
            self.create_line(*coords, fill=self.theme["accent"], width=2, smooth=True)


class ComparePage(ctk.CTkScrollableFrame):
    def __init__(self, master, theme: dict[str, str], **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.theme = theme
        self._avatar_refs = []

        ctk.CTkLabel(
            self,
            text="Compare Accounts",
            font=app_font(28, weight="bold"),
            text_color=theme["text"],
        ).pack(anchor="w", padx=12, pady=(8, 18))

        self.summary_card = PanelCard(self, theme, "Quick Comparison")
        self.summary_card.pack(fill="x", padx=10, pady=(0, 14))
        self.summary_text = ctk.CTkTextbox(
            self.summary_card,
            height=120,
            fg_color=theme["panel_alt"],
            text_color=theme["text"],
            border_width=0,
        )
        self.summary_text.pack(fill="x", padx=18, pady=(0, 18))

        self.list_card = PanelCard(self, theme, "Account Ranking")
        self.list_card.pack(fill="both", expand=True, padx=10, pady=(0, 18))
        self.rows_host = ctk.CTkFrame(self.list_card, fg_color="transparent")
        self.rows_host.pack(fill="both", expand=True, padx=18, pady=(0, 18))

    def render(self, compare_rows: list[dict]) -> None:
        self._avatar_refs.clear()
        self.summary_text.configure(state="normal")
        self.summary_text.delete("1.0", "end")
        for child in self.rows_host.winfo_children():
            child.destroy()

        ranked = sorted(
            compare_rows,
            key=lambda item: float(item.get("latest", {}).get("hourly_rate") or 0.0),
            reverse=True,
        )
        if not ranked:
            self.summary_text.insert("end", "No configured tabs yet.")
            self.summary_text.configure(state="disabled")
            return

        top = ranked[0]
        top_tab = top["tab"]
        top_rate = format_compact_number(top.get("latest", {}).get("hourly_rate"))
        summary_lines = [
            f"Top hourly rate: {top_tab['name']} at {top_rate}",
            f"Tracked accounts: {len(ranked)}",
        ]
        active_count = sum(1 for item in ranked if (item.get("latest", {}) or {}).get("online_status") == "online")
        summary_lines.append(f"Currently online: {active_count} / {len(ranked)}")
        self.summary_text.insert("end", "\n".join(summary_lines))
        self.summary_text.configure(state="disabled")

        for index, item in enumerate(ranked, start=1):
            self._render_row(index, item)

    def _render_row(self, rank: int, item: dict) -> None:
        tab = item["tab"]
        latest = item.get("latest") or {}
        card = ctk.CTkFrame(
            self.rows_host,
            fg_color=self.theme["panel"],
            border_color=self.theme["border"],
            border_width=1,
            corner_radius=18,
        )
        card.pack(fill="x", pady=8)

        left = ctk.CTkFrame(card, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True, padx=14, pady=14)

        identity = ctk.CTkFrame(left, fg_color="transparent")
        identity.pack(fill="x")
        ctk.CTkLabel(identity, text=f"#{rank}", width=42, text_color=self.theme["accent"], font=app_font(18, weight="bold")).pack(side="left", padx=(0, 8))
        avatar_path = str(tab["roblox_avatar_path"] or "").strip()
        if avatar_path and Path(avatar_path).exists():
            try:
                image = Image.open(avatar_path)
                ref = ctk.CTkImage(light_image=image, dark_image=image, size=(42, 42))
                self._avatar_refs.append(ref)
                ctk.CTkLabel(identity, text="", image=ref).pack(side="left", padx=(0, 10))
            except Exception:
                ctk.CTkLabel(identity, text="RB", width=42, height=42, corner_radius=21, fg_color=self.theme["panel_alt"]).pack(side="left", padx=(0, 10))
        else:
            ctk.CTkLabel(identity, text="RB", width=42, height=42, corner_radius=21, fg_color=self.theme["panel_alt"]).pack(side="left", padx=(0, 10))

        name_block = ctk.CTkFrame(identity, fg_color="transparent")
        name_block.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(name_block, text=tab["name"], anchor="w", text_color=self.theme["text"], font=app_font(18, weight="bold")).pack(fill="x")
        subtitle = tab["roblox_username"] or tab["account_name"] or "Unassigned account"
        ctk.CTkLabel(name_block, text=subtitle, anchor="w", text_color=self.theme["text_muted"], font=app_font(12)).pack(fill="x")

        stats = ctk.CTkFrame(left, fg_color="transparent")
        stats.pack(fill="x", pady=(10, 6))
        backpack_text = "--" if latest.get("backpack_percent") is None else f"{int(latest.get('backpack_percent'))}%"
        stat_line = "  |  ".join(
            [
                f"Hourly {format_compact_number(latest.get('hourly_rate'))}",
                f"Honey {format_compact_number(latest.get('honey'))}",
                f"Pollen {format_compact_number(latest.get('pollen'))}",
                f"Backpack {backpack_text}",
                f"Status {(latest.get('online_status') or 'unknown')}",
            ]
        )
        ctk.CTkLabel(stats, text=stat_line, text_color=self.theme["text"]).pack(anchor="w")

        meta = []
        latest_message = item.get("latest_message")
        if latest_message:
            meta.append(f"Last update {self._format_time(latest_message['created_at'])}")
        last_hourly = item.get("last_hourly")
        if last_hourly:
            meta.append(f"Last hourly {last_hourly['report_time_label'] or self._format_time(last_hourly['created_at'])}")
        ctk.CTkLabel(left, text="  |  ".join(meta) if meta else "No recent data yet", text_color=self.theme["text_muted"], font=app_font(12)).pack(anchor="w")

        right = ctk.CTkFrame(card, fg_color="transparent", width=240)
        right.pack(side="right", fill="y", padx=(0, 14), pady=14)
        right.pack_propagate(False)
        ctk.CTkLabel(right, text="Hourly Trend", text_color=self.theme["text_muted"], font=app_font(12)).pack(anchor="w")
        trend = MiniTrend(right, self.theme, width=220)
        trend.pack(fill="x", pady=(6, 0))
        trend.draw(item.get("trend", []))

    def _format_time(self, raw_value: str) -> str:
        try:
            stamp = datetime.fromisoformat(str(raw_value).replace("Z", "+00:00"))
        except ValueError:
            return str(raw_value)
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        return stamp.astimezone().strftime("%b %d · %I:%M %p").replace(" 0", " ")
