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
class BackgroundSelection:
    mode: str = "white"
    image_id: str = ""
    group_name: str = ""


@dataclass(slots=True)
class RenderConfig:
    width: int
    height: int
    top_blank_ratio: float = 1 / 3
    background_selection: BackgroundSelection = field(default_factory=BackgroundSelection)
    background_library_dir: Path | None = None
    show_content_panel: bool = True
    panel_opacity: int = 212
    text_font_family: str = "microsoft_yahei"
    math_font_family: str = "dejavusans"
    formula_renderer: str = "auto"
    text_color: str = "#000000"
    math_color: str = "#000000"


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
    manifest_data: dict[str, object] | None = None
    render_state_data: dict[str, object] | None = None
    image_index_data: dict[str, object] | None = None

    @property
    def image_count(self) -> int:
        return len(self.results)

    @property
    def changed_count(self) -> int:
        return self.created_count + self.updated_count + len(self.deleted_paths)
