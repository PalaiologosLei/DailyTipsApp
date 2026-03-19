from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


class CloudSyncError(RuntimeError):
    pass


@dataclass(slots=True)
class CloudSyncSummary:
    target_dir: Path
    copied_count: int
    deleted_count: int


def sync_images_to_cloud(source_dir: Path, cloud_dir: Path) -> CloudSyncSummary:
    if not source_dir.exists() or not source_dir.is_dir():
        raise CloudSyncError(f"Source image directory does not exist: {source_dir}")

    cloud_dir.mkdir(parents=True, exist_ok=True)

    source_files = {path.name: path for path in source_dir.glob("*.png") if path.is_file()}
    target_files = {path.name: path for path in cloud_dir.glob("*.png") if path.is_file()}

    copied_count = 0
    for name, source_path in source_files.items():
        target_path = cloud_dir / name
        if not target_path.exists() or source_path.read_bytes() != target_path.read_bytes():
            shutil.copy2(source_path, target_path)
            copied_count += 1

    deleted_count = 0
    for name, target_path in target_files.items():
        if name not in source_files:
            target_path.unlink()
            deleted_count += 1

    return CloudSyncSummary(target_dir=cloud_dir, copied_count=copied_count, deleted_count=deleted_count)
