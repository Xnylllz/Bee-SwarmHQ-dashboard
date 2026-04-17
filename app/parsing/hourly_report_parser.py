from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re


TIME_LABEL_PATTERN = re.compile(r"\[(\d{1,2}:\d{2}:\d{2})\]")


@dataclass
class HourlyReportResult:
    is_hourly_report: bool
    title: str
    report_time_label: str
    body: str


class HourlyReportParser:
    def parse(self, *, text: str, embed_text: str, attachment_paths: list[str]) -> HourlyReportResult:
        combined = "\n".join(part for part in (text, embed_text) if part).strip()
        lowered = combined.lower()
        has_hourly_phrase = "hourly report" in lowered or "hourly" in lowered
        has_image = bool(attachment_paths)
        time_match = TIME_LABEL_PATTERN.search(combined)
        report_time_label = self._normalize_time_label(time_match.group(1) if time_match else "")

        lines = [line.strip() for line in combined.splitlines() if line.strip()]
        title = lines[0] if lines else "Hourly Report"
        if "hourly report" not in title.lower():
            for line in lines[1:]:
                if "hourly report" in line.lower():
                    title = line
                    break
        if report_time_label:
            title = f"Hourly Report: {report_time_label}"
        elif not title:
            title = "Hourly Report"
        body = combined[:500]

        is_hourly_report = has_hourly_phrase and (has_image or bool(report_time_label))
        return HourlyReportResult(
            is_hourly_report=is_hourly_report,
            title=title[:160],
            report_time_label=report_time_label,
            body=body,
        )

    def _normalize_time_label(self, raw_label: str) -> str:
        value = raw_label.strip()
        if not value:
            return ""
        try:
            parsed = datetime.strptime(value, "%H:%M:%S")
        except ValueError:
            return value
        return parsed.strftime("%I:%M %p").lstrip("0")
