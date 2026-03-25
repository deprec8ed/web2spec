# Web2Spec

Web2Spec is a proof-of-concept pipeline that crawls a live website, extracts a machine-readable interaction map, distills each page into LLM-friendly markdown, and uses multimodal models to generate product-facing documentation.

It was done with pure hatred towards *vibing*, but done with it nonetheless

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
8. Compiles a final `report.md` and `site_map.json`.

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

- `outputs/target-site/report.md`
- `outputs/target-site/site_map.json`
- `outputs/target-site/analysis.json`

If Playwright-managed Chromium is unavailable, keep `--browser-channel chrome`. This repo also auto-detects local macOS Chrome and Chromium installs.

## Suggested Workflow

1. Write a short `site_context.md` describing what the company does, who the users are, and any known conversion goals.
2. Run the crawler against the target site with a small depth limit first.
3. Review `report.md` for hallucinations, missing flows, and CTA interpretation quality.
4. Expand depth or refine the business context if the first pass is too generic.
