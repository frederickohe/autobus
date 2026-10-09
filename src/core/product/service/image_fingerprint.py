"""Perceptual hash, visual vector, and the short code stamped on Autobus posts.

Same-photo checks use a difference hash, which still matches after WhatsApp or
Instagram recompresses the file. Photos from somewhere else are compared with a
small color-layout vector. Neither step calls a model.
"""

from __future__ import annotations

import io
import re
import secrets
from typing import Iterable, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError

HASH_SIZE = 8
BIT_HEX_LEN = HASH_SIZE * HASH_SIZE // 4  # 16
COLOR_HEX_LEN = 6
HASH_HEX_LEN = BIT_HEX_LEN + COLOR_HEX_LEN
VECTOR_DIM = 64
EXACT_HAMMING = 12
COLOR_DISTANCE_MAX = 48
RELATED_COSINE = 0.90
MAX_RELATED = 4

# Unambiguous alphabet: no 0/O, 1/I/L.
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_CODE_RE = re.compile(r"AB-[ABCDEFGHJKLMNPQRSTUVWXYZ23456789]{4}", re.IGNORECASE)


def new_match_code() -> str:
    body = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(4))
    return f"AB-{body}"


def find_match_code(text: str) -> Optional[str]:
    match = _CODE_RE.search(text or "")
    if not match:
        return None
    return match.group(0).upper()


def open_image(data: bytes) -> Optional[Image.Image]:
    if not data:
        return None
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError, ValueError):
        return None
    image = ImageOps.exif_transpose(image) or image
    if image.mode != "RGB":
        image = image.convert("RGB")
    return image


def _flat_pixels(image: Image.Image):
    reader = getattr(image, "get_flattened_data", None)
    if reader is not None:
        return list(reader())
    return list(image.getdata())


def _mean_color(image: Image.Image) -> Tuple[int, int, int]:
    small = image.convert("RGB").resize((8, 8), Image.Resampling.BOX)
    pixels = _flat_pixels(small)
    count = len(pixels) or 1
    red = sum(pixel[0] for pixel in pixels) // count
    green = sum(pixel[1] for pixel in pixels) // count
    blue = sum(pixel[2] for pixel in pixels) // count
    return red, green, blue


def dhash_hex(image: Image.Image, hash_size: int = HASH_SIZE) -> str:
    """Difference hash plus average color, so two flat colors do not collide."""
    gray = image.convert("L").resize(
        (hash_size + 1, hash_size), Image.Resampling.LANCZOS
    )
    pixels = _flat_pixels(gray)
    width = hash_size + 1
    bits = 0
    for row in range(hash_size):
        for col in range(hash_size):
            left = pixels[row * width + col]
            right = pixels[row * width + col + 1]
            bits = (bits << 1) | (1 if left > right else 0)
    red, green, blue = _mean_color(image)
    return f"{bits:0{BIT_HEX_LEN}x}{red:02x}{green:02x}{blue:02x}"


def _split_hash(value: str) -> Tuple[str, str]:
    text = (value or "").strip().lower()
    if len(text) == HASH_HEX_LEN:
        return text[:BIT_HEX_LEN], text[BIT_HEX_LEN:]
    if len(text) == BIT_HEX_LEN:
        return text, ""
    return "", ""


def _color_distance(left: str, right: str) -> Optional[int]:
    try:
        lr, lg, lb = int(left[0:2], 16), int(left[2:4], 16), int(left[4:6], 16)
        rr, rg, rb = int(right[0:2], 16), int(right[2:4], 16), int(right[4:6], 16)
    except (ValueError, IndexError):
        return None
    return abs(lr - rr) + abs(lg - rg) + abs(lb - rb)


def hamming(left: str, right: str) -> Optional[int]:
    left_bits, left_color = _split_hash(left)
    right_bits, right_color = _split_hash(right)
    if not left_bits or not right_bits:
        return None
    if left_color and right_color:
        distance = _color_distance(left_color, right_color)
        if distance is None or distance > COLOR_DISTANCE_MAX:
            return None
    try:
        return (int(left_bits, 16) ^ int(right_bits, 16)).bit_count()
    except ValueError:
        return None


def visual_vector(image: Image.Image) -> Tuple[float, ...]:
    """4x4 average color plus a luminance histogram, L2-normalized to 64 dims."""
    small = image.convert("RGB").resize((32, 32), Image.Resampling.BILINEAR)
    pixels = _flat_pixels(small)
    cell = 8
    values: list[float] = []
    for gy in range(4):
        for gx in range(4):
            red = green = blue = 0
            for y in range(gy * cell, (gy + 1) * cell):
                row = y * 32
                for x in range(gx * cell, (gx + 1) * cell):
                    r, g, b = pixels[row + x]
                    red += r
                    green += g
                    blue += b
            count = cell * cell
            values.extend((red / count / 255.0, green / count / 255.0, blue / count / 255.0))

    hist = [0.0] * 16
    for r, g, b in pixels:
        lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
        bucket = min(15, int(lum * 16))
        hist[bucket] += 1.0
    total = float(len(pixels)) or 1.0
    values.extend(bucket / total for bucket in hist)
    norm = sum(value * value for value in values) ** 0.5
    if norm <= 1e-9:
        return tuple(values)
    return tuple(value / norm for value in values)


def cosine(left: Sequence[float], right: Sequence[float]) -> Optional[float]:
    if not left or not right or len(left) != len(right):
        return None
    return float(sum(a * b for a, b in zip(left, right)))


def _badge_font(image_width: int) -> ImageFont.ImageFont:
    size = max(18, min(42, image_width // 28))
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def stamp_match_code(image: Image.Image, code: str) -> Image.Image:
    """Draw a high-contrast code badge in the bottom-right corner."""
    marked = image.convert("RGB").copy()
    label = find_match_code(code) or (code or "").strip().upper()
    if not label:
        return marked
    draw = ImageDraw.Draw(marked)
    font = _badge_font(marked.width)
    pad_x = max(8, marked.width // 80)
    pad_y = max(6, marked.height // 100)
    margin = max(10, marked.width // 60)
    try:
        bbox = draw.textbbox((0, 0), label, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
    except Exception:
        text_w = len(label) * 8
        text_h = 14
    box_w = text_w + pad_x * 2
    box_h = text_h + pad_y * 2
    left = max(0, marked.width - box_w - margin)
    top = max(0, marked.height - box_h - margin)
    draw.rectangle((left, top, left + box_w, top + box_h), fill=(0, 0, 0))
    draw.text((left + pad_x, top + pad_y), label, fill=(255, 255, 255), font=font)
    return marked


def jpeg_bytes(image: Image.Image, *, quality: int = 85) -> bytes:
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=quality, optimize=True)
    return buffer.getvalue()


def stamp_jpeg_bytes(data: bytes, code: str, *, quality: int = 85) -> Optional[bytes]:
    image = open_image(data)
    if image is None:
        return None
    return jpeg_bytes(stamp_match_code(image, code), quality=quality)


def best_hash_distance(query_hash: str, stored: Iterable[str]) -> Optional[int]:
    best: Optional[int] = None
    for item in stored:
        distance = hamming(query_hash, item or "")
        if distance is None:
            continue
        if best is None or distance < best:
            best = distance
    return best
