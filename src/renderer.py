from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageFont

from .background_library import choose_background_path
from .cloud_sync import update_cloud_image_index
from .models import KnowledgeItem, RenderConfig, RenderResult, RenderSummary

DEFAULT_WIDTH = 1179
DEFAULT_HEIGHT = 2556
BACKGROUND = "white"
DEFAULT_TEXT_COLOR = "#000000"
MARGIN_X = 90
MARGIN_BOTTOM = 120
CONTENT_TOP_GAP = 70
BLOCK_SPACING = 44
LINE_SPACING = 14
TITLE_SIZE = 76
BODY_SIZE = 56
NOTE_SIZE = 42
MANIFEST_NAME = ".manifest.json"
RENDER_STATE_NAME = "render_state.json"
RENDERER_VERSION = "7"
INLINE_MATH_PATTERN = re.compile(r"(\$[^$]+\$)")
CJK_PATTERN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+")
MATH_SAFE_PATTERN = re.compile(r"^[A-Za-z0-9\\{}_^=+\-*/()\[\]|.,:;<>!?%&~'\" ]+$")
MATH_SIZE_MULTIPLIER = 0.96
TECTONIC_TARGET_HEIGHT_MULTIPLIER = 1.08
MATPLOTLIB_TARGET_HEIGHT_MULTIPLIER = 0.96
CONTENT_PANEL_BASE_FILL = (255, 255, 255)
CONTENT_PANEL_ALPHA = 212
NOTE_BULLET = "\u2022 "
CONTENT_PANEL_RADIUS = 48
PANEL_SIDE_PADDING = 36
PANEL_TOP_PADDING = 28
PANEL_BOTTOM_PADDING = 36
CONTENT_TEXT_TOP_PADDING = 24

TEXT_FONT_CHOICES = [
    ("Microsoft YaHei", "microsoft_yahei"),
    ("SimHei", "simhei"),
    ("SimSun", "simsun"),
]
MATH_FONT_CHOICES = [
    ("DejaVu Sans", "dejavusans"),
    ("STIX Sans", "stixsans"),
    ("DejaVu Serif", "dejavuserif"),
    ("STIX", "stix"),
    ("Computer Modern", "cm"),
]
FORMULA_RENDERER_CHOICES = [
    ("Auto (Recommended)", "auto"),
    ("Tectonic LaTeX", "tectonic"),
    ("Matplotlib MathText", "matplotlib"),
]

TEXT_FONT_FILES = {
    "microsoft_yahei": [Path(r"C:\Windows\Fonts\msyh.ttc"), Path(r"C:\Windows\Fonts\msyhbd.ttc")],
    "simhei": [Path(r"C:\Windows\Fonts\simhei.ttf")],
    "simsun": [Path(r"C:\Windows\Fonts\simsun.ttc")],
}

try:
    from matplotlib import rc_context
    from matplotlib.font_manager import FontProperties
    from matplotlib.mathtext import math_to_image

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    rc_context = None
    FontProperties = None
    math_to_image = None
    MATPLOTLIB_AVAILABLE = False

try:
    import fitz

    PYMUPDF_AVAILABLE = True
except ImportError:
    fitz = None
    PYMUPDF_AVAILABLE = False


@dataclass(frozen=True, slots=True)
class FormulaBackend:
    requested: str
    effective: str
    description: str
    tectonic_path: Path | None = None


def describe_formula_support(requested: str) -> str:
    return resolve_formula_backend(requested).description


