from __future__ import annotations

import json
from pathlib import Path

DEFAULT_GUI_SETTINGS = {
    "language": "zh",
    "source_mode": "local",
    "local_path": "",
    "github_url": "https://github.com/PalaiologosLei/DailyTips",
    "output_dir": "output/images",
    "cloud_dir": "C:/Users/lky14/iCloudDrive/DailyTips",
    "width": "1179",
    "height": "2556",
}


def load_gui_settings(settings_path: Path) -> dict[str, object]:
    if not settings_path.exists():
        return dict(DEFAULT_GUI_SETTINGS)

    try:
        loaded = json.loads(settings_path.read_text(encoding="utf-8"))
    except Exception:
        return dict(DEFAULT_GUI_SETTINGS)

    settings = dict(DEFAULT_GUI_SETTINGS)
    for key in DEFAULT_GUI_SETTINGS:
        if key in loaded:
            settings[key] = loaded[key]
    return settings


def save_gui_settings(settings_path: Path, settings: dict[str, object]) -> None:
    merged = dict(DEFAULT_GUI_SETTINGS)
    for key in DEFAULT_GUI_SETTINGS:
        if key in settings:
            merged[key] = settings[key]

    settings_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
