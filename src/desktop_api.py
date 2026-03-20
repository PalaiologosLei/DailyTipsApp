from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from .app import AppError, clear_backgrounds, clear_formula_memory, run_app
from .background_library import (
    BackgroundLibraryError,
    create_group,
    delete_background,
    delete_group,
    ensure_library_root,
    import_backgrounds,
    list_backgrounds,
    list_groups,
)
from .device_profiles import DEVICE_PROFILES
from .gui_settings import load_gui_settings, save_gui_settings
from .models import BackgroundSelection, KnowledgeItem, RenderConfig
from .renderer import (
    FORMULA_RENDERER_CHOICES,
    MATH_FONT_CHOICES,
    TEXT_FONT_CHOICES,
    describe_formula_support,
    render_item,
    resolve_formula_backend,
)

SETTINGS_FILE_NAME = '.gui_settings.json'
BACKGROUND_LIBRARY_RELATIVE_DIR = Path('assets') / 'backgrounds'


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Desktop JSON API for DailyTipsApp.')
    parser.add_argument(
        'command',
        choices=[
            'bootstrap',
            'save-settings',
            'run',
            'render-prepared',
            'clear-generated',
            'clear-library',
            'add-group',
            'delete-group',
            'delete-image',
            'import-images',
        ],
    )
    parser.add_argument('--payload', default='{}', help='JSON payload for the selected command.')
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = _parse_payload(args.payload)
    repo_dir = Path(__file__).resolve().parent.parent

    try:
        result = dispatch_command(repo_dir, args.command, payload)
    except (AppError, BackgroundLibraryError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    except Exception as error:
        print(f'Unexpected desktop API error: {error}', file=sys.stderr)
        return 1

    print(json.dumps(_to_jsonable(result), ensure_ascii=False))
    return 0


def dispatch_command(repo_dir: Path, command: str, payload: dict[str, Any]) -> Any:
    if command == 'bootstrap':
        return _bootstrap(repo_dir)
    if command == 'save-settings':
        return _save_settings(repo_dir, payload)
    if command == 'run':
        return _run(repo_dir, payload)
    if command == 'render-prepared':
        return _render_prepared(repo_dir, payload)
    if command == 'clear-generated':
        return _clear_generated(repo_dir, payload)
    if command == 'clear-library':
        return _clear_library(repo_dir)
    if command == 'add-group':
        return _add_group(repo_dir, payload)
    if command == 'delete-group':
        return _delete_group(repo_dir, payload)
    if command == 'delete-image':
        return _delete_image(repo_dir, payload)
    if command == 'import-images':
        return _import_images(repo_dir, payload)
    raise ValueError(f'Unsupported desktop API command: {command}')


def _bootstrap(repo_dir: Path) -> dict[str, Any]:
    settings = load_gui_settings(_settings_path(repo_dir))
    ensure_library_root(_background_library_dir(repo_dir))
    return {
        'settings': settings,
        'devices': [
            {'key': profile.key, 'label': profile.label, 'width': profile.width, 'height': profile.height}
            for profile in DEVICE_PROFILES
        ],
        'textFonts': [{'label': label, 'key': key} for label, key in TEXT_FONT_CHOICES],
        'mathFonts': [{'label': label, 'key': key} for label, key in MATH_FONT_CHOICES],
        'formulaRenderers': [{'label': label, 'key': key} for label, key in FORMULA_RENDERER_CHOICES],
        'backgroundLibrary': _background_library_state(repo_dir),
        'runtime': _runtime_state(repo_dir, str(settings.get('formula_renderer', 'auto'))),
    }


def _save_settings(repo_dir: Path, payload: dict[str, Any]) -> dict[str, Any]:
    settings = payload.get('settings')
    if not isinstance(settings, dict):
        raise ValueError('Missing settings object.')
    save_gui_settings(_settings_path(repo_dir), settings)
    stored = load_gui_settings(_settings_path(repo_dir))
    return {
        'settings': stored,
        'runtime': _runtime_state(repo_dir, str(stored.get('formula_renderer', 'auto'))),
    }


def _run(repo_dir: Path, payload: dict[str, Any]) -> dict[str, Any]:
    settings = payload.get('settings')
    if not isinstance(settings, dict):
        raise ValueError('Missing settings object.')

    save_gui_settings(_settings_path(repo_dir), settings)
    summary = run_app(
        repo_dir=repo_dir,
        notes_dir=_required_path(settings.get('local_path'), 'Local notes directory is required.'),
        output_dir_arg=str(settings.get('output_dir', '.dailytipsapp')).strip() or '.dailytipsapp',
        cloud_dir=_required_path(settings.get('cloud_dir'), 'Cloud image directory is required.'),
        render_config=_render_config_from_settings(repo_dir, settings),
    )
    return {
        'summary': _to_jsonable(summary),
        'runtime': _runtime_state(repo_dir, str(settings.get('formula_renderer', 'auto'))),
        'backgroundLibrary': _background_library_state(repo_dir),
    }


def _render_prepared(repo_dir: Path, payload: dict[str, Any]) -> dict[str, Any]:
    settings = payload.get('settings')
    raw_items = payload.get('items')
    if not isinstance(settings, dict):
        raise ValueError('Missing settings object.')
    if not isinstance(raw_items, list):
        raise ValueError('Missing prepared items list.')

    save_gui_settings(_settings_path(repo_dir), settings)
    render_config = _render_config_from_settings(repo_dir, settings)
    cloud_dir = _required_path(settings.get('cloud_dir'), 'Cloud image directory is required.').resolve()
    cloud_dir.mkdir(parents=True, exist_ok=True)

    rendered_count = 0
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue
        output_file = str(raw_item.get('output_file', '')).strip()
        if not output_file:
            raise ValueError('Prepared render item is missing output_file.')
        item = KnowledgeItem(
            title=str(raw_item.get('title', '')).strip(),
            body=str(raw_item.get('body', '')).strip(),
            notes=[str(note).strip() for note in raw_item.get('notes', []) if str(note).strip()],
            source_path=Path(str(raw_item.get('source_path', ''))),
            source_line=int(raw_item.get('source_line', 0) or 0),
        )
        output_path = cloud_dir / output_file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        render_item(item, output_path, render_config)
        rendered_count += 1

    return {
        'renderedCount': rendered_count,
        'runtime': _runtime_state(repo_dir, str(settings.get('formula_renderer', 'auto'))),
        'backgroundLibrary': _background_library_state(repo_dir),
    }


def _clear_generated(repo_dir: Path, payload: dict[str, Any]) -> dict[str, Any]:
    settings = payload.get('settings')
    if not isinstance(settings, dict):
        raise ValueError('Missing settings object.')
    summary = clear_formula_memory(
        repo_dir=repo_dir,
        output_dir_arg=str(settings.get('output_dir', '.dailytipsapp')).strip() or '.dailytipsapp',
        cloud_dir=_optional_path(settings.get('cloud_dir')),
    )
    return {
        'summary': _to_jsonable(summary),
        'backgroundLibrary': _background_library_state(repo_dir),
    }


def _clear_library(repo_dir: Path) -> dict[str, Any]:
    summary = clear_backgrounds(_background_library_dir(repo_dir))
    return {
        'summary': _to_jsonable(summary),
        'backgroundLibrary': _background_library_state(repo_dir),
    }


def _add_group(repo_dir: Path, payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get('name', '')).strip()
    if not name:
        raise ValueError('Group name cannot be empty.')
    create_group(_background_library_dir(repo_dir), name)
    return {'backgroundLibrary': _background_library_state(repo_dir)}


def _delete_group(repo_dir: Path, payload: dict[str, Any]) -> dict[str, Any]:
    group_name = str(payload.get('groupName', '')).strip()
    if not group_name:
        raise ValueError('Group name cannot be empty.')
    delete_group(_background_library_dir(repo_dir), group_name)
    return {'backgroundLibrary': _background_library_state(repo_dir)}


def _delete_image(repo_dir: Path, payload: dict[str, Any]) -> dict[str, Any]:
    image_id = str(payload.get('imageId', '')).strip()
    if not image_id:
        raise ValueError('Image id cannot be empty.')
    delete_background(_background_library_dir(repo_dir), image_id)
    return {'backgroundLibrary': _background_library_state(repo_dir)}


def _import_images(repo_dir: Path, payload: dict[str, Any]) -> dict[str, Any]:
    group_name = str(payload.get('groupName', '')).strip()
    raw_paths = payload.get('paths')
    if not group_name:
        raise ValueError('Group name cannot be empty.')
    if not isinstance(raw_paths, list) or not raw_paths:
        raise ValueError('At least one image path is required.')
    source_paths = [Path(str(path)).expanduser() for path in raw_paths]
    imported = import_backgrounds(_background_library_dir(repo_dir), group_name, source_paths)
    return {
        'imported': _to_jsonable(imported),
        'backgroundLibrary': _background_library_state(repo_dir),
    }


def _runtime_state(repo_dir: Path, formula_renderer: str) -> dict[str, Any]:
    backend = resolve_formula_backend(formula_renderer)
    python_summary = f"{Path(sys.executable).name} ({sys.executable})"
    if backend.tectonic_path and backend.tectonic_path.exists():
        tectonic_summary = f'Tectonic ready: {backend.tectonic_path}'
    else:
        tectonic_summary = 'Tectonic executable not found.'
    return {
        'repoRoot': str(repo_dir),
        'pythonOk': True,
        'pythonSummary': python_summary,
        'formulaSupport': describe_formula_support(formula_renderer),
        'formulaBackendRequested': backend.requested,
        'formulaBackendEffective': backend.effective,
        'tectonicBundled': backend.tectonic_path is not None and backend.tectonic_path.exists(),
        'tectonicSummary': tectonic_summary,
    }


def _background_library_state(repo_dir: Path) -> dict[str, Any]:
    library_root = _background_library_dir(repo_dir)
    ensure_library_root(library_root)
    return {
        'groups': list_groups(library_root),
        'images': [
            {
                'id': image.id,
                'groupName': image.group_name,
                'name': image.name,
                'path': str(image.path),
            }
            for image in list_backgrounds(library_root)
        ],
    }


def _render_config_from_settings(repo_dir: Path, settings: dict[str, Any]) -> RenderConfig:
    width = _required_int(settings.get('width'), 'Image width must be an integer.')
    height = _required_int(settings.get('height'), 'Image height must be an integer.')
    return RenderConfig(
        width=width,
        height=height,
        background_selection=BackgroundSelection(
            mode=str(settings.get('background_mode', 'white')),
            image_id=str(settings.get('background_image_id', '')),
            group_name=str(settings.get('background_group', '')),
        ),
        background_library_dir=_background_library_dir(repo_dir),
        show_content_panel=bool(settings.get('show_content_panel', True)),
        panel_opacity=int(settings.get('panel_opacity', 212)),
        text_font_family=str(settings.get('text_font_family', 'microsoft_yahei')),
        math_font_family=str(settings.get('math_font_family', 'dejavusans')),
        formula_renderer=str(settings.get('formula_renderer', 'auto')),
        text_color=str(settings.get('text_color', '#000000')),
        math_color=str(settings.get('math_color', '#000000')),
    )


def _settings_path(repo_dir: Path) -> Path:
    return repo_dir / SETTINGS_FILE_NAME


def _background_library_dir(repo_dir: Path) -> Path:
    return repo_dir / BACKGROUND_LIBRARY_RELATIVE_DIR


def _required_path(value: Any, error_message: str) -> Path:
    path = _optional_path(value)
    if path is None:
        raise ValueError(error_message)
    return path


def _optional_path(value: Any) -> Path | None:
    raw = str(value or '').strip()
    if not raw:
        return None
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
        raise ValueError(f'Invalid JSON payload: {error}') from error
    if not isinstance(payload, dict):
        raise ValueError('Payload must be a JSON object.')
    return payload


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    return value


if __name__ == '__main__':
    raise SystemExit(main())