from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .models import BackgroundSelection

VALID_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
DEFAULT_GROUP = "default"


class BackgroundLibraryError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class BackgroundImage:
    id: str
    group_name: str
    name: str
    path: Path


def ensure_library_root(library_root: Path) -> None:
    library_root.mkdir(parents=True, exist_ok=True)


def list_groups(library_root: Path) -> list[str]:
    ensure_library_root(library_root)
    groups = [path.name for path in library_root.iterdir() if path.is_dir()]
    return sorted(groups)


def list_backgrounds(library_root: Path, group_name: str | None = None) -> list[BackgroundImage]:
    ensure_library_root(library_root)
    base_dirs = [library_root / group_name] if group_name else [path for path in library_root.iterdir() if path.is_dir()]
    images: list[BackgroundImage] = []
    for base_dir in sorted(base_dirs):
        if not base_dir.exists() or not base_dir.is_dir():
            continue
        for path in sorted(base_dir.iterdir()):
            if not path.is_file() or path.suffix.lower() not in VALID_SUFFIXES:
                continue
            image_id = f"{base_dir.name}/{path.name}"
            images.append(BackgroundImage(image_id, base_dir.name, path.name, path))
    return images


def create_group(library_root: Path, group_name: str) -> Path:
    normalized = _normalize_group_name(group_name)
    group_path = library_root / normalized
    group_path.mkdir(parents=True, exist_ok=True)
    return group_path


def delete_group(library_root: Path, group_name: str) -> None:
    group_path = library_root / group_name
    if group_path.exists():
        shutil.rmtree(group_path)


def import_backgrounds(library_root: Path, group_name: str, source_paths: list[Path]) -> list[BackgroundImage]:
    group_path = create_group(library_root, group_name)
    imported: list[BackgroundImage] = []
    for source_path in source_paths:
        _validate_image_file(source_path)
        target_name = _dedupe_name(group_path, source_path.name)
        target_path = group_path / target_name
        shutil.copy2(source_path, target_path)
        imported.append(BackgroundImage(f"{group_path.name}/{target_name}", group_path.name, target_name, target_path))
    return imported


def delete_background(library_root: Path, image_id: str) -> None:
    path = resolve_image_id(library_root, image_id)
    if path.exists():
        path.unlink()


def clear_background_library(library_root: Path, keep_default_group: bool = True) -> int:
    ensure_library_root(library_root)
    removed_count = 0
    for group_path in [path for path in library_root.iterdir() if path.is_dir()]:
        if keep_default_group and group_path.name == DEFAULT_GROUP:
            for file_path in group_path.iterdir():
                if file_path.is_file() and file_path.name != ".gitkeep":
                    file_path.unlink()
                    removed_count += 1
            continue
        for file_path in group_path.rglob("*"):
            if file_path.is_file():
                removed_count += 1
        shutil.rmtree(group_path)
    if keep_default_group:
        (library_root / DEFAULT_GROUP).mkdir(parents=True, exist_ok=True)
        gitkeep = library_root / DEFAULT_GROUP / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.write_text("", encoding="utf-8")
    return removed_count


def resolve_image_id(library_root: Path, image_id: str) -> Path:
    if "/" not in image_id:
        raise BackgroundLibraryError(f"Invalid background id: {image_id}")
    group_name, name = image_id.split("/", 1)
    return library_root / group_name / name


def choose_background_path(library_root: Path, selection: BackgroundSelection, item_key: str) -> Path | None:
    if selection.mode == "white":
        return None

    if selection.mode == "specific":
        if not selection.image_id:
            return None
        path = resolve_image_id(library_root, selection.image_id)
        return path if path.exists() else None

    if selection.mode == "random_group":
        candidates = list_backgrounds(library_root, selection.group_name)
    elif selection.mode == "random_all":
        candidates = list_backgrounds(library_root)
    else:
        candidates = []

    if not candidates:
        return None

    stable_seed = hashlib.sha256(
        f"{selection.mode}|{selection.group_name}|{item_key}|{'|'.join(image.id for image in candidates)}".encode("utf-8")
    ).hexdigest()
    index = int(stable_seed[:8], 16) % len(candidates)
    return candidates[index].path


def _validate_image_file(path: Path) -> None:
    if path.suffix.lower() not in VALID_SUFFIXES:
        raise BackgroundLibraryError(f"Unsupported image format: {path.name}")
    try:
        with Image.open(path) as image:
            image.verify()
    except Exception as error:
        raise BackgroundLibraryError(f"Invalid image file: {path}") from error


def _normalize_group_name(group_name: str) -> str:
    normalized = group_name.strip().replace("\\", "_").replace("/", "_")
    if not normalized:
        raise BackgroundLibraryError("Group name cannot be empty.")
    return normalized


def _dedupe_name(group_path: Path, file_name: str) -> str:
    stem = Path(file_name).stem
    suffix = Path(file_name).suffix
    candidate = file_name
    index = 1
    while (group_path / candidate).exists():
        candidate = f"{stem}_{index}{suffix}"
        index += 1
    return candidate
