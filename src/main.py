from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .app import AppError, run_app
from .renderer import DEFAULT_HEIGHT, DEFAULT_WIDTH


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scan markdown notes, extract formulas/knowledge points, and render them as images."
    )
    parser.add_argument("--notes-dir", help="Root directory of a local markdown notes repository.")
    parser.add_argument("--github-url", help="GitHub public repository URL, such as https://github.com/owner/repo.")
    parser.add_argument("--output-dir", default="output/images", help="Directory used to save generated images.")
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH, help="Image width in pixels.")
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT, help="Image height in pixels.")
    parser.add_argument("--skip-git", action="store_true", help="Generate images only and skip git add/commit/push.")
    parser.add_argument("--commit-message", default=None, help="Custom git commit message.")
    parser.add_argument("--gui", action="store_true", help="Launch the simple desktop GUI.")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.gui:
        from .gui import launch_gui

        launch_gui()
        return 0

    if bool(args.notes_dir) == bool(args.github_url):
        print("Provide exactly one of --notes-dir or --github-url.", file=sys.stderr)
        return 2

    repo_dir = Path(__file__).resolve().parent.parent

    try:
        summary = run_app(
            repo_dir=repo_dir,
            notes_dir=Path(args.notes_dir).expanduser().resolve() if args.notes_dir else None,
            github_url=args.github_url,
            output_dir_arg=args.output_dir,
            width=args.width,
            height=args.height,
            skip_git=args.skip_git,
            commit_message=args.commit_message,
        )
    except AppError as error:
        print(str(error), file=sys.stderr)
        return 1

    print(f"Source: {summary.source_description}")
    print(f"Scanned markdown files: {summary.markdown_file_count}")
    print(f"Extracted items: {summary.item_count}")
    print(f"Generated images: {summary.image_count}")
    print(f"Output directory: {summary.output_dir}")

    if args.skip_git:
        print("Git sync skipped.")
    elif summary.git_pushed:
        print("Git sync completed.")
    else:
        print("No git changes detected.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
