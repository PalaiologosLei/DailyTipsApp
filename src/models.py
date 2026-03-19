from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class KnowledgeItem:
    title: str
    body: str
    notes: list[str]
    source_path: Path
    source_line: int


@dataclass(slots=True)
class RenderResult:
    item: KnowledgeItem
    image_path: Path
