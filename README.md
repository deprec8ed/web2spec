# Web2Spec

Web2Spec is a Playwright-based crawler that captures real pages, distills UI structure into machine-readable artifacts, and optionally uses multimodal LLM analysis to produce documentation outputs.

## What It Generates

Depending on `--output-format`, the pipeline can produce:

- `report.md`: human-readable page-by-page documentation.
- `dashboard.html`: interactive visual viewer of screenshots, markdown, and analysis.
- `site_map.json`: structured crawl output (pages, semantic elements, links, errors).
- `analysis.json`: structured LLM analysis per URL.
- `guide.docx`: procedural user guide document (section/step style).
- `markdown/`: one distilled markdown file per page.
- `screenshots/`: full-page screenshots per crawled page.
- `overlays/`: optional annotated screenshots with element bounding boxes.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .[dev]
python -m playwright install chromium
```

If Playwright-managed Chromium is unavailable, use local browser options (`--browser-channel` or `--browser-executable-path`).

## LLM Credentials

Set credentials only for the provider you use:

```bash
# Azure OpenAI
export AZURE_API_KEY=...
export AZURE_BASE_URL="https://<resource>.openai.azure.com/openai/v1"

# OpenAI
export OPENAI_API_KEY=...

# Anthropic
export ANTHROPIC_API_KEY=...
```

Defaults:

- Provider: `azure-openai`
- Model for Azure: `gpt-5.4`
- Locale: `pl`

## Quick Start

```bash
source .venv/bin/activate

web2spec https://example.com \
  --output-dir outputs/example \
  --depth-limit 2 \
  --max-pages 20 \
  --provider azure-openai \
  --model gpt-5.4 \
  --locale pl \
  --output-format both
```

## CLI Reference

Usage:

```bash
web2spec URL [options]
```

Required:

- `url` Starting URL to crawl.

General options:

- `--output-dir PATH` Output directory. Default: `outputs/run`
- `--depth-limit N` Maximum crawl depth from start URL. Default: `2`
- `--max-pages N` Maximum number of queued/visited pages. Default: `20`
- `--quiet` Suppress progress logs.

Analysis options:

- `--skip-analysis` Disable LLM analysis stage.
- `--provider azure-openai|openai|anthropic` LLM provider. Default: `azure-openai`
- `--model NAME` Override model/deployment name.
- `--business-context TEXT` Inline business context appended to prompts.
- `--business-context-file FILE` Read business context from file.
- `--locale pl|en` Localization for generated text and report fields. Default: `pl`

Output options:

- `--output-format report|guide|both` Choose output type(s). Default: `report`
- `--no-overlay` Disable generation of overlay images.

Browser options:

- `--show-browser` Run in headed mode (not headless).
- `--browser-channel chrome|msedge` Use locally installed browser channel.
- `--browser-executable-path PATH` Explicit browser executable path.

## Output Modes

`--output-format report`

- Writes: `report.md`, `dashboard.html`, `site_map.json`, `analysis.json`, plus crawl assets.

`--output-format guide`

- Writes: `guide.docx`, plus crawl assets.

`--output-format both`

- Writes both report artifacts and `guide.docx`.

Important note about `--skip-analysis`:

- No LLM call is made.
- Report files are still generated, but analysis sections are empty/skipped.
- Guide file is still generated, but it may contain no or minimal procedural content because steps are produced by LLM analysis.

## Recommended Commands

Report-only crawl:

```bash
web2spec https://target-site.example \
  --output-dir outputs/target-report \
  --depth-limit 2 \
  --output-format report
```

Guide-only crawl:

```bash
web2spec https://target-site.example \
  --output-dir outputs/target-guide \
  --depth-limit 2 \
  --output-format guide \
  --provider azure-openai
```

All artifacts in one run:

```bash
web2spec https://target-site.example \
  --output-dir outputs/target-all \
  --depth-limit 2 \
  --output-format both
```

## How To Read Results

Start with this order:

1. `dashboard.html`
   - Best first-pass visual QA.
   - Use it to compare screenshot, overlay, markdown, and analysis side by side.

2. `report.md`
   - Best narrative, page-by-page summary.
   - Good for quick review with product/stakeholder teams.

3. `analysis.json`
   - Best structured LLM output for downstream automation.
   - Includes functional documentation, user stories, intent map, and raw response.

4. `site_map.json`
   - Best source-of-truth crawl structure.
   - Includes headings, semantic elements, internal links, and asset paths.

5. `guide.docx` (if guide mode enabled)
   - Best for process-style user documentation.
   - Organized as section + numbered steps with screenshot blocks.

## Output Directory Layout

Typical `--output-format both` tree:

```text
outputs/example/
  guide.docx
  report.md
  dashboard.html
  site_map.json
  analysis.json
  markdown/
  screenshots/
  overlays/
