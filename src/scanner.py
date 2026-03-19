from __future__ import annotations

from pathlib import Path


def find_markdown_files(notes_dir: Path) -> list[Path]:
    """Return all markdown files under notes_dir recursively."""
    if not notes_dir.exists():
        raise FileNotFoundError(f"Notes directory does not exist: {notes_dir}")
    if not notes_dir.is_dir():
        raise NotADirectoryError(f"Notes directory is not a directory: {notes_dir}")
    return sorted(path for path in notes_dir.rglob("*.md") if path.is_file())
