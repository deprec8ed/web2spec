from __future__ import annotations

import json
from pathlib import Path

from .models import PageAnalysis, PageSnapshot


def write_site_map(path: Path, pages: list[PageSnapshot], errors: list[str]) -> None:
    payload = {
        "pages": [page.to_dict() for page in pages],
        "errors": errors,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_analysis(path: Path, analyses: dict[str, PageAnalysis]) -> None:
    payload = {url: analysis.to_dict() for url, analysis in analyses.items()}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_report(
    root_url: str,
    pages: list[PageSnapshot],
    analyses: dict[str, PageAnalysis],
    errors: list[str],
) -> str:
    lines = [
        "# Web2Spec Report",
        "",
        f"- Root URL: {root_url}",
        f"- Pages crawled: {len(pages)}",
        f"- Analyses generated: {len(analyses)}",
        "",
        "## Sitemap",
        "",
    ]

    for page in sorted(pages, key=lambda item: (item.depth, item.url)):
        indent = "  " * page.depth
        lines.append(f"{indent}- {page.title} ({page.url})")

    if errors:
        lines.extend(["", "## Crawl Errors", ""])
        lines.extend(f"- {error}" for error in errors)

    for page in sorted(pages, key=lambda item: (item.depth, item.url)):
        analysis = analyses.get(page.url)
        lines.extend(
            [
                "",
                f"## {page.title}",
                "",
                f"- URL: {page.url}",
                f"- Template: {page.template_key}",
                f"- Depth: {page.depth}",
                f"- Screenshot: {page.screenshot_path}",
                f"- Overlay: {page.overlay_path}",
                "",
                "### Distilled Markdown",
                "",
                "```markdown",
                page.markdown.rstrip(),
                "```",
                "",
            ]
        )

        if analysis is None:
            lines.extend(["### Analysis", "", "_Skipped or unavailable._", ""])
            continue

        lines.extend(
            [
                "### Functional Documentation",
                "",
                analysis.functional_documentation or "_No summary returned._",
                "",
                "### User Stories",
                "",
            ]
        )

        if analysis.user_stories:
            lines.extend(f"- {story}" for story in analysis.user_stories)
        else:
            lines.append("- _No user stories returned._")

        lines.extend(["", "### Intent Map", ""])
        if analysis.intent_map:
            for intent in analysis.intent_map:
                lines.append(f"- CTA: {intent.cta or 'Unknown CTA'}")
                lines.append(f"  Why: {intent.why or 'No rationale returned.'}")
                if intent.evidence:
                    lines.append(f"  Evidence: {'; '.join(intent.evidence)}")
        else:
            lines.append("- _No CTA analysis returned._")

    return "\n".join(lines).strip() + "\n"

