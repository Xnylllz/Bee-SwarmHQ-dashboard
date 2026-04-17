from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import threading
from tkinter import filedialog, messagebox
import customtkinter as ctk

from app.core.config import AppPaths, write_env_value
from app.core.fonts import set_active_font_preset, app_font
from app.core.theme import build_theme, normalize_hex
from app.data.database import Database
from app.discord_client.client import DiscordService
from app.parsing.natro_parser import NatroMessageParser
from app.services.image_cache import ImageCache
from app.services.launch_agent_service import LaunchAgentService
from app.services.menubar_service import MenuBarService
from app.services.notification_service import NotificationService
from app.services.roblox_profile import RobloxProfileService
from app.ui.components.dialogs import TabEditorDialog
from app.ui.components.sidebar import SidebarTabButton
from app.ui.pages.compare_page import ComparePage
from app.ui.pages.dashboard_page import DashboardPage
from app.ui.pages.hourly_reports_page import HourlyReportsPage
from app.ui.pages.setup_guide_page import SetupGuidePage
from app.ui.pages.settings_page import SettingsPage


class BeeDashboardApp(ctk.CTk):
    def __init__(self, database: Database, paths: AppPaths):
        super().__init__()
        self.database = database
        self.paths = paths
        self.parser = NatroMessageParser()
        self.image_cache = ImageCache(paths.image_cache, paths.backgrounds)
        self.roblox_profile_service = RobloxProfileService(self.image_cache)
        self.discord_service = DiscordService(
            database=database,
            parser=self.parser,
            image_cache=self.image_cache,
            ui_callback=self.enqueue_ui_event,
        )
        self.notification_service = NotificationService()
        self.pending_events: list[dict] = []
        self.selected_tab_id: int | None = None
        self.sidebar_buttons: dict[int, SidebarTabButton] = {}
        self.current_page = "dashboard"
        self.background_label = None
        self.background_image_ref = None
        self._background_signature = None
        self._background_hidden = False

        ctk.set_appearance_mode("dark")
        self.settings_store = self.database.get_settings()
        set_active_font_preset(self.settings_store.get("font_preset", "System Sans"))
        self.theme = build_theme(self.settings_store)
        self.menu_bar_service = MenuBarService(
            on_show=lambda: self.after(0, self.restore_from_background),
            on_quit=lambda: self.after(0, self.quit_application),
        )
        self.launch_agent_service = LaunchAgentService(paths.root)

        self.title("Bee Swarm / Natro Dashboard")
        self.geometry("1480x920")
        self.minsize(1240, 780)
        self.configure(fg_color=self.theme["bg"])
        self.protocol("WM_DELETE_WINDOW", self.handle_close)

        self._build_layout()
        self._apply_background_preferences()
        self.bind("<Command-r>", lambda _event: self.refresh_dashboard())
        self.bind("<Command-comma>", lambda _event: self.show_page("settings"))
        self.bind("<Escape>", lambda _event: self.show_page("dashboard"))
        self.bind("<Command-1>", lambda _event: self.show_page("dashboard"))
        self.bind("<Command-2>", lambda _event: self.show_page("hourly"))
        self.bind("<Command-3>", lambda _event: self.show_page("guide"))
        self.bind("<Command-4>", lambda _event: self.show_page("compare"))
        self.bind("<Command-w>", lambda _event: self.handle_close())
        self.bind("<Command-q>", lambda _event: self.quit_application())
        self.refresh_sidebar()
        self.settings_page.load_settings(self.settings_store)
        self.apply_background()
        self.select_first_tab()
        if not self.settings_store.get("discord_token") or not any(row["channel_id"] for row in self.database.get_tabs()):
            self.show_page("guide")
        self.after(500, self.poll_ui_events)
        self.after(self._refresh_interval_ms(), self.periodic_refresh)
        self.after(3000, self.check_offline_status)

        token = self.settings_store.get("discord_token", "")
        if token:
            self.discord_service.start(token)

    def _build_layout(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.main_background = ctk.CTkFrame(self, fg_color=self.theme["bg"])
        self.main_background.grid(row=0, column=0, columnspan=2, sticky="nsew")
        self.main_background.grid_columnconfigure(1, weight=1)
        self.main_background.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(
            self.main_background,
            width=280,
            fg_color=self.theme["bg_alt"],
            corner_radius=0,
            border_width=1,
            border_color=self.theme["border"],
        )
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        self.sidebar.grid_propagate(False)

        ctk.CTkLabel(
            self.sidebar,
            text="BEE HQ",
            font=app_font(28, weight="bold"),
            text_color=self.theme["text"],
        ).pack(anchor="w", padx=20, pady=(26, 4))
        ctk.CTkLabel(
            self.sidebar,
            text="Discord-fed Natro dashboard",
            text_color=self.theme["text_muted"],
        ).pack(anchor="w", padx=20, pady=(0, 18))

        top_buttons = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        top_buttons.pack(fill="x", padx=16, pady=(0, 14))
        ctk.CTkButton(top_buttons, text="Dashboard", fg_color=self.theme["accent"], command=lambda: self.show_page("dashboard")).pack(side="left", padx=(0, 8))
        ctk.CTkButton(top_buttons, text="Hourly", fg_color=self.theme["panel_alt"], command=lambda: self.show_page("hourly")).pack(side="left", padx=(0, 8))
        ctk.CTkButton(top_buttons, text="Guide", fg_color=self.theme["panel_alt"], command=lambda: self.show_page("guide")).pack(side="left", padx=(0, 8))
        ctk.CTkButton(top_buttons, text="Compare", fg_color=self.theme["panel_alt"], command=lambda: self.show_page("compare")).pack(side="left", padx=(0, 8))
        ctk.CTkButton(top_buttons, text="Settings", fg_color=self.theme["panel_alt"], command=lambda: self.show_page("settings")).pack(side="left")

        ctk.CTkLabel(self.sidebar, text="Accounts", text_color=self.theme["text_muted"]).pack(anchor="w", padx=20, pady=(0, 10))
        self.tab_list = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent", width=248)
        self.tab_list.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        bottom_actions = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom_actions.pack(fill="x", padx=16, pady=(0, 18))
        ctk.CTkButton(bottom_actions, text="+ New Tab", fg_color=self.theme["accent"], command=self.create_tab).pack(fill="x", pady=(0, 8))
        ctk.CTkButton(bottom_actions, text="Move Up", fg_color=self.theme["panel_alt"], command=lambda: self.move_selected_tab(-1)).pack(fill="x", pady=(0, 8))
        ctk.CTkButton(bottom_actions, text="Move Down", fg_color=self.theme["panel_alt"], command=lambda: self.move_selected_tab(1)).pack(fill="x")

        self.content_host = ctk.CTkFrame(self.main_background, fg_color="transparent")
        self.content_host.grid(row=0, column=1, sticky="nsew", padx=18, pady=18)
        self.content_host.grid_rowconfigure(0, weight=1)
        self.content_host.grid_columnconfigure(0, weight=1)

        self.dashboard_page = DashboardPage(
            self.content_host,
            self.theme,
            callbacks={
                "send_command": self.send_macro_command,
                "refresh_dashboard": self.refresh_dashboard,
            },
        )
        self.dashboard_page.grid(row=0, column=0, sticky="nsew")
        self.dashboard_page.history_search.bind("<KeyRelease>", lambda _event: self.refresh_dashboard())

        self.hourly_reports_page = HourlyReportsPage(self.content_host, self.theme)
        self.hourly_reports_page.grid(row=0, column=0, sticky="nsew")
        self.hourly_reports_page.grid_remove()

        self.compare_page = ComparePage(self.content_host, self.theme)
        self.compare_page.grid(row=0, column=0, sticky="nsew")
        self.compare_page.grid_remove()

        self.setup_guide_page = SetupGuidePage(
            self.content_host,
            self.theme,
            callbacks={
                "show_page": self.show_page,
                "create_tab": self.create_tab,
            },
        )
        self.setup_guide_page.grid(row=0, column=0, sticky="nsew")
        self.setup_guide_page.grid_remove()

        self.settings_page = SettingsPage(
            self.content_host,
            self.theme,
            callbacks={
                "choose_background": self.choose_background_image,
                "remove_background": self.remove_background_image,
                "save_settings": self.save_settings,
                "test_discord": self.test_discord_connection,
                "export_csv": self.export_csv,
                "export_config": self.export_app_config,
                "import_config": self.import_app_config,
                "clear_history": self.clear_history,
                "create_tab": self.create_tab,
                "duplicate_tab": self.duplicate_selected_tab,
                "delete_tab": self.delete_selected_tab,
            },
        )
        self.settings_page.grid(row=0, column=0, sticky="nsew")
        self.settings_page.grid_remove()

    def enqueue_ui_event(self, payload: dict) -> None:
        self.pending_events.append(payload)

    def poll_ui_events(self) -> None:
        while self.pending_events:
            event = self.pending_events.pop(0)
            self.handle_ui_event(event)
        self.after(500, self.poll_ui_events)

    def handle_ui_event(self, payload: dict) -> None:
        event_type = payload.get("type")
        if event_type == "message_received":
            if payload.get("hourly_report") and self.settings_store.get("desktop_notifications", "1") == "1":
                tab_name = self._tab_name_for_id(payload.get("tab_id"))
                title = payload.get("hourly_title") or "A new hourly report image was captured."
                self.notification_service.show_hourly_report_notification(tab_name, title)
            if self.current_page == "hourly" and payload.get("hourly_report"):
                self.refresh_hourly_reports()
            else:
                self.refresh_dashboard()
        elif event_type == "discord_status":
            detail = payload.get("detail", "Discord status updated")
            self.settings_page.tab_hint.configure(text=f"Discord: {detail}")
        elif event_type == "command_sent":
            self.dashboard_page.set_command_status(payload.get("detail", "Command sent"), self.theme["success"])
            self.refresh_dashboard()
        elif event_type == "command_failed":
            self.dashboard_page.set_command_status(payload.get("detail", "Command failed"), self.theme["danger"])
            self.refresh_dashboard()
        elif event_type == "backfill_complete":
            detail = payload.get("detail", "Synced recent Discord history")
            self.settings_page.tab_hint.configure(text=detail)
            self.dashboard_page.set_command_status(detail, self.theme["accent"])
            if self.current_page == "hourly":
                self.refresh_hourly_reports()
            else:
                self.refresh_dashboard()
        elif event_type == "roblox_profile_synced":
            self.settings_page.tab_hint.configure(text=payload.get("detail", "Roblox profile synced"))
            self.refresh_sidebar()
            if self.current_page == "dashboard":
                self.refresh_dashboard()
            elif self.current_page == "hourly":
                self.refresh_hourly_reports()

    def show_page(self, name: str) -> None:
        self.current_page = name
        if name == "dashboard":
            self.compare_page.grid_remove()
            self.setup_guide_page.grid_remove()
            self.hourly_reports_page.grid_remove()
            self.settings_page.grid_remove()
            self.dashboard_page.grid()
            self.refresh_dashboard()
        elif name == "hourly":
            self.compare_page.grid_remove()
            self.setup_guide_page.grid_remove()
            self.settings_page.grid_remove()
            self.dashboard_page.grid_remove()
            self.hourly_reports_page.grid()
            self.refresh_hourly_reports()
        elif name == "compare":
            self.setup_guide_page.grid_remove()
            self.hourly_reports_page.grid_remove()
            self.dashboard_page.grid_remove()
            self.settings_page.grid_remove()
            self.compare_page.grid()
            self.refresh_compare_page()
        elif name == "guide":
            self.compare_page.grid_remove()
            self.hourly_reports_page.grid_remove()
            self.dashboard_page.grid_remove()
            self.settings_page.grid_remove()
            self.setup_guide_page.grid()
            self.setup_guide_page.render(self.settings_store, self.database.get_tabs())
        else:
            self.compare_page.grid_remove()
            self.setup_guide_page.grid_remove()
            self.hourly_reports_page.grid_remove()
            self.dashboard_page.grid_remove()
            self.settings_page.grid()

    def refresh_sidebar(self) -> None:
        for child in self.tab_list.winfo_children():
            child.destroy()
        self.sidebar_buttons.clear()
        tabs = self.database.get_tabs()
        for row in tabs:
            latest = self.database.get_latest_stat(row["id"])
            status_color = self.theme["text_muted"]
            if latest:
                status_color = self._tab_status_color(latest["created_at"], latest["online_status"])
            button = SidebarTabButton(
                self.tab_list,
                self.theme,
                row,
                status_color,
                on_select=self.select_tab,
                on_edit=self.edit_tab_dialog,
            )
            button.pack(fill="x", padx=4, pady=6)
            self.sidebar_buttons[row["id"]] = button
        if tabs and self.selected_tab_id is None:
            self.selected_tab_id = tabs[0]["id"]
        self._refresh_active_button()

    def _refresh_active_button(self) -> None:
        for tab_id, button in self.sidebar_buttons.items():
            button.set_active(tab_id == self.selected_tab_id)

    def select_first_tab(self) -> None:
        tabs = self.database.get_tabs()
        if tabs:
            self.select_tab(tabs[0]["id"])

    def select_tab(self, tab_id: int) -> None:
        self.selected_tab_id = tab_id
        self._refresh_active_button()
        if self.current_page == "hourly":
            self.refresh_hourly_reports()
        else:
            self.refresh_dashboard()

    def refresh_dashboard(self) -> None:
        if self.selected_tab_id is None:
            return
        tab_row = next((row for row in self.database.get_tabs() if row["id"] == self.selected_tab_id), None)
        if tab_row is None:
            return
        summary = self.database.get_tab_summary(self.selected_tab_id)
        announcement_channel_id = tab_row["announcement_channel_id"] or None
        summary["recent_announcements"] = self.database.get_recent_announcements(
            tab_id=self.selected_tab_id,
            channel_id=announcement_channel_id,
            limit=8,
        )
        summary["recent_commands"] = self.database.get_recent_commands(self.selected_tab_id, limit=6)
        search = self.dashboard_page.history_search.get().strip()
        messages = self.database.get_recent_messages(self.selected_tab_id, search=search, limit=30)
        self.dashboard_page.render(tab_row, summary, messages, search_term=search)
        background_override = tab_row["background_override"] if tab_row["background_override"] else self.settings_store.get("background_image", "")
        self.apply_background(background_override)

    def refresh_hourly_reports(self) -> None:
        if self.selected_tab_id is None:
            return
        tab_row = next((row for row in self.database.get_tabs() if row["id"] == self.selected_tab_id), None)
        if tab_row is None:
            return
        reports = self.database.get_recent_hourly_reports(self.selected_tab_id, limit=12)
        self.hourly_reports_page.render(tab_row, reports)
        background_override = tab_row["background_override"] if tab_row["background_override"] else self.settings_store.get("background_image", "")
        self.apply_background(background_override)

    def refresh_compare_page(self) -> None:
        self.compare_page.render(self.database.get_compare_rows())
        self.apply_background()

    def create_tab(self) -> None:
        tab_id = self.database.create_tab("New Account")
        self.refresh_sidebar()
        self.select_tab(tab_id)
        self.edit_tab_dialog(next(row for row in self.database.get_tabs() if row["id"] == tab_id))

    def edit_tab_dialog(self, tab_row) -> None:
        initial = {
            "name": tab_row["name"],
            "account_name": tab_row["account_name"],
            "roblox_username": tab_row["roblox_username"],
            "channel_id": tab_row["channel_id"],
            "source_author_filter": tab_row["source_author_filter"],
            "ingest_bots_only": str(tab_row["ingest_bots_only"]),
            "command_channel_id": tab_row["command_channel_id"],
            "announcement_channel_id": tab_row["announcement_channel_id"],
            "accent_color": tab_row["accent_color"],
            "background_override": tab_row["background_override"],
            "layout_preference": tab_row["layout_preference"],
        }

        def on_save(values: dict[str, str]) -> None:
            values["ingest_bots_only"] = "1" if values.get("ingest_bots_only", "Yes").strip().lower() in {"1", "true", "yes", "on"} else "0"
            roblox_username = values.get("roblox_username", "").strip()
            if not roblox_username:
                values.update(
                    {
                        "roblox_user_id": "",
                        "roblox_display_name": "",
                        "roblox_avatar_url": "",
                        "roblox_avatar_path": "",
                    }
                )
            self.database.update_tab(tab_row["id"], values)
            if roblox_username:
                threading.Thread(
                    target=self._sync_roblox_profile_worker,
                    args=(tab_row["id"], roblox_username),
                    daemon=True,
                ).start()
            self.refresh_sidebar()
            self.refresh_dashboard()

        dialog = TabEditorDialog(self, self.theme, initial, on_save)
        dialog.focus()

    def duplicate_selected_tab(self) -> None:
        if self.selected_tab_id is None:
            return
        new_id = self.database.duplicate_tab(self.selected_tab_id)
        self.refresh_sidebar()
        self.select_tab(new_id)

    def delete_selected_tab(self) -> None:
        if self.selected_tab_id is None:
            return
        tabs = self.database.get_tabs()
        if len(tabs) <= 1:
            messagebox.showinfo("Cannot delete", "At least one tab is required.")
            return
        if not messagebox.askyesno("Delete tab", "Delete the selected tab?"):
            return
        self.database.delete_tab(self.selected_tab_id)
        self.selected_tab_id = None
        self.refresh_sidebar()
        self.select_first_tab()

    def move_selected_tab(self, delta: int) -> None:
        if self.selected_tab_id is None:
            return
        tabs = self.database.get_tabs()
        ids = [row["id"] for row in tabs]
        try:
            index = ids.index(self.selected_tab_id)
        except ValueError:
            return
        new_index = max(0, min(len(ids) - 1, index + delta))
        if new_index == index:
            return
        ids[index], ids[new_index] = ids[new_index], ids[index]
        self.database.reorder_tabs(ids)
        self.refresh_sidebar()
        self._refresh_active_button()

    def choose_background_image(self) -> None:
        selected = filedialog.askopenfilename(
            title="Choose background image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp")],
        )
        if not selected:
            return
        imported_path = self.image_cache.import_background(Path(selected))
        self.settings_page.set_background_path(imported_path)
        self.save_settings()

    def remove_background_image(self) -> None:
        current = self.settings_page.background_image_path.get().strip()
        if current:
            self.image_cache.remove_background(current)
        self.settings_page.set_background_path("")
        self.save_settings()

    def save_settings(self) -> None:
        previous_font = self.settings_store.get("font_preset", "System Sans")
        values = self.settings_page.collect_settings()
        self.database.save_settings(values)
        write_env_value("DISCORD_BOT_TOKEN", values["discord_token"])
        write_env_value("DISCORD_WATCHED_CHANNELS", values["watched_channels"])
        write_env_value("ANNOUNCEMENT_CHANNELS", values["announcement_channels"])
        write_env_value("COMMAND_PREFIX", values["command_prefix"])
        write_env_value("DEBUG_LOGGING", "true" if values["debug_logging"] == "1" else "false")
        self.settings_store = self.database.get_settings()
        set_active_font_preset(self.settings_store.get("font_preset", "System Sans"))
        self.theme = build_theme(self.settings_store)
        self._apply_background_preferences()
        launch_message = self.launch_agent_service.sync(self.settings_store.get("launch_at_login", "0") == "1")
        self._rebuild_ui()
        self.discord_service.stop()
        if self.settings_store.get("discord_token"):
            self.discord_service.start(self.settings_store.get("discord_token", ""))
        font_note = ""
        if self.settings_store.get("font_preset", "System Sans") != previous_font:
            font_note = "\nFont preset applied across the app."
        messagebox.showinfo("Saved", f"Settings saved.{font_note}\n{launch_message}")

    def _apply_background_preferences(self) -> None:
        if self.settings_store.get("enable_menubar_helper", "1") == "1":
            self.menu_bar_service.start()
        else:
            self.menu_bar_service.stop()

    def _rebuild_ui(self) -> None:
        selected_tab = self.selected_tab_id
        current_page = self.current_page
        if hasattr(self, "main_background") and self.main_background is not None:
            self.main_background.destroy()
        self.sidebar_buttons.clear()
        self.background_label = None
        self.background_image_ref = None
        self._background_signature = None
        self._build_layout()
        self.settings_page.load_settings(self.settings_store)
        self.apply_background()
        self.refresh_sidebar()
        tabs = self.database.get_tabs()
        valid_ids = {row["id"] for row in tabs}
        self.selected_tab_id = selected_tab if selected_tab in valid_ids else None
        if self.selected_tab_id is None and tabs:
            self.selected_tab_id = tabs[0]["id"]
        self._refresh_active_button()
        self.show_page(current_page if current_page in {"dashboard", "hourly", "guide", "compare", "settings"} else "dashboard")

    def apply_background(self, override_path: str | None = None) -> None:
        image_path = override_path or self.settings_store.get("background_image", "")
        if self.background_label is None:
            self.background_label = ctk.CTkLabel(self.main_background, text="")
            self.background_label.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.background_label.lower()
        use_gradient = self.settings_store.get("gradient_enabled", "1") == "1"
        if not image_path or not Path(image_path).exists():
            if not use_gradient:
                self.background_label.configure(image=None, text="")
                self.background_image_ref = None
                self._background_signature = ("none", self.theme["bg"])
                self.main_background.configure(fg_color=self.theme["bg"])
                return
            image_path = ""
        try:
            width = max(self.winfo_width(), 1440)
            height = max(self.winfo_height(), 900)
            blur_amount = float(self.settings_store.get("blur_amount", 8))
            dim_amount = float(self.settings_store.get("background_dim", 0.42))
            if image_path:
                signature = (
                    "image",
                    image_path,
                    width,
                    height,
                    blur_amount,
                    dim_amount,
                )
            else:
                signature = (
                    "gradient",
                    normalize_hex(self.settings_store.get("gradient_start", "#090909"), "#090909"),
                    normalize_hex(self.settings_store.get("gradient_end", "#161a22"), "#161a22"),
                    self.settings_store.get("gradient_direction", "diagonal"),
                    width,
                    height,
                    blur_amount,
                    dim_amount,
                )
            if signature == self._background_signature and self.background_image_ref is not None:
                return
            styled_path = self.paths.cache / "styled_background.png"
            if image_path:
                final_path = self.image_cache.build_styled_background(
                    image_path,
                    styled_path,
                    size=(width, height),
                    blur_amount=blur_amount,
                    dim_amount=dim_amount,
                )
            else:
                final_path = self.image_cache.build_gradient_background(
                    styled_path,
                    size=(width, height),
                    start_color=signature[1],
                    end_color=signature[2],
                    direction=str(signature[3]),
                    blur_amount=blur_amount,
                    dim_amount=dim_amount,
                )
            from PIL import Image

            image = Image.open(final_path)
            self.background_image_ref = ctk.CTkImage(light_image=image, dark_image=image, size=(width, height))
            self.background_label.configure(image=self.background_image_ref)
            self._background_signature = signature
        except Exception:
            self.background_label.configure(image=None)
            self.background_image_ref = None
            self._background_signature = None

    def test_discord_connection(self) -> None:
        values = self.settings_page.collect_settings()
        self.database.save_settings(values)
        self.discord_service.stop()
        self.discord_service.test_connection(values["discord_token"])

    def export_csv(self) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = self.paths.exports / f"stats_export_{timestamp}.csv"
        exported = self.database.export_stats_csv(target)
        messagebox.showinfo("Export complete", f"Saved CSV to:\n{exported}")

    def export_app_config(self) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = filedialog.asksaveasfilename(
            title="Export Bee HQ config",
            defaultextension=".json",
            initialfile=f"beehq_config_{timestamp}.json",
            filetypes=[("JSON", "*.json")],
        )
        if not target:
            return
        exported = self.database.export_app_config(Path(target))
        messagebox.showinfo("Export complete", f"Saved Bee HQ config to:\n{exported}")

    def import_app_config(self) -> None:
        selected = filedialog.askopenfilename(
            title="Import Bee HQ config",
            filetypes=[("JSON", "*.json")],
        )
        if not selected:
            return
        if not messagebox.askyesno("Import config", "Importing a config will replace your current tabs and settings. Continue?"):
            return
        result = self.database.import_app_config(Path(selected))
        self.settings_store = self.database.get_settings()
        set_active_font_preset(self.settings_store.get("font_preset", "System Sans"))
        self.theme = build_theme(self.settings_store)
        self._apply_background_preferences()
        self._rebuild_ui()
        self.discord_service.stop()
        if self.settings_store.get("discord_token"):
            self.discord_service.start(self.settings_store.get("discord_token", ""))
        messagebox.showinfo("Import complete", f"Imported {result['tabs']} tab(s) and refreshed settings.")

    def clear_history(self) -> None:
        if not messagebox.askyesno("Clear history", "Delete all stored messages and parsed stats?"):
            return
        self.database.clear_history()
        self.refresh_dashboard()

    def send_macro_command(self, action: str) -> None:
        if self.selected_tab_id is None:
            return
        tabs = self.database.get_tabs()
        tab_row = next((row for row in tabs if row["id"] == self.selected_tab_id), None)
        if tab_row is None:
            return
        channel_id = tab_row["command_channel_id"] or tab_row["channel_id"]
        if not channel_id:
            messagebox.showwarning("Missing channel", "Set a command channel or update channel for this tab first.")
            return
        prefix = self.settings_store.get("command_prefix", "?") or "?"
        command_text = f"{prefix}{action}"
        self.dashboard_page.set_command_status(f"Sending {command_text}...", self.theme["warning"])
        threading.Thread(
            target=self._send_command_worker,
            args=(tab_row["id"], str(channel_id), command_text),
            daemon=True,
        ).start()

    def _send_command_worker(self, tab_id: int, channel_id: str, command_text: str) -> None:
        self.discord_service.send_command(
            tab_id=tab_id,
            channel_id=channel_id,
            command_text=command_text,
        )

    def _sync_roblox_profile_worker(self, tab_id: int, roblox_username: str) -> None:
        try:
            profile = self.roblox_profile_service.fetch_profile(roblox_username)
            self.database.update_tab(
                tab_id,
                {
                    "roblox_username": profile.username,
                    "roblox_user_id": profile.user_id,
                    "roblox_display_name": profile.display_name,
                    "roblox_avatar_url": profile.avatar_url,
                    "roblox_avatar_path": profile.avatar_path,
                },
            )
            self.enqueue_ui_event(
                {
                    "type": "roblox_profile_synced",
                    "detail": f"Roblox profile synced for @{profile.username}",
                }
            )
        except Exception as exc:
            self.enqueue_ui_event(
                {
                    "type": "roblox_profile_synced",
                    "detail": f"Roblox sync failed: {exc}",
                }
            )

    def periodic_refresh(self) -> None:
        self.refresh_sidebar()
        if self.current_page == "dashboard":
            self.refresh_dashboard()
        elif self.current_page == "hourly":
            self.refresh_hourly_reports()
        elif self.current_page == "compare":
            self.refresh_compare_page()
        self.after(self._refresh_interval_ms(), self.periodic_refresh)

    def _refresh_interval_ms(self) -> int:
        try:
            value = int(self.settings_store.get("refresh_interval", "1200"))
        except ValueError:
            value = 1200
        return max(500, min(value, 10_000))

    def handle_close(self) -> None:
        if self.settings_store.get("run_in_background_on_close", "1") == "1":
            self.hide_to_background()
            return
        self.quit_application()

    def hide_to_background(self) -> None:
        self._background_hidden = True
        try:
            self.iconify()
        except Exception:
            self.withdraw()
        self.settings_page.tab_hint.configure(
            text="Bee HQ is still running in the background and can keep syncing Discord until you fully quit it."
        )

    def restore_from_background(self) -> None:
        self._background_hidden = False
        try:
            self.deiconify()
        except Exception:
            pass
        self.lift()
        self.focus_force()
        if self.current_page == "hourly":
            self.refresh_hourly_reports()
        else:
            self.refresh_dashboard()

    def quit_application(self) -> None:
        self.menu_bar_service.stop()
        self.discord_service.stop()
        self.destroy()

    def _tab_name_for_id(self, tab_id: int | None) -> str:
        if tab_id is None:
            return "Bee HQ"
        for row in self.database.get_tabs():
            if row["id"] == tab_id:
                return row["name"]
        return "Bee HQ"


    def check_offline_status(self) -> None:
        timeout_minutes = int(self.settings_store.get("offline_timeout_minutes", 10))
        for tab in self.database.get_tabs():
            latest = self.database.get_latest_stat(tab["id"])
            last_update = None
            if latest:
                try:
                    stamp = datetime.fromisoformat(str(latest["created_at"]).replace("Z", "+00:00"))
                    last_update = stamp.astimezone(timezone.utc).replace(tzinfo=None)
                except ValueError:
                    last_update = None
            if self.notification_service.should_alert(tab["id"], last_update, timeout_minutes):
                self.notification_service.show_offline_alert(tab["name"])
        self.after(60_000, self.check_offline_status)

    def _tab_status_color(self, created_at: str, online_status: str) -> str:
        try:
            stamp = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
            age_minutes = (datetime.now(timezone.utc) - stamp.astimezone(timezone.utc)).total_seconds() / 60
        except ValueError:
            return self.theme["text_muted"]
        timeout_minutes = int(self.settings_store.get("offline_timeout_minutes", 10))
        if online_status == "offline":
            return self.theme["danger"]
        if age_minutes <= timeout_minutes:
            return self.theme["success"]
        if age_minutes <= timeout_minutes * 2:
            return self.theme["warning"]
        return self.theme["danger"]
