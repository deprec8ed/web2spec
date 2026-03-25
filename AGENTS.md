# Repository Guidelines

## Project Structure & Module Organization
Core code lives in `src/web2spec/`. Keep pipeline stages split by responsibility: `cartographer.py` handles crawl and link discovery, `distiller.py` renders markdown and overlays, `analyst.py` handles LLM analysis, and `report.py` compiles final artifacts. CLI entry points are in `cli.py` and `__main__.py`; shared config and models live in `config.py` and `models.py`. Tests live in `tests/`. Generated crawl artifacts belong in `outputs/` and should be treated as disposable run output, not hand-edited source.

## Build, Test, and Development Commands
Create a local environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
python -m playwright install chromium
```

Run the test suite with `pytest`. Run a local crawl with `web2spec https://example.com --depth-limit 2 --output-dir outputs/example`. Add `--skip-analysis` when validating crawl and distillation without calling an LLM.

## Coding Style & Naming Conventions
Target Python 3.10+ and follow the existing style: 4-space indentation, type hints, `snake_case` for functions and variables, `PascalCase` for dataclasses, and small focused modules. Prefer explicit dataclasses and plain functions over hidden state. Keep CLI flags descriptive and long-form, matching current patterns such as `--depth-limit` and `--business-context-file`. No formatter or linter is configured in `pyproject.toml`, so match surrounding code closely and keep imports and control flow tidy.

## Testing Guidelines
Use `pytest` with tests named `tests/test_*.py`. Existing tests focus on deterministic unit behavior such as URL canonicalization and markdown rendering; extend that pattern before adding broader integration coverage. New tests should cover crawl limits, link filtering, markdown output, and config-driven branches. Run `pytest` before opening a PR.

## Commit & Pull Request Guidelines
Current history uses short subject lines such as `readme modified` and `basic working cli tool`. Keep commits small and use a concise imperative summary that describes the behavior change. PRs should state the target problem, list key commands run, and note any required env vars or browser setup. Include sample output paths or screenshots when changing crawl artifacts, overlays, or report structure.

## Security & Configuration Tips
Do not commit API keys or real customer site context. Use environment variables for `AZURE_API_KEY`, `AZURE_BASE_URL`, `OPENAI_API_KEY`, and `ANTHROPIC_API_KEY`, and keep reusable context in local markdown files modeled on `site_context.example.md`.
