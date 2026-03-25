from pathlib import Path

from web2spec.models import CTAIntent, PageAnalysis, PageSnapshot
from web2spec.report import write_dashboard


def test_write_dashboard_renders_expected_sections(tmp_path: Path) -> None:
    screenshot_dir = tmp_path / "screenshots"
    screenshot_dir.mkdir()
    screenshot_path = screenshot_dir / "page.png"
    screenshot_path.write_bytes(b"png")

    overlay_dir = tmp_path / "overlays"
    overlay_dir.mkdir()
    overlay_path = overlay_dir / "page.png"
    overlay_path.write_bytes(b"png")

    page = PageSnapshot(
        url="https://example.com",
        depth=0,
        title="Example",
        headings=["Welcome"],
        elements=[],
        internal_links=["https://example.com/docs"],
        template_key="home-123",
        screenshot_path=screenshot_path,
        overlay_path=overlay_path,
        markdown="# Example",
    )
    analysis = PageAnalysis(
        url=page.url,
        functional_documentation="Home page for the product.",
        user_stories=["As a visitor, I want to learn about the product, so that I can evaluate it."],
        intent_map=[CTAIntent(cta="Get Started", why="Begin onboarding", evidence=["Primary hero CTA"])],
    )

    dashboard_path = tmp_path / "dashboard.html"
    write_dashboard(dashboard_path, "https://example.com", [page], {page.url: analysis}, [])
    dashboard = dashboard_path.read_text(encoding="utf-8")

    assert "Pulpit Web2Spec" in dashboard
    assert "Get Started" in dashboard
    assert "screenshots/page.png" in dashboard
    assert "Primary hero CTA" in dashboard
