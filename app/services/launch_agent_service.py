from __future__ import annotations

import os
import platform
import plistlib
import sys
from pathlib import Path


class LaunchAgentService:
    def __init__(self, app_root: Path):
        self.app_root = Path(app_root)
        self.system = platform.system()
        self.launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
        self.plist_path = self.launch_agents_dir / "com.beehq.dashboard.plist"
        self.windows_startup_dir = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        self.windows_launcher_path = self.windows_startup_dir / "BeeHQ.cmd"

    def sync(self, enabled: bool) -> str:
        if enabled:
            self.install()
            if self.system == "Windows":
                return f"Launch at login enabled via {self.windows_launcher_path}"
            if self.system == "Darwin":
                return f"Launch at login enabled via {self.plist_path}"
            return "Launch at login enabled"
        self.remove()
        return "Launch at login disabled"

    def install(self) -> None:
        if self.system == "Windows":
            self._install_windows_startup()
            return
        if self.system != "Darwin":
            return
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
        if self.system == "Windows":
            if self.windows_launcher_path.exists():
                self.windows_launcher_path.unlink()
            return
        if self.system == "Darwin" and self.plist_path.exists():
            self.plist_path.unlink()

    def is_installed(self) -> bool:
        if self.system == "Windows":
            return self.windows_launcher_path.exists()
        if self.system == "Darwin":
            return self.plist_path.exists()
        return False

    def _install_windows_startup(self) -> None:
        self.windows_startup_dir.mkdir(parents=True, exist_ok=True)
        python_executable = Path(sys.executable)
        pythonw_executable = python_executable.with_name("pythonw.exe")
        launcher = pythonw_executable if pythonw_executable.exists() else python_executable
        if getattr(sys, "frozen", False):
            command = f'@echo off\nstart "" "{sys.executable}"\n'
        else:
            command = (
                "@echo off\n"
                f'cd /d "{self.app_root}"\n'
                f'start "" "{launcher}" -m app.main\n'
            )
        self.windows_launcher_path.write_text(command, encoding="utf-8")
