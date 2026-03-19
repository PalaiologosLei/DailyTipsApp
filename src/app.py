from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .git_sync import GitSyncError, commit_and_push
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
    git_pushed: bool
    created_count: int
    updated_count: int
    unchanged_count: int
    deleted_count: int


def run_app(
    repo_dir: Path,
    notes_dir: Path | None,
    github_url: str | None,
    output_dir_arg: str,
    width: int,
    height: int,
    skip_git: bool,
    commit_message: str | None,
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

        render_summary = render_items(items, output_dir, width=width, height=height)

        git_pushed = False
        if not skip_git:
            try:
                git_pushed = commit_and_push(repo_dir, commit_message=commit_message)
            except GitSyncError as error:
                raise AppError(f"Git sync failed: {error}") from error

        return RunSummary(
            source_description=source.description,
            markdown_file_count=len(markdown_files),
            item_count=len(items),
            image_count=render_summary.image_count,
            output_dir=output_dir,
            git_pushed=git_pushed,
            created_count=render_summary.created_count,
            updated_count=render_summary.updated_count,
            unchanged_count=render_summary.unchanged_count,
            deleted_count=len(render_summary.deleted_paths),
        )
    finally:
        source.cleanup()
