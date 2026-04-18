from __future__ import annotations

from datetime import datetime, timedelta
import platform
import subprocess
from tkinter import messagebox

try:
    from plyer import notification as plyer_notification
except Exception:  # pragma: no cover - optional at runtime
    plyer_notification = None


class NotificationService:
    def __init__(self):
        self.last_alerts: dict[int, datetime] = {}

    def should_alert(self, tab_id: int, last_update: datetime | None, offline_timeout_minutes: int) -> bool:
        if last_update is None:
            return False
        deadline = last_update + timedelta(minutes=offline_timeout_minutes)
        now = datetime.now()
        if now < deadline:
            return False
        previous = self.last_alerts.get(tab_id)
        if previous and (now - previous).total_seconds() < offline_timeout_minutes * 60:
            return False
        self.last_alerts[tab_id] = now
        return True

    def show_offline_alert(self, tab_name: str) -> None:
        self.send_system_notification(
            "Bee HQ: updates delayed",
            f"{tab_name} has not sent an update within the configured timeout.",
        )
        try:
            messagebox.showwarning(
                "Updates delayed",
                f"{tab_name} has not sent an update within the configured timeout.",
            )
        except Exception:
            pass

    def show_hourly_report_notification(self, tab_name: str, report_title: str) -> None:
        self.send_system_notification(
            f"Hourly report · {tab_name}",
            report_title or "A new hourly report image was captured.",
        )

    def send_system_notification(self, title: str, message: str) -> None:
        system = platform.system()
        if plyer_notification is not None:
            try:
                plyer_notification.notify(
                    title=str(title),
                    message=str(message),
                    app_name="BeeHQ",
                    timeout=10,
                )
                return
            except Exception:
                pass
        if system == "Darwin":
            safe_title = str(title).replace('"', '\\"')
            safe_message = str(message).replace('"', '\\"')
            script = f'display notification "{safe_message}" with title "{safe_title}"'
            try:
                subprocess.run(["osascript", "-e", script], check=False)
            except Exception:
                pass
