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
