# Web2Spec

Web2Spec is a proof-of-concept pipeline that crawls a live website, extracts a machine-readable interaction map, distills each page into LLM-friendly markdown, and uses multimodal models to generate product-facing documentation.

## What the PoC does

1. Uses Playwright to crawl a dynamic website in headless mode.
2. Extracts semantic UI structure from `<a>`, `<button>`, `<input>`, `<form>`, and `<nav>` elements.
3. Builds a bounded internal-link site map.
4. Produces cleaned markdown and screenshots for each crawled page.
5. Optionally renders bounding-box overlays to align DOM elements with screenshots.
6. Accepts optional business context for the target site so the LLM can anchor documentation in the product's purpose.
7. Sends markdown plus screenshots to Azure OpenAI, OpenAI, or Claude for:
   - Functional documentation
   - User stories
   - CTA intent analysis
8. Compiles a final `report.md`, `dashboard.html`, `site_map.json`, and `analysis.json`.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
python -m playwright install chromium
```

If the Playwright browser download fails on your machine, the crawler can use an existing local Chrome install instead. This repo already auto-detects `/Applications/Google Chrome.app` and `/Applications/Chromium.app` on macOS, or you can set `--browser-channel chrome` explicitly.

## Environment

Set one of the following before running analysis:

```bash
export AZURE_API_KEY=...
export AZURE_BASE_URL="https://<resource>.openai.azure.com/openai/v1"
export OPENAI_API_KEY=...
export ANTHROPIC_API_KEY=...
```

Azure OpenAI is the default provider. The default model is `gpt-5.4`, which should match your Azure deployment name. Override with `--model gpt-5` if you want the other deployment.

## Usage

```bash
source .venv/bin/activate
export AZURE_API_KEY="key-here"
export AZURE_BASE_URL="https://oai-hackathon-tst-swecen-001.openai.azure.com/openai/v1"

web2spec https://example.com \
  --depth-limit 2 \
  --provider azure-openai \
  --model gpt-5.4 \
  --browser-channel chrome \
  --business-context "B2B SaaS platform for collaborative product planning and analytics." \
  --output-dir outputs/example
```

Useful flags:

- `--skip-analysis`: crawl and distill only.
- `--provider openai`: use the public OpenAI API.
- `--provider anthropic`: switch to Claude.
- `--model ...`: override the default model.
- `--browser-channel chrome`: use a locally installed Chrome instead of Playwright-managed Chromium.
- `--browser-executable-path /path/to/browser`: point Playwright at an explicit browser binary.
- `--no-overlay`: skip annotated screenshots.
- `--max-pages 20`: cap crawl breadth for the PoC.
- `--business-context-file site_context.md`: load a longer business brief from disk.

## Output Layout

```text
outputs/example/
  analysis.json
  dashboard.html
  report.md
  site_map.json
  markdown/
  screenshots/
  overlays/
```

## Notes

- The crawler stays within the starting domain.
- Depth is counted from the start URL at depth `0`.
- LLM prompts explicitly request JSON-only output and forbid unsupported feature claims.
- The overlay step is optional and only runs when Pillow is available.

## Run a Crawl

1. Create and activate the virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
python -m pip install -e .[dev]
python -m playwright install chromium
```

3. Export Azure OpenAI credentials:

```bash
export AZURE_API_KEY="key-here"
export AZURE_BASE_URL="https://oai-hackathon-tst-swecen-001.openai.azure.com/openai/v1"
```

4. Prepare a short business brief. You can start from `site_context.example.md` and tailor it to the target site.

5. Run the crawler:

```bash
web2spec https://target-site.example \
  --provider azure-openai \
  --model gpt-5.4 \
  --depth-limit 2 \
  --max-pages 15 \
  --business-context-file site_context.example.md \
  --browser-channel chrome \
  --output-dir outputs/target-site
```

6. Review:

- `outputs/target-site/dashboard.html`
- `outputs/target-site/report.md`
- `outputs/target-site/site_map.json`
- `outputs/target-site/analysis.json`

If Playwright-managed Chromium is unavailable, keep `--browser-channel chrome`. This repo also auto-detects local macOS Chrome and Chromium installs.

## Suggested Workflow

1. Write a short `site_context.md` describing what the company does, who the users are, and any known conversion goals.
2. Run the crawler against the target site with a small depth limit first.
3. Review `report.md` for hallucinations, missing flows, and CTA interpretation quality.
4. Expand depth or refine the business context if the first pass is too generic.

## Which Output Should You Treat As The Basis Document?

Use the outputs differently depending on the job:

