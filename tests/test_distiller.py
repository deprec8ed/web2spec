from pathlib import Path

from web2spec.config import RunConfig
from web2spec.distiller import Distiller
from web2spec.models import PageSnapshot, SemanticElement


def test_distiller_renders_clean_markdown(tmp_path: Path) -> None:
    config = RunConfig(
        start_url="https://example.com",
        output_dir=tmp_path,
        capture_overlay=False,
        skip_analysis=True,
        locale="en",
    )
    distiller = Distiller(config)
    snapshot = PageSnapshot(
        url="https://example.com",
        depth=0,
        title="Example Home",
        headings=["Ship faster"],
        elements=[
            SemanticElement(tag="nav", text="Docs Pricing Blog"),
            SemanticElement(tag="button", text="Get Started", aria_label="Get Started"),
            SemanticElement(tag="input", placeholder="Work email", input_type="email"),
            SemanticElement(tag="a", text="Pricing", href="https://example.com/pricing"),
        ],
        internal_links=["https://example.com/pricing"],
        template_key="home-1234567890",
    )

    distilled = distiller.distill(snapshot)

    assert "# Example Home" in distilled.markdown
    assert "## Buttons" in distilled.markdown
    assert "[Button: 'Get Started']" in distilled.markdown
    assert "https://example.com/pricing" in distilled.markdown


def test_distiller_compresses_large_nav_blocks_and_dedupes_links(tmp_path: Path) -> None:
    config = RunConfig(
        start_url="https://example.com",
        output_dir=tmp_path,
        capture_overlay=False,
        skip_analysis=True,
    )
    distiller = Distiller(config)
    long_nav = " ".join(f"Item{i}" for i in range(25))
    snapshot = PageSnapshot(
        url="https://example.com/docs",
        depth=0,
        title="Docs",
        headings=[],
        elements=[
            SemanticElement(tag="nav", text=long_nav),
            SemanticElement(tag="a", text="Docs", href="https://example.com/docs"),
            SemanticElement(tag="a", text="Docs", href="https://example.com/docs"),
        ],
        internal_links=["https://example.com/docs"],
        template_key="docs-1234567890",
    )

    distilled = distiller.distill(snapshot)

    assert "Menu nawigacyjne" in distilled.markdown
    assert distilled.markdown.count("https://example.com/docs") >= 1
    assert distilled.markdown.count("[Odnośnik: 'Docs']") == 1


def test_distiller_supports_polish_locale(tmp_path: Path) -> None:
    config = RunConfig(
        start_url="https://example.com",
        output_dir=tmp_path,
        capture_overlay=False,
        skip_analysis=True,
        locale="pl",
    )
    distiller = Distiller(config)
    snapshot = PageSnapshot(
        url="https://example.com",
        depth=0,
        title="Example Home",
        headings=["Ship faster"],
        elements=[SemanticElement(tag="button", text="Get Started", aria_label="Get Started")],
        internal_links=[],
        template_key="home-1234567890",
    )

    distilled = distiller.distill(snapshot)

    assert "## Przyciski" in distilled.markdown
    assert "[Przycisk: 'Get Started']" in distilled.markdown