def resolve_formula_backend(requested: str) -> FormulaBackend:
    normalized = requested if requested in {"auto", "tectonic", "matplotlib"} else "auto"
    tectonic_path = _find_tectonic_executable()
    tectonic_ready = tectonic_path is not None and PYMUPDF_AVAILABLE

    if normalized == "tectonic":
        if tectonic_ready:
            return FormulaBackend("tectonic", "tectonic", "Formula renderer: Tectonic LaTeX", tectonic_path)
        if MATPLOTLIB_AVAILABLE:
            return FormulaBackend("tectonic", "matplotlib", "Formula renderer: Tectonic unavailable, fell back to Matplotlib", tectonic_path)
        return FormulaBackend("tectonic", "plain", "Formula renderer: Tectonic unavailable, plain text fallback", tectonic_path)

    if normalized == "matplotlib":
        if MATPLOTLIB_AVAILABLE:
            return FormulaBackend("matplotlib", "matplotlib", "Formula renderer: Matplotlib MathText")
        return FormulaBackend("matplotlib", "plain", "Formula renderer: Matplotlib unavailable, plain text fallback")

    if tectonic_ready:
        return FormulaBackend("auto", "tectonic", "Formula renderer: Auto selected Tectonic LaTeX", tectonic_path)
    if MATPLOTLIB_AVAILABLE:
        return FormulaBackend("auto", "matplotlib", "Formula renderer: Auto selected Matplotlib MathText", tectonic_path)
    return FormulaBackend("auto", "plain", "Formula renderer: No backend available, plain text fallback", tectonic_path)


