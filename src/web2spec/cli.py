from __future__ import annotations

import argparse
from pathlib import Path

from .config import RunConfig
from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Przeskanuj stronę i wygeneruj ustrukturyzowane artefakty dokumentacyjne.")
    parser.add_argument("url", help="Początkowy adres URL do przeskanowania.")
    parser.add_argument("--output-dir", default="outputs/run", help="Katalog dla wygenerowanych artefaktów.")
    parser.add_argument("--depth-limit", type=int, default=2, help="Maksymalna głębokość przejścia od adresu startowego.")
    parser.add_argument(
        "--provider",
        choices=("azure-openai", "openai", "anthropic"),
        default="azure-openai",
        help="Dostawca modelu multimodalnego.",
    )
    parser.add_argument("--model", default=None, help="Nadpisz nazwę modelu.")
    parser.add_argument("--max-pages", type=int, default=20, help="Maksymalna liczba stron dodanych do kolejki w PoC.")
    parser.add_argument("--skip-analysis", action="store_true", help="Pomiń fazę analizy przez LLM.")
    parser.add_argument("--no-overlay", action="store_true", help="Pomiń generowanie zrzutów z naniesionymi obramowaniami.")
    parser.add_argument("--show-browser", action="store_true", help="Uruchom przeglądarkę w trybie z interfejsem.")
    parser.add_argument("--quiet", action="store_true", help="Ukryj logi postępu podczas crawlowania.")
    parser.add_argument(
        "--browser-channel",
        choices=("chrome", "msedge"),
        default=None,
        help="Użyj lokalnie zainstalowanej przeglądarki zamiast Chromium zarządzanego przez Playwright.",
    )
    parser.add_argument(
        "--browser-executable-path",
        default=None,
        help="Jawna ścieżka do pliku wykonywalnego przeglądarki dla Playwright.",
    )
    parser.add_argument(
        "--business-context",
        default=None,
        help="Krótki opis produktu lub biznesu, który ma ukierunkować prompt analityczny.",
    )
    parser.add_argument(
        "--business-context-file",
        default=None,
        help="Ścieżka do pliku tekstowego lub markdown z kontekstem biznesowym dla analizowanej strony.",
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
    )
    try:
        result = run_pipeline(config)
    except KeyboardInterrupt:
        print("Przerwano.")
        raise SystemExit(130)

    print(f"Raport: {result.report_path}")
    print(f"Pulpit: {result.dashboard_path}")
    print(f"Mapa strony JSON: {result.site_map_path}")
    print(f"Analiza JSON: {result.analysis_path}")
    if result.errors:
        print("Błędy:")
        for error in result.errors:
            print(f"- {error}")