- `site_map.json`: the structural source of truth. Use this when you want the raw crawl result, semantic elements, links, headings, and screenshots represented in machine-readable form.
- `markdown/*.md`: the best pre-LLM page basis for documentation generation. This is the cleaned page representation that gets sent to the analyst prompt.
- `analysis.json`: the best structured post-LLM documentation artifact. Use this if you want to consume the generated functional docs, user stories, and intent maps programmatically.
- `report.md`: the best human-readable consolidated document for review.
- `dashboard.html`: the best human-readable visual review surface.

If the question is, "what single structured artifact should I build downstream documentation from?", the answer is usually:

1. `analysis.json` if you want the generated documentation output.
2. `site_map.json` if you want the raw crawl source of truth and plan to run your own downstream documentation generation.

## Where To Change What Gets Analyzed

There are three main places to edit depending on what you mean by "analyzed":

- `src/web2spec/cartographer.py`
  This controls what gets extracted from the live page.
  Edit `EXTRACTION_SCRIPT` if you want to capture more DOM elements, different attributes, or extra page metadata.
  Current focus is on `<a>`, `<button>`, `<input>`, `<form>`, and `<nav>`.

- `src/web2spec/distiller.py`
  This controls how the extracted structure is converted into the cleaned markdown that is sent to the LLM.
  Edit this if you want to:
  - keep more or fewer links
  - include more context text
  - change how navigation is summarized
  - alter markdown headings and section layout

- `src/web2spec/analyst.py`
  This controls the LLM reasoning step.
  Edit `SYSTEM_PROMPT` if you want to change what the model should infer, how strict it should be, or what output shape it should return.
  Edit `_build_prompt()` if you want to send additional context into the model.

## Where To Change How It Is Returned

If you want to add another returned section, for example:

- acceptance criteria
- risks
- developer notes
- test suggestions
- component inventory

then update these places together:

1. `src/web2spec/models.py`
   Add the new field to `PageAnalysis` and, if needed, add a dedicated dataclass like `CTAIntent`.

2. `src/web2spec/analyst.py`
   Update `SYSTEM_PROMPT` so the LLM knows it must return the new field.
   Update `analyze()` so the returned JSON is parsed into the new model field.

3. `src/web2spec/report.py`
   Update `build_report()` so the new field appears in `report.md`.
   Update `write_dashboard()` if you also want it shown in `dashboard.html`.

4. Optional: `tests/`
   Add or update tests so the new shape is covered.

That is the full path. In practice, the model schema, parser, and output renderers must stay aligned.

## Duplicate Analysis Guardrail

The pipeline already has a guardrail against analyzing the same page twice.

It works in three parts:

1. `src/web2spec/utils.py`
   `canonicalize_url()` normalizes URLs before the crawl loop uses them.
   This is what collapses cases like `https://docs.qmk.fm` and `https://docs.qmk.fm/`.

2. `src/web2spec/pipeline.py`
   The loop keeps a `visited` set. Once a canonical URL has been processed, it will not be processed again.

3. `src/web2spec/pipeline.py`
   Before adding newly found links to the queue, the loop also checks a `queued_urls` set so the same page is not scheduled multiple times before it is visited.

Important caveat:

- Different query strings are currently treated as different pages.
- If a site exposes the same content under multiple genuinely different URLs, those may still be crawled separately unless you add stronger canonicalization rules.

## Detailed Process

This is the full pipeline, step by step.

### 1. CLI Input Is Parsed

File:

- `src/web2spec/cli.py`

What happens:

- The user provides a start URL and optional flags like depth limit, provider, model, output directory, and business context.
- The CLI builds a `RunConfig` object.
- That config is passed into the main pipeline.

Why it matters:

- This is where you control runtime behavior without editing code.

### 2. The Pipeline Initializes State

File:

- `src/web2spec/pipeline.py`

What happens:

- The start URL is canonicalized.
- The output directory is created.
- The pipeline initializes:
  - a pending queue of URLs to crawl
  - a visited set
  - a page collection
  - an analysis collection
  - an error list

Why it matters:

- This is the orchestration layer.
- It controls the crawl loop, dedupe behavior, and artifact generation.

### 3. Playwright Launches A Browser Context

File:

- `src/web2spec/cartographer.py`

What happens:

- Playwright starts.
- A Chromium-compatible browser is launched.
- The project prefers a local installed Chromium or Chrome if available.
- A browser context is created with the configured viewport.

Why it matters:

- This is what lets the tool handle dynamic SPAs instead of just downloading HTML.

### 4. A Page Is Navigated To

File:

- `src/web2spec/cartographer.py`

