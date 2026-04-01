from __future__ import annotations

import asyncio
import re
from typing import TypedDict

from .analyst import Analyst
from .cartographer import Cartographer
from .config import RunConfig
from .distiller import Distiller
from .guide import attach_focused_step_images, write_guide
from .models import GuideSection, PageAnalysis, PageSnapshot, PipelineResult, QueueItem
from .report import build_report, write_analysis, write_dashboard, write_site_map
from .utils import canonicalize_url, ensure_dir


class PipelineState(TypedDict):
    pending: list[QueueItem]
    visited: list[str]
    pages: list[PageSnapshot]
    analyses: dict[str, PageAnalysis]
    guide_sections: list[GuideSection]
    errors: list[str]


class Web2SpecPipeline:
    def __init__(self, config: RunConfig) -> None:
        self.config = config
        ensure_dir(config.output_dir)

    async def run(self) -> PipelineResult:
        try:
            from langgraph.graph import END, START, StateGraph
        except ImportError as exc:
            raise RuntimeError("LangGraph is not installed. Run `pip install -e .`.") from exc

        distiller = Distiller(self.config)
        analyst = None if self.config.skip_analysis else Analyst(self.config)
        start_url = canonicalize_url(self.config.start_url)

        async with Cartographer(self.config) as cartographer:
            async def process_page(state: PipelineState) -> PipelineState:
                pending = list(state["pending"])
                if not pending:
                    return state

                visited = set(state["visited"])
                pages = list(state["pages"])
                analyses = dict(state["analyses"])
                guide_sections = list(state["guide_sections"])
                errors = list(state["errors"])

                current = pending.pop(0)
                if current.url in visited:
                    return {
                        "pending": pending,
                        "visited": list(visited),
                        "pages": pages,
                        "analyses": analyses,
                        "guide_sections": guide_sections,
                        "errors": errors,
                    }

                visited.add(current.url)
                self._log(
                    f"[crawl] depth={current.depth} pending={len(pending)} visited={len(visited)} url={current.url}"
                )

                try:
                    snapshot = await cartographer.capture_page(current)
                    snapshot = distiller.distill(snapshot)
                    pages.append(snapshot)
                    self._log(
                        f"[distill] title={snapshot.title!r} links={len(snapshot.internal_links)} template={snapshot.template_key}"
                    )

                    if analyst is not None:
                        self._log(f"[analyze] url={snapshot.url} model={self.config.resolved_model()}")
                        if self.config.output_format in ("report", "both"):
                            analyses[snapshot.url] = await analyst.analyze(snapshot)
                        if self.config.output_format in ("guide", "both"):
                            page_is_relevant = _is_goal_relevant(snapshot, self.config.goal_context)
                            if self.config.intent_only and self.config.goal_context and not page_is_relevant:
                                self._log(f"[guide-skip] url={snapshot.url} reason=not_goal_relevant")
                            else:
                                guide_section = await analyst.analyze_for_guide(snapshot)
                                guide_section = attach_focused_step_images(
                                    guide_section,
                                    snapshot,
                                    self.config.output_dir / "guide_crops",
                                    self.config.crop_top_padding,
                                    self.config.crop_bottom_padding,
                                )
                                guide_sections.append(guide_section)
                        self._log(f"[done] analyzed url={snapshot.url}")

                    if current.depth < self.config.depth_limit:
                        queued_urls = {item.url for item in pending}

                        if self.config.action_runner and analyst is not None:
                            candidate_links = await analyst.decide_next_links(snapshot)
                            self._log(
                                f"[action-runner] LLM selected {len(candidate_links)} link(s) to follow"
                                + (f": {candidate_links}" if candidate_links else "")
                            )
                        else:
                            candidate_links = _prioritize_links_for_goal(
                                snapshot.internal_links, self.config.goal_context
                            )

                        for link in candidate_links:
                            if link in visited or link in queued_urls:
                                continue
                            if len(visited) + len(pending) >= self.config.max_pages:
                                break
                            pending.append(
                                QueueItem(
                                    url=link,
                                    depth=current.depth + 1,
                                    parent_url=current.url,
                                )
                            )
                            queued_urls.add(link)
                            self._log(f"[queue] depth={current.depth + 1} url={link}")
                except Exception as exc:
                    self._log(f"[error] url={current.url} error={exc}")
                    errors.append(f"{current.url}: {exc}")

                return {
                    "pending": pending,
                    "visited": list(visited),
                    "pages": pages,
                    "analyses": analyses,
                    "guide_sections": guide_sections,
                    "errors": errors,
                }

            def next_step(state: PipelineState) -> str:
                return "process_page" if state["pending"] else END

            graph = StateGraph(PipelineState)
            graph.add_node("process_page", process_page)
            graph.add_edge(START, "process_page")
            graph.add_conditional_edges("process_page", next_step)
            app = graph.compile()

            final_state = await app.ainvoke(
                {
                    "pending": [QueueItem(url=start_url, depth=0)],
                    "visited": [],
                    "pages": [],
                    "analyses": {},
                    "guide_sections": [],
                    "errors": [],
                }
            )

        pages = final_state["pages"]
        analyses = final_state["analyses"]
        guide_sections = final_state["guide_sections"]
        errors = final_state["errors"]

        report_path = self.config.output_dir / "report.md"
        site_map_path = self.config.output_dir / "site_map.json"
        analysis_path = self.config.output_dir / "analysis.json"
        dashboard_path = self.config.output_dir / "dashboard.html"
        guide_path = self.config.output_dir / "guide.docx"

        if self.config.output_format in ("report", "both"):
            report_path.write_text(
                build_report(start_url, pages, analyses, errors, locale=self.config.locale),
                encoding="utf-8",
            )
            write_site_map(site_map_path, pages, errors, locale=self.config.locale)
            write_analysis(analysis_path, analyses, locale=self.config.locale)
            write_dashboard(dashboard_path, start_url, pages, analyses, errors, locale=self.config.locale)

        if self.config.output_format in ("guide", "both"):
            write_guide(guide_path, start_url, guide_sections, locale=self.config.locale)

        return PipelineResult(
            pages=pages,
            analyses=analyses,
            errors=errors,
            report_path=report_path,
            site_map_path=site_map_path,
            analysis_path=analysis_path,
            dashboard_path=dashboard_path,
            guide_path=guide_path if self.config.output_format in ("guide", "both") else None,
        )

    def _log(self, message: str) -> None:
        if self.config.show_progress:
            print(message, flush=True)


