from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

IMAGE_INDEX_NAME = "images_index.json"


class CloudSyncError(RuntimeError):
    pass


@dataclass(slots=True)
class CloudIndexSummary:
    target_dir: Path
    image_count: int
    index_path: Path


@dataclass(slots=True)
class ClearSummary:
    removed_metadata_count: int
    removed_cloud_count: int
    removed_index_count: int


def ensure_cloud_dir(cloud_dir: Path) -> Path:
    cloud_dir.mkdir(parents=True, exist_ok=True)
    return cloud_dir


def update_cloud_image_index(cloud_dir: Path) -> CloudIndexSummary:
    if not cloud_dir.exists() or not cloud_dir.is_dir():
        raise CloudSyncError(f"Cloud image directory does not exist: {cloud_dir}")

    names = sorted(path.name for path in cloud_dir.glob("*.png") if path.is_file())
    payload = {
        "images": names,
        "count": len(names),
    }
    index_path = cloud_dir / IMAGE_INDEX_NAME
    index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return CloudIndexSummary(target_dir=cloud_dir, image_count=len(names), index_path=index_path)


def clear_generated_outputs(metadata_dir: Path, cloud_dir: Path | None = None) -> ClearSummary:
    removed_metadata_count = 0
    if metadata_dir.exists() and metadata_dir.is_dir():
        for path in metadata_dir.iterdir():
            if path.is_file():
                path.unlink()
                removed_metadata_count += 1

    removed_cloud_count = 0
    removed_index_count = 0
    if cloud_dir is not None and cloud_dir.exists() and cloud_dir.is_dir():
        for path in cloud_dir.glob("*.png"):
            if path.is_file():
                path.unlink()
                removed_cloud_count += 1
        index_path = cloud_dir / IMAGE_INDEX_NAME
        if index_path.exists():
            index_path.unlink()
            removed_index_count = 1

    return ClearSummary(
        removed_metadata_count=removed_metadata_count,
        removed_cloud_count=removed_cloud_count,
        removed_index_count=removed_index_count,
    )
