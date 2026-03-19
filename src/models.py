from __future__ import annotations

from dataclasses import dataclass, field
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
    status: str


@dataclass(slots=True)
class RenderSummary:
    results: list[RenderResult] = field(default_factory=list)
    manifest_path: Path | None = None
    created_count: int = 0
    updated_count: int = 0
    unchanged_count: int = 0
    deleted_paths: list[Path] = field(default_factory=list)

    @property
    def image_count(self) -> int:
        return len(self.results)

    @property
    def changed_count(self) -> int:
        return self.created_count + self.updated_count + len(self.deleted_paths)
