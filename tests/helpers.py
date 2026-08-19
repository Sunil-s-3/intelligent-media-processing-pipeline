"""Shared test helpers for generating synthetic images."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


def png_bytes(
    size: tuple[int, int] = (64, 64),
    color: tuple[int, int, int] = (200, 40, 40),
) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


def save_png(path: Path, image: Image.Image) -> Path:
    image.save(path, format="PNG")
    return path


def solid_image(size: tuple[int, int], color: tuple[int, int, int]) -> Image.Image:
    return Image.new("RGB", size, color)


def noisy_image(size: tuple[int, int] = (128, 128), seed: int = 1) -> Image.Image:
    rng = np.random.default_rng(seed)
    array = rng.integers(0, 255, (size[1], size[0], 3), dtype=np.uint8)
    return Image.fromarray(array, mode="RGB")


def blurred_image(size: tuple[int, int] = (128, 128), radius: int = 8) -> Image.Image:
    return noisy_image(size).filter(ImageFilter.GaussianBlur(radius=radius))


def dark_image(size: tuple[int, int] = (64, 64)) -> Image.Image:
    return solid_image(size, (8, 8, 8))


def bright_image(size: tuple[int, int] = (64, 64)) -> Image.Image:
    return solid_image(size, (220, 220, 220))


def text_image(text: str, size: tuple[int, int] = (400, 120)) -> Image.Image:
    image = Image.new("RGB", size, (255, 255, 255))
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.load_default()
    except OSError:
        font = None
    draw.text((20, 40), text, fill=(0, 0, 0), font=font)
    return image
