from __future__ import annotations

import hashlib
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .models import KnowledgeItem, RenderResult

DEFAULT_WIDTH = 1179
DEFAULT_HEIGHT = 2556
BACKGROUND = "white"
FOREGROUND = "black"
MARGIN_X = 90
MARGIN_TOP = 120
MARGIN_BOTTOM = 120
BLOCK_SPACING = 44
LINE_SPACING = 14
TITLE_SIZE = 76
BODY_SIZE = 56
NOTE_SIZE = 42

WINDOWS_FONT_CANDIDATES = [
    Path(r"C:\Windows\Fonts\msyh.ttc"),
    Path(r"C:\Windows\Fonts\msyhbd.ttc"),
    Path(r"C:\Windows\Fonts\simhei.ttf"),
    Path(r"C:\Windows\Fonts\simsun.ttc"),
]


def render_items(
    items: list[KnowledgeItem], output_dir: Path, width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT
) -> list[RenderResult]:
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[RenderResult] = []
    for item in items:
        image_path = output_dir / _build_filename(item)
        render_item(item, image_path, width=width, height=height)
        results.append(RenderResult(item=item, image_path=image_path))
    return results


def render_item(item: KnowledgeItem, output_path: Path, width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT) -> None:
    image = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(image)

    title_font = _load_font(TITLE_SIZE)
    body_font = _load_font(BODY_SIZE)
    note_font = _load_font(NOTE_SIZE)

    max_width = width - MARGIN_X * 2
    y = MARGIN_TOP

    y = _draw_block(draw, item.title, title_font, max_width, MARGIN_X, y)
    y += BLOCK_SPACING
    y = _draw_block(draw, item.body, body_font, max_width, MARGIN_X, y)
    y += BLOCK_SPACING

    remaining_height = height - MARGIN_BOTTOM - y
    note_lines_budget = None
    if item.notes:
        line_height = _line_height(note_font)
        note_lines_budget = max(1, remaining_height // max(1, line_height))

    for note_index, note in enumerate(item.notes):
        if note_lines_budget is not None and note_lines_budget <= 0:
            break

        prefix = f"{note_index + 1}. "
        lines = wrap_text(f"{prefix}{note}", note_font, max_width, draw)
        if note_lines_budget is not None and len(lines) > note_lines_budget:
            lines = lines[:note_lines_budget]
            lines[-1] = _truncate_line(lines[-1], note_font, max_width, draw)

        for line in lines:
            if y + _line_height(note_font) > height - MARGIN_BOTTOM:
                break
            draw.text((MARGIN_X, y), line, fill=FOREGROUND, font=note_font)
            y += _line_height(note_font)

        if y + BLOCK_SPACING > height - MARGIN_BOTTOM:
            break

        y += 18
        if note_lines_budget is not None:
            note_lines_budget -= len(lines)

    image.save(output_path)


def wrap_text(text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        paragraph = paragraph.strip()
        if not paragraph:
            lines.append("")
            continue

        current = ""
        for char in paragraph:
            tentative = current + char
            if _text_width(tentative, font, draw) <= max_width or not current:
                current = tentative
                continue

            lines.append(current)
            current = char

        if current:
            lines.append(current)

    return lines or [text]


def _draw_block(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
    x: int,
    y: int,
) -> int:
    for line in wrap_text(text, font, max_width, draw):
        draw.text((x, y), line, fill=FOREGROUND, font=font)
        y += _line_height(font)
    return y


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in WINDOWS_FONT_CANDIDATES:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def _line_height(font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> int:
    bbox = font.getbbox("Ag")
    return (bbox[3] - bbox[1]) + LINE_SPACING


def _text_width(
    text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, draw: ImageDraw.ImageDraw
) -> int:
    left, _, right, _ = draw.textbbox((0, 0), text, font=font)
    return right - left


def _truncate_line(
    text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw
) -> str:
    if _text_width(text + "...", font, draw) <= max_width:
        return text + "..."

    truncated = text
    while truncated and _text_width(truncated + "...", font, draw) > max_width:
        truncated = truncated[:-1]
    return (truncated or "") + "..."


def _build_filename(item: KnowledgeItem) -> str:
    safe_title = re.sub(r'[<>:"/\\|?*]+', "_", item.title).strip().replace(" ", "_")
    safe_title = safe_title[:40] or "item"
    digest = hashlib.md5(
        f"{item.source_path.as_posix()}:{item.source_line}:{item.title}".encode("utf-8")
    ).hexdigest()[:8]
    return f"{safe_title}_{digest}.png"
