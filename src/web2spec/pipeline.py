from __future__ import annotations

import asyncio
from typing import TypedDict

from .analyst import Analyst
from .cartographer import Cartographer
from .config import RunConfig
from .distiller import Distiller
from .models import PageAnalysis, PageSnapshot, PipelineResult, QueueItem
from .report import build_report, write_analysis, write_dashboard, write_site_map
from .utils import canonicalize_url, ensure_dir


class PipelineState(TypedDict):
    pending: list[QueueItem]
    visited: list[str]
    pages: list[PageSnapshot]
    analyses: dict[str, PageAnalysis]
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
                errors = list(state["errors"])

                current = pending.pop(0)
                if current.url in visited:
                    return {
                        "pending": pending,
                        "visited": list(visited),
                        "pages": pages,
                        "analyses": analyses,
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
                        analyses[snapshot.url] = await analyst.analyze(snapshot)
                        self._log(f"[done] analyzed url={snapshot.url}")

                    if current.depth < self.config.depth_limit:
                        queued_urls = {item.url for item in pending}
                        for link in snapshot.internal_links:
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
                    "errors": [],
                }
            )

        pages = final_state["pages"]
        analyses = final_state["analyses"]
        errors = final_state["errors"]

        report_path = self.config.output_dir / "report.md"
        site_map_path = self.config.output_dir / "site_map.json"
        analysis_path = self.config.output_dir / "analysis.json"
        dashboard_path = self.config.output_dir / "dashboard.html"

        report_path.write_text(
            build_report(start_url, pages, analyses, errors, locale=self.config.locale),
            encoding="utf-8",
        )
        write_site_map(site_map_path, pages, errors, locale=self.config.locale)
        write_analysis(analysis_path, analyses, locale=self.config.locale)
        write_dashboard(dashboard_path, start_url, pages, analyses, errors, locale=self.config.locale)

        return PipelineResult(
            pages=pages,
            analyses=analyses,
            errors=errors,
            report_path=report_path,
            site_map_path=site_map_path,
            analysis_path=analysis_path,
            dashboard_path=dashboard_path,
        )

    def _log(self, message: str) -> None:
        if self.config.show_progress:
            print(message, flush=True)


def run_pipeline(config: RunConfig) -> PipelineResult:
    return asyncio.run(Web2SpecPipeline(config).run())
