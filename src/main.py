from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .app import AppError, run_app
from .models import BackgroundSelection, RenderConfig
from .renderer import DEFAULT_HEIGHT, DEFAULT_WIDTH


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scan markdown notes, extract formulas/knowledge points, and render them as images."
    )
    parser.add_argument("--notes-dir", help="Root directory of a local markdown notes repository.")
    parser.add_argument("--github-url", help="GitHub public repository URL, such as https://github.com/owner/repo.")
    parser.add_argument("--output-dir", default="output/images", help="Directory used to save generated images.")
    parser.add_argument("--cloud-dir", help="Directory in iCloud, OneDrive, or another synced folder used to publish images.")
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH, help="Image width in pixels.")
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT, help="Image height in pixels.")
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
    render_config = RenderConfig(width=args.width, height=args.height, background_selection=BackgroundSelection())

    try:
        summary = run_app(
            repo_dir=repo_dir,
            notes_dir=Path(args.notes_dir).expanduser().resolve() if args.notes_dir else None,
            github_url=args.github_url,
            output_dir_arg=args.output_dir,
            cloud_dir=Path(args.cloud_dir).expanduser() if args.cloud_dir else None,
            render_config=render_config,
        )
    except AppError as error:
        print(str(error), file=sys.stderr)
        return 1

    print(f"Source: {summary.source_description}")
    print(f"Scanned markdown files: {summary.markdown_file_count}")
    print(f"Extracted items: {summary.item_count}")
    print(f"Generated images: {summary.image_count}")
    print(f"Created: {summary.created_count}, Updated: {summary.updated_count}, Unchanged: {summary.unchanged_count}, Deleted: {summary.deleted_count}")
    print(f"Output directory: {summary.output_dir}")
    if summary.cloud_dir is not None:
        print(f"Cloud directory: {summary.cloud_dir}")
        print(f"Cloud copied: {summary.cloud_copied_count}, Cloud deleted: {summary.cloud_deleted_count}")
    else:
        print("Cloud sync skipped.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
