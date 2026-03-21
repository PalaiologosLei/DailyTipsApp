from __future__ import annotations

import re
from pathlib import Path

from .models import KnowledgeItem

TITLE_PATTERN = re.compile(r"【([^】]+)】")
LIST_MARKER_PATTERN = re.compile(r"^([-*+])\s+(.*)$")
READ_ENCODINGS = ("utf-8", "utf-8-sig", "gbk", "gb18030")


def parse_markdown_file(path: Path) -> list[KnowledgeItem]:
    return parse_markdown_text(_read_markdown_text(path), path)


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
        child_lines = _collect_direct_children(lines, index + 1, indent)
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

    return items


def _read_markdown_text(path: Path) -> str:
    for encoding in READ_ENCODINGS:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="ignore")


def _collect_direct_children(lines: list[str], start_index: int, parent_indent: int) -> list[tuple[int, str]]:
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

    return candidate_lines


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