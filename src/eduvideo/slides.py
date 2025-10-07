from __future__ import annotations
from pathlib import Path
from typing import List, Optional
from PIL import Image, ImageDraw, ImageFont

from .config import CONFIG
from .models import SceneSpec
from .utils import unique_path


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    # Try to load a default TTF; fallback to PIL default
    for name in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]:
        try:
            return ImageFont.truetype(name, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def create_slide(scene: SceneSpec, visual_paths: List[str]) -> Image.Image:
    width, height = CONFIG.width, CONFIG.height
    img = Image.new("RGB", (width, height), color=(250, 250, 250))
    draw = ImageDraw.Draw(img)

    title_font = _load_font(48)
    body_font = _load_font(28)

    # Title
    margin = 50
    draw.text((margin, margin), scene.title, fill=(0, 0, 0), font=title_font)

    # Bullets
    y = margin + 70
    for b in scene.bullets[:6]:
        draw.text((margin, y), f"• {b}", fill=(30, 30, 30), font=body_font)
        y += 40

    # Visuals area
    x_visual = width // 2
    y_visual = margin + 20
    max_w = width - x_visual - margin
    max_h = height - y_visual - margin

    # Place up to two visuals side by side
    visuals_to_place = visual_paths[:2]
    num = len(visuals_to_place)
    if num:
        target_w = max_w if num == 1 else max_w // 2
        target_h = max_h
        x = x_visual
        for vp in visuals_to_place:
            try:
                vimg = Image.open(vp).convert("RGB")
                vimg.thumbnail((target_w, target_h))
                img.paste(vimg, (x, y_visual))
                x += target_w + 10
            except Exception:
                continue

    return img


def render_slide_image(scene: SceneSpec, visual_paths: List[str], out_dir: str) -> str:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    img = create_slide(scene, visual_paths)
    out_png = unique_path(out_dir, "slide", ".png")
    img.save(out_png)
    return out_png
