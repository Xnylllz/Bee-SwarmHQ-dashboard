from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class TabRecord:
    id: int
    name: str
    channel_id: str
    account_name: str
    accent_color: str
    background_override: str
    layout_preference: str
    display_order: int
    custom_settings_json: str


@dataclass
class MessageRecord:
    id: int
    tab_id: int
    channel_id: str
    message_id: str
    author_name: str
    content: str
    embed_json: str
    attachment_paths: str
    created_at: str
    parsed_ok: int


@dataclass
class ParsedStatRecord:
    id: int
    tab_id: int
    message_id: str
    honey: Optional[float]
    pollen: Optional[float]
    honey_per_second: Optional[float]
    backpack_percent: Optional[float]
    convert_status: str
    session_total: Optional[float]
    hourly_rate: Optional[float]
    online_status: str
    raw_summary: str
    created_at: str
