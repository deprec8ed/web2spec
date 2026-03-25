from __future__ import annotations

import json
from pathlib import Path

from .models import PageAnalysis, PageSnapshot


def write_site_map(path: Path, pages: list[PageSnapshot], errors: list[str]) -> None:
    payload = {
        "strony": [_serialize_page_snapshot(page) for page in pages],
        "błędy": errors,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_analysis(path: Path, analyses: dict[str, PageAnalysis]) -> None:
    payload = {url: _serialize_analysis(analysis) for url, analysis in analyses.items()}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_dashboard(
    path: Path,
    root_url: str,
    pages: list[PageSnapshot],
    analyses: dict[str, PageAnalysis],
    errors: list[str],
) -> None:
    page_payload = []
    for page in sorted(pages, key=lambda item: (item.depth, item.url)):
        analysis = analyses.get(page.url)
        page_payload.append(
            {
                "url": page.url,
                "depth": page.depth,
                "title": page.title,
                "template_key": page.template_key,
                "parent_url": page.parent_url,
                "markdown": page.markdown,
                "headings": page.headings,
                "internal_links": page.internal_links,
                "screenshot_path": _relative_path(path.parent, page.screenshot_path),
                "overlay_path": _relative_path(path.parent, page.overlay_path),
                "analysis": analysis.to_dict() if analysis else None,
            }
        )

    payload = {
        "root_url": root_url,
        "pages": page_payload,
        "errors": errors,
        "summary": {
            "pages_crawled": len(pages),
            "analyses_generated": len(analyses),
            "errors": len(errors),
        },
    }
    payload_json = json.dumps(payload, ensure_ascii=False)
    path.write_text(_build_dashboard_html(payload_json), encoding="utf-8")


def build_report(
    root_url: str,
    pages: list[PageSnapshot],
    analyses: dict[str, PageAnalysis],
    errors: list[str],
) -> str:
    lines = [
        "# Raport Web2Spec",
        "",
        f"- URL główny: {root_url}",
        f"- Liczba przeskanowanych stron: {len(pages)}",
        f"- Liczba wygenerowanych analiz: {len(analyses)}",
        "",
        "## Mapa strony",
        "",
    ]

    for page in sorted(pages, key=lambda item: (item.depth, item.url)):
        indent = "  " * page.depth
        lines.append(f"{indent}- {page.title} ({page.url})")

    if errors:
        lines.extend(["", "## Błędy crawlowania", ""])
        lines.extend(f"- {error}" for error in errors)

    for page in sorted(pages, key=lambda item: (item.depth, item.url)):
        analysis = analyses.get(page.url)
        lines.extend(
            [
                "",
                f"## {page.title}",
                "",
                f"- URL: {page.url}",
                f"- Szablon: {page.template_key}",
                f"- Głębokość: {page.depth}",
                f"- Zrzut ekranu: {page.screenshot_path}",
                f"- Nakładka: {page.overlay_path}",
                "",
                "### Oczyszczony Markdown",
                "",
                "```markdown",
                page.markdown.rstrip(),
                "```",
                "",
            ]
        )

        if analysis is None:
            lines.extend(["### Analiza", "", "_Pominięto lub niedostępne._", ""])
            continue

        lines.extend(
            [
                "### Dokumentacja funkcjonalna",
                "",
                analysis.functional_documentation or "_Model nie zwrócił podsumowania._",
                "",
                "### Historie użytkownika",
                "",
            ]
        )

        if analysis.user_stories:
            lines.extend(f"- {story}" for story in analysis.user_stories)
        else:
            lines.append("- _Model nie zwrócił historii użytkownika._")

        lines.extend(["", "### Mapa intencji", ""])
        if analysis.intent_map:
            for intent in analysis.intent_map:
                lines.append(f"- CTA: {intent.cta or 'Nieznane CTA'}")
                lines.append(f"  Dlaczego: {intent.why or 'Model nie zwrócił uzasadnienia.'}")
                if intent.evidence:
                    lines.append(f"  Dowody: {'; '.join(intent.evidence)}")
        else:
            lines.append("- _Model nie zwrócił analizy CTA._")

    return "\n".join(lines).strip() + "\n"


def _relative_path(base_dir: Path, value: Path | None) -> str | None:
    if value is None:
        return None
    return str(value.relative_to(base_dir))


def _serialize_page_snapshot(page: PageSnapshot) -> dict:
    return {
        "url": page.url,
        "głębokość": page.depth,
        "tytuł": page.title,
        "nagłówki": page.headings,
        "elementy": [
            {
                "tag": element.tag,
                "tekst": element.text,
                "href": element.href,
                "id_elementu": element.element_id,
                "nazwa": element.name,
                "aria_label": element.aria_label,
                "placeholder": element.placeholder,
                "typ_pola": element.input_type,
                "rola": element.role,
                "tekst_sekcji": element.section_text,
                "bbox": None
                if element.bbox is None
                else {
                    "x": element.bbox.x,
                    "y": element.bbox.y,
                    "szerokość": element.bbox.width,
                    "wysokość": element.bbox.height,
                },
            }
            for element in page.elements
        ],
        "linki_wewnętrzne": page.internal_links,
        "klucz_szablonu": page.template_key,
        "url_rodzica": page.parent_url,
        "ścieżka_zrzutu": str(page.screenshot_path) if page.screenshot_path else None,
        "ścieżka_nakładki": str(page.overlay_path) if page.overlay_path else None,
        "markdown": page.markdown,
        "reprezentant_szablonu": page.is_template_representative,
    }


def _serialize_analysis(analysis: PageAnalysis) -> dict:
    return {
        "url": analysis.url,
        "dokumentacja_funkcjonalna": analysis.functional_documentation,
        "historie_użytkownika": analysis.user_stories,
        "mapa_intencji": [
            {
                "cta": intent.cta,
                "dlaczego": intent.why,
                "dowody": intent.evidence,
            }
            for intent in analysis.intent_map
        ],
        "surowa_odpowiedź": analysis.raw_response,
    }


def _build_dashboard_html(payload_json: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Pulpit Web2Spec</title>
  <style>
    :root {{
      --bg: #f5efe4;
      --panel: #fffaf1;
      --panel-strong: #fff;
      --ink: #1e1b18;
      --muted: #6a6158;
      --accent: #c44f2a;
      --accent-2: #145b73;
      --border: #dccfbd;
      --shadow: 0 18px 50px rgba(38, 27, 16, 0.08);
      --radius: 18px;
      --mono: "SFMono-Regular", "SF Mono", Consolas, "Liberation Mono", Menlo, monospace;
      --sans: "Avenir Next", "Segoe UI", Helvetica, Arial, sans-serif;
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      font-family: var(--sans);
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(196, 79, 42, 0.18), transparent 26%),
        radial-gradient(circle at right 20%, rgba(20, 91, 115, 0.14), transparent 24%),
        linear-gradient(180deg, #f8f2e9 0%, var(--bg) 100%);
    }}

    .shell {{
      display: grid;
      grid-template-columns: 320px minmax(0, 1fr);
      min-height: 100vh;
    }}

    .sidebar {{
      border-right: 1px solid var(--border);
      background: rgba(255, 250, 241, 0.86);
      backdrop-filter: blur(18px);
      padding: 24px 18px;
      position: sticky;
      top: 0;
      height: 100vh;
      overflow: auto;
    }}

    .brand {{
      margin-bottom: 18px;
      padding: 18px;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      background: linear-gradient(135deg, rgba(196, 79, 42, 0.1), rgba(20, 91, 115, 0.08));
      box-shadow: var(--shadow);
    }}

    .brand h1 {{
      margin: 0 0 8px;
      font-size: 1.5rem;
      line-height: 1;
    }}

    .brand p,
    .meta,
    .nav-item small,
    .empty,
    .error-list li {{
      color: var(--muted);
    }}

    .stats {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin: 18px 0 22px;
    }}

    .stat {{
      padding: 12px;
      border-radius: 14px;
      background: var(--panel-strong);
      border: 1px solid var(--border);
    }}

    .stat strong {{
      display: block;
      font-size: 1.25rem;
      margin-bottom: 4px;
    }}

    .nav-list {{
      display: flex;
      flex-direction: column;
      gap: 10px;
    }}

    .nav-item {{
      border: 1px solid var(--border);
      background: var(--panel);
      border-radius: 14px;
      padding: 12px;
      cursor: pointer;
      transition: transform 120ms ease, border-color 120ms ease, background 120ms ease;
    }}

    .nav-item:hover,
    .nav-item.active {{
      transform: translateY(-1px);
      border-color: var(--accent);
      background: #fff;
    }}

    .nav-item .depth {{
      display: inline-block;
      min-width: 28px;
      font-family: var(--mono);
      font-size: 0.78rem;
      color: var(--accent-2);
    }}

    .main {{
      padding: 28px;
    }}

    .hero {{
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      gap: 18px;
      margin-bottom: 24px;
    }}

    .hero h2 {{
      margin: 0;
      font-size: clamp(2rem, 3vw, 3.4rem);
      line-height: 0.95;
      max-width: 12ch;
    }}

    .hero .meta {{
      font-size: 0.95rem;
      max-width: 56ch;
    }}

    .content {{
      display: grid;
      gap: 18px;
    }}

    .panel {{
      background: rgba(255, 250, 241, 0.9);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 18px;
      box-shadow: var(--shadow);
    }}

    .panel h3 {{
      margin: 0 0 12px;
      font-size: 1rem;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: var(--accent-2);
    }}

    .media {{
      display: grid;
      grid-template-columns: minmax(0, 1.25fr) minmax(280px, 0.75fr);
      gap: 18px;
    }}

    .image-wrap {{
      border-radius: 14px;
      overflow: hidden;
      border: 1px solid var(--border);
      background: #efe5d6;
      min-height: 240px;
    }}

    .image-wrap img {{
      display: block;
      width: 100%;
      height: auto;
    }}

    .image-toggle {{
      display: inline-flex;
      gap: 8px;
      margin-bottom: 12px;
      flex-wrap: wrap;
    }}

    .image-toggle button {{
      border: 1px solid var(--border);
      background: #fff;
      color: var(--ink);
      border-radius: 999px;
      padding: 8px 12px;
      cursor: pointer;
    }}

    .image-toggle button.active {{
      background: var(--accent);
      color: white;
      border-color: var(--accent);
    }}

    .chips {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 10px;
    }}

    .chip {{
      background: #fff;
      border: 1px solid var(--border);
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 0.86rem;
    }}

    pre, code {{
      font-family: var(--mono);
    }}

    pre {{
      margin: 0;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      background: #1f1d1a;
      color: #f7f1e8;
      padding: 16px;
      border-radius: 14px;
      max-height: 560px;
      overflow: auto;
    }}

    .story-list,
    .intent-list,
    .error-list {{
      display: grid;
      gap: 10px;
      margin: 0;
      padding-left: 20px;
    }}

    .intent-card {{
      border: 1px solid var(--border);
      background: #fff;
      border-radius: 14px;
      padding: 14px;
    }}

    .intent-card strong {{
      color: var(--accent);
    }}

    .split {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
    }}

    a {{
      color: var(--accent-2);
    }}

    @media (max-width: 1100px) {{
      .shell,
      .media,
      .split {{
        grid-template-columns: 1fr;
      }}

      .sidebar {{
        position: relative;
        height: auto;
        border-right: 0;
        border-bottom: 1px solid var(--border);
      }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <h1>Web2Spec</h1>
        <p id="root-url"></p>
      </div>
      <div class="stats" id="stats"></div>
      <div id="error-panel"></div>
      <div class="nav-list" id="page-list"></div>
    </aside>
    <main class="main">
      <div class="hero">
        <div>
          <div class="meta">Wygenerowany pulpit przeglądu crawlów</div>
          <h2 id="page-title">Brak stron</h2>
        </div>
        <div class="meta" id="page-meta"></div>
      </div>
      <div class="content" id="content"></div>
    </main>
  </div>

  <script id="payload" type="application/json">{payload_json}</script>
  <script>
    const payload = JSON.parse(document.getElementById("payload").textContent);
    const pages = payload.pages;
    let currentIndex = 0;
    let currentImage = "screenshot";

    const rootUrl = document.getElementById("root-url");
    const stats = document.getElementById("stats");
    const pageList = document.getElementById("page-list");
    const pageTitle = document.getElementById("page-title");
    const pageMeta = document.getElementById("page-meta");
    const content = document.getElementById("content");
    const errorPanel = document.getElementById("error-panel");

    rootUrl.textContent = payload.root_url;

    const statItems = [
      ["Strony", payload.summary.pages_crawled],
      ["Analizy", payload.summary.analyses_generated],
      ["Błędy", payload.summary.errors],
      ["Szablony", new Set(pages.map((page) => page.template_key)).size],
    ];
    stats.innerHTML = statItems.map(([label, value]) => `
      <div class="stat">
        <strong>${{value}}</strong>
        <span>${{label}}</span>
      </div>
    `).join("");

    if (payload.errors.length) {{
      errorPanel.innerHTML = `
        <div class="panel">
          <h3>Błędy crawlowania</h3>
          <ul class="error-list">${{payload.errors.map((error) => `<li>${{escapeHtml(error)}}</li>`).join("")}}</ul>
        </div>
      `;
    }}

    pageList.innerHTML = pages.map((page, index) => `
      <button class="nav-item" data-index="${{index}}">
        <div><span class="depth">d${{page.depth}}</span> <strong>${{escapeHtml(page.title)}}</strong></div>
        <small>${{escapeHtml(page.url)}}</small>
      </button>
    `).join("");

    pageList.addEventListener("click", (event) => {{
      const button = event.target.closest(".nav-item");
      if (!button) return;
      currentIndex = Number(button.dataset.index);
      render();
    }});

    function render() {{
      const page = pages[currentIndex];
      if (!page) {{
        content.innerHTML = '<div class="panel empty">Brak danych crawlowania.</div>';
        return;
      }}

      document.querySelectorAll(".nav-item").forEach((item, index) => {{
        item.classList.toggle("active", index === currentIndex);
      }});

      pageTitle.textContent = page.title;
      pageMeta.innerHTML = `
        <div>Głębokość ${{
          page.depth
        }} · Szablon <code>${{escapeHtml(page.template_key)}}</code></div>
        <div><a href="${{escapeAttr(page.url)}}" target="_blank" rel="noreferrer">${{escapeHtml(page.url)}}</a></div>
      `;

      const imagePath = currentImage === "overlay" && page.overlay_path ? page.overlay_path : page.screenshot_path;
      const analysis = page.analysis;
      const storyList = analysis?.user_stories?.length
        ? `<ul class="story-list">${{analysis.user_stories.map((story) => `<li>${{escapeHtml(story)}}</li>`).join("")}}</ul>`
        : '<div class="empty">Nie wygenerowano historii użytkownika.</div>';
      const intentList = analysis?.intent_map?.length
        ? analysis.intent_map.map((item) => `
            <div class="intent-card">
              <div><strong>${{escapeHtml(item.cta || "Nieznane CTA")}}</strong></div>
              <p>${{escapeHtml(item.why || "Model nie zwrócił uzasadnienia.")}}</p>
              ${{
                item.evidence?.length
                  ? `<ul class="intent-list">${{item.evidence.map((evidence) => `<li>${{escapeHtml(evidence)}}</li>`).join("")}}</ul>`
                  : ""
              }}
            </div>
          `).join("")
        : '<div class="empty">Nie wygenerowano mapy intencji.</div>';

      content.innerHTML = `
        <section class="media">
          <div class="panel">
            <div class="image-toggle">
              <button class="${{currentImage === "screenshot" ? "active" : ""}}" data-image="screenshot">Zrzut ekranu</button>
              <button class="${{currentImage === "overlay" ? "active" : ""}}" data-image="overlay" ${{
                page.overlay_path ? "" : "disabled"
              }}>Nakładka</button>
            </div>
            <div class="image-wrap">
              ${{
                imagePath
                  ? `<img src="${{escapeAttr(imagePath)}}" alt="Podgląd przechwyconej strony">`
                  : '<div class="empty" style="padding: 18px;">Brak obrazu.</div>'
              }}
            </div>
            <div class="chips">
              ${{
                page.headings.slice(0, 10).map((heading) => `<span class="chip">${{escapeHtml(heading)}}</span>`).join("")
                  || '<span class="chip">Nie przechwycono nagłówków</span>'
              }}
            </div>
          </div>
          <div class="panel">
            <h3>Dokumentacja funkcjonalna</h3>
            <p>${{escapeHtml(analysis?.functional_documentation || "Analiza została pominięta lub jest niedostępna.")}}</p>
            <div class="chips">
              <span class="chip">Linki wewnętrzne: ${{page.internal_links.length}}</span>
              <span class="chip">Nagłówki: ${{page.headings.length}}</span>
              <span class="chip">Jest analiza: ${{analysis ? "tak" : "nie"}}</span>
            </div>
          </div>
        </section>

        <section class="split">
          <div class="panel">
            <h3>Historie użytkownika</h3>
            ${{storyList}}
          </div>
          <div class="panel">
            <h3>Mapa intencji</h3>
            ${{intentList}}
          </div>
        </section>

        <section class="panel">
          <h3>Oczyszczony Markdown</h3>
          <pre>${{escapeHtml(page.markdown)}}</pre>
        </section>
      `;

      content.querySelectorAll("[data-image]").forEach((button) => {{
        button.addEventListener("click", () => {{
          currentImage = button.dataset.image;
          render();
        }});
      }});
    }}

    function escapeHtml(value) {{
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
    }}

    function escapeAttr(value) {{
      return escapeHtml(value).replaceAll("'", "&#39;");
    }}

    render();
  </script>
</body>
</html>
"""
