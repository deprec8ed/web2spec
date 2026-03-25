from web2spec.cartographer import build_template_key, extract_internal_links
from web2spec.models import SemanticElement
from web2spec.utils import canonicalize_url, safe_filename_from_url


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


def test_canonicalize_url_collapses_trailing_slash_and_fragment() -> None:
    assert canonicalize_url("HTTPS://Example.com/docs/#intro") == "https://example.com/docs"
    assert canonicalize_url("https://example.com/") == "https://example.com/"


def test_extract_internal_links_uses_canonical_urls() -> None:
    links = extract_internal_links(
        "https://example.com/docs/",
        [
            "https://example.com/docs",
            "https://example.com/docs/",
            "https://example.com/docs#overview",
        ],
    )

    assert links == ["https://example.com/docs"]


def test_safe_filename_uses_home_for_root_path() -> None:
    assert safe_filename_from_url("https://example.com/") == "example-com-home"
