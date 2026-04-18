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
class LiveUpdateOCRResult:
    supported: bool
    extracted: bool
    honey: float | None
    pollen: float | None
    honey_per_second: float | None
    backpack_percent: float | None
    raw_text: str


class LiveUpdateOCRService:
    COMMON_TESSERACT_PATHS = (
        "/opt/homebrew/bin/tesseract",
        "/usr/local/bin/tesseract",
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    )

    HONEY_PATTERN = re.compile(
        r"honey[^\d]{0,12}([0-9][0-9,.\s]*)[^\n]{0,30}\(\+?([0-9][0-9,.\s]*)\s*/\s*(?:sec|5ec)\)",
        re.IGNORECASE,
    )
    POLLEN_PATTERN = re.compile(
        r"pollen[^\d]{0,12}([0-9][0-9,.\s]*)\s*/\s*([0-9][0-9,.\s]*)[^\n]{0,30}\(\+?([0-9][0-9,.\s]*)\s*/\s*(?:sec|5ec)\)",
        re.IGNORECASE,
    )
    POLLEN_RATIO_PATTERN = re.compile(
        r"pollen[^\d]{0,12}([0-9][0-9,.\s]*)\s*/\s*([0-9][0-9,.\s]*)",
        re.IGNORECASE,
    )

    def extract(self, image_path: str) -> LiveUpdateOCRResult:
        if pytesseract is None or not self._ensure_tesseract_available():
            return LiveUpdateOCRResult(False, False, None, None, None, None, "")
        path = Path(image_path)
        if not path.exists():
            return LiveUpdateOCRResult(True, False, None, None, None, None, "")
        try:
            with Image.open(path) as image:
                raw_text, values = self._extract_best_text_and_values(image)
        except Exception:
            return LiveUpdateOCRResult(True, False, None, None, None, None, "")

        extracted = any(
            values[key] is not None for key in ("honey", "pollen", "honey_per_second", "backpack_percent")
        )
        return LiveUpdateOCRResult(
            supported=True,
            extracted=extracted,
            honey=values["honey"],
            pollen=values["pollen"],
            honey_per_second=values["honey_per_second"],
            backpack_percent=values["backpack_percent"],
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
            if candidate and self._command_exists(candidate):
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
        best_values = {
            "honey": None,
            "pollen": None,
            "honey_per_second": None,
            "backpack_percent": None,
        }
        for region in self._candidate_regions(image):
            for prepared in self._prepared_variants(region):
                for config in (
                    "--psm 6",
                    "--psm 11",
                    "--psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789:+-()/., ",
                ):
                    text = pytesseract.image_to_string(prepared, config=config)
                    values = self._parse_values(text)
                    score = self._score(text, values)
                    if score > best_score:
                        best_score = score
                        best_text = text
                        best_values = values
        return best_text, best_values

    def _candidate_regions(self, image: Image.Image) -> list[Image.Image]:
        width, height = image.size
        return [
            image.crop((int(width * 0.20), 0, int(width * 0.78), int(height * 0.10))),
            image.crop((int(width * 0.22), 0, int(width * 0.74), int(height * 0.08))),
            image.crop((int(width * 0.16), 0, int(width * 0.82), int(height * 0.12))),
        ]

    def _prepared_variants(self, image: Image.Image) -> list[Image.Image]:
        base = image.convert("L")
        base = ImageOps.autocontrast(base)
        base = base.filter(ImageFilter.SHARPEN)
        doubled = base.resize((base.width * 2, base.height * 2))
        tripled = base.resize((base.width * 3, base.height * 3))
        threshold = doubled.point(lambda value: 255 if value > 165 else 0)
        return [doubled, tripled, threshold]

    def _normalize_text(self, raw_text: str) -> str:
        text = raw_text.replace("|", "I")
        text = text.replace("5ec", "sec")
        text = text.replace("P0llen", "Pollen")
        text = text.replace("H0ney", "Honey")
        text = re.sub(r"[ \t]+", " ", text)
        return text

    def _parse_values(self, raw_text: str) -> dict[str, float | None]:
        text = self._normalize_text(raw_text)
        values = {
            "honey": None,
            "pollen": None,
            "honey_per_second": None,
            "backpack_percent": None,
        }
        honey_match = self.HONEY_PATTERN.search(text)
        if honey_match:
            values["honey"] = parse_number(self._clean_number(honey_match.group(1)))
            values["honey_per_second"] = parse_number(self._clean_number(honey_match.group(2)))

        pollen_match = self.POLLEN_PATTERN.search(text)
        if pollen_match:
            current = parse_number(self._clean_number(pollen_match.group(1)))
            total = parse_number(self._clean_number(pollen_match.group(2)))
            values["pollen"] = current
            if current is not None and total not in (None, 0):
                values["backpack_percent"] = round((current / total) * 100, 1)

        if values["pollen"] is None or values["backpack_percent"] is None:
            ratio_match = self.POLLEN_RATIO_PATTERN.search(text)
            if ratio_match:
                current = parse_number(self._clean_number(ratio_match.group(1)))
                total = parse_number(self._clean_number(ratio_match.group(2)))
                if values["pollen"] is None:
                    values["pollen"] = current
                if values["backpack_percent"] is None and current is not None and total not in (None, 0):
                    values["backpack_percent"] = round((current / total) * 100, 1)

        return values

    def _clean_number(self, token: str) -> str:
        cleaned = token.strip()
        cleaned = cleaned.replace("O", "0").replace("o", "0")
        cleaned = cleaned.replace("I", "1").replace("l", "1")
        cleaned = re.sub(r"[^0-9,.\sKMBTkmbt]", "", cleaned)
        cleaned = re.sub(r"\s+", "", cleaned)
        return cleaned

    def _score(self, raw_text: str, values: dict[str, float | None]) -> int:
        text = self._normalize_text(raw_text).lower()
        score = 0
        if "honey" in text:
            score += 4
        if "pollen" in text:
            score += 4
        if "/sec" in text:
            score += 3
        if values["honey"] is not None:
            score += 10
        if values["pollen"] is not None:
            score += 8
        if values["honey_per_second"] is not None:
            score += 10
        if values["backpack_percent"] is not None:
            score += 6
        return score
