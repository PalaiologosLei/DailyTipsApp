from __future__ import annotations

import hashlib
import io
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .models import KnowledgeItem, RenderResult, RenderSummary

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
MANIFEST_NAME = ".manifest.json"
RENDERER_VERSION = "3"
INLINE_MATH_PATTERN = re.compile(r"(\$[^$]+\$)")
CJK_PATTERN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+")
MATH_SAFE_PATTERN = re.compile(r"^[A-Za-z0-9\\{}_^=+\-*/()\[\]|.,:;<>!?%&~'\" ]+$")
MATH_SIZE_MULTIPLIER = 1.55

WINDOWS_FONT_CANDIDATES = [
    Path(r"C:\Windows\Fonts\msyh.ttc"),
    Path(r"C:\Windows\Fonts\msyhbd.ttc"),
    Path(r"C:\Windows\Fonts\simhei.ttf"),
    Path(r"C:\Windows\Fonts\simsun.ttc"),
]

try:
    from matplotlib.font_manager import FontProperties
    from matplotlib.mathtext import math_to_image

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    FontProperties = None
    math_to_image = None
    MATPLOTLIB_AVAILABLE = False


def render_items(
    items: list[KnowledgeItem], output_dir: Path, width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT
) -> RenderSummary:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / MANIFEST_NAME
    manifest = _load_manifest(manifest_path)
    previous_entries = manifest.get("items", {})
    current_entries: dict[str, dict[str, str]] = {}
    summary = RenderSummary(manifest_path=manifest_path)

    for item in items:
        item_key = _build_item_key(item)
        file_name = _build_filename(item)
        image_path = output_dir / file_name
        content_hash = _build_content_hash(item, width=width, height=height)
        previous = previous_entries.get(item_key)

        if previous and previous.get("hash") == content_hash and image_path.exists():
            summary.results.append(RenderResult(item=item, image_path=image_path, status="unchanged"))
            summary.unchanged_count += 1
        else:
            existed_before = image_path.exists()
            render_item(item, image_path, width=width, height=height)
            if previous or existed_before:
                status = "updated"
                summary.updated_count += 1
            else:
                status = "created"
                summary.created_count += 1
            summary.results.append(RenderResult(item=item, image_path=image_path, status=status))

        current_entries[item_key] = {"file": file_name, "hash": content_hash}

    old_files = {entry.get("file") for entry in previous_entries.values() if entry.get("file")}
    current_files = {entry["file"] for entry in current_entries.values()}
    stale_files = sorted(old_files - current_files)
    for file_name in stale_files:
        stale_path = output_dir / file_name
        if stale_path.exists():
            stale_path.unlink()
        summary.deleted_paths.append(stale_path)

    new_manifest = {
        "version": RENDERER_VERSION,
        "items": current_entries,
    }
    if new_manifest != manifest or summary.deleted_paths:
        manifest_path.write_text(json.dumps(new_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    return summary


def render_item(item: KnowledgeItem, output_path: Path, width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT) -> None:
    image = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(image)

    title_font = _load_font(TITLE_SIZE)
    body_font = _load_font(BODY_SIZE)
    note_font = _load_font(NOTE_SIZE)

    max_width = width - MARGIN_X * 2
    y = MARGIN_TOP

    y = _draw_rich_block(image, draw, item.title, title_font, max_width, MARGIN_X, y)
    y += BLOCK_SPACING
    y = _draw_rich_block(image, draw, item.body, body_font, max_width, MARGIN_X, y)
    y += BLOCK_SPACING

    for note_index, note in enumerate(item.notes):
        if y + _line_height(note_font) > height - MARGIN_BOTTOM:
            break

        prefix = f"{note_index + 1}. "
        y = _draw_rich_block(
            image,
            draw,
            f"{prefix}{note}",
            note_font,
            max_width,
            MARGIN_X,
            y,
            max_bottom=height - MARGIN_BOTTOM,
            truncate=True,
        )
        if y + BLOCK_SPACING > height - MARGIN_BOTTOM:
            break
        y += 18

    image.save(output_path)


def _draw_rich_block(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
    x: int,
    y: int,
    max_bottom: int | None = None,
    truncate: bool = False,
) -> int:
    tokens = _tokenize(text, font, draw, max_width)
    lines = _layout_tokens(tokens, max_width)

    available_bottom = max_bottom if max_bottom is not None else 10**9
    truncated = False

    for line in lines:
        line_height = max((int(token["height"]) for token in line), default=_line_height(font))
        if y + line_height > available_bottom:
            truncated = True
            break

        cursor_x = x
        for token in line:
            token_y = y + max(0, (line_height - int(token["height"])) // 2)
            if token["kind"] == "text":
                draw.text((cursor_x, token_y), str(token["text"]), fill=FOREGROUND, font=font)
            else:
                token_image = token["image"]
                image.paste(token_image, (cursor_x, token_y), token_image)
            cursor_x += int(token["width"])

        y += line_height + LINE_SPACING

    if truncate and truncated and y + _line_height(font) <= available_bottom:
        draw.text((x, y), "...", fill=FOREGROUND, font=font)
        y += _line_height(font)

    return y


def _tokenize(
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    draw: ImageDraw.ImageDraw,
    max_width: int,
) -> list[dict[str, object]]:
    tokens: list[dict[str, object]] = []
    paragraphs = text.splitlines() or [""]
    for paragraph_index, paragraph in enumerate(paragraphs):
        parts = INLINE_MATH_PATTERN.split(paragraph)
        for part in parts:
            if not part:
                continue

            if part.startswith("$") and part.endswith("$") and len(part) >= 2:
                math_tokens = _build_formula_tokens(part[1:-1], font, draw, max_width)
                if math_tokens:
                    tokens.extend(math_tokens)
                    continue

            tokens.extend(_build_text_tokens(part, font, draw))

        if paragraph_index < len(paragraphs) - 1:
            tokens.append({"kind": "newline", "width": 0, "height": _line_height(font)})

    return tokens


def _build_text_tokens(
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    draw: ImageDraw.ImageDraw,
) -> list[dict[str, object]]:
    tokens: list[dict[str, object]] = []
    for char in text:
        tokens.append(
            {
                "kind": "text",
                "text": char,
                "width": _text_width(char, font, draw),
                "height": _line_height(font),
            }
        )
    return tokens


def _build_formula_tokens(
    formula_content: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    draw: ImageDraw.ImageDraw,
    max_width: int,
) -> list[dict[str, object]]:
    if not formula_content.strip():
        return []

    segments = _split_formula_content(formula_content)
    tokens: list[dict[str, object]] = []
    for kind, segment in segments:
        if not segment:
            continue
        if kind == "math":
            token = _build_math_token(segment, font, max_width)
            if token is not None:
                tokens.append(token)
                continue
        tokens.extend(_build_text_tokens(segment, font, draw))
    return tokens


def _split_formula_content(formula_content: str) -> list[tuple[str, str]]:
    pieces: list[tuple[str, str]] = []
    buffer = ""
    current_kind: str | None = None

    for char in formula_content:
        kind = _classify_formula_char(char)
        if current_kind == kind:
            buffer += char
            continue
        if buffer:
            pieces.append((current_kind or "text", buffer))
        current_kind = kind
        buffer = char

    if buffer:
        pieces.append((current_kind or "text", buffer))

    return pieces


def _classify_formula_char(char: str) -> str:
    if CJK_PATTERN.fullmatch(char):
        return "text"
    if MATH_SAFE_PATTERN.fullmatch(char):
        return "math"
    return "text"


def _layout_tokens(tokens: list[dict[str, object]], max_width: int) -> list[list[dict[str, object]]]:
    lines: list[list[dict[str, object]]] = []
    current_line: list[dict[str, object]] = []
    current_width = 0

    for token in tokens:
        if token["kind"] == "newline":
            lines.append(current_line)
            current_line = []
            current_width = 0
            continue

        token_width = int(token["width"])
        if current_line and current_width + token_width > max_width:
            lines.append(current_line)
            current_line = [token]
            current_width = token_width
        else:
            current_line.append(token)
            current_width += token_width

    if current_line or not lines:
        lines.append(current_line)

    return lines


def _build_math_token(
    formula_segment: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
) -> dict[str, object] | None:
    if not MATPLOTLIB_AVAILABLE or math_to_image is None or FontProperties is None:
        return None

    font_size = _extract_font_size(font)
    buffer = io.BytesIO()
    try:
        prop = FontProperties(size=max(12, font_size * MATH_SIZE_MULTIPLIER))
        math_to_image(f"${formula_segment}$", buffer, prop=prop, dpi=180, format="png", color=FOREGROUND)
    except Exception:
        return None

    buffer.seek(0)
    image = Image.open(buffer).convert("RGBA")
    image = _crop_rgba(image)
    if image.width == 0 or image.height == 0:
        return None

    target_height = max(font_size + 10, int(font_size * 1.28))
    if image.height != target_height:
        scale = target_height / image.height
        image = image.resize((max(1, int(image.width * scale)), max(1, int(image.height * scale))), Image.Resampling.LANCZOS)

    if image.width > max_width:
        scale = max_width / image.width
        image = image.resize((max(1, int(image.width * scale)), max(1, int(image.height * scale))), Image.Resampling.LANCZOS)

    return {
        "kind": "math",
        "image": image,
        "width": image.width,
        "height": image.height,
    }


def _crop_rgba(image: Image.Image) -> Image.Image:
    bbox = image.getbbox()
    if bbox is None:
        return image
    return image.crop(bbox)


def _load_manifest(manifest_path: Path) -> dict[str, object]:
    if not manifest_path.exists():
        return {"version": RENDERER_VERSION, "items": {}}

    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return {"version": RENDERER_VERSION, "items": {}}


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in WINDOWS_FONT_CANDIDATES:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def _extract_font_size(font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> int:
    return int(getattr(font, "size", BODY_SIZE))


def _line_height(font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> int:
    bbox = font.getbbox("Ag")
    return (bbox[3] - bbox[1]) + LINE_SPACING


def _text_width(
    text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, draw: ImageDraw.ImageDraw
) -> int:
    left, _, right, _ = draw.textbbox((0, 0), text, font=font)
    return right - left


def _build_filename(item: KnowledgeItem) -> str:
    safe_title = re.sub(r'[<>:"/\\|?*]+', "_", item.title).strip().replace(" ", "_")
    safe_title = safe_title[:40] or "item"
    digest = hashlib.md5(
        f"{item.source_path.as_posix()}:{item.source_line}:{item.title}".encode("utf-8")
    ).hexdigest()[:8]
    return f"{safe_title}_{digest}.png"


def _build_item_key(item: KnowledgeItem) -> str:
    return f"{item.source_path.as_posix()}:{item.source_line}:{item.title}"


def _build_content_hash(item: KnowledgeItem, width: int, height: int) -> str:
    payload = json.dumps(
        {
            "renderer_version": RENDERER_VERSION,
            "title": item.title,
            "body": item.body,
            "notes": item.notes,
            "width": width,
            "height": height,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
