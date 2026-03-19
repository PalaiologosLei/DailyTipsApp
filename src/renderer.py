from __future__ import annotations

import hashlib
import io
import json
import re
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageFont

from .background_library import choose_background_path
from .models import KnowledgeItem, RenderConfig, RenderResult, RenderSummary

DEFAULT_WIDTH = 1179
DEFAULT_HEIGHT = 2556
BACKGROUND = "white"
FOREGROUND = "black"
MARGIN_X = 90
MARGIN_BOTTOM = 120
CONTENT_TOP_GAP = 70
BLOCK_SPACING = 44
LINE_SPACING = 14
TITLE_SIZE = 76
BODY_SIZE = 56
NOTE_SIZE = 42
MANIFEST_NAME = ".manifest.json"
RENDERER_VERSION = "4"
INLINE_MATH_PATTERN = re.compile(r"(\$[^$]+\$)")
CJK_PATTERN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+")
MATH_SAFE_PATTERN = re.compile(r"^[A-Za-z0-9\\{}_^=+\-*/()\[\]|.,:;<>!?%&~'\" ]+$")
MATH_SIZE_MULTIPLIER = 1.18
CONTENT_PANEL_FILL = (255, 255, 255, 212)
CONTENT_PANEL_RADIUS = 48

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


def render_items(items: list[KnowledgeItem], output_dir: Path, render_config: RenderConfig) -> RenderSummary:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / MANIFEST_NAME
    manifest = _load_manifest(manifest_path)
    previous_entries = manifest.get("items", {})
    current_entries: dict[str, dict[str, str]] = {}
    summary = RenderSummary(manifest_path=manifest_path)

    for item in items:
        item_key = _build_item_key(item)
        background_path = _choose_background(render_config, item_key)
        background_stamp = _background_stamp(background_path)
        file_name = _build_filename(item)
        image_path = output_dir / file_name
        content_hash = _build_content_hash(item, render_config, background_stamp)
        previous = previous_entries.get(item_key)

        if previous and previous.get("hash") == content_hash and image_path.exists():
            summary.results.append(RenderResult(item=item, image_path=image_path, status="unchanged"))
            summary.unchanged_count += 1
        else:
            existed_before = image_path.exists()
            render_item(item, image_path, render_config, background_path)
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

    new_manifest = {"version": RENDERER_VERSION, "items": current_entries}
    if new_manifest != manifest or summary.deleted_paths:
        manifest_path.write_text(json.dumps(new_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    return summary


def render_item(item: KnowledgeItem, output_path: Path, render_config: RenderConfig, background_path: Path | None = None) -> None:
    width = render_config.width
    height = render_config.height
    image = _create_base_image(width, height, background_path)
    draw = ImageDraw.Draw(image)

    title_font = _load_font(TITLE_SIZE)
    body_font = _load_font(BODY_SIZE)
    note_font = _load_font(NOTE_SIZE)

    top_blank_height = int(height * render_config.top_blank_ratio)
    content_top = max(top_blank_height + CONTENT_TOP_GAP, int(height * 0.36))
    max_width = width - MARGIN_X * 2

    _draw_content_panel(image, content_top, height)
    draw = ImageDraw.Draw(image)
    y = content_top + 24

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


def _create_base_image(width: int, height: int, background_path: Path | None) -> Image.Image:
    if background_path is None or not background_path.exists():
        return Image.new("RGB", (width, height), BACKGROUND)

    with Image.open(background_path) as background:
        background = background.convert("RGB")
        return _cover_resize(background, width, height)


def _cover_resize(image: Image.Image, target_width: int, target_height: int) -> Image.Image:
    source_ratio = image.width / image.height
    target_ratio = target_width / target_height

    if source_ratio > target_ratio:
        scaled_height = target_height
        scaled_width = int(target_height * source_ratio)
    else:
        scaled_width = target_width
        scaled_height = int(target_width / source_ratio)

    resized = image.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
    left = max(0, (scaled_width - target_width) // 2)
    top = max(0, (scaled_height - target_height) // 2)
    return resized.crop((left, top, left + target_width, top + target_height))


def _draw_content_panel(image: Image.Image, content_top: int, height: int) -> None:
    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    panel_box = (36, max(24, content_top - 28), image.width - 36, height - 36)
    overlay_draw.rounded_rectangle(panel_box, radius=CONTENT_PANEL_RADIUS, fill=CONTENT_PANEL_FILL)
    image.alpha_composite(overlay) if image.mode == "RGBA" else image.paste(Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB"))


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


def _tokenize(text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, draw: ImageDraw.ImageDraw, max_width: int) -> list[dict[str, object]]:
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


def _build_text_tokens(text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, draw: ImageDraw.ImageDraw) -> list[dict[str, object]]:
    return [
        {"kind": "text", "text": char, "width": _text_width(char, font, draw), "height": _line_height(font)}
        for char in text
    ]


def _build_formula_tokens(formula_content: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, draw: ImageDraw.ImageDraw, max_width: int) -> list[dict[str, object]]:
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


def _build_math_token(formula_segment: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, max_width: int) -> dict[str, object] | None:
    if not MATPLOTLIB_AVAILABLE or math_to_image is None or FontProperties is None:
        return None

    font_size = _extract_font_size(font)
    buffer = io.BytesIO()
    try:
        prop = FontProperties(size=max(12, font_size * MATH_SIZE_MULTIPLIER))
        math_to_image(f"${formula_segment}$", buffer, prop=prop, dpi=170, format="png", color=FOREGROUND)
    except Exception:
        return None

    buffer.seek(0)
    image = Image.open(buffer).convert("RGBA")
    image = _crop_rgba(image)
    if image.width == 0 or image.height == 0:
        return None

    target_height = max(font_size + 2, int(font_size * 1.05))
    if image.height != target_height:
        scale = target_height / image.height
        image = image.resize((max(1, int(image.width * scale)), max(1, int(image.height * scale))), Image.Resampling.LANCZOS)
    if image.width > max_width:
        scale = max_width / image.width
        image = image.resize((max(1, int(image.width * scale)), max(1, int(image.height * scale))), Image.Resampling.LANCZOS)

    return {"kind": "math", "image": image, "width": image.width, "height": image.height}


def _crop_rgba(image: Image.Image) -> Image.Image:
    bbox = image.getbbox()
    return image.crop(bbox) if bbox is not None else image


def _choose_background(render_config: RenderConfig, item_key: str) -> Path | None:
    if render_config.background_library_dir is None:
        return None
    return choose_background_path(render_config.background_library_dir, render_config.background_selection, item_key)


def _background_stamp(background_path: Path | None) -> str:
    if background_path is None or not background_path.exists():
        return "white"
    stat = background_path.stat()
    return f"{background_path.as_posix()}|{stat.st_mtime_ns}|{stat.st_size}"


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


def _text_width(text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, draw: ImageDraw.ImageDraw) -> int:
    left, _, right, _ = draw.textbbox((0, 0), text, font=font)
    return right - left


def _build_filename(item: KnowledgeItem) -> str:
    safe_title = re.sub(r'[<>:"/\\|?*]+', "_", item.title).strip().replace(" ", "_")
    safe_title = safe_title[:40] or "item"
    digest = hashlib.md5(f"{item.source_path.as_posix()}:{item.source_line}:{item.title}".encode("utf-8")).hexdigest()[:8]
    return f"{safe_title}_{digest}.png"


def _build_item_key(item: KnowledgeItem) -> str:
    return f"{item.source_path.as_posix()}:{item.source_line}:{item.title}"


def _build_content_hash(item: KnowledgeItem, render_config: RenderConfig, background_stamp: str) -> str:
    payload = json.dumps(
        {
            "renderer_version": RENDERER_VERSION,
            "title": item.title,
            "body": item.body,
            "notes": item.notes,
            "width": render_config.width,
            "height": render_config.height,
            "top_blank_ratio": render_config.top_blank_ratio,
            "background_mode": render_config.background_selection.mode,
            "background_image_id": render_config.background_selection.image_id,
            "background_group_name": render_config.background_selection.group_name,
            "background_stamp": background_stamp,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
