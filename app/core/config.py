from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import platform
import sys

from dotenv import load_dotenv


APP_NAME = "BeeHQ"
DEV_ROOT_DIR = Path(__file__).resolve().parents[2]
IS_FROZEN = bool(getattr(sys, "frozen", False))
BUNDLE_RESOURCES_DIR = Path(getattr(sys, "_MEIPASS", DEV_ROOT_DIR))


def _frozen_runtime_root() -> Path:
    system = platform.system()
    if system == "Windows":
        appdata = os.getenv("APPDATA")
        if appdata:
            return Path(appdata) / APP_NAME
        return Path.home() / "AppData" / "Roaming" / APP_NAME
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    return Path.home() / f".{APP_NAME.lower()}"


ROOT_DIR = _frozen_runtime_root() if IS_FROZEN else DEV_ROOT_DIR
ENV_PATH = ROOT_DIR / ".env"
DATA_DIR = ROOT_DIR / "data"
CACHE_DIR = ROOT_DIR / "cache"
IMAGE_CACHE_DIR = CACHE_DIR / "images"
BACKGROUND_DIR = ROOT_DIR / "assets" / "backgrounds"
EXPORT_DIR = DATA_DIR / "exports"


def ensure_directories() -> None:
    for path in (DATA_DIR, CACHE_DIR, IMAGE_CACHE_DIR, BACKGROUND_DIR, EXPORT_DIR):
        path.mkdir(parents=True, exist_ok=True)


def load_environment() -> None:
    ensure_directories()
    load_dotenv(ENV_PATH)


@dataclass
class AppPaths:
    root: Path = ROOT_DIR
    bundle_resources: Path = BUNDLE_RESOURCES_DIR
    env: Path = ENV_PATH
    data: Path = DATA_DIR
    cache: Path = CACHE_DIR
    image_cache: Path = IMAGE_CACHE_DIR
    backgrounds: Path = BACKGROUND_DIR
    exports: Path = EXPORT_DIR


@dataclass
class RuntimeConfig:
    db_path: Path
    discord_token: str
    watched_channels: list[int]
    debug_logging: bool

    @classmethod
    def from_env(cls) -> "RuntimeConfig":
        load_environment()
        raw_channels = os.getenv("DISCORD_WATCHED_CHANNELS", "")
        watched_channels = [
            int(channel.strip())
            for channel in raw_channels.split(",")
            if channel.strip().isdigit()
        ]
        db_path = ROOT_DIR / os.getenv("APP_DB_PATH", "data/dashboard.db")
        return cls(
            db_path=db_path,
            discord_token=os.getenv("DISCORD_BOT_TOKEN", "").strip(),
            watched_channels=watched_channels,
            debug_logging=os.getenv("DEBUG_LOGGING", "false").lower() == "true",
        )


def write_env_value(key: str, value: str) -> None:
    load_environment()
    existing: dict[str, str] = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.strip().startswith("#") or "=" not in line:
                continue
            current_key, current_value = line.split("=", 1)
            existing[current_key.strip()] = current_value
    existing[key] = value
    lines = [f"{env_key}={env_value}" for env_key, env_value in sorted(existing.items())]
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