```

## Practical Workflow

1. Start with `--depth-limit 1` or `2` and a smaller `--max-pages`.
2. Review `dashboard.html` for coverage and extraction quality.
3. Tune `--business-context` or `--business-context-file` to improve analysis focus.
4. Re-run with deeper crawl when quality is acceptable.
5. Use `--output-format guide` or `both` for user-facing procedural docs.

## Implementation Pointers

- Crawl/extraction: `src/web2spec/cartographer.py`
- Markdown distillation + overlays: `src/web2spec/distiller.py`
- LLM analysis/parsing: `src/web2spec/analyst.py`
- Report/dashboard writers: `src/web2spec/report.py`
- DOCX guide writer: `src/web2spec/guide.py`
- Pipeline orchestration: `src/web2spec/pipeline.py`
- CLI flags: `src/web2spec/cli.py`

## Known Constraints

- Crawl is constrained to the start domain.
- Depth is counted from the start URL as depth `0`.
- URL canonicalization prevents many duplicates, but distinct query-string URLs may still be treated as separate pages.
- Overlay generation requires Pillow.
- Guide quality depends on LLM availability and prompt quality when analysis is enabled.
  - semantyczne elementy interaktywne
  - metadane takie jak `aria-label`, `id`, `name`, `placeholder`, `type`
  - przybliżone współrzędne DOM przez bounding boxy

Dlaczego to ważne:

- To surowa warstwa strukturalna crawla.
- Ignoruje większość stylowania i skupia się na elementach istotnych behawioralnie.

### 6. Normalizacja i filtrowanie linków wewnętrznych

Pliki:

- `src/web2spec/cartographer.py`
- `src/web2spec/utils.py`

Co się dzieje:

- Linki są rozwijane względem bieżącej strony.
- Fragmenty są usuwane.
- Linki zewnętrzne nie są używane do rekursji.
- Kanoniczne URL-e są używane do unikania duplikatów w kolejce.

Dlaczego to ważne:

- W ten sposób budowana jest mapa strony.
- To też główny guardrail przeciw recrawlowaniu tej samej strony pod trywialnie różnymi URL-ami.

### 7. Generowanie zrzutu ekranu i opcjonalnej nakładki

Pliki:

- `src/web2spec/cartographer.py`
- `src/web2spec/distiller.py`

Co się dzieje:

- Zapisywany jest pełny zrzut ekranu strony.
- Jeśli overlay jest włączony, obramowania elementów semantycznych są rysowane na kopii zrzutu.

Dlaczego to ważne:

- Zrzut ekranu daje modelowi multimodalnemu kontekst wizualny.
- Nakładka pomaga człowiekowi zweryfikować, czy ekstrakcja mniej więcej odpowiada temu, co widać.

### 8. Distiller zamienia surową strukturę na markdown przyjazny dla LLM

Plik:

- `src/web2spec/distiller.py`

Co się dzieje:

- Surowe elementy są oczyszczane i deduplikowane.
- Duże bloki nawigacji są kompresowane.
- Liczba linków jest ograniczana, aby zmniejszyć szum tokenowy.
- Powstaje ustrukturyzowany markdown zapisywany do katalogu `markdown/`.

Dlaczego to ważne:

- To główna warstwa kontroli tokenów.
- Lepsza distylacja zwykle poprawia jakość analizy bardziej niż samo grzebanie w promptach.

### 9. Analyst wysyła markdown i zrzut ekranu do LLM

Plik:

- `src/web2spec/analyst.py`

Co się dzieje:

- Prompt jest budowany z:
  - URL-a strony
  - tytułu
  - klucza szablonu
  - opcjonalnego kontekstu biznesowego
  - oczyszczonego markdownu
- Do promptu dołączany jest zrzut ekranu.
- Model jest instruowany, by zwrócić wyłącznie JSON.

Dlaczego to ważne:

- To warstwa rozumowania.
- Jeśli chcesz innego rodzaju wyników dokumentacyjnych, to jest główne miejsce zmian.

### 10. Odpowiedź JSON jest parsowana do typu analizy

Pliki:

- `src/web2spec/analyst.py`
- `src/web2spec/models.py`

Co się dzieje:

- Odpowiedź modelu jest parsowana jako JSON.
- Zostaje zamieniona na obiekt `PageAnalysis`, który zawiera:
  - `functional_documentation`
  - `user_stories`
  - `intent_map`
  - `raw_response`

Dlaczego to ważne:

- To kontrakt między LLM a resztą aplikacji.
- Jeśli schema się zmienia, parser i renderery też muszą się zmienić.

### 11. Pętla crawla dodaje kolejne strony

Plik:

- `src/web2spec/pipeline.py`

Co się dzieje:

- Pipeline bierze linki wewnętrzne z aktualnej strony.
- Dodaje nowe kanoniczne URL-e do kolejki, jeśli:
  - nie są już odwiedzone
  - nie są już w kolejce
  - nie przekraczają limitu głębokości
  - nie przekraczają limitu `max-pages`

Dlaczego to ważne:

- W ten sposób działa rekursja.
- W ten sposób PoC pozostaje ograniczony i przewidywalny.

### 12. Zapisywane są finalne artefakty

Pliki:

- `src/web2spec/report.py`
- `src/web2spec/pipeline.py`

Co się dzieje:

- `site_map.json` powstaje z surowych snapshotów stron.
- `analysis.json` powstaje z sparsowanych wyników LLM.
- `report.md` powstaje jako czytelne podsumowanie tekstowe.
- `dashboard.html` powstaje jako wizualny interfejs przeglądowy.

Dlaczego to ważne:

- To warstwa przekazania wyników użytkownikowi i ewentualnym systemom downstream.

## Mapa plików

Jeśli chcesz coś szybko zmienić, to najkrótsza mapa wygląda tak:

- `src/web2spec/cli.py`: flagi runtime i wejście użytkownika
- `src/web2spec/config.py`: domyślne ustawienia konfiguracji
- `src/web2spec/utils.py`: normalizacja URL-i i współdzielone helpery
- `src/web2spec/cartographer.py`: crawl przeglądarkowy i ekstrakcja semantyczna
- `src/web2spec/distiller.py`: kształt markdownu i redukcja szumu
- `src/web2spec/analyst.py`: prompty, wywołania modeli i parser odpowiedzi
- `src/web2spec/models.py`: kontrakty danych
- `src/web2spec/pipeline.py`: pętla crawla, deduplikacja, rekursja, logi postępu
- `src/web2spec/report.py`: końcowe pliki wynikowe i generowanie dashboardu
