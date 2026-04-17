from __future__ import annotations

import shutil
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

from PIL import Image, ImageColor, ImageEnhance, ImageFilter


class ImageCache:
    def __init__(self, cache_dir: Path, backgrounds_dir: Path):
        self.cache_dir = Path(cache_dir)
        self.backgrounds_dir = Path(backgrounds_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.backgrounds_dir.mkdir(parents=True, exist_ok=True)

    def cache_remote_file(self, url: str, preferred_name: str = "") -> str:
        parsed = urlparse(url)
        filename = preferred_name or Path(parsed.path).name or "attachment.bin"
        target = self.cache_dir / filename
        suffix_index = 1
        while target.exists():
            target = self.cache_dir / f"{target.stem}_{suffix_index}{target.suffix}"
            suffix_index += 1
        with urlopen(url, timeout=10) as response, target.open("wb") as handle:
            handle.write(response.read())
        return str(target)

    def import_background(self, source_path: Path) -> str:
        source_path = Path(source_path)
        if not source_path.exists():
            raise FileNotFoundError(source_path)
        target = self.backgrounds_dir / source_path.name
        suffix_index = 1
        while target.exists():
            target = self.backgrounds_dir / f"{source_path.stem}_{suffix_index}{source_path.suffix}"
            suffix_index += 1
        shutil.copy2(source_path, target)
        return str(target)

    def remove_background(self, background_path: str) -> None:
        path = Path(background_path)
        if path.exists() and self.backgrounds_dir in path.parents:
            path.unlink()

    def build_styled_background(
        self,
        image_path: str,
        output_path: Path,
        *,
        size: tuple[int, int],
        blur_amount: float,
        dim_amount: float,
    ) -> str:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image = Image.open(image_path).convert("RGB")
        image = image.resize(size, Image.Resampling.LANCZOS)
        if blur_amount > 0:
            image = image.filter(ImageFilter.GaussianBlur(radius=blur_amount))
        if dim_amount > 0:
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(max(0.05, 1.0 - dim_amount))
        image.save(output_path)
        return str(output_path)

    def build_gradient_background(
        self,
        output_path: Path,
        *,
        size: tuple[int, int],
        start_color: str,
        end_color: str,
        direction: str,
        dim_amount: float,
        blur_amount: float,
    ) -> str:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        width, height = size
        start_rgb = ImageColor.getrgb(start_color)
        end_rgb = ImageColor.getrgb(end_color)
        image = Image.new("RGB", size)
        pixels = image.load()
        for y in range(height):
            for x in range(width):
                if direction == "horizontal":
                    ratio = x / max(1, width - 1)
                elif direction == "vertical":
                    ratio = y / max(1, height - 1)
                else:
                    ratio = (x + y) / max(1, (width - 1) + (height - 1))
                color = tuple(
                    int(start_rgb[index] * (1 - ratio) + end_rgb[index] * ratio)
                    for index in range(3)
                )
                pixels[x, y] = color
        if blur_amount > 0:
            image = image.filter(ImageFilter.GaussianBlur(radius=max(0, blur_amount / 2)))
        if dim_amount > 0:
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(max(0.05, 1.0 - dim_amount * 0.45))
        image.save(output_path)
        return str(output_path)
