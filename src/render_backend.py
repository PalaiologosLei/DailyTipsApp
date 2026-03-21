from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .models import KnowledgeItem, PreparedRenderJob, RenderConfig
from .renderer import build_render_job, render_job


class RenderBackendError(RuntimeError):
    pass


@dataclass(slots=True)
class PreparedRenderRequest:
    item: KnowledgeItem
    output_path: Path


@dataclass(slots=True)
class RenderBackendResult:
    rendered_count: int


class RenderBackend:
    def render_prepared(self, requests: list[PreparedRenderRequest], render_config: RenderConfig) -> RenderBackendResult:
        raise NotImplementedError


class PythonRendererBackend(RenderBackend):
    def render_prepared(self, requests: list[PreparedRenderRequest], render_config: RenderConfig) -> RenderBackendResult:
        rendered_count = 0
        for request in requests:
            request.output_path.parent.mkdir(parents=True, exist_ok=True)
            job = build_render_job(request.item, request.output_path, render_config)
            render_job(job, render_config)
            rendered_count += 1
        return RenderBackendResult(rendered_count=rendered_count)


def build_prepared_requests(raw_items: list[dict[str, object]], output_root: Path) -> list[PreparedRenderRequest]:
    requests: list[PreparedRenderRequest] = []
    for raw_item in raw_items:
        output_file = str(raw_item.get("output_file", "")).strip()
        if not output_file:
            raise RenderBackendError("Prepared render item is missing output_file.")
        item = KnowledgeItem(
            title=str(raw_item.get("title", "")).strip(),
            body=str(raw_item.get("body", "")).strip(),
            notes=[str(note).strip() for note in raw_item.get("notes", []) if str(note).strip()],
            source_path=Path(str(raw_item.get("source_path", ""))),
            source_line=int(raw_item.get("source_line", 0) or 0),
        )
        requests.append(PreparedRenderRequest(item=item, output_path=output_root / output_file))
    return requests