def _find_tectonic_executable() -> Path | None:
    candidates: list[Path] = []
    try:
        import os
        raw = os.environ.get("DAILYTIPS_TECTONIC")
        if raw:
            candidates.append(Path(raw).expanduser())
    except Exception:
        pass

    runtime_roots = [Path(__file__).resolve().parent.parent]
    if getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", None):
        runtime_roots.insert(0, Path(getattr(sys, "_MEIPASS")))

    for root in runtime_roots:
        candidates.extend([
            root / "vendor" / "tectonic" / "tectonic.exe",
            root / "vendor" / "tectonic" / "tectonic",
            root / "tools" / "tectonic" / "tectonic.exe",
            root / "tools" / "tectonic" / "tectonic",
            root / "bin" / "tectonic.exe",
            root / "bin" / "tectonic",
        ])

    which = shutil.which("tectonic")
    if which:
        candidates.append(Path(which))

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def render_items(items: list[KnowledgeItem], image_dir: Path, metadata_dir: Path, render_config: RenderConfig, persist_outputs: bool = True) -> RenderSummary:
    image_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = metadata_dir / MANIFEST_NAME
    state_path = metadata_dir / RENDER_STATE_NAME
    manifest = _load_manifest(manifest_path)
    previous_entries = manifest.get("items", {})
    current_entries: dict[str, dict[str, str]] = {}
    summary = RenderSummary(manifest_path=manifest_path)
    formula_backend = resolve_formula_backend(render_config.formula_renderer)
    render_state = _build_render_state(render_config, formula_backend)
    previous_render_state = _load_state(state_path)
    force_regenerate = previous_render_state != render_state

    for item in items:
        item_key = _build_item_key(item)
        background_path = _choose_background(render_config, item_key)
        background_stamp = _background_stamp(background_path)
        file_name = _build_filename(item)
        image_path = image_dir / file_name
        content_hash = _build_content_hash(item, render_config, background_stamp, formula_backend)
        previous = previous_entries.get(item_key)

        if not force_regenerate and previous and previous.get("hash") == content_hash and image_path.exists():
            summary.results.append(RenderResult(item=item, image_path=image_path, status="unchanged"))
            summary.unchanged_count += 1
        else:
            existed_before = image_path.exists()
            render_item(item, image_path, render_config, formula_backend, background_path)
            if previous or existed_before:
                summary.updated_count += 1
                status = "updated"
            else:
                summary.created_count += 1
                status = "created"
            summary.results.append(RenderResult(item=item, image_path=image_path, status=status))

        current_entries[item_key] = {"file": file_name, "hash": content_hash}

    old_files = {entry.get("file") for entry in previous_entries.values() if entry.get("file")}
    current_files = {entry["file"] for entry in current_entries.values()}
    stale_files = sorted(old_files - current_files)
    for file_name in stale_files:
        stale_path = image_dir / file_name
        if stale_path.exists():
            stale_path.unlink()
        summary.deleted_paths.append(stale_path)

    new_manifest = {"version": RENDERER_VERSION, "items": current_entries}
    image_index_payload = {"images": sorted(path.name for path in image_dir.glob("*.png") if path.is_file()), "count": len(current_entries)}
    summary.manifest_data = new_manifest
    summary.render_state_data = render_state
    summary.image_index_data = image_index_payload

    if persist_outputs:
        if new_manifest != manifest or summary.deleted_paths or not manifest_path.exists():
            manifest_path.write_text(json.dumps(new_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        if force_regenerate or not state_path.exists():
            state_path.write_text(json.dumps(render_state, ensure_ascii=False, indent=2), encoding="utf-8")
        update_cloud_image_index(image_dir)

    return summary


def render_item(item: KnowledgeItem, output_path: Path, render_config: RenderConfig, formula_backend: FormulaBackend | None = None, background_path: Path | None = None) -> None:
    formula_backend = formula_backend or resolve_formula_backend(render_config.formula_renderer)
    width = render_config.width
    height = render_config.height
    image = _create_base_image(width, height, background_path)
    draw = ImageDraw.Draw(image)

    text_color = _normalize_color(render_config.text_color)
    math_color = _normalize_color(render_config.math_color)
    title_font = _load_font(TITLE_SIZE, render_config.text_font_family)
    body_font = _load_font(BODY_SIZE, render_config.text_font_family)
    note_font = _load_font(NOTE_SIZE, render_config.text_font_family)

    top_blank_height = int(height * render_config.top_blank_ratio)
    content_top = max(top_blank_height + CONTENT_TOP_GAP, int(height * 0.36))
    max_width = width - MARGIN_X * 2
    y_start = content_top + CONTENT_TEXT_TOP_PADDING
    max_bottom = height - MARGIN_BOTTOM

    measured_bottom = _measure_item_bottom(
        draw,
        item,
        max_width,
        y_start,
        max_bottom,
        title_font,
        body_font,
        note_font,
        render_config.math_font_family,
        math_color,
        formula_backend,
    )

    if render_config.show_content_panel:
        _draw_content_panel(image, content_top, measured_bottom, render_config.panel_opacity)
        draw = ImageDraw.Draw(image)

    y = y_start
    y = _render_rich_block(
        image,
        draw,
        item.title,
        title_font,
        max_width,
        MARGIN_X,
        y,
        render_config.math_font_family,
        text_color,
        math_color,
        formula_backend,
    )
    y += BLOCK_SPACING
    y = _render_rich_block(
        image,
        draw,
        item.body,
        body_font,
        max_width,
        MARGIN_X,
        y,
        render_config.math_font_family,
        text_color,
        math_color,
        formula_backend,
    )
    y += BLOCK_SPACING

    for note_index, note in enumerate(item.notes):
        if y + _line_height(note_font) > max_bottom:
            break
        y = _render_rich_block(
            image,
            draw,
            f"{NOTE_BULLET}{note}",
            note_font,
            max_width,
            MARGIN_X,
            y,
            render_config.math_font_family,
            text_color,
            math_color,
            formula_backend,
            max_bottom=max_bottom,
            truncate=True,
        )
        if y + BLOCK_SPACING > max_bottom:
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


def _draw_content_panel(image: Image.Image, content_top: int, content_bottom: int, panel_opacity: int) -> None:
    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    panel_top = max(24, content_top - PANEL_TOP_PADDING)
    panel_bottom = min(image.height - 36, content_bottom + PANEL_BOTTOM_PADDING)
    if panel_bottom <= panel_top:
        panel_bottom = panel_top + 120
    panel_box = (PANEL_SIDE_PADDING, panel_top, image.width - PANEL_SIDE_PADDING, panel_bottom)
    alpha = max(0, min(255, int(panel_opacity)))
    fill = (*CONTENT_PANEL_BASE_FILL, alpha)
    overlay_draw.rounded_rectangle(panel_box, radius=CONTENT_PANEL_RADIUS, fill=fill)
    composited = Image.alpha_composite(image.convert("RGBA"), overlay)
    if image.mode == "RGBA":
        image.alpha_composite(overlay)
    else:
        image.paste(composited.convert("RGB"))


def _measure_item_bottom(
    draw: ImageDraw.ImageDraw,
    item: KnowledgeItem,
    max_width: int,
    y: int,
    max_bottom: int,
    title_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    body_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    note_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    math_font_family: str,
    math_color: str,
    formula_backend: FormulaBackend,
) -> int:
    y = _render_rich_block(None, draw, item.title, title_font, max_width, 0, y, math_font_family, DEFAULT_TEXT_COLOR, math_color, formula_backend, paint=False)
    y += BLOCK_SPACING
    y = _render_rich_block(None, draw, item.body, body_font, max_width, 0, y, math_font_family, DEFAULT_TEXT_COLOR, math_color, formula_backend, paint=False)
    y += BLOCK_SPACING
    for note_index, note in enumerate(item.notes):
        if y + _line_height(note_font) > max_bottom:
            break
        y = _render_rich_block(
            None,
            draw,
            f"{NOTE_BULLET}{note}",
            note_font,
            max_width,
            0,
            y,
            math_font_family,
            DEFAULT_TEXT_COLOR,
            math_color,
            formula_backend,
            max_bottom=max_bottom,
            truncate=True,
            paint=False,
        )
        if y + BLOCK_SPACING > max_bottom:
            break
        y += 18
    return y


def _render_rich_block(
    image: Image.Image | None,
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
    x: int,
    y: int,
    math_font_family: str,
    text_color: str,
    math_color: str,
    formula_backend: FormulaBackend,
    max_bottom: int | None = None,
    truncate: bool = False,
    paint: bool = True,
) -> int:
    tokens = _tokenize(text, font, draw, max_width, math_color, math_font_family, formula_backend)
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
            if paint:
                if token["kind"] == "text":
                    draw.text((cursor_x, token_y), str(token["text"]), fill=text_color, font=font)
                else:
                    token_image = token["image"]
                    if image is not None:
                        image.paste(token_image, (cursor_x, token_y), token_image)
            cursor_x += int(token["width"])

        y += line_height + LINE_SPACING

    if truncate and truncated and y + _line_height(font) <= available_bottom:
        if paint:
            draw.text((x, y), "...", fill=text_color, font=font)
        y += _line_height(font)

    return y


def _tokenize(
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    draw: ImageDraw.ImageDraw,
    max_width: int,
    math_color: str,
    math_font_family: str,
    formula_backend: FormulaBackend,
) -> list[dict[str, object]]:
    tokens: list[dict[str, object]] = []
    paragraphs = text.splitlines() or [""]
    for paragraph_index, paragraph in enumerate(paragraphs):
        parts = INLINE_MATH_PATTERN.split(paragraph)
        for part in parts:
            if not part:
                continue
            if part.startswith("$") and part.endswith("$") and len(part) >= 2:
                math_tokens = _build_formula_tokens(part[1:-1], font, draw, max_width, math_color, math_font_family, formula_backend)
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


def _build_formula_tokens(
    formula_content: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    draw: ImageDraw.ImageDraw,
    max_width: int,
    math_color: str,
    math_font_family: str,
    formula_backend: FormulaBackend,
) -> list[dict[str, object]]:
    if not formula_content.strip():
        return []
    segments = _split_formula_content(formula_content)
    tokens: list[dict[str, object]] = []
    for kind, segment in segments:
        if not segment:
            continue
        if kind == "math":
            token = _build_math_token(segment, font, max_width, math_color, math_font_family, formula_backend)
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
    math_color: str,
    math_font_family: str,
    formula_backend: FormulaBackend,
) -> dict[str, object] | None:
    font_size = _extract_font_size(font)

    image: Image.Image | None = None
    if formula_backend.effective == "tectonic":
        image = _render_math_with_tectonic(formula_segment, font_size, max_width, math_color, formula_backend)
        if image is None and MATPLOTLIB_AVAILABLE:
            image = _render_math_with_matplotlib(formula_segment, font_size, max_width, math_color, math_font_family)
    elif formula_backend.effective == "matplotlib":
        image = _render_math_with_matplotlib(formula_segment, font_size, max_width, math_color, math_font_family)
    else:
        return None

    if image is None:
        return None
    return {"kind": "math", "image": image, "width": image.width, "height": image.height}


def _render_math_with_matplotlib(
    formula_segment: str,
    font_size: int,
    max_width: int,
    math_color: str,
    math_font_family: str,
) -> Image.Image | None:
    if not MATPLOTLIB_AVAILABLE or math_to_image is None or FontProperties is None or rc_context is None:
        return None

    buffer = io.BytesIO()
    context = {
        "mathtext.fontset": _math_fontset(math_font_family),
        "mathtext.default": "regular",
    }
    try:
        with rc_context(context):
            prop = FontProperties(size=max(12, font_size * MATH_SIZE_MULTIPLIER))
            math_to_image(f"${formula_segment}$", buffer, prop=prop, dpi=180, format="png", color=math_color)
    except Exception:
        return None

    buffer.seek(0)
    image = Image.open(buffer).convert("RGBA")
    image = _flatten_math_image(image, math_color)
    return _finalize_formula_image(image, font_size, max_width, MATPLOTLIB_TARGET_HEIGHT_MULTIPLIER)


def _render_math_with_tectonic(
    formula_segment: str,
    font_size: int,
    max_width: int,
    math_color: str,
    formula_backend: FormulaBackend,
) -> Image.Image | None:
    if formula_backend.tectonic_path is None or not PYMUPDF_AVAILABLE or fitz is None:
        return None

    latex_expression = _to_latex_math(formula_segment)
    if not latex_expression.strip():
        return None

    color_hex = _normalize_color(math_color).lstrip("#")
    document = _build_tectonic_document(latex_expression, color_hex)

    try:
        with tempfile.TemporaryDirectory(prefix="dailytips_formula_") as tmp_dir:
            temp_root = Path(tmp_dir)
            tex_path = temp_root / "formula.tex"
            pdf_path = temp_root / "formula.pdf"
            tex_path.write_text(document, encoding="utf-8")
            command = [str(formula_backend.tectonic_path), "--outdir", str(temp_root), str(tex_path)]
            subprocess.run(command, cwd=temp_root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if not pdf_path.exists():
                return None
            document_pdf = fitz.open(pdf_path)
            page = document_pdf[0]
            scale = max(1.0, font_size / 20)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=True)
            image = Image.frombytes("RGBA", (pixmap.width, pixmap.height), pixmap.samples)
            document_pdf.close()
    except Exception:
        return None

    return _finalize_formula_image(image, font_size, max_width, TECTONIC_TARGET_HEIGHT_MULTIPLIER)


def _finalize_formula_image(image: Image.Image, font_size: int, max_width: int, target_height_multiplier: float) -> Image.Image | None:
    image = _crop_rgba(image)
    if image.width == 0 or image.height == 0:
        return None

    target_height = max(font_size - 2, int(font_size * target_height_multiplier))
    if image.height < target_height:
        scale = target_height / image.height
        image = image.resize((max(1, int(image.width * scale)), max(1, int(image.height * scale))), Image.Resampling.LANCZOS)
    if image.width > max_width:
        scale = max_width / image.width
        image = image.resize((max(1, int(image.width * scale)), max(1, int(image.height * scale))), Image.Resampling.LANCZOS)
    return image


def _build_tectonic_document(latex_expression: str, color_hex: str) -> str:
    return r"""\documentclass[varwidth,border=0pt]{standalone}
\usepackage[UTF8]{ctex}
\usepackage{amsmath,amssymb}
\usepackage{xcolor}
\begin{document}
\color[HTML]{%s}
$\displaystyle %s$
\end{document}
""" % (color_hex, latex_expression)


def _to_latex_math(formula_content: str) -> str:
    parts: list[str] = []
    for kind, segment in _split_formula_content(formula_content):
        if not segment:
            continue
        if kind == "math":
            parts.append(segment)
        else:
            escaped = (
                segment.replace("\\", r"\textbackslash{}")
                .replace("{", r"\{")
                .replace("}", r"\}")
                .replace("%", r"\%")
                .replace("&", r"\&")
                .replace("#", r"\#")
                .replace("_", r"\_")
            )
            parts.append(r"\text{" + escaped + "}")
    return "".join(parts)


def _crop_rgba(image: Image.Image) -> Image.Image:
    bbox = image.getbbox()
    return image.crop(bbox) if bbox is not None else image


def _flatten_math_image(image: Image.Image, math_color: str) -> Image.Image:
    target_rgb = ImageColor.getrgb(_normalize_color(math_color))
    source = image.convert("RGBA")
    flattened = Image.new("RGBA", source.size, (0, 0, 0, 0))

    for y in range(source.height):
        for x in range(source.width):
            red, green, blue, alpha = source.getpixel((x, y))
            if alpha == 0:
                continue

            # Convert the opaque white mathtext background into transparency
            # while preserving anti-aliased ink intensity.
            luminance = (red + green + blue) / 3
            ink_alpha = int(max(0, min(255, (255 - luminance) * (alpha / 255))))
            if ink_alpha == 0:
                continue
            flattened.putpixel((x, y), (*target_rgb, ink_alpha))

    return flattened


def _choose_background(render_config: RenderConfig, item_key: str) -> Path | None:
    if render_config.background_library_dir is None:
        return None
    return choose_background_path(render_config.background_library_dir, render_config.background_selection, item_key)


def _background_stamp(background_path: Path | None) -> str:
    if background_path is None or not background_path.exists():
        return "white"
    stat = background_path.stat()
    return f"{background_path.as_posix()}|{stat.st_mtime_ns}|{stat.st_size}"


def _build_render_state(render_config: RenderConfig, formula_backend: FormulaBackend) -> dict[str, object]:
    return {
        "renderer_version": RENDERER_VERSION,
        "width": render_config.width,
        "height": render_config.height,
        "top_blank_ratio": render_config.top_blank_ratio,
        "background_mode": render_config.background_selection.mode,
        "background_image_id": render_config.background_selection.image_id,
        "background_group_name": render_config.background_selection.group_name,
        "show_content_panel": render_config.show_content_panel,
        "panel_opacity": max(0, min(255, int(render_config.panel_opacity))),
        "text_font_family": render_config.text_font_family,
        "math_font_family": render_config.math_font_family,
        "text_color": _normalize_color(render_config.text_color),
        "math_color": _normalize_color(render_config.math_color),
        "formula_renderer": render_config.formula_renderer,
        "formula_renderer_effective": formula_backend.effective,
    }


def _load_state(state_path: Path) -> dict[str, object]:
    if not state_path.exists():
        return {}
    try:
        loaded = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _load_manifest(manifest_path: Path) -> dict[str, object]:
    if not manifest_path.exists():
        return {"version": RENDERER_VERSION, "items": {}}
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return {"version": RENDERER_VERSION, "items": {}}


def _load_font(size: int, family_key: str) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = TEXT_FONT_FILES.get(family_key, [])
    fallback_candidates = [path for paths in TEXT_FONT_FILES.values() for path in paths]
    for candidate in [*candidates, *fallback_candidates]:
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


def _build_content_hash(item: KnowledgeItem, render_config: RenderConfig, background_stamp: str, formula_backend: FormulaBackend) -> str:
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
            "show_content_panel": render_config.show_content_panel,
            "panel_opacity": max(0, min(255, int(render_config.panel_opacity))),
            "text_font_family": render_config.text_font_family,
            "math_font_family": render_config.math_font_family,
            "text_color": _normalize_color(render_config.text_color),
            "math_color": _normalize_color(render_config.math_color),
            "formula_renderer": render_config.formula_renderer,
            "formula_renderer_effective": formula_backend.effective,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalize_color(color_value: str) -> str:
    try:
        return ImageColor.getrgb(color_value) and color_value
    except ValueError:
        return DEFAULT_TEXT_COLOR


def _math_fontset(math_font_family: str) -> str:
    valid = {choice[1] for choice in MATH_FONT_CHOICES}
    return math_font_family if math_font_family in valid else "dejavusans"
