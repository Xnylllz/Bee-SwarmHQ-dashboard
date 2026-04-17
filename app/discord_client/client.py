from __future__ import annotations

import asyncio
import json
import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

import discord

from app.data.database import Database
from app.parsing.announcement_parser import AnnouncementParser
from app.parsing.hourly_report_parser import HourlyReportParser
from app.parsing.natro_parser import NatroMessageParser
from app.services.image_cache import ImageCache


logger = logging.getLogger(__name__)


@dataclass
class DiscordStatus:
    connected: bool = False
    detail: str = "Disconnected"
    last_error: str = ""


class DashboardDiscordClient(discord.Client):
    def __init__(
        self,
        *,
        database: Database,
        parser: NatroMessageParser,
        announcement_parser: AnnouncementParser,
        hourly_report_parser: HourlyReportParser,
        image_cache: ImageCache,
        watched_channels_getter: Callable[[], set[int]],
        announcement_channels_getter: Callable[[], set[int]],
        ui_callback: Callable[[dict], None],
    ):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.messages = True
        super().__init__(intents=intents)
        self.database = database
        self.parser = parser
        self.announcement_parser = announcement_parser
        self.hourly_report_parser = hourly_report_parser
        self.image_cache = image_cache
        self.watched_channels_getter = watched_channels_getter
        self.announcement_channels_getter = announcement_channels_getter
        self.ui_callback = ui_callback

    def _message_allowed_for_tab(self, tab, message: discord.Message) -> bool:
        if tab is None:
            return True
        if int(tab["ingest_bots_only"] or 1) == 1 and not getattr(message.author, "bot", False):
            return False
        source_filter = str(tab["source_author_filter"] or "").strip()
        if not source_filter:
            return True
        author_id = str(getattr(message.author, "id", ""))
        display_name = str(getattr(message.author, "display_name", "") or "")
        username = str(getattr(message.author, "name", "") or "")
        lowered_filter = source_filter.lower()
        return (
            author_id == source_filter
            or display_name.lower() == lowered_filter
            or username.lower() == lowered_filter
        )

    async def on_ready(self) -> None:
        self.ui_callback({"type": "discord_status", "connected": True, "detail": f"Connected as {self.user}"})
        asyncio.create_task(self.backfill_recent_history())

    async def on_message(self, message: discord.Message) -> None:
        await self._process_message(message, emit_event=True)

    async def _process_message(self, message: discord.Message, *, emit_event: bool) -> bool:
        if message.author == self.user:
            return False
        watched_channels = self.watched_channels_getter()
        if watched_channels and message.channel.id not in watched_channels:
            return False
        if self.database.has_message(str(message.id)):
            return False

        embed_payload = []
        embed_text_parts = []
        for embed in message.embeds:
            embed_dict = embed.to_dict()
            embed_payload.append(embed_dict)
            if embed.title:
                embed_text_parts.append(str(embed.title))
            if embed.description:
                embed_text_parts.append(str(embed.description))
            for field in embed_dict.get("fields", []):
                embed_text_parts.append(f"{field.get('name', '')}: {field.get('value', '')}")

        attachment_paths: list[str] = []
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith("image"):
                try:
                    cached_path = self.image_cache.cache_remote_file(attachment.url, attachment.filename)
                    attachment_paths.append(cached_path)
                except Exception as exc:
                    logger.exception("Failed to cache image attachment: %s", exc)

        channel_id = str(message.channel.id)
        tab = self.database.find_tab_for_channel(channel_id)
        announcement_tab = self.database.find_tab_for_announcement_channel(channel_id)
        if tab is not None and not self._message_allowed_for_tab(tab, message):
            return False
        if tab is None and announcement_tab is not None and not self._message_allowed_for_tab(announcement_tab, message):
            return False
        tab_id = tab["id"] if tab else announcement_tab["id"] if announcement_tab else None
        created_at = message.created_at.astimezone(timezone.utc).isoformat(timespec="seconds")
        known_announcement_channel = message.channel.id in self.announcement_channels_getter()

        parse_result = self.parser.parse(message.content or "", "\n".join(embed_text_parts))
        announcement_result = self.announcement_parser.parse(
            text=message.content or "",
            embed_text="\n".join(embed_text_parts),
            known_announcement_channel=known_announcement_channel,
        )
        hourly_report_result = self.hourly_report_parser.parse(
            text=message.content or "",
            embed_text="\n".join(embed_text_parts),
            attachment_paths=attachment_paths,
        )
        self.database.insert_message(
            tab_id=tab_id,
            channel_id=channel_id,
            message_id=str(message.id),
            author_name=getattr(message.author, "display_name", str(message.author)),
            content=message.content or "",
            embed_json=json.dumps(embed_payload),
            attachment_paths=json.dumps(attachment_paths),
            created_at=created_at,
            parsed_ok=1 if parse_result.parsed_ok else 0,
        )

        if tab_id is not None:
            values = {
                "tab_id": tab_id,
                "message_id": str(message.id),
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
            self.database.insert_parsed_stats(values)

        if announcement_result.is_announcement:
            self.database.insert_announcement(
                {
                    "tab_id": announcement_tab["id"] if announcement_tab else tab_id,
                    "channel_id": channel_id,
                    "source_message_id": str(message.id),
                    "title": announcement_result.title,
                    "body": announcement_result.body,
                    "category": announcement_result.category,
                    "relevance_score": announcement_result.relevance_score,
                    "embed_json": json.dumps(embed_payload),
                    "attachment_paths": json.dumps(attachment_paths),
                    "created_at": created_at,
                }
            )

        if tab_id is not None and hourly_report_result.is_hourly_report:
            self.database.insert_hourly_report(
                {
                    "tab_id": tab_id,
                    "channel_id": channel_id,
                    "source_message_id": str(message.id),
                    "title": hourly_report_result.title,
                    "report_time_label": hourly_report_result.report_time_label,
                    "body": hourly_report_result.body,
                    "embed_json": json.dumps(embed_payload),
                    "attachment_paths": json.dumps(attachment_paths),
                    "created_at": created_at,
                }
            )

        if emit_event:
            self.ui_callback(
                {
                    "type": "message_received",
                    "tab_id": tab_id,
                    "channel_id": channel_id,
                    "created_at": created_at,
                    "summary": parse_result.summary,
                    "announcement": announcement_result.is_announcement,
                    "hourly_report": hourly_report_result.is_hourly_report,
                    "hourly_title": hourly_report_result.title,
                }
            )
        return True

    async def backfill_recent_history(self) -> None:
        watched_channels = sorted(self.watched_channels_getter())
        if not watched_channels:
            return
        settings = self.database.get_settings()
        try:
            backfill_hours = max(1, min(int(settings.get("startup_backfill_hours", "12")), 72))
        except ValueError:
            backfill_hours = 12
        inserted = 0
        for channel_id in watched_channels:
            try:
                channel = self.get_channel(channel_id)
                if channel is None:
                    channel = await self.fetch_channel(channel_id)
                latest_seen_raw = self.database.get_latest_message_created_at_for_channel(str(channel_id))
                if latest_seen_raw:
                    try:
                        after = datetime.fromisoformat(latest_seen_raw.replace("Z", "+00:00")).astimezone(timezone.utc)
                    except ValueError:
                        after = datetime.now(timezone.utc) - timedelta(hours=backfill_hours)
                else:
                    after = datetime.now(timezone.utc) - timedelta(hours=backfill_hours)
                if not isinstance(channel, discord.abc.Messageable):
                    continue
                history = []
                async for message in channel.history(limit=200, after=after, oldest_first=True):
                    history.append(message)
                for message in history:
                    if await self._process_message(message, emit_event=False):
                        inserted += 1
            except Exception as exc:
                logger.exception("Backfill failed for channel %s: %s", channel_id, exc)
        self.ui_callback(
            {
                "type": "backfill_complete",
                "detail": f"Synced {inserted} missed Discord messages on startup",
            }
        )


class DiscordService:
    def __init__(
        self,
        *,
        database: Database,
        parser: NatroMessageParser,
        image_cache: ImageCache,
        ui_callback: Callable[[dict], None],
    ):
        self.database = database
        self.parser = parser
        self.announcement_parser = AnnouncementParser()
        self.hourly_report_parser = HourlyReportParser()
        self.image_cache = image_cache
        self.ui_callback = ui_callback
        self.status = DiscordStatus()
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._client: DashboardDiscordClient | None = None

    def _parse_id_list(self, raw_values: list[str]) -> set[int]:
        values: set[int] = set()
        for raw in raw_values:
            for token in raw.split(","):
                token = token.strip()
                if token.isdigit():
                    values.add(int(token))
        return values

    def announcement_channels(self) -> set[int]:
        settings = self.database.get_settings()
        ids = [settings.get("announcement_channels", "")]
        for tab in self.database.get_tabs():
            ids.append(tab["announcement_channel_id"] or "")
        return self._parse_id_list(ids)

    def watched_channels(self) -> set[int]:
        settings = self.database.get_settings()
        ids = [settings.get("watched_channels", ""), settings.get("announcement_channels", "")]
        for tab in self.database.get_tabs():
            ids.append(tab["channel_id"] or "")
            ids.append(tab["announcement_channel_id"] or "")
        return self._parse_id_list(ids)

    def start(self, token: str) -> None:
        if not token or self._thread:
            if not token:
                self.status = DiscordStatus(False, "Token missing", "Set the token in Settings")
            return
        self._thread = threading.Thread(target=self._run_client, args=(token,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._loop and self._client:
            asyncio.run_coroutine_threadsafe(self._client.close(), self._loop)
        self._thread = None
        self._loop = None
        self._client = None
        self.status = DiscordStatus(False, "Disconnected", "")
        self.ui_callback({"type": "discord_status", "connected": False, "detail": "Disconnected"})

    def test_connection(self, token: str) -> None:
        self.start(token)

    def _run_client(self, token: str) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._client = DashboardDiscordClient(
            database=self.database,
            parser=self.parser,
            announcement_parser=self.announcement_parser,
            hourly_report_parser=self.hourly_report_parser,
            image_cache=self.image_cache,
            watched_channels_getter=self.watched_channels,
            announcement_channels_getter=self.announcement_channels,
            ui_callback=self.ui_callback,
        )
        try:
            self.status = DiscordStatus(False, "Connecting...", "")
            self.ui_callback({"type": "discord_status", "connected": False, "detail": "Connecting..."})
            self._loop.run_until_complete(self._client.start(token))
        except Exception as exc:
            logger.exception("Discord client failed: %s", exc)
            self.status = DiscordStatus(False, "Discord error", str(exc))
            self.ui_callback(
                {
                    "type": "discord_status",
                    "connected": False,
                    "detail": "Discord connection failed",
                    "last_error": str(exc),
                }
            )
        finally:
            pending = asyncio.all_tasks(self._loop)
            for task in pending:
                task.cancel()
            try:
                self._loop.run_until_complete(asyncio.sleep(0))
            except Exception:
                pass
            self._loop.close()
            self._thread = None
            self._client = None
            self._loop = None

    def send_command(self, *, tab_id: int | None, channel_id: str, command_text: str) -> tuple[bool, str]:
        if not channel_id.strip().isdigit():
            detail = "Missing or invalid command channel ID."
            self.ui_callback(
                {
                    "type": "command_failed",
                    "tab_id": tab_id,
                    "channel_id": channel_id,
                    "command_text": command_text,
                    "detail": detail,
                }
            )
            return False, detail
        if not self._loop or not self._client:
            detail = "Discord is not connected."
            self.ui_callback(
                {
                    "type": "command_failed",
                    "tab_id": tab_id,
                    "channel_id": channel_id,
                    "command_text": command_text,
                    "detail": detail,
                }
            )
            return False, detail

        requested_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        command_id = self.database.insert_command_log(
            tab_id=tab_id,
            channel_id=channel_id,
            command_text=command_text,
            status="pending",
            detail="Queued",
            requested_at=requested_at,
        )
        future = asyncio.run_coroutine_threadsafe(
            self._send_message(channel_id=int(channel_id), content=command_text),
            self._loop,
        )
        try:
            sent_message_id = future.result(timeout=12)
            completed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            detail = f"Sent successfully ({sent_message_id})"
            self.database.update_command_log(command_id, "sent", detail, completed_at)
            self.ui_callback(
                {
                    "type": "command_sent",
                    "tab_id": tab_id,
                    "channel_id": channel_id,
                    "command_text": command_text,
                    "detail": detail,
                }
            )
            return True, detail
        except Exception as exc:
            logger.exception("Failed to send command: %s", exc)
            completed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            detail = str(exc)
            self.database.update_command_log(command_id, "failed", detail, completed_at)
            self.ui_callback(
                {
                    "type": "command_failed",
                    "tab_id": tab_id,
                    "channel_id": channel_id,
                    "command_text": command_text,
                    "detail": detail,
                }
            )
            return False, detail

    async def _send_message(self, *, channel_id: int, content: str) -> str:
        channel = self.get_channel(channel_id)
        if channel is None:
            channel = await self.fetch_channel(channel_id)
        if not isinstance(channel, discord.abc.Messageable):
            raise RuntimeError("Channel is not messageable.")
        sent_message = await channel.send(content)
        return str(sent_message.id)
