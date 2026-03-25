from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .config import RunConfig
from .models import PageSnapshot, SemanticElement
from .utils import ensure_dir, safe_filename_from_url


class Distiller:
    def __init__(self, config: RunConfig) -> None:
        self.config = config
        self.markdown_dir = ensure_dir(config.output_dir / "markdown")
        self.overlays_dir = ensure_dir(config.output_dir / "overlays")
        self._seen_templates: set[str] = set()

    def distill(self, snapshot: PageSnapshot) -> PageSnapshot:
        snapshot.markdown = self._render_markdown(snapshot)
        snapshot.is_template_representative = snapshot.template_key not in self._seen_templates
        self._seen_templates.add(snapshot.template_key)

        markdown_path = self.markdown_dir / f"{safe_filename_from_url(snapshot.url)}.md"
        markdown_path.write_text(snapshot.markdown, encoding="utf-8")

        if self.config.capture_overlay and snapshot.screenshot_path is not None:
            snapshot.overlay_path = self._create_overlay(snapshot)
        return snapshot

    def _render_markdown(self, snapshot: PageSnapshot) -> str:
        grouped: dict[str, list[SemanticElement]] = defaultdict(list)
        for element in snapshot.elements:
            grouped[element.tag].append(element)

        lines = [
            f"# {snapshot.title}",
            "",
            f"- URL: {snapshot.url}",
            f"- Depth: {snapshot.depth}",
            f"- Template: {snapshot.template_key}",
            "",
        ]

        if snapshot.headings:
            lines.extend(["## Headings", ""])
            lines.extend(f"- {heading}" for heading in snapshot.headings)
            lines.append("")

        for tag, section_name in (
            ("nav", "Navigation"),
            ("a", "Links"),
            ("button", "Buttons"),
            ("input", "Inputs"),
            ("form", "Forms"),
        ):
            elements = grouped.get(tag, [])
            if not elements:
                continue
            lines.extend([f"## {section_name}", ""])
            for element in elements:
                lines.append(self._render_element_line(element))
            lines.append("")

        if snapshot.internal_links:
            lines.extend(["## Internal Links", ""])
            lines.extend(f"- {link}" for link in snapshot.internal_links)
            lines.append("")

        return "\n".join(lines).strip() + "\n"

    def _render_element_line(self, element: SemanticElement) -> str:
        label = element.label()
        metadata: list[str] = []
        if element.href:
            metadata.append(f"href={element.href}")
        if element.aria_label:
            metadata.append(f"aria-label={element.aria_label!r}")
        if element.name:
            metadata.append(f"name={element.name!r}")
        if element.placeholder:
            metadata.append(f"placeholder={element.placeholder!r}")
        if element.element_id:
            metadata.append(f"id={element.element_id!r}")
        if element.input_type:
            metadata.append(f"type={element.input_type!r}")
        if element.section_text:
            metadata.append(f"context={element.section_text[:120]!r}")
        suffix = f" ({', '.join(metadata)})" if metadata else ""
        return f"- [{element.tag.capitalize()}: {label!r}]{suffix}"

    def _create_overlay(self, snapshot: PageSnapshot) -> Path | None:
        if snapshot.screenshot_path is None:
            return None

        try:
            from PIL import Image, ImageDraw
        except ImportError:
            return None

        overlay_path = self.overlays_dir / snapshot.screenshot_path.name
        image = Image.open(snapshot.screenshot_path).convert("RGBA")
        draw = ImageDraw.Draw(image)
        colors = {
            "a": (27, 94, 32, 190),
            "button": (183, 28, 28, 190),
            "input": (13, 71, 161, 190),
            "form": (109, 76, 65, 190),
            "nav": (74, 20, 140, 190),
        }

        for element in snapshot.elements:
            if element.bbox is None:
                continue
            color = colors.get(element.tag, (33, 33, 33, 180))
            x1 = element.bbox.x
            y1 = element.bbox.y
            x2 = x1 + element.bbox.width
            y2 = y1 + element.bbox.height
            draw.rectangle((x1, y1, x2, y2), outline=color, width=3)

        image.save(overlay_path)
        return overlay_path
