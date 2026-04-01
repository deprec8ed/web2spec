from pathlib import Path

from PIL import Image

from web2spec.guide import attach_focused_step_images
from web2spec.models import BoundingBox, GuideSection, GuideStep, PageSnapshot, SemanticElement


def test_attach_focused_step_images_creates_crop_from_bracket_label(tmp_path: Path) -> None:
    screenshot_path = tmp_path / "page.png"
    Image.new("RGB", (1000, 2000), color="white").save(screenshot_path)

    snapshot = PageSnapshot(
        url="https://example.com/accounts",
        depth=0,
        title="Accounts",
        headings=["Open an account"],
        elements=[
            SemanticElement(
                tag="a",
                text="Open account",
                bbox=BoundingBox(x=420, y=600, width=160, height=40),
            )
        ],
        internal_links=[],
        template_key="accounts-template",
        screenshot_path=screenshot_path,
        markdown="# Accounts",
    )

    section = GuideSection(
        url=snapshot.url,
        depth=0,
        title="Open an account",
        intro="Intro",
        steps=[
            GuideStep(
                step_number=1,
                heading="Start",
                action_bullets=["Click [Open account]"],
                what_you_see="You see the account form.",
                screenshot_path=screenshot_path,
            )
        ],
    )

    updated = attach_focused_step_images(
        section,
        snapshot,
        tmp_path / "guide_crops",
        top_padding=100,
        bottom_padding=120,
    )

    result_path = updated.steps[0].screenshot_path
    assert result_path is not None
    assert result_path.exists()
    assert result_path != screenshot_path

    with Image.open(result_path) as cropped:
        assert cropped.width == 1000
        assert cropped.height == 260


def test_attach_focused_step_images_falls_back_to_full_screenshot(tmp_path: Path) -> None:
    screenshot_path = tmp_path / "page.png"
    Image.new("RGB", (900, 1200), color="white").save(screenshot_path)

    snapshot = PageSnapshot(
        url="https://example.com/accounts",
        depth=0,
        title="Accounts",
        headings=[],
        elements=[],
        internal_links=[],
        template_key="accounts-template",
        screenshot_path=screenshot_path,
        markdown="# Accounts",
    )
    section = GuideSection(
        url=snapshot.url,
        depth=0,
        title="Open an account",
        intro="Intro",
        steps=[
            GuideStep(
                step_number=1,
                heading="Start",
                action_bullets=["Scroll down"],
                what_you_see="You see product cards.",
                screenshot_path=screenshot_path,
            )
        ],
    )

    updated = attach_focused_step_images(
        section,
        snapshot,
        tmp_path / "guide_crops",
        top_padding=100,
        bottom_padding=120,
    )

    assert updated.steps[0].screenshot_path == screenshot_path
