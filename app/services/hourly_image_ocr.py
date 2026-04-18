from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import shutil

from PIL import Image, ImageFilter, ImageOps

from app.parsing.natro_parser import parse_number

try:
    import pytesseract
except Exception:  # pragma: no cover - optional runtime dependency
    pytesseract = None


@dataclass
class HourlyImageOCRResult:
    supported: bool
    extracted: bool
    hourly_average: float | None
    last_hour: float | None
    raw_text: str


class HourlyImageOCRService:
    VALUE_PATTERNS = {
        "hourly_average": [
            re.compile(r"hourly\s+average[:\s]*([^\n]+)", re.IGNORECASE),
            re.compile(r"hourly\s+avg[:\s]*([^\n]+)", re.IGNORECASE),
            re.compile(r"\bhourly[:\s]*([^\n]+)", re.IGNORECASE),
        ],
        "last_hour": [
            re.compile(r"last\s+hour[:\s]*([^\n]+)", re.IGNORECASE),
            re.compile(r"honey\s+earned[:\s]*([^\n]+)", re.IGNORECASE),
        ],
    }
    LINE_VALUE_PATTERN = re.compile(
        r"(?:honey\s+earned|hourly\s+average|last\s+hour|hourly(?:\s+avg)?)"
        r"[^\d\n]{0,12}([0-9][0-9,.\s]*[kmbt]?)",
        re.IGNORECASE,
    )
    ZEROISH_PATTERN = re.compile(r"\b0(?:[.,]0+)?\s*([kmbt])?\b", re.IGNORECASE)
    COMMON_TESSERACT_PATHS = (
        "/opt/homebrew/bin/tesseract",
        "/usr/local/bin/tesseract",
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    )

    def extract(self, image_path: str) -> HourlyImageOCRResult:
        if pytesseract is None:
            return HourlyImageOCRResult(False, False, None, None, "")
        if not self._ensure_tesseract_available():
            return HourlyImageOCRResult(False, False, None, None, "")
        path = Path(image_path)
        if not path.exists():
            return HourlyImageOCRResult(True, False, None, None, "")
        try:
            with Image.open(path) as image:
                raw_text, values = self._extract_best_text_and_values(image)
        except Exception:
            return HourlyImageOCRResult(True, False, None, None, "")

        extracted = values["hourly_average"] is not None or values["last_hour"] is not None
        return HourlyImageOCRResult(
            supported=True,
            extracted=extracted,
            hourly_average=values["hourly_average"],
            last_hour=values["last_hour"],
            raw_text=raw_text[:2000],
        )

    def _ensure_tesseract_available(self) -> bool:
        if pytesseract is None:
            return False
        current_cmd = getattr(pytesseract.pytesseract, "tesseract_cmd", "") or "tesseract"
        if self._command_exists(current_cmd):
            return True

        override = os.environ.get("BEEHQ_TESSERACT_CMD") or os.environ.get("TESSERACT_CMD")
        candidates = [override] if override else []
        candidates.extend(self.COMMON_TESSERACT_PATHS)

        for candidate in candidates:
            if not candidate:
                continue
            if self._command_exists(candidate):
                pytesseract.pytesseract.tesseract_cmd = candidate
                return True
        return False

    def _command_exists(self, candidate: str) -> bool:
        if not candidate:
            return False
        candidate_path = Path(candidate)
        if candidate_path.exists():
            return True
        return shutil.which(candidate) is not None

    def _extract_best_text_and_values(self, image: Image.Image) -> tuple[str, dict[str, float | None]]:
        best_score = -1
        best_text = ""
        best_values = {"hourly_average": None, "last_hour": None}
        for region in self._candidate_regions(image):
            for prepared in self._prepared_variants(region):
                for config in (
                    "--psm 6",
                    "--psm 11",
                    "--psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789:+-%()., ",
                ):
                    text = pytesseract.image_to_string(prepared, config=config)
                    values = self._parse_values(text)
                    score = self._score_candidate(text, values)
                    if score > best_score:
                        best_score = score
                        best_text = text
                        best_values = values
        return best_text, best_values

    def _candidate_regions(self, image: Image.Image) -> list[Image.Image]:
        width, height = image.size
        # StatMonitor's "LAST HOUR" card sits in the upper-right column.
        upper_right_card = image.crop(
            (
                int(width * 0.71),
                int(height * 0.03),
                int(width * 0.985),
                int(height * 0.235),
            )
        )
        upper_right_numbers = image.crop(
            (
                int(width * 0.73),
                int(height * 0.04),
                int(width * 0.97),
                int(height * 0.125),
            )
        )
        upper_right_column = image.crop(
            (
                int(width * 0.68),
                int(height * 0.02),
                int(width * 0.985),
                int(height * 0.30),
            )
        )
        return [upper_right_numbers, upper_right_card, upper_right_column]

    def _prepared_variants(self, image: Image.Image) -> list[Image.Image]:
        base = image.convert("L")
        base = ImageOps.autocontrast(base)
        base = base.filter(ImageFilter.SHARPEN)
        doubled = base.resize((base.width * 2, base.height * 2))
        tripled = base.resize((base.width * 3, base.height * 3))
        threshold = doubled.point(lambda value: 255 if value > 160 else 0)
        inverted_threshold = ImageOps.invert(doubled).point(lambda value: 255 if value > 130 else 0)
        return [doubled, tripled, threshold, inverted_threshold]

    def _normalize_text(self, raw_text: str) -> str:
        text = raw_text.replace("|", "I")
        text = text.replace("Hourly Averaqe", "Hourly Average")
        text = text.replace("Honey Eamed", "Honey Earned")
        text = text.replace("Honey Eamned", "Honey Earned")
        text = text.replace("LastHour", "Last Hour")
        text = text.replace("HourlyAverage", "Hourly Average")
        text = re.sub(r"[ \t]+", " ", text)
        return text

    def _parse_values(self, raw_text: str) -> dict[str, float | None]:
        text = self._normalize_text(raw_text)
        values = {
            "hourly_average": None,
            "last_hour": None,
        }
        for key, patterns in self.VALUE_PATTERNS.items():
            for pattern in patterns:
                match = pattern.search(text)
                if not match:
                    continue
                token = self._clean_numeric_token(match.group(1))
                values[key] = parse_number(token)
                if values[key] is not None:
                    break

        # Fallback when labels and values end up on the same OCR line.
        if values["last_hour"] is None or values["hourly_average"] is None:
            fallback_hits = []
            for match in self.LINE_VALUE_PATTERN.finditer(text):
                parsed = parse_number(self._clean_numeric_token(match.group(1)))
                if parsed is not None:
                    fallback_hits.append(parsed)
            if values["last_hour"] is None and fallback_hits:
                values["last_hour"] = fallback_hits[0]
            if values["hourly_average"] is None and len(fallback_hits) > 1:
                values["hourly_average"] = fallback_hits[1]

        if values["last_hour"] is None and self.ZEROISH_PATTERN.search(text):
            values["last_hour"] = 0.0
        if values["hourly_average"] is None and "hourly average" in text.lower() and self.ZEROISH_PATTERN.search(text):
            values["hourly_average"] = 0.0
        return values

    def _clean_numeric_token(self, token: str) -> str:
        cleaned = token.strip()
        cleaned = cleaned.replace("O", "0").replace("o", "0")
        cleaned = cleaned.replace("I", "1").replace("l", "1")
        cleaned = cleaned.replace("S", "5") if re.fullmatch(r"[0-9S,.]+\s*[KMBTkmbt]?", cleaned) else cleaned
        cleaned = re.split(r"[\n(+<|]", cleaned, maxsplit=1)[0]
        cleaned = re.sub(r"[^0-9,.\sKMBTkmbt]", "", cleaned)
        cleaned = re.sub(r"\s+", "", cleaned)
        return cleaned

    def _score_candidate(self, raw_text: str, values: dict[str, float | None]) -> int:
        text = self._normalize_text(raw_text).lower()
        score = 0
        if "last hour" in text:
            score += 5
        if "hourly average" in text:
            score += 5
        if "honey earned" in text:
            score += 4
        if values["last_hour"] is not None:
            score += 10
        if values["hourly_average"] is not None:
            score += 12
        if values["last_hour"] is not None and values["hourly_average"] is not None:
            score += 8
        if values["last_hour"] == 0 and values["hourly_average"] == 0:
            score += 2
        return score
