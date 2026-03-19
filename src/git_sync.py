from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path


class GitSyncError(RuntimeError):
    pass


def commit_and_push(repo_dir: Path, commit_message: str | None = None) -> bool:
    if not _has_changes(repo_dir):
        return False

    _run_git(["add", "-A"], repo_dir)

    if not _has_changes(repo_dir):
        return False

    message = commit_message or f"Generate images {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    _run_git(["commit", "-m", message], repo_dir)

    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], repo_dir).strip()
    _run_git(["push", "origin", branch], repo_dir)
    return True


def _has_changes(repo_dir: Path) -> bool:
    status = _run_git(["status", "--porcelain"], repo_dir)
    return bool(status.strip())


def _run_git(args: list[str], repo_dir: Path) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        raise GitSyncError(completed.stderr.strip() or completed.stdout.strip() or "git command failed")
    return completed.stdout
