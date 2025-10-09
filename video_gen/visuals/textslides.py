from __future__ import annotations

from typing import Iterable, Tuple
from PIL import Image, ImageDraw, ImageFont


def render_text_slide(
    title: str,
    bullets: Iterable[str],
    output_path: str,
    size: Tuple[int, int] = (1280, 720),
    background_color: tuple[int, int, int] = (248, 250, 252),
) -> None:
    width, height = size
    img = Image.new("RGB", (width, height), background_color)
    draw = ImageDraw.Draw(img)

    # Load default fonts; Pillow will fallback if not present
    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 54)
        bullet_font = ImageFont.truetype("DejaVuSans.ttf", 36)
    except Exception:
        title_font = ImageFont.load_default()
        bullet_font = ImageFont.load_default()

    margin = 60
    y = margin

    # Title
    draw.text((margin, y), title, fill=(15, 23, 42), font=title_font)
    y += 80

    # Bullets
    bullet_prefix = "• "
    for bullet in bullets:
        wrapped_lines = _wrap_text(bullet, bullet_font, draw, max_width=width - 2 * margin)
        for line in wrapped_lines:
            draw.text((margin, y), bullet_prefix + line, fill=(31, 41, 55), font=bullet_font)
            y += 48
        y += 16

    img.save(output_path)


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, draw: ImageDraw.ImageDraw, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []

    def _measure_width(s: str) -> int:
        # Pillow 10+ deprecates textsize; use textbbox
        try:
            left, top, right, bottom = draw.textbbox((0, 0), s, font=font)
            return int(right - left)
        except Exception:
            try:
                return int(font.getlength(s))  # type: ignore[attr-defined]
            except Exception:
                w, _ = draw.textsize(s, font=font)  # type: ignore[attr-defined]
                return int(w)

    for word in words:
        candidate = " ".join(current + [word])
        w = _measure_width(candidate)
        if w <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines
