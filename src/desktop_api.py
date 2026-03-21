from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .models import BackgroundSelection, RenderConfig
from .render_backend import PythonRendererBackend, RenderBackendError, build_prepared_requests

BACKGROUND_LIBRARY_RELATIVE_DIR = Path("assets") / "backgrounds"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Minimal Python render bridge for the Tauri desktop app.")
    parser.add_argument("command", choices=["render-prepared"])
    parser.add_argument("--payload", default="{}", help="JSON payload for the selected command.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = _parse_payload(args.payload)
    repo_dir = Path(__file__).resolve().parent.parent

    try:
        if args.command != "render-prepared":
            raise ValueError(f"Unsupported desktop API command: {args.command}")
        result = _render_prepared(repo_dir, payload)
    except (RenderBackendError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    except Exception as error:
        print(f"Unexpected desktop API error: {error}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False))
    return 0


def _render_prepared(repo_dir: Path, payload: dict[str, Any]) -> dict[str, Any]:
    settings = payload.get("settings")
    raw_items = payload.get("items")
    if not isinstance(settings, dict):
        raise ValueError("Missing settings object.")
    if not isinstance(raw_items, list):
        raise ValueError("Missing prepared items list.")

    render_config = _render_config_from_settings(repo_dir, settings)
    cloud_dir = _required_path(settings.get("cloud_dir"), "Cloud image directory is required.").resolve()
    cloud_dir.mkdir(parents=True, exist_ok=True)

    prepared_items = [raw_item for raw_item in raw_items if isinstance(raw_item, dict)]
    requests = build_prepared_requests(prepared_items, cloud_dir)
    result = PythonRendererBackend().render_prepared(requests, render_config)
    return {"renderedCount": result.rendered_count}


def _render_config_from_settings(repo_dir: Path, settings: dict[str, Any]) -> RenderConfig:
    width = _required_int(settings.get("width"), "Image width must be an integer.")
    height = _required_int(settings.get("height"), "Image height must be an integer.")
    return RenderConfig(
        width=width,
        height=height,
        background_selection=BackgroundSelection(
            mode=str(settings.get("background_mode", "white")),
            image_id=str(settings.get("background_image_id", "")),
            group_name=str(settings.get("background_group", "")),
        ),
        background_library_dir=repo_dir / BACKGROUND_LIBRARY_RELATIVE_DIR,
        show_content_panel=bool(settings.get("show_content_panel", True)),
        panel_opacity=int(settings.get("panel_opacity", 212)),
        text_font_family=str(settings.get("text_font_family", "microsoft_yahei")),
        math_font_family=str(settings.get("math_font_family", "dejavusans")),
        formula_renderer=str(settings.get("formula_renderer", "auto")),
        text_color=str(settings.get("text_color", "#000000")),
        math_color=str(settings.get("math_color", "#000000")),
    )


def _required_path(value: Any, error_message: str) -> Path:
    raw = str(value or "").strip()
    if not raw:
        raise ValueError(error_message)
    return Path(raw).expanduser()


def _required_int(value: Any, error_message: str) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError) as error:
        raise ValueError(error_message) from error


def _parse_payload(raw: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON payload: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError("Payload must be a JSON object.")
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
