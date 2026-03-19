from __future__ import annotations

import re
from pathlib import Path

from .models import KnowledgeItem

TITLE_PATTERN = re.compile(r"【([^】]+)】")
LIST_MARKER_PATTERN = re.compile(r"^([-*+])\s+(.*)$")


def parse_markdown_file(path: Path) -> list[KnowledgeItem]:
    return parse_markdown_text(path.read_text(encoding="utf-8"), path)


def parse_markdown_text(text: str, source_path: Path) -> list[KnowledgeItem]:
    lines = text.splitlines()
    items: list[KnowledgeItem] = []

    for index, raw_line in enumerate(lines):
        parsed = _parse_line(raw_line)
        if parsed is None:
            continue

        indent, content = parsed
        title_match = TITLE_PATTERN.search(content)
        if not title_match:
            continue

        title = title_match.group(1).strip()
        child_lines, next_index = _collect_direct_children(lines, index + 1, indent)
        if not child_lines:
            continue

        body = child_lines[0][1].strip()
        if not body:
            continue

        notes = [child_text.strip() for _, child_text in child_lines[1:] if child_text.strip()]
        items.append(
            KnowledgeItem(
                title=title,
                body=body,
                notes=notes,
                source_path=source_path,
                source_line=index + 1,
            )
        )

        if next_index <= index:
            continue

    return items


def _collect_direct_children(
    lines: list[str], start_index: int, parent_indent: int
) -> tuple[list[tuple[int, str]], int]:
    candidate_lines: list[tuple[int, str]] = []
    child_indent: int | None = None
    index = start_index

    while index < len(lines):
        parsed = _parse_line(lines[index])
        if parsed is None:
            index += 1
            continue

        indent, content = parsed
        if indent <= parent_indent:
            break

        if child_indent is None:
            child_indent = indent

        if indent == child_indent and content.strip():
            candidate_lines.append((index + 1, content))

        index += 1

    return candidate_lines, index


def _parse_line(raw_line: str) -> tuple[int, str] | None:
    if not raw_line.strip():
        return None

    expanded = raw_line.expandtabs(4)
    indent = len(expanded) - len(expanded.lstrip(" "))
    content = expanded.lstrip(" ")

    marker_match = LIST_MARKER_PATTERN.match(content)
    if marker_match:
        content = marker_match.group(2).strip()
    else:
        content = content.strip()

    if not content:
        return None

    return indent, content