def run_pipeline(config: RunConfig) -> PipelineResult:
    return asyncio.run(Web2SpecPipeline(config).run())


_STOP_WORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "your",
    "you",
    "oraz",
    "or",
    "dla",
    "aby",
    "sie",
    "się",
    "ktore",
    "które",
}


def _extract_goal_tokens(goal_context: str | None) -> list[str]:
    if not goal_context:
        return []
    tokens = re.findall(r"[\w\-]{4,}", goal_context.casefold())
    result: list[str] = []
    for token in tokens:
        if token in _STOP_WORDS or token.isdigit():
            continue
        if token not in result:
            result.append(token)
    return result


def _is_goal_relevant(snapshot: PageSnapshot, goal_context: str | None) -> bool:
    tokens = _extract_goal_tokens(goal_context)
    if not tokens:
        return True

    haystack_parts = [snapshot.url, snapshot.title, " ".join(snapshot.headings), snapshot.markdown[:3000]]
    for element in snapshot.elements[:200]:
        haystack_parts.extend(
            [
                element.text or "",
                element.aria_label or "",
                element.placeholder or "",
                element.name or "",
                element.href or "",
            ]
        )
    haystack = " ".join(haystack_parts).casefold()
    matches = sum(1 for token in tokens if token in haystack)
    threshold = 1 if len(tokens) <= 3 else 2
    return matches >= threshold


def _prioritize_links_for_goal(links: list[str], goal_context: str | None) -> list[str]:
    tokens = _extract_goal_tokens(goal_context)
    if not tokens:
        return links

    scored: list[tuple[int, str]] = []
    for link in links:
        lowered = link.casefold()
        score = sum(1 for token in tokens if token in lowered)
        scored.append((score, link))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [link for _, link in scored]
