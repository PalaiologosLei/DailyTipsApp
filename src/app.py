from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .background_library import clear_background_library
from .cloud_sync import ClearSummary, CloudSyncError, clear_generated_outputs, ensure_cloud_dir, update_cloud_image_index
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
    data_dir: Path
    cloud_dir: Path
    index_path: Path
    created_count: int
    updated_count: int
    unchanged_count: int
    deleted_count: int


@dataclass(slots=True)
class ResetSummary:
    removed_metadata_count: int
    removed_cloud_count: int
    removed_index_count: int
    removed_background_count: int




@dataclass(slots=True)
class ClearFormulaSummary:
    removed_metadata_count: int
    removed_cloud_count: int
    removed_index_count: int


@dataclass(slots=True)
class ClearBackgroundSummary:
    removed_background_count: int
def run_app(
    repo_dir: Path,
    notes_dir: Path | None,
    github_url: str | None,
    output_dir_arg: str,
    cloud_dir: Path | None,
    render_config: RenderConfig,
) -> RunSummary:
    data_dir = (repo_dir / output_dir_arg).resolve()
    if cloud_dir is None:
        raise AppError("Cloud directory is required because images are now published directly to the synced folder.")
    resolved_cloud_dir = ensure_cloud_dir(cloud_dir.resolve())

    try:
        source = materialize_notes_source(repo_dir=repo_dir, notes_dir=notes_dir, github_url=github_url)
    except Exception as error:
        raise AppError(f"Failed to prepare notes source: {error}") from error

    try:
        markdown_files = find_markdown_files(source.notes_dir)
        items = []
        for markdown_file in markdown_files:
            items.extend(parse_markdown_file(markdown_file))

        try:
            render_summary = render_items(items, resolved_cloud_dir, data_dir, render_config)
            index_summary = update_cloud_image_index(resolved_cloud_dir)
        except CloudSyncError as error:
            raise AppError(f"Cloud output failed: {error}") from error

        return RunSummary(
            source_description=source.description,
            markdown_file_count=len(markdown_files),
            item_count=len(items),
            image_count=render_summary.image_count,
            data_dir=data_dir,
            cloud_dir=resolved_cloud_dir,
            index_path=index_summary.index_path,
            created_count=render_summary.created_count,
            updated_count=render_summary.updated_count,
            unchanged_count=render_summary.unchanged_count,
            deleted_count=len(render_summary.deleted_paths),
        )
    finally:
        source.cleanup()


def clear_formula_memory(
    repo_dir: Path,
    output_dir_arg: str,
    cloud_dir: Path | None,
) -> ClearFormulaSummary:
    data_dir = (repo_dir / output_dir_arg).resolve()
    resolved_cloud_dir = cloud_dir.resolve() if cloud_dir is not None else None
    clear_summary = clear_generated_outputs(data_dir, resolved_cloud_dir)
    return ClearFormulaSummary(
        removed_metadata_count=clear_summary.removed_metadata_count,
        removed_cloud_count=clear_summary.removed_cloud_count,
        removed_index_count=clear_summary.removed_index_count,
    )


def clear_backgrounds(background_library_dir: Path) -> ClearBackgroundSummary:
    return ClearBackgroundSummary(removed_background_count=clear_background_library(background_library_dir))


def reset_formula_memory_and_backgrounds(
    repo_dir: Path,
    output_dir_arg: str,
    cloud_dir: Path | None,
    background_library_dir: Path,
) -> ResetSummary:
    formula_summary = clear_formula_memory(repo_dir, output_dir_arg, cloud_dir)
    background_summary = clear_backgrounds(background_library_dir)
    return ResetSummary(
        removed_metadata_count=formula_summary.removed_metadata_count,
        removed_cloud_count=formula_summary.removed_cloud_count,
        removed_index_count=formula_summary.removed_index_count,
        removed_background_count=background_summary.removed_background_count,
    )
