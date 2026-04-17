from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from app.data.database import Database
from app.parsing.natro_parser import NatroMessageParser


SAMPLE_MESSAGES = [
    "Honey: 12.4B | Pollen: 523.8M | HPS: 4.5M | Backpack: 78% | Gathering",
    "Current Honey: 12.8B\nCurrent Pollen: 610M\nHoney/sec: 5.1M\nSession: 22.7B\nHourly: 18.2B\nBackpack: 54%\nConverting",
    "Honey: 13.1B | Pollen: 150M | HPS: 3.8M | Session Total: 24.4B | Hourly: 17.9B | Backpack: 22%",
    "Macro screenshot update - backpack nearly full, converting soon.",
]


def seed_demo_data(database: Database) -> None:
    parser = NatroMessageParser()
    tabs = database.get_tabs()
    if not tabs:
        tab_id = database.create_tab("Main Account")
        tabs = database.get_tabs()
    tab_id = tabs[0]["id"]

    start_time = datetime.now() - timedelta(hours=2)
    for index, message in enumerate(SAMPLE_MESSAGES * 3):
        created_at = (start_time + timedelta(minutes=index * 10)).isoformat(timespec="seconds")
        message_id = f"demo-{index}"
        parse_result = parser.parse(message)
        database.insert_message(
            tab_id=tab_id,
            channel_id="demo-channel",
            message_id=message_id,
            author_name="Demo Bot",
            content=message,
            embed_json=json.dumps([]),
            attachment_paths=json.dumps([]),
            created_at=created_at,
            parsed_ok=1 if parse_result.parsed_ok else 0,
        )
        database.insert_parsed_stats(
            {
                "tab_id": tab_id,
                "message_id": message_id,
                "honey": parse_result.values["honey"],
                "pollen": parse_result.values["pollen"],
                "honey_per_second": parse_result.values["honey_per_second"],
                "backpack_percent": parse_result.values["backpack_percent"],
                "convert_status": parse_result.values["convert_status"],
                "session_total": parse_result.values["session_total"],
                "hourly_rate": parse_result.values["hourly_rate"],
                "online_status": parse_result.values["online_status"],
                "raw_summary": parse_result.summary,
                "created_at": created_at,
            }
        )

    database.update_tab(
        tab_id,
        {
            "roblox_username": "Builderman",
            "channel_id": "123456789012345678",
            "source_author_filter": "Demo Bot",
            "ingest_bots_only": "1",
            "command_channel_id": "123456789012345678",
            "announcement_channel_id": "987654321098765432",
        },
    )
    database.insert_announcement(
        {
            "tab_id": tab_id,
            "channel_id": "987654321098765432",
            "source_message_id": "announcement-1",
            "title": "Natro macro status update",
            "body": "Important: hourly rate checks are stable again. Use ?hr if you need a fresh hourly pull.",
            "category": "macro",
            "relevance_score": 88,
            "embed_json": "[]",
            "attachment_paths": "[]",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    database.insert_announcement(
        {
            "tab_id": None,
            "channel_id": "987654321098765432",
            "source_message_id": "announcement-2",
            "title": "Maintenance notice",
            "body": "Warning: Discord command routing may pause briefly during maintenance. If a start or stop command fails, retry once after reconnect.",
            "category": "system",
            "relevance_score": 92,
            "embed_json": "[]",
            "attachment_paths": "[]",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    requested_at = datetime.now().isoformat(timespec="seconds")
    database.insert_command_log(
        tab_id=tab_id,
        channel_id="123456789012345678",
        command_text="?hr",
        status="sent",
        detail="Sent successfully (demo)",
        requested_at=requested_at,
    )
    database.insert_hourly_report(
        {
            "tab_id": tab_id,
            "channel_id": "123456789012345678",
            "source_message_id": "hourly-demo-1",
            "title": "[09:00:00] Hourly Report",
            "report_time_label": "09:00:00",
            "body": "[09:00:00] Hourly Report with attached image and hourly chart.",
            "embed_json": "[]",
            "attachment_paths": "[]",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
