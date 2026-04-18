from __future__ import annotations

import csv
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


DEFAULT_SETTINGS: dict[str, str] = {
    "theme_preset": "black",
    "font_preset": "System Sans",
    "accent_color": "#58c4ff",
    "transparent_mode": "1",
    "panel_opacity": "0.9",
    "background_dim": "0.42",
    "blur_amount": "8",
    "background_image": "",
    "gradient_enabled": "1",
    "gradient_start": "#090909",
    "gradient_end": "#161a22",
    "gradient_direction": "diagonal",
    "discord_token": "",
    "watched_channels": "",
    "announcement_channels": "",
    "command_prefix": "?",
    "debug_logging": "0",
    "refresh_interval": "1200",
    "startup_backfill_hours": "12",
    "offline_timeout_minutes": "10",
    "run_in_background_on_close": "0",
    "enable_menubar_helper": "1",
    "desktop_notifications": "1",
    "launch_at_login": "0",
    "close_behavior_migrated_v2": "1",
}


class Database:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connection(self) -> Iterable[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connection() as conn:
            conn.executescript(
                """
                PRAGMA foreign_keys = ON;

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS tabs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    channel_id TEXT DEFAULT '',
                    account_name TEXT DEFAULT '',
                    accent_color TEXT DEFAULT '',
                    background_override TEXT DEFAULT '',
                    layout_preference TEXT DEFAULT 'overview',
                    display_order INTEGER NOT NULL DEFAULT 0,
                    custom_settings_json TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS raw_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tab_id INTEGER,
                    channel_id TEXT NOT NULL,
                    message_id TEXT NOT NULL UNIQUE,
                    author_name TEXT DEFAULT '',
                    content TEXT DEFAULT '',
                    embed_json TEXT DEFAULT '[]',
                    attachment_paths TEXT DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    parsed_ok INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (tab_id) REFERENCES tabs(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS parsed_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tab_id INTEGER,
                    message_id TEXT NOT NULL,
                    honey REAL,
                    pollen REAL,
                    honey_per_second REAL,
                    backpack_percent REAL,
                    convert_status TEXT DEFAULT '',
                    session_total REAL,
                    hourly_rate REAL,
                    online_status TEXT DEFAULT 'unknown',
                    raw_summary TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (tab_id) REFERENCES tabs(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS notification_state (
                    tab_id INTEGER PRIMARY KEY,
                    last_alert_at TEXT DEFAULT '',
                    FOREIGN KEY (tab_id) REFERENCES tabs(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS announcements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tab_id INTEGER,
                    channel_id TEXT NOT NULL,
                    source_message_id TEXT NOT NULL UNIQUE,
                    title TEXT DEFAULT '',
                    body TEXT DEFAULT '',
                    category TEXT DEFAULT 'general',
                    relevance_score INTEGER NOT NULL DEFAULT 0,
                    embed_json TEXT DEFAULT '[]',
                    attachment_paths TEXT DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (tab_id) REFERENCES tabs(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS command_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tab_id INTEGER,
                    channel_id TEXT NOT NULL,
                    command_text TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    detail TEXT DEFAULT '',
                    requested_at TEXT NOT NULL,
                    completed_at TEXT DEFAULT '',
                    FOREIGN KEY (tab_id) REFERENCES tabs(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS hourly_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tab_id INTEGER,
                    channel_id TEXT NOT NULL,
                    source_message_id TEXT NOT NULL UNIQUE,
                    title TEXT DEFAULT '',
                    report_time_label TEXT DEFAULT '',
                    body TEXT DEFAULT '',
                    embed_json TEXT DEFAULT '[]',
                    attachment_paths TEXT DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (tab_id) REFERENCES tabs(id) ON DELETE SET NULL
                );
                """
            )
            self._ensure_column(conn, "tabs", "command_channel_id", "TEXT DEFAULT ''")
            self._ensure_column(conn, "tabs", "announcement_channel_id", "TEXT DEFAULT ''")
            self._ensure_column(conn, "tabs", "source_author_filter", "TEXT DEFAULT ''")
            self._ensure_column(conn, "tabs", "ingest_bots_only", "INTEGER NOT NULL DEFAULT 1")
            self._ensure_column(conn, "tabs", "roblox_username", "TEXT DEFAULT ''")
            self._ensure_column(conn, "tabs", "roblox_user_id", "TEXT DEFAULT ''")
            self._ensure_column(conn, "tabs", "roblox_display_name", "TEXT DEFAULT ''")
            self._ensure_column(conn, "tabs", "roblox_avatar_url", "TEXT DEFAULT ''")
            self._ensure_column(conn, "tabs", "roblox_avatar_path", "TEXT DEFAULT ''")
            self._ensure_column(conn, "tabs", "auto_hr_enabled", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(conn, "tabs", "auto_hr_interval_minutes", "INTEGER NOT NULL DEFAULT 30")
            self._ensure_column(conn, "tabs", "auto_hr_last_requested_at", "TEXT DEFAULT ''")
            self._ensure_column(conn, "hourly_reports", "ocr_hourly_average", "REAL")
            self._ensure_column(conn, "hourly_reports", "ocr_last_hour", "REAL")
            self._ensure_column(conn, "hourly_reports", "ocr_text", "TEXT DEFAULT ''")
            self._ensure_column(conn, "hourly_reports", "ocr_ok", "INTEGER NOT NULL DEFAULT 0")
            conn.executescript(
                """
                CREATE INDEX IF NOT EXISTS idx_tabs_channel_id ON tabs(channel_id);
                CREATE INDEX IF NOT EXISTS idx_tabs_announcement_channel_id ON tabs(announcement_channel_id);
                CREATE INDEX IF NOT EXISTS idx_raw_messages_tab_created_at ON raw_messages(tab_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_raw_messages_channel_created_at ON raw_messages(channel_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_parsed_stats_tab_created_at ON parsed_stats(tab_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_announcements_tab_relevance_created_at ON announcements(tab_id, relevance_score DESC, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_announcements_channel_relevance_created_at ON announcements(channel_id, relevance_score DESC, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_command_history_tab_requested_at ON command_history(tab_id, requested_at DESC);
                CREATE INDEX IF NOT EXISTS idx_hourly_reports_tab_created_at ON hourly_reports(tab_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_hourly_reports_channel_created_at ON hourly_reports(channel_id, created_at DESC);
                """
            )
            for key, value in DEFAULT_SETTINGS.items():
                conn.execute(
                    "INSERT OR IGNORE INTO settings(key, value) VALUES(?, ?)",
                    (key, value),
                )
            migrated = conn.execute(
                "SELECT value FROM settings WHERE key='close_behavior_migrated_v2'"
            ).fetchone()
            if not migrated:
                conn.execute(
                    """
                    INSERT INTO settings(key, value) VALUES('run_in_background_on_close', '0')
                    ON CONFLICT(key) DO UPDATE SET value='0'
                    """
                )
                conn.execute(
                    """
                    INSERT INTO settings(key, value) VALUES('close_behavior_migrated_v2', '1')
                    ON CONFLICT(key) DO UPDATE SET value='1'
                    """
                )
            if not conn.execute("SELECT 1 FROM tabs LIMIT 1").fetchone():
                conn.execute(
                    """
                    INSERT INTO tabs(
                        name, channel_id, account_name, accent_color,
                        background_override, layout_preference, display_order
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "Main Account",
                        "",
                        "Bee Main",
                        "#58c4ff",
                        "",
                        "overview",
                        0,
                    ),
                )

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        columns = {
            row["name"]
            for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def get_settings(self) -> dict[str, str]:
        with self.connection() as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
        return {row["key"]: row["value"] for row in rows}

    def save_settings(self, values: dict[str, Any]) -> None:
        with self.connection() as conn:
            for key, value in values.items():
                conn.execute(
                    """
                    INSERT INTO settings(key, value) VALUES(?, ?)
                    ON CONFLICT(key) DO UPDATE SET value=excluded.value
                    """,
                    (key, str(value)),
                )

    def get_tabs(self) -> list[sqlite3.Row]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM tabs ORDER BY display_order ASC, id ASC"
            ).fetchall()
        return list(rows)

    def create_tab(self, name: str = "New Tab") -> int:
        with self.connection() as conn:
            next_order = conn.execute(
                "SELECT COALESCE(MAX(display_order), -1) + 1 AS next_order FROM tabs"
            ).fetchone()["next_order"]
            cursor = conn.execute(
                """
                INSERT INTO tabs(
                    name, channel_id, account_name, accent_color, background_override,
                    layout_preference, display_order, custom_settings_json
                ) VALUES (?, '', '', '', '', 'overview', ?, '{}')
                """,
                (name, next_order),
            )
            return int(cursor.lastrowid)

    def update_tab(self, tab_id: int, values: dict[str, Any]) -> None:
        if not values:
            return
        columns = ", ".join(f"{key}=?" for key in values.keys())
        params = list(values.values()) + [tab_id]
        with self.connection() as conn:
            conn.execute(f"UPDATE tabs SET {columns} WHERE id=?", params)

    def duplicate_tab(self, tab_id: int) -> int:
        with self.connection() as conn:
            source = conn.execute("SELECT * FROM tabs WHERE id=?", (tab_id,)).fetchone()
            if source is None:
                raise ValueError("Tab not found")
            next_order = conn.execute(
                "SELECT COALESCE(MAX(display_order), -1) + 1 AS next_order FROM tabs"
            ).fetchone()["next_order"]
            cursor = conn.execute(
                """
                INSERT INTO tabs(
                    name, channel_id, account_name, accent_color, background_override,
                    layout_preference, display_order, custom_settings_json,
                    source_author_filter, ingest_bots_only,
                    roblox_username, roblox_user_id, roblox_display_name, roblox_avatar_url, roblox_avatar_path,
                    command_channel_id, announcement_channel_id,
                    auto_hr_enabled, auto_hr_interval_minutes, auto_hr_last_requested_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"{source['name']} Copy",
                    source["channel_id"],
                    source["account_name"],
                    source["accent_color"],
                    source["background_override"],
                    source["layout_preference"],
                    next_order,
                    source["custom_settings_json"],
                    source["source_author_filter"],
                    source["ingest_bots_only"],
                    source["roblox_username"],
                    source["roblox_user_id"],
                    source["roblox_display_name"],
                    source["roblox_avatar_url"],
                    source["roblox_avatar_path"],
                    source["command_channel_id"],
                    source["announcement_channel_id"],
                    source["auto_hr_enabled"],
                    source["auto_hr_interval_minutes"],
                    "",
                ),
            )
            return int(cursor.lastrowid)

    def delete_tab(self, tab_id: int) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM tabs WHERE id=?", (tab_id,))

    def reorder_tabs(self, ordered_ids: list[int]) -> None:
        with self.connection() as conn:
            for index, tab_id in enumerate(ordered_ids):
                conn.execute(
                    "UPDATE tabs SET display_order=? WHERE id=?",
                    (index, tab_id),
                )

    def find_tab_for_channel(self, channel_id: str) -> sqlite3.Row | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM tabs WHERE channel_id=? ORDER BY id ASC LIMIT 1",
                (str(channel_id),),
            ).fetchone()
        return row

    def find_tab_for_announcement_channel(self, channel_id: str) -> sqlite3.Row | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM tabs WHERE announcement_channel_id=? ORDER BY id ASC LIMIT 1",
                (str(channel_id),),
            ).fetchone()
        return row

    def insert_message(
        self,
        *,
        tab_id: int | None,
        channel_id: str,
        message_id: str,
        author_name: str,
        content: str,
        embed_json: str,
        attachment_paths: str,
        created_at: str,
        parsed_ok: int,
    ) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO raw_messages(
                    tab_id, channel_id, message_id, author_name, content, embed_json,
                    attachment_paths, created_at, parsed_ok
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tab_id,
                    channel_id,
                    message_id,
                    author_name,
                    content,
                    embed_json,
                    attachment_paths,
                    created_at,
                    parsed_ok,
                ),
            )

    def has_message(self, message_id: str) -> bool:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM raw_messages WHERE message_id=? LIMIT 1",
                (str(message_id),),
            ).fetchone()
        return row is not None

    def get_latest_message_created_at_for_channel(self, channel_id: str) -> str:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT created_at FROM raw_messages
                WHERE channel_id=?
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (str(channel_id),),
            ).fetchone()
        return str(row["created_at"]) if row else ""

    def insert_parsed_stats(self, values: dict[str, Any]) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO parsed_stats(
                    tab_id, message_id, honey, pollen, honey_per_second,
                    backpack_percent, convert_status, session_total, hourly_rate,
                    online_status, raw_summary, created_at
                ) VALUES (
                    :tab_id, :message_id, :honey, :pollen, :honey_per_second,
                    :backpack_percent, :convert_status, :session_total, :hourly_rate,
                    :online_status, :raw_summary, :created_at
                )
                """,
                values,
            )

    def insert_announcement(self, values: dict[str, Any]) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO announcements(
                    tab_id, channel_id, source_message_id, title, body, category,
                    relevance_score, embed_json, attachment_paths, created_at
                ) VALUES(
                    :tab_id, :channel_id, :source_message_id, :title, :body, :category,
                    :relevance_score, :embed_json, :attachment_paths, :created_at
                )
                """,
                values,
            )

    def insert_command_log(
        self,
        *,
        tab_id: int | None,
        channel_id: str,
        command_text: str,
        status: str,
        detail: str,
        requested_at: str,
    ) -> int:
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO command_history(
                    tab_id, channel_id, command_text, status, detail, requested_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (tab_id, channel_id, command_text, status, detail, requested_at),
            )
            return int(cursor.lastrowid)

    def insert_hourly_report(self, values: dict[str, Any]) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO hourly_reports(
                    tab_id, channel_id, source_message_id, title, report_time_label,
                    body, embed_json, attachment_paths, created_at,
                    ocr_hourly_average, ocr_last_hour, ocr_text, ocr_ok
                ) VALUES(
                    :tab_id, :channel_id, :source_message_id, :title, :report_time_label,
                    :body, :embed_json, :attachment_paths, :created_at,
                    :ocr_hourly_average, :ocr_last_hour, :ocr_text, :ocr_ok
                )
                """,
                values,
            )

    def update_command_log(self, command_id: int, status: str, detail: str, completed_at: str) -> None:
        with self.connection() as conn:
            conn.execute(
                """
                UPDATE command_history
                SET status=?, detail=?, completed_at=?
                WHERE id=?
                """,
                (status, detail, completed_at, command_id),
            )

    def get_recent_messages(self, tab_id: int, search: str = "", limit: int = 50) -> list[sqlite3.Row]:
        with self.connection() as conn:
            if search:
                rows = conn.execute(
                    """
                    SELECT * FROM raw_messages
                    WHERE tab_id=? AND (content LIKE ? OR author_name LIKE ?)
                    ORDER BY created_at DESC, id DESC
                    LIMIT ?
                    """,
                    (tab_id, f"%{search}%", f"%{search}%", limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM raw_messages
                    WHERE tab_id=?
                    ORDER BY created_at DESC, id DESC
                    LIMIT ?
                    """,
                    (tab_id, limit),
                ).fetchall()
        return list(rows)

    def get_recent_stats(self, tab_id: int, limit: int = 24) -> list[sqlite3.Row]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM parsed_stats
                WHERE tab_id=?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (tab_id, limit),
            ).fetchall()
        return list(rows)

    def get_latest_stat(self, tab_id: int) -> sqlite3.Row | None:
        with self.connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM parsed_stats
                WHERE tab_id=?
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (tab_id,),
            ).fetchone()
        return row

    def get_effective_latest_stat(self, tab_id: int, lookback: int = 20) -> dict[str, Any] | None:
        recent = self.get_recent_stats(tab_id, limit=lookback)
        if not recent:
            return None
        latest = dict(recent[0])
        tracked_fields = (
            "honey",
            "pollen",
            "honey_per_second",
            "backpack_percent",
            "convert_status",
            "session_total",
            "hourly_rate",
            "online_status",
            "raw_summary",
        )
        for field in tracked_fields:
            if latest.get(field) not in (None, "", "unknown"):
                continue
            for row in recent[1:]:
                value = row[field]
                if value not in (None, "", "unknown"):
                    latest[field] = value
                    break
        return latest

    def get_recent_images(self, tab_id: int, limit: int = 8) -> list[str]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT attachment_paths FROM raw_messages
                WHERE tab_id=? AND attachment_paths != '[]'
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (tab_id, limit),
            ).fetchall()
        paths: list[str] = []
        for row in rows:
            for path in json.loads(row["attachment_paths"] or "[]"):
                if path not in paths:
                    paths.append(path)
        return paths[:limit]

    def get_tab_summary(self, tab_id: int) -> dict[str, Any]:
        latest = self.get_effective_latest_stat(tab_id)
        recent = self.get_recent_stats(tab_id, limit=12)
        messages = self.get_recent_messages(tab_id, limit=1)
        result: dict[str, Any] = {
            "latest": latest,
            "recent": recent,
            "latest_message": messages[0] if messages else None,
            "recent_images": self.get_recent_images(tab_id),
        }
        return result

    def get_recent_announcements(
        self,
        *,
        tab_id: int | None = None,
        channel_id: str | None = None,
        limit: int = 8,
    ) -> list[sqlite3.Row]:
        with self.connection() as conn:
            if channel_id:
                rows = conn.execute(
                    """
                    SELECT * FROM announcements
                    WHERE channel_id=?
                    ORDER BY relevance_score DESC, created_at DESC, id DESC
                    LIMIT ?
                    """,
                    (str(channel_id), limit),
                ).fetchall()
            elif tab_id is not None:
                rows = conn.execute(
                    """
                    SELECT * FROM announcements
                    WHERE tab_id=? OR tab_id IS NULL
                    ORDER BY relevance_score DESC, created_at DESC, id DESC
                    LIMIT ?
                    """,
                    (tab_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM announcements
                    ORDER BY relevance_score DESC, created_at DESC, id DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
        return list(rows)

    def get_recent_hourly_reports(self, tab_id: int, limit: int = 12) -> list[sqlite3.Row]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM hourly_reports
                WHERE tab_id=?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (tab_id, limit),
            ).fetchall()
        return list(rows)

    def get_recent_commands(self, tab_id: int, limit: int = 6) -> list[sqlite3.Row]:
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM command_history
                WHERE tab_id=?
                ORDER BY requested_at DESC, id DESC
                LIMIT ?
                """,
                (tab_id, limit),
            ).fetchall()
        return list(rows)

    def update_auto_hr_state(self, tab_id: int, requested_at: str) -> None:
        with self.connection() as conn:
            conn.execute(
                "UPDATE tabs SET auto_hr_last_requested_at=? WHERE id=?",
                (requested_at, tab_id),
            )

    def clear_history(self) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM parsed_stats")
            conn.execute("DELETE FROM raw_messages")
            conn.execute("DELETE FROM announcements")
            conn.execute("DELETE FROM command_history")
            conn.execute("DELETE FROM hourly_reports")

    def export_stats_csv(self, export_path: Path) -> Path:
        export_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM parsed_stats ORDER BY created_at DESC, id DESC"
            ).fetchall()
        with export_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "id",
                    "tab_id",
                    "message_id",
                    "honey",
                    "pollen",
                    "honey_per_second",
                    "backpack_percent",
                    "convert_status",
                    "session_total",
                    "hourly_rate",
                    "online_status",
                    "raw_summary",
                    "created_at",
                ]
            )
            for row in rows:
                writer.writerow([row[column] for column in row.keys()])
        return export_path

    def export_app_config(self, export_path: Path) -> Path:
        export_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as conn:
            settings_rows = conn.execute("SELECT key, value FROM settings ORDER BY key ASC").fetchall()
            tab_rows = conn.execute("SELECT * FROM tabs ORDER BY display_order ASC, id ASC").fetchall()
        payload = {
            "version": 1,
            "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "settings": {row["key"]: row["value"] for row in settings_rows},
            "tabs": [dict(row) for row in tab_rows],
        }
        export_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return export_path

    def import_app_config(self, import_path: Path) -> dict[str, int]:
        payload = json.loads(import_path.read_text(encoding="utf-8"))
        settings = payload.get("settings", {})
        tabs = payload.get("tabs", [])
        default_tab = {
            "name": "Main Account",
            "channel_id": "",
            "account_name": "Bee Main",
            "accent_color": "#58c4ff",
            "background_override": "",
            "layout_preference": "overview",
            "display_order": 0,
            "custom_settings_json": "{}",
            "command_channel_id": "",
            "announcement_channel_id": "",
            "source_author_filter": "",
            "ingest_bots_only": 1,
            "roblox_username": "",
            "roblox_user_id": "",
            "roblox_display_name": "",
            "roblox_avatar_url": "",
            "roblox_avatar_path": "",
            "auto_hr_enabled": 0,
            "auto_hr_interval_minutes": 30,
            "auto_hr_last_requested_at": "",
        }
        columns = list(default_tab.keys())
        placeholders = ", ".join("?" for _ in columns)
        with self.connection() as conn:
            conn.execute("DELETE FROM tabs")
            for key, default in DEFAULT_SETTINGS.items():
                conn.execute(
                    """
                    INSERT INTO settings(key, value) VALUES(?, ?)
                    ON CONFLICT(key) DO UPDATE SET value=excluded.value
                    """,
                    (key, str(settings.get(key, default))),
                )
            for index, raw_tab in enumerate(tabs):
                values = default_tab.copy()
                for key in columns:
                    if key in raw_tab:
                        values[key] = raw_tab[key]
                values["display_order"] = index if values["display_order"] in (None, "") else values["display_order"]
                conn.execute(
                    f"INSERT INTO tabs({', '.join(columns)}) VALUES ({placeholders})",
                    [values[column] for column in columns],
                )
            if not tabs:
                conn.execute(
                    f"INSERT INTO tabs({', '.join(columns)}) VALUES ({placeholders})",
                    [default_tab[column] for column in columns],
                )
        return {"settings": len(settings), "tabs": max(1, len(tabs))}

    def get_compare_rows(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        tabs = self.get_tabs()
        for tab in tabs:
            latest = self.get_effective_latest_stat(tab["id"])
            recent = self.get_recent_stats(tab["id"], limit=12)
            last_hourly = self.get_recent_hourly_reports(tab["id"], limit=1)
            latest_message = self.get_recent_messages(tab["id"], limit=1)
            effective_hourly = None
            if latest and latest.get("hourly_rate") is not None:
                effective_hourly = float(latest["hourly_rate"])
            elif last_hourly:
                report = last_hourly[0]
                if report["ocr_hourly_average"] is not None:
                    effective_hourly = float(report["ocr_hourly_average"])
                elif report["ocr_last_hour"] is not None:
                    effective_hourly = float(report["ocr_last_hour"])
            rows.append(
                {
                    "tab": tab,
                    "latest": latest,
                    "trend": [float(row["hourly_rate"]) for row in recent if row["hourly_rate"] is not None],
                    "last_hourly": last_hourly[0] if last_hourly else None,
                    "latest_message": latest_message[0] if latest_message else None,
                    "effective_hourly_rate": effective_hourly,
                }
            )
        return rows
