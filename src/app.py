from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .background_library import clear_background_library
from .cloud_sync import ClearSummary, CloudSyncError, clear_generated_outputs, sync_images_to_cloud
from .models import RenderConfig
from .note_source import materialize_notes_source
from .parser import parse_markdown_file
from .renderer import render_items
from .scanner import find_markdown_files


class AppError(RuntimeError):
    pass


@dataclass(slots=True)
class RunSummary:
    source_description: str
    markdown_file_count: int
    item_count: int
    image_count: int
    output_dir: Path
    cloud_dir: Path | None
    created_count: int
    updated_count: int
    unchanged_count: int
    deleted_count: int
    cloud_copied_count: int
    cloud_deleted_count: int


@dataclass(slots=True)
class ResetSummary:
    removed_generated_count: int
    removed_cloud_count: int
    removed_background_count: int


def run_app(
    repo_dir: Path,
    notes_dir: Path | None,
    github_url: str | None,
    output_dir_arg: str,
    cloud_dir: Path | None,
    render_config: RenderConfig,
) -> RunSummary:
    output_dir = (repo_dir / output_dir_arg).resolve()

    try:
        source = materialize_notes_source(repo_dir=repo_dir, notes_dir=notes_dir, github_url=github_url)
    except Exception as error:
        raise AppError(f"Failed to prepare notes source: {error}") from error

    try:
        markdown_files = find_markdown_files(source.notes_dir)
        items = []
        for markdown_file in markdown_files:
            items.extend(parse_markdown_file(markdown_file))

        render_summary = render_items(items, output_dir, render_config)

        cloud_copied_count = 0
        cloud_deleted_count = 0
        resolved_cloud_dir = cloud_dir.resolve() if cloud_dir is not None else None
        if resolved_cloud_dir is not None:
            try:
                cloud_summary = sync_images_to_cloud(output_dir, resolved_cloud_dir)
            except CloudSyncError as error:
                raise AppError(f"Cloud sync failed: {error}") from error
            cloud_copied_count = cloud_summary.copied_count
            cloud_deleted_count = cloud_summary.deleted_count

        return RunSummary(
            source_description=source.description,
            markdown_file_count=len(markdown_files),
            item_count=len(items),
            image_count=render_summary.image_count,
            output_dir=output_dir,
            cloud_dir=resolved_cloud_dir,
            created_count=render_summary.created_count,
            updated_count=render_summary.updated_count,
            unchanged_count=render_summary.unchanged_count,
            deleted_count=len(render_summary.deleted_paths),
            cloud_copied_count=cloud_copied_count,
            cloud_deleted_count=cloud_deleted_count,
        )
    finally:
        source.cleanup()


def reset_formula_memory_and_backgrounds(
    repo_dir: Path,
    output_dir_arg: str,
    cloud_dir: Path | None,
    background_library_dir: Path,
) -> ResetSummary:
    output_dir = (repo_dir / output_dir_arg).resolve()
    resolved_cloud_dir = cloud_dir.resolve() if cloud_dir is not None else None
    clear_summary = clear_generated_outputs(output_dir, resolved_cloud_dir)
    removed_background_count = clear_background_library(background_library_dir)
    return ResetSummary(
        removed_generated_count=clear_summary.removed_generated_count,
        removed_cloud_count=clear_summary.removed_cloud_count,
        removed_background_count=removed_background_count,
    )
