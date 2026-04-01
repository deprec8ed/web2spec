from __future__ import annotations

import argparse
from pathlib import Path

from .config import RunConfig
from .i18n import DEFAULT_LOCALE, SUPPORTED_LOCALES
from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Crawl a website into structured documentation artifacts.")
    parser.add_argument("url", help="Starting URL to crawl.")
    parser.add_argument("--output-dir", default="outputs/run", help="Directory for generated artifacts.")
    parser.add_argument("--depth-limit", type=int, default=2, help="Maximum crawl depth from the start URL.")
    parser.add_argument(
        "--provider",
        choices=("azure-openai", "openai", "anthropic"),
        default="azure-openai",
        help="Multimodal LLM provider.",
    )
    parser.add_argument("--model", default=None, help="Override the model name.")
    parser.add_argument("--max-pages", type=int, default=20, help="Maximum pages to queue for the PoC.")
    parser.add_argument("--skip-analysis", action="store_true", help="Skip the LLM analysis phase.")
    parser.add_argument("--no-overlay", action="store_true", help="Skip annotated screenshot generation.")
    parser.add_argument("--show-browser", action="store_true", help="Run Chromium in headed mode.")
    parser.add_argument("--quiet", action="store_true", help="Suppress crawl progress logs.")
    parser.add_argument(
        "--browser-channel",
        choices=("chrome", "msedge"),
        default=None,
        help="Use a locally installed browser channel instead of Playwright-managed Chromium.",
    )
    parser.add_argument(
        "--browser-executable-path",
        default=None,
        help="Explicit browser executable path for Playwright launch.",
    )
    parser.add_argument(
        "--business-context",
        default=None,
        help="Short product or business description to guide the analyst prompts.",
    )
    parser.add_argument(
        "--business-context-file",
        default=None,
        help="Path to a text or markdown file with business context for the target site.",
    )
    parser.add_argument(
        "--locale",
        choices=SUPPORTED_LOCALES,
        default=DEFAULT_LOCALE,
        help="Locale for generated artifacts and analysis output.",
    )
    parser.add_argument(
        "--output-format",
        choices=("report", "guide", "both"),
        default="report",
        help="Output format: 'report' for markdown/dashboard, 'guide' for DOCX user guide, 'both' for all.",
    )
    parser.add_argument(
        "--goal-context",
        default=None,
        help="Goal/intention text used to focus guide generation on relevant pages and actions.",
    )
    parser.add_argument(
        "--goal-context-file",
        default=None,
        help="Path to a text or markdown file with the goal/intention for focused guide generation.",
    )
    parser.add_argument(
        "--intent-only",
        action="store_true",
        help="When goal context is provided, generate guide sections only for goal-relevant pages.",
    )
    parser.add_argument(
        "--crop-top-padding",
        type=int,
        default=180,
        help="Top padding in pixels when cropping step screenshots around matched UI controls.",
    )
    parser.add_argument(
        "--crop-bottom-padding",
        type=int,
        default=260,
        help="Bottom padding in pixels when cropping step screenshots around matched UI controls.",
    )
    parser.add_argument(
        "--action-runner",
        action="store_true",
        help="Use LLM to decide which links to follow on each page instead of queueing all internal links.",
    )
    return parser


def _load_business_context(args: argparse.Namespace) -> str | None:
    values: list[str] = []
    if args.business_context:
        values.append(args.business_context.strip())
    if args.business_context_file:
        values.append(Path(args.business_context_file).read_text(encoding="utf-8").strip())
    joined = "\n\n".join(value for value in values if value)
    return joined or None


def _load_goal_context(args: argparse.Namespace) -> str | None:
    values: list[str] = []
    if args.goal_context:
        values.append(args.goal_context.strip())
    if args.goal_context_file:
        values.append(Path(args.goal_context_file).read_text(encoding="utf-8").strip())
    joined = "\n\n".join(value for value in values if value)
    return joined or None


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    config = RunConfig(
        start_url=args.url,
        output_dir=Path(args.output_dir),
        depth_limit=args.depth_limit,
        provider=args.provider,
        model=args.model,
        skip_analysis=args.skip_analysis,
        headless=not args.show_browser,
        capture_overlay=not args.no_overlay,
        max_pages=args.max_pages,
        business_context=_load_business_context(args),
        browser_channel=args.browser_channel,
        browser_executable_path=args.browser_executable_path,
        show_progress=not args.quiet,
        locale=args.locale,
        output_format=args.output_format,
        goal_context=_load_goal_context(args),
        intent_only=args.intent_only,
        action_runner=args.action_runner,
        crop_top_padding=max(0, args.crop_top_padding),
        crop_bottom_padding=max(0, args.crop_bottom_padding),
    )
    try:
        result = run_pipeline(config)
    except KeyboardInterrupt:
        print("Interrupted.")
        raise SystemExit(130)

    if config.output_format in ("report", "both"):
        print(f"Report: {result.report_path}")
        print(f"Dashboard: {result.dashboard_path}")
        print(f"Sitemap JSON: {result.site_map_path}")
        print(f"Analysis JSON: {result.analysis_path}")
    
    if config.output_format in ("guide", "both"):
        print(f"Guide: {result.guide_path}")
    
    if result.errors:
        print("Errors:")
        for error in result.errors:
            print(f"- {error}")
