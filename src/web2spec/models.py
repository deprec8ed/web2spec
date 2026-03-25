from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class BoundingBox:
    x: float
    y: float
    width: float
    height: float


@dataclass(slots=True)
class SemanticElement:
    tag: str
    text: str = ""
    href: str | None = None
    element_id: str | None = None
    name: str | None = None
    aria_label: str | None = None
    placeholder: str | None = None
    input_type: str | None = None
    role: str | None = None
    section_text: str | None = None
    bbox: BoundingBox | None = None

    def label(self) -> str:
        for candidate in (
            self.text,
            self.aria_label,
            self.placeholder,
            self.name,
            self.element_id,
            self.href,
        ):
            if candidate:
                return candidate
        return self.tag


@dataclass(slots=True)
class PageSnapshot:
    url: str
    depth: int
    title: str
    headings: list[str]
    elements: list[SemanticElement]
    internal_links: list[str]
    template_key: str
    parent_url: str | None = None
    screenshot_path: Path | None = None
    overlay_path: Path | None = None
    markdown: str = ""
    is_template_representative: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in ("screenshot_path", "overlay_path"):
            if payload[key] is not None:
                payload[key] = str(payload[key])
        return payload


@dataclass(slots=True)
class CTAIntent:
    cta: str
    why: str
    evidence: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PageAnalysis:
    url: str
    functional_documentation: str
    user_stories: list[str]
    intent_map: list[CTAIntent]
    raw_response: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class QueueItem:
    url: str
    depth: int
    parent_url: str | None = None


@dataclass(slots=True)
class PipelineResult:
    pages: list[PageSnapshot]
    analyses: dict[str, PageAnalysis]
    errors: list[str]
    report_path: Path
    site_map_path: Path
    analysis_path: Path

