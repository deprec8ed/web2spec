from __future__ import annotations

from contextlib import suppress
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urldefrag, urlsplit

from .config import RunConfig
from .models import BoundingBox, PageSnapshot, QueueItem, SemanticElement
from .utils import canonicalize_url, ensure_dir, normalize_whitespace, safe_filename_from_url, slugify

EXTRACTION_SCRIPT = """
() => {
  const normalize = (value) => (value || "").replace(/\\s+/g, " ").trim();
  const elements = Array.from(document.querySelectorAll("a, button, input, form, nav"));
  const headings = Array.from(document.querySelectorAll("h1, h2, h3"))
    .map((node) => normalize(node.innerText || node.textContent))
    .filter(Boolean)
    .slice(0, 12);

  return {
    title: normalize(document.title),
    headings,
    elements: elements.map((node) => {
      const rect = node.getBoundingClientRect();
      const section = node.closest("section, article, main, header, footer, aside, form, nav, div");
      return {
        tag: node.tagName.toLowerCase(),
        text: normalize(node.innerText || node.textContent || node.value),
        href: node.tagName.toLowerCase() === "a" ? node.href : null,
        element_id: node.id || null,
        name: node.getAttribute("name"),
        aria_label: node.getAttribute("aria-label"),
        placeholder: node.getAttribute("placeholder"),
        input_type: node.getAttribute("type"),
        role: node.getAttribute("role"),
        section_text: normalize(section ? section.innerText : "").slice(0, 280),
        bbox: rect.width > 0 && rect.height > 0 ? {
          x: Math.max(rect.x, 0),
          y: Math.max(rect.y, 0),
          width: rect.width,
          height: rect.height
        } : null
      };
    }).filter((item) => item.text || item.aria_label || item.placeholder || item.href || item.tag === "form" || item.tag === "nav")
  };
}
"""


def extract_internal_links(base_url: str, hrefs: list[str]) -> list[str]:
    base_url = canonicalize_url(base_url)
    base = urlsplit(base_url)
    internal: list[str] = []
    seen: set[str] = set()

    for href in hrefs:
        if not href or href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        absolute = urljoin(base_url, href)
        absolute, _ = urldefrag(absolute)
        parsed = urlsplit(canonicalize_url(absolute))
        if parsed.scheme not in {"http", "https"}:
            continue
        if parsed.netloc != base.netloc:
            continue
        normalized = parsed.geturl()
        if normalized not in seen:
            seen.add(normalized)
            internal.append(normalized)
    return internal


def build_template_key(url: str, elements: list[SemanticElement], headings: list[str]) -> str:
    path = urlsplit(url).path or "/"
    path_shape = re.sub(r"/\d+", "/:id", path)
    tag_signature = "|".join(
        f"{element.tag}:{element.role or ''}:{slugify(element.label())[:24]}" for element in elements[:40]
    )
    heading_signature = "|".join(slugify(heading)[:24] for heading in headings[:5])
    digest = hashlib.sha1(f"{path_shape}|{tag_signature}|{heading_signature}".encode("utf-8")).hexdigest()[:10]
    return f"{slugify(path_shape.strip('/') or 'home')}-{digest}"


