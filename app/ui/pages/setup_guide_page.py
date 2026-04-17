from __future__ import annotations

import customtkinter as ctk

from app.core.fonts import app_font
from app.ui.components.cards import PanelCard


class SetupGuidePage(ctk.CTkScrollableFrame):
    def __init__(self, master, theme: dict[str, str], callbacks: dict[str, callable], **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.theme = theme
        self.callbacks = callbacks

        ctk.CTkLabel(
            self,
            text="Setup Guide",
            font=app_font(28, weight="bold"),
            text_color=theme["text"],
        ).pack(anchor="w", padx=12, pady=(8, 18))

        self.status_card = PanelCard(self, theme, "Quick Checklist")
        self.status_card.pack(fill="x", padx=10, pady=(0, 14))
        self.status_text = ctk.CTkTextbox(
            self.status_card,
            height=150,
            fg_color=theme["panel_alt"],
            text_color=theme["text"],
            border_width=0,
        )
        self.status_text.pack(fill="x", padx=18, pady=(0, 18))

        self.steps_card = PanelCard(self, theme, "How To Set Everything Up")
        self.steps_card.pack(fill="x", padx=10, pady=(0, 14))
        self.steps_text = ctk.CTkTextbox(
            self.steps_card,
            height=520,
            fg_color=theme["panel_alt"],
            text_color=theme["text"],
            border_width=0,
        )
        self.steps_text.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        self.steps_text.insert(
            "end",
            "\n".join(
                [
                    "1. Discord bot setup",
                    "   Create or open your Discord bot in the Discord Developer Portal.",
                    "   Turn on MESSAGE CONTENT INTENT.",
                    "   Invite the bot to your server with read/send access for the channels you want to use.",
                    "",
                    "2. Put the token into Bee HQ",
                    "   Open Settings.",
                    "   Paste the bot token into Bot Token.",
                    "   Click Save Discord Settings.",
                    "",
                    "3. Create one app tab per macro/account",
                    "   Click + New Tab in the sidebar.",
                    "   Name it after the account.",
                    "   Paste the Update Channel ID for that account's Discord channel.",
                    "   Optionally set Command Channel ID if commands should go to a different channel.",
                    "   Optionally set Announcement Channel ID if that account has a separate announcement feed.",
                    "",
                    "4. Filter to the right source bot",
                    "   If the channel has extra chatter, set Source Bot Name or User ID.",
                    "   Leave Only Ingest Bot Messages on for the cleanest setup.",
                    "",
                    "5. Link Roblox profile",
                    "   Enter the Roblox username in the tab editor.",
                    "   Save the tab and Bee HQ will fetch the circular avatar automatically.",
                    "",
                    "6. Backgrounds and themes",
                    "   In Settings you can pick a theme preset, font preset, custom accent, image background, or gradient background.",
                    "",
                    "7. Hourly reports",
                    "   If Natro posts automatic hourly report images, Bee HQ captures them in the Hourly page.",
                    "   Even if the app was fully closed, startup sync can still catch recent hourly messages when you open it again.",
                    "",
                    "8. Background mode",
                    "   If Keep Running In Background When Window Closes is on, closing the window hides Bee HQ instead of quitting it.",
                    "   With the optional menu bar helper on, you can reopen it from the menu bar.",
                    "",
                    "9. Launch at login",
                    "   Turn on Launch At Login in Settings if you want Bee HQ to start automatically after reboot.",
                    "",
                    "10. Common IDs",
                    "   In Discord developer mode, right click a channel and choose Copy Channel ID.",
                    "   If you need the source bot ID, right click the bot/app and choose Copy User ID.",
                ]
            ),
        )
        self.steps_text.configure(state="disabled")

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=10, pady=(0, 18))
        ctk.CTkButton(actions, text="Open Settings", fg_color=theme["accent"], command=lambda: self.callbacks["show_page"]("settings")).pack(side="left", padx=(0, 10))
        ctk.CTkButton(actions, text="Create New Tab", fg_color=theme["panel_alt"], command=self.callbacks["create_tab"]).pack(side="left", padx=(0, 10))
        ctk.CTkButton(actions, text="Go To Dashboard", fg_color=theme["panel_alt"], command=lambda: self.callbacks["show_page"]("dashboard")).pack(side="left")

    def render(self, settings: dict[str, str], tabs: list) -> None:
        configured_tabs = [row for row in tabs if row["channel_id"]]
        profile_tabs = [row for row in tabs if row["roblox_username"]]
        command_tabs = [row for row in tabs if row["command_channel_id"] or row["channel_id"]]
        checklist = [
            f"Discord token saved: {'Yes' if settings.get('discord_token') else 'No'}",
            f"Account tabs created: {len(tabs)}",
            f"Tabs linked to update channels: {len(configured_tabs)} / {len(tabs)}",
            f"Tabs ready for macro commands: {len(command_tabs)} / {len(tabs)}",
            f"Tabs with Roblox profile picture: {len(profile_tabs)} / {len(tabs)}",
            f"Background mode on close: {'Enabled' if settings.get('run_in_background_on_close', '1') == '1' else 'Disabled'}",
            f"Menu bar helper: {'Enabled' if settings.get('enable_menubar_helper', '1') == '1' else 'Disabled'}",
            f"Launch at login: {'Enabled' if settings.get('launch_at_login', '0') == '1' else 'Disabled'}",
            f"Desktop notifications: {'Enabled' if settings.get('desktop_notifications', '1') == '1' else 'Disabled'}",
            f"Startup catch-up window: {settings.get('startup_backfill_hours', '12')} hour(s)",
        ]
        self.status_text.configure(state="normal")
        self.status_text.delete("1.0", "end")
        self.status_text.insert("end", "\n".join(checklist))
        self.status_text.configure(state="disabled")
