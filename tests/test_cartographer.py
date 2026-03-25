from web2spec.cartographer import build_template_key, extract_internal_links
from web2spec.models import SemanticElement


def test_extract_internal_links_filters_external_and_fragments() -> None:
    links = extract_internal_links(
        "https://example.com/products",
        [
            "/pricing",
            "https://example.com/about#team",
            "https://external.example.net/",
            "mailto:hello@example.com",
            "javascript:void(0)",
            "/pricing",
        ],
    )

    assert links == [
        "https://example.com/pricing",
        "https://example.com/about",
    ]


def test_build_template_key_is_stable_for_same_shape() -> None:
    elements = [
        SemanticElement(tag="button", text="Get started"),
        SemanticElement(tag="input", placeholder="Email"),
    ]
    first = build_template_key("https://example.com/signup", elements, ["Join now"])
    second = build_template_key("https://example.com/signup", elements, ["Join now"])
    assert first == second

