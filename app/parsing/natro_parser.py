from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


NUMBER_PATTERN = re.compile(r"([\d,.]+(?:\.\d+)?)\s*([kmbtKMBT]?)")


def parse_number(token: str) -> float | None:
    if not token:
        return None
    match = NUMBER_PATTERN.search(token.replace(" ", ""))
    if not match:
        return None
    number = float(match.group(1).replace(",", ""))
    suffix = match.group(2).lower()
    multipliers = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000, "t": 1_000_000_000_000}
    return number * multipliers.get(suffix, 1)


@dataclass
class ParseResult:
    parsed_ok: bool
    values: dict[str, Any]
    summary: str


class NatroMessageParser:
    FIELD_PATTERNS = {
        "honey": [
            re.compile(r"honey[:\s]+([^\n|]+)", re.IGNORECASE),
            re.compile(r"current honey[:\s]+([^\n|]+)", re.IGNORECASE),
            re.compile(r"total honey[:\s]+([^\n|]+)", re.IGNORECASE),
            re.compile(r"current\s+honey\s*=\s*([^\n|]+)", re.IGNORECASE),
            re.compile(r"session current honey[:\s]+([^\n|]+)", re.IGNORECASE),
        ],
        "pollen": [
            re.compile(r"pollen[:\s]+([^\n|]+)", re.IGNORECASE),
            re.compile(r"current pollen[:\s]+([^\n|]+)", re.IGNORECASE),
            re.compile(r"current field pollen[:\s]+([^\n|]+)", re.IGNORECASE),
            re.compile(r"field pollen[:\s]+([^\n|]+)", re.IGNORECASE),
        ],
        "honey_per_second": [
            re.compile(r"honey(?:\/|\s+)sec(?:ond)?[:\s]+([^\n|]+)", re.IGNORECASE),
            re.compile(r"hps[:\s]+([^\n|]+)", re.IGNORECASE),
            re.compile(r"honey per second[:\s]+([^\n|]+)", re.IGNORECASE),
            re.compile(r"sec(?:ond)? rate[:\s]+([^\n|]+)", re.IGNORECASE),
            re.compile(r"current rate[:\s]+([^\n|]+)", re.IGNORECASE),
            re.compile(r"honeys\/sec[:\s]+([^\n|]+)", re.IGNORECASE),
        ],
        "session_total": [
            re.compile(r"session(?: total)?[:\s]+([^\n|]+)", re.IGNORECASE),
            re.compile(r"session honey[:\s]+([^\n|]+)", re.IGNORECASE),
            re.compile(r"session total honey[:\s]+([^\n|]+)", re.IGNORECASE),
            re.compile(r"current session[:\s]+([^\n|]+)", re.IGNORECASE),
        ],
        "hourly_rate": [
            re.compile(r"hourly(?: rate)?[:\s]+([^\n|]+)", re.IGNORECASE),
            re.compile(r"honey(?:\/|\s+)hr[:\s]+([^\n|]+)", re.IGNORECASE),
            re.compile(r"honey per hour[:\s]+([^\n|]+)", re.IGNORECASE),
            re.compile(r"hr(?:ly)?[:\s]+([^\n|]+)", re.IGNORECASE),
            re.compile(r"hourly average[:\s]+([^\n|]+)", re.IGNORECASE),
            re.compile(r"last hour[:\s]+([^\n|]+)", re.IGNORECASE),
            re.compile(r"session hourly[:\s]+([^\n|]+)", re.IGNORECASE),
        ],
        "backpack_percent": [
            re.compile(r"backpack[:\s]+(\d{1,3})\s*%", re.IGNORECASE),
            re.compile(r"bag[:\s]+(\d{1,3})\s*%", re.IGNORECASE),
            re.compile(r"backpack(?: fill)?[:\s]+(\d{1,3})\s*%", re.IGNORECASE),
            re.compile(r"backpack[^\n|]*\((\d{1,3})%\)", re.IGNORECASE),
            re.compile(r"bag[^\n|]*\((\d{1,3})%\)", re.IGNORECASE),
        ],
        "convert_status": [
            re.compile(r"(converting|gathering|farming|idle|boosting)", re.IGNORECASE),
            re.compile(r"(stopped|paused|running|started)", re.IGNORECASE),
            re.compile(r"(returning to hive|at hive|in field)", re.IGNORECASE),
            re.compile(r"status[:\s]+(converting|gathering|farming|idle|boosting|paused|running|stopped)", re.IGNORECASE),
            re.compile(r"macro[:\s]+(paused|running|stopped|started)", re.IGNORECASE),
        ],
    }

    def parse(self, text: str, embed_text: str = "") -> ParseResult:
        combined = "\n".join(part for part in [text, embed_text] if part).strip()
        values: dict[str, Any] = {
            "honey": None,
            "pollen": None,
            "honey_per_second": None,
            "backpack_percent": None,
            "convert_status": "",
            "session_total": None,
            "hourly_rate": None,
            "online_status": "online" if combined else "unknown",
            "raw_summary": combined[:400],
        }

        lowered = combined.lower()

        for key, patterns in self.FIELD_PATTERNS.items():
            for pattern in patterns:
                match = pattern.search(combined)
                if not match:
                    continue
                captured = match.group(1) if match.groups() else match.group(0)
                if key == "convert_status":
                    values[key] = captured.strip().lower()
                elif key == "backpack_percent":
                    values[key] = float(captured)
                else:
                    values[key] = parse_number(captured)
                break

        if values["hourly_rate"] is None and values["honey_per_second"] is not None:
            values["hourly_rate"] = values["honey_per_second"] * 3600

        if "offline" in lowered:
            values["online_status"] = "offline"
        elif "paused" in lowered or "stopped" in lowered:
            values["online_status"] = "idle"
        elif "online" in lowered or "running" in lowered or "gathering" in lowered or "converting" in lowered:
            values["online_status"] = "online"

        if values["backpack_percent"] is None:
            if "backpack full" in lowered or "bag full" in lowered:
                values["backpack_percent"] = 100.0
            elif "backpack empty" in lowered or "bag empty" in lowered:
                values["backpack_percent"] = 0.0
            else:
                ratio_match = re.search(r"(?:backpack|bag)[^\n|]*?(\d[\d,\.]*)\s*/\s*(\d[\d,\.]*)", combined, re.IGNORECASE)
                if ratio_match:
                    current = parse_number(ratio_match.group(1))
                    total = parse_number(ratio_match.group(2))
                    if current is not None and total not in (None, 0):
                        values["backpack_percent"] = round((current / total) * 100, 1)

        if values["convert_status"] == "":
            if "convert" in lowered:
                values["convert_status"] = "converting"
            elif "gather" in lowered or "collect" in lowered or "farm" in lowered:
                values["convert_status"] = "gathering"
            elif "paused" in lowered:
                values["convert_status"] = "paused"
            elif "running" in lowered or "macro on" in lowered:
                values["convert_status"] = "running"

        if values["session_total"] is None:
            current_honey = values["honey"]
            session_gain_match = re.search(r"(?:session gain|gain this session|gained)[:\s]+([^\n|]+)", combined, re.IGNORECASE)
            if session_gain_match:
                values["session_total"] = parse_number(session_gain_match.group(1))

        if values["hourly_rate"] is None:
            last_hour_match = re.search(r"(?:last hour honey|last hour)[:\s]+([^\n|]+)", combined, re.IGNORECASE)
            if last_hour_match:
                values["hourly_rate"] = parse_number(last_hour_match.group(1))

        parsed_ok = any(
            values[field] is not None
            for field in ("honey", "pollen", "honey_per_second", "session_total", "hourly_rate")
        )
        summary_parts = []
        for field in ("honey", "pollen", "honey_per_second", "backpack_percent", "convert_status"):
            value = values.get(field)
            if value not in (None, ""):
                summary_parts.append(f"{field}={value}")

        return ParseResult(
            parsed_ok=parsed_ok,
            values=values,
            summary=", ".join(summary_parts) if summary_parts else "Raw message stored",
        )
