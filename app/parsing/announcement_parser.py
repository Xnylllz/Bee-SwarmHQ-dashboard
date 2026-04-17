from __future__ import annotations

from dataclasses import dataclass
import re


IMPORTANT_KEYWORDS = {
    "urgent": 85,
    "important": 80,
    "warning": 75,
    "outage": 90,
    "offline": 80,
    "maintenance": 72,
    "broken": 76,
    "restart": 68,
    "stopped": 66,
    "pause": 60,
    "paused": 60,
}

UPDATE_KEYWORDS = {
    "update": 58,
    "patch": 54,
    "release": 52,
    "changelog": 50,
    "announcement": 48,
    "fix": 46,
    "bug": 42,
    "version": 44,
    "macro": 46,
    "natro": 50,
    "bee swarm": 38,
    "event": 40,
    "boost": 34,
}


@dataclass
class AnnouncementResult:
    is_announcement: bool
    title: str
    body: str
    category: str
    relevance_score: int


class AnnouncementParser:
    def parse(
        self,
        *,
        text: str,
        embed_text: str,
        known_announcement_channel: bool = False,
    ) -> AnnouncementResult:
        combined = "\n".join(part for part in (text, embed_text) if part).strip()
        lowered = combined.lower()
        score = 0
        if known_announcement_channel:
            score += 40
        if "@everyone" in lowered or "@here" in lowered:
            score += 25

        matched_important = [value for key, value in IMPORTANT_KEYWORDS.items() if key in lowered]
        matched_updates = [value for key, value in UPDATE_KEYWORDS.items() if key in lowered]
        if matched_important:
            score += max(matched_important)
        if matched_updates:
            score += max(matched_updates)

        category = "general"
        if any(keyword in lowered for keyword in ("offline", "outage", "maintenance", "restart")):
            category = "system"
        elif any(keyword in lowered for keyword in ("macro", "natro", "pause", "start", "stop", "hourly")):
            category = "macro"
        elif any(keyword in lowered for keyword in ("update", "patch", "release", "changelog", "fix")):
            category = "update"
        elif "event" in lowered or "boost" in lowered:
            category = "event"

        if len(combined) > 220:
            score += 6

        lines = [line.strip() for line in combined.splitlines() if line.strip()]
        title = lines[0][:120] if lines else "Announcement"
        if len(title) < 8 and len(lines) > 1:
            title = lines[1][:120]
        body = combined[:500]

        is_announcement = known_announcement_channel or score >= 45
        return AnnouncementResult(
            is_announcement=is_announcement and bool(combined),
            title=title or "Announcement",
            body=body,
            category=category,
            relevance_score=min(score, 100),
        )
