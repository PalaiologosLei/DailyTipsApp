from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .git_sync import GitSyncError, commit_and_push
from .parser import parse_markdown_file
from .renderer import DEFAULT_HEIGHT, DEFAULT_WIDTH, render_items
from .scanner import find_markdown_files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scan markdown notes, extract formulas/knowledge points, and render them as images."
    )
    parser.add_argument("--notes-dir", required=True, help="Root directory of the markdown notes repository.")
    parser.add_argument("--output-dir", default="output/images", help="Directory used to save generated images.")
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH, help="Image width in pixels.")
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT, help="Image height in pixels.")
    parser.add_argument("--skip-git", action="store_true", help="Generate images only and skip git add/commit/push.")
    parser.add_argument("--commit-message", default=None, help="Custom git commit message.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_dir = Path(__file__).resolve().parent.parent
    notes_dir = Path(args.notes_dir).expanduser().resolve()
    output_dir = (repo_dir / args.output_dir).resolve()

    markdown_files = find_markdown_files(notes_dir)
    all_items = []
    for markdown_file in markdown_files:
        all_items.extend(parse_markdown_file(markdown_file))

    render_results = render_items(all_items, output_dir, width=args.width, height=args.height)

    print(f"Scanned markdown files: {len(markdown_files)}")
    print(f"Extracted items: {len(all_items)}")
    print(f"Generated images: {len(render_results)}")
    print(f"Output directory: {output_dir}")

    if args.skip_git:
        print("Git sync skipped.")
        return 0

    try:
        pushed = commit_and_push(repo_dir, commit_message=args.commit_message)
    except GitSyncError as error:
        print(f"Git sync failed: {error}", file=sys.stderr)
        return 1

    if pushed:
        print("Git sync completed.")
    else:
        print("No git changes detected.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
