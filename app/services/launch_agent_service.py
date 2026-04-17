from __future__ import annotations

import plistlib
import sys
from pathlib import Path


class LaunchAgentService:
    def __init__(self, app_root: Path):
        self.app_root = Path(app_root)
        self.launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
        self.plist_path = self.launch_agents_dir / "com.beehq.dashboard.plist"

    def sync(self, enabled: bool) -> str:
        if enabled:
            self.install()
            return f"Launch at login enabled via {self.plist_path}"
        self.remove()
        return "Launch at login disabled"

    def install(self) -> None:
        self.launch_agents_dir.mkdir(parents=True, exist_ok=True)
        plist = {
            "Label": "com.beehq.dashboard",
            "ProgramArguments": [sys.executable, "-m", "app.main"],
            "WorkingDirectory": str(self.app_root),
            "RunAtLoad": True,
            "KeepAlive": False,
            "StandardOutPath": str(self.app_root / "data" / "launchagent_stdout.log"),
            "StandardErrorPath": str(self.app_root / "data" / "launchagent_stderr.log"),
        }
        with self.plist_path.open("wb") as handle:
            plistlib.dump(plist, handle)

    def remove(self) -> None:
        if self.plist_path.exists():
            self.plist_path.unlink()

    def is_installed(self) -> bool:
        return self.plist_path.exists()
