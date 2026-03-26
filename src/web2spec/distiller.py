from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .config import RunConfig
from .i18n import get_text
from .models import PageSnapshot, SemanticElement
from .utils import ensure_dir, normalize_whitespace, safe_filename_from_url

MAX_LABEL_LENGTH = 80
MAX_LINKS_PER_PAGE = 60
MAX_INTERNAL_LINKS = 40


class Distiller:
    def __init__(self, config: RunConfig) -> None:
        self.config = config
        self.text = get_text(config.locale)["distiller"]
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
        selected_elements = self._select_elements(snapshot.elements)
        grouped: dict[str, list[SemanticElement]] = defaultdict(list)
        for element in selected_elements:
            grouped[element.tag].append(element)

        lines = [
            f"# {snapshot.title}",
            "",
            f"- {self.text['url']}: {snapshot.url}",
            f"- {self.text['depth']}: {snapshot.depth}",
            f"- {self.text['template']}: {snapshot.template_key}",
            "",
        ]

        if snapshot.headings:
            lines.extend([f"## {self.text['headings']}", ""])
            lines.extend(f"- {heading}" for heading in snapshot.headings)
            lines.append("")

        for tag in ("nav", "a", "button", "input", "form"):
            section_name = self.text["section_titles"][tag]
            elements = grouped.get(tag, [])
            if not elements:
                continue
            lines.extend([f"## {section_name}", ""])
            for element in elements:
                lines.append(self._render_element_line(element))
            if tag == "a":
                total_links = self._count_renderable_links(snapshot.elements)
                if total_links > len(elements):
                    lines.append(
                        "- ["
                        + self.text["link_inventory_truncated"].format(shown=len(elements), total=total_links)
                        + "]"
                    )
            lines.append("")

        if snapshot.internal_links:
            lines.extend([f"## {self.text['internal_links']}", ""])
            lines.extend(f"- {link}" for link in snapshot.internal_links[:MAX_INTERNAL_LINKS])
            if len(snapshot.internal_links) > MAX_INTERNAL_LINKS:
                lines.append(
                    "- ["
                    + self.text["internal_link_inventory_truncated"].format(
                        shown=MAX_INTERNAL_LINKS,
                        total=len(snapshot.internal_links),
                    )
                    + "]"
                )
            lines.append("")

        return "\n".join(lines).strip() + "\n"

    def _render_element_line(self, element: SemanticElement) -> str:
        label = self._display_label(element)
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
        if element.tag in {"button", "input", "form"} and element.section_text:
            metadata.append(f"{self.text['context']}={element.section_text[:120]!r}")
        elif element.tag == "nav":
            nav_item_count = len(element.text.split())
            metadata.append(f"{self.text['items']}~{nav_item_count}")
        suffix = f" ({', '.join(metadata)})" if metadata else ""
        tag_label = self.text["tag_labels"].get(element.tag, element.tag.capitalize())
        return f"- [{tag_label}: {label!r}]{suffix}"

    def _select_elements(self, elements: list[SemanticElement]) -> list[SemanticElement]:
        deduped: list[SemanticElement] = []
        seen: set[tuple[str, str, str]] = set()

        for element in elements:
            label = normalize_whitespace(element.label())
            href = element.href or ""
            key = (element.tag, href, label.lower())
            if key in seen:
                continue
            seen.add(key)
            deduped.append(element)

        selected: list[SemanticElement] = []
        link_count = 0
        for element in deduped:
            if self._is_noise(element):
                continue
            if element.tag == "a":
                if link_count >= MAX_LINKS_PER_PAGE:
                    continue
                link_count += 1
            selected.append(element)
        return selected

    def _is_noise(self, element: SemanticElement) -> bool:
        label = normalize_whitespace(element.label())
        if not label and not element.href and element.tag not in {"nav", "form"}:
            return True
        if element.tag == "nav" and (len(label) > 100 or len(label.split()) > 14):
            return False
        if element.tag == "a" and not label and not (element.aria_label or "").strip():
            return True
        return False

    def _display_label(self, element: SemanticElement) -> str:
        label = normalize_whitespace(element.label())
        if element.tag == "nav" and (len(label) > 100 or len(label.split()) > 14):
            return self.text["navigation_menu"]
        if len(label) > MAX_LABEL_LENGTH:
            return f"{label[: MAX_LABEL_LENGTH - 1].rstrip()}…"
        return label

    def _count_renderable_links(self, elements: list[SemanticElement]) -> int:
        deduped_link_keys: set[tuple[str, str, str]] = set()
        for element in elements:
            if element.tag != "a" or self._is_noise(element):
                continue
            label = normalize_whitespace(element.label())
            key = (element.tag, element.href or "", label.lower())
            deduped_link_keys.add(key)
        return len(deduped_link_keys)

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