class Cartographer:
    def __init__(self, config: RunConfig) -> None:
        self.config = config
        self._playwright = None
        self._browser = None
        self._context = None
        self.screenshots_dir = ensure_dir(config.output_dir / "screenshots")

    async def __aenter__(self) -> "Cartographer":
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeError("Playwright is not installed. Run `pip install -e .` and `playwright install chromium`.") from exc

        self._playwright = await async_playwright().start()
        launch_kwargs = self._launch_kwargs()
        self._browser = await self._playwright.chromium.launch(**launch_kwargs)
        self._context = await self._browser.new_context(
            viewport={
                "width": self.config.viewport_width,
                "height": self.config.viewport_height,
            }
        )
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._context is not None:
            with suppress(Exception):
                await self._context.close()
        if self._browser is not None:
            with suppress(Exception):
                await self._browser.close()
        if self._playwright is not None:
            with suppress(Exception):
                await self._playwright.stop()

    async def capture_page(self, item: QueueItem) -> PageSnapshot:
        if self._context is None:
            raise RuntimeError("Cartographer context has not been initialized.")

        page = await self._context.new_page()
        try:
            await self._navigate(page, item.url)
            current_url = canonicalize_url(page.url or item.url)
            extracted = await page.evaluate(EXTRACTION_SCRIPT)
            title = normalize_whitespace(extracted.get("title")) or current_url
            headings = [normalize_whitespace(value) for value in extracted.get("headings", []) if normalize_whitespace(value)]
            elements = [self._deserialize_element(payload) for payload in extracted.get("elements", [])]
            internal_links = extract_internal_links(current_url, [element.href or "" for element in elements])
            template_key = build_template_key(current_url, elements, headings)

            screenshot_name = f"{item.depth:02d}-{safe_filename_from_url(current_url)}.png"
            screenshot_path = self.screenshots_dir / screenshot_name
            await page.screenshot(path=str(screenshot_path), full_page=True)

            return PageSnapshot(
                url=current_url,
                depth=item.depth,
                title=title,
                headings=headings,
                elements=elements,
                internal_links=internal_links,
                template_key=template_key,
                parent_url=item.parent_url,
                screenshot_path=screenshot_path,
            )
        finally:
            with suppress(Exception):
                await page.close()

    @staticmethod
    def _deserialize_element(payload: dict) -> SemanticElement:
        bbox_payload = payload.get("bbox")
        bbox = None
        if bbox_payload:
            bbox = BoundingBox(
                x=float(bbox_payload["x"]),
                y=float(bbox_payload["y"]),
                width=float(bbox_payload["width"]),
                height=float(bbox_payload["height"]),
            )
        return SemanticElement(
            tag=payload["tag"],
            text=normalize_whitespace(payload.get("text")),
            href=payload.get("href"),
            element_id=payload.get("element_id"),
            name=payload.get("name"),
            aria_label=payload.get("aria_label"),
            placeholder=payload.get("placeholder"),
            input_type=payload.get("input_type"),
            role=payload.get("role"),
            section_text=normalize_whitespace(payload.get("section_text")),
            bbox=bbox,
        )

    def _launch_kwargs(self) -> dict:
        launch_kwargs: dict[str, object] = {"headless": self.config.headless}
        if self.config.browser_channel:
            launch_kwargs["channel"] = self.config.browser_channel
            return launch_kwargs

        if self.config.browser_executable_path:
            launch_kwargs["executable_path"] = self.config.browser_executable_path
            return launch_kwargs

        chromium_path = Path("/Applications/Chromium.app/Contents/MacOS/Chromium")
        if chromium_path.exists():
            launch_kwargs["executable_path"] = str(chromium_path)
            return launch_kwargs
        chrome_path = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        if chrome_path.exists():
            launch_kwargs["channel"] = "chrome"
            return launch_kwargs
        return launch_kwargs

    async def _navigate(self, page, url: str) -> None:
        last_error: Exception | None = None
        for wait_until in ("domcontentloaded", "load"):
            try:
                await page.goto(url, wait_until=wait_until, timeout=self.config.request_timeout_ms)
                with suppress(Exception):
                    await page.wait_for_load_state("networkidle", timeout=min(self.config.request_timeout_ms, 5_000))
                return
            except Exception as exc:
                last_error = exc
                with suppress(Exception):
                    await page.wait_for_timeout(750)

        if last_error is None:
            raise RuntimeError(f"Navigation failed for {url}")
        raise last_error


def page_snapshot_json(snapshot: PageSnapshot) -> str:
    return json.dumps(snapshot.to_dict(), indent=2)