What happens:

- The crawler opens a page from the queue.
- It navigates using a more tolerant strategy than strict `networkidle`:
  - first `domcontentloaded`
  - then `load`
  - then a short `networkidle` wait if available

Why it matters:

- Some sites never fully settle into a clean `networkidle` state.
- This makes crawling more robust on real-world docs sites and SPAs.

### 5. Semantic Extraction Happens In The Browser

File:

- `src/web2spec/cartographer.py`

What happens:

- `EXTRACTION_SCRIPT` runs in the page.
- It extracts:
  - title
  - headings
  - semantic interactive elements
  - metadata like `aria-label`, `id`, `name`, `placeholder`, `type`
  - rough DOM coordinates through bounding boxes

Why it matters:

- This is the raw structured crawl layer.
- It intentionally ignores most styling and focuses on behaviorally meaningful UI elements.

### 6. Internal Links Are Normalized And Filtered

Files:

- `src/web2spec/cartographer.py`
- `src/web2spec/utils.py`

What happens:

- Extracted links are resolved against the current page.
- Fragments are removed.
- External links are excluded from recursive crawling.
- Canonical URLs are used to avoid duplicate queue entries.

Why it matters:

- This is how the site tree is built.
- It is also the main guardrail against recrawling the same page under trivial URL variations.

### 7. Screenshot And Optional Overlay Are Generated

Files:

- `src/web2spec/cartographer.py`
- `src/web2spec/distiller.py`

What happens:

- A full-page screenshot is saved.
- If overlay generation is enabled, the semantic element bounding boxes are drawn on a copy of the screenshot.

Why it matters:

- The screenshot gives the multimodal model visual context.
- The overlay helps humans validate whether the extraction roughly matches what is visible.

### 8. The Distiller Converts Raw Structure Into LLM-Friendly Markdown

File:

- `src/web2spec/distiller.py`

What happens:

- The raw elements are cleaned and deduplicated.
- Large navigation blocks are compressed.
- Links are truncated to reduce token waste.
- A structured markdown representation is generated and saved to `markdown/`.

Why it matters:

- This is the main token-control layer.
- Better distillation usually improves analysis quality more than prompt tweaks.

### 9. The Analyst Sends Markdown Plus Screenshot To The LLM

File:

- `src/web2spec/analyst.py`

What happens:

- The prompt is built from:
  - the page URL
  - the title
  - the template key
  - optional business context
  - the distilled markdown
- The screenshot is attached.
- The LLM is instructed to return JSON only.

Why it matters:

- This is the reasoning layer.
- If you want different documentation outputs, this is the main place to change them.

### 10. The JSON Response Is Parsed Into A Typed Analysis Object

Files:

- `src/web2spec/analyst.py`
- `src/web2spec/models.py`

What happens:

- The model response is parsed as JSON.
- It is converted into a `PageAnalysis` object containing:
  - `functional_documentation`
  - `user_stories`
  - `intent_map`
  - `raw_response`

Why it matters:

- This is the contract between the LLM and the rest of the application.
- If this schema changes, the parser and renderers must change too.

### 11. The Crawl Loop Queues More Pages

File:

- `src/web2spec/pipeline.py`

What happens:

- The pipeline looks at the current page's internal links.
- It adds new canonical URLs to the queue if:
  - they are not already visited
  - they are not already queued
  - the depth limit has not been exceeded
  - the max-pages limit has not been exceeded

Why it matters:

- This is how recursion works.
- It is also how the PoC stays bounded.

### 12. Final Artifacts Are Written

Files:

- `src/web2spec/report.py`
- `src/web2spec/pipeline.py`

What happens:

- `site_map.json` is written from the raw page snapshots.
- `analysis.json` is written from the parsed LLM outputs.
- `report.md` is written as a readable summary.
- `dashboard.html` is generated as a visual review interface.

Why it matters:

- This is the handoff layer for users and downstream systems.

## File Map

If you want to change the system quickly, this is the shortest map:

- `src/web2spec/cli.py`: runtime flags and input handling
- `src/web2spec/config.py`: runtime configuration defaults
- `src/web2spec/utils.py`: URL normalization and shared helpers
- `src/web2spec/cartographer.py`: browser crawling and semantic extraction
- `src/web2spec/distiller.py`: markdown shaping and noise reduction
- `src/web2spec/analyst.py`: prompts, model calls, and response parsing
- `src/web2spec/models.py`: structured data contracts
- `src/web2spec/pipeline.py`: crawl loop, dedupe, recursion, progress logging
- `src/web2spec/report.py`: final output files and dashboard generation
