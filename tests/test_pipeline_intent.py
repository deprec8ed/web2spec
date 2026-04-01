from web2spec.models import PageSnapshot, SemanticElement
from web2spec.pipeline import _extract_goal_tokens, _is_goal_relevant, _prioritize_links_for_goal


def test_extract_goal_tokens_removes_short_and_stop_words() -> None:
    tokens = _extract_goal_tokens("Open an account in polish bank and compare konto options")

    assert "open" in tokens
    assert "account" in tokens
    assert "polish" in tokens
    assert "bank" in tokens
    assert "konto" in tokens
    assert "and" not in tokens


def test_is_goal_relevant_matches_on_snapshot_content() -> None:
    snapshot = PageSnapshot(
        url="https://example.com/konta",
        depth=0,
        title="Konta osobiste",
        headings=["Otworz konto"],
        elements=[SemanticElement(tag="a", text="Otworz konto")],
        internal_links=[],
        template_key="konta-123",
        markdown="Kliknij Otworz konto aby przejsc dalej.",
    )

    assert _is_goal_relevant(snapshot, "otworz konto osobiste")
    assert not _is_goal_relevant(snapshot, "credit card travel insurance")


def test_prioritize_links_for_goal_sorts_more_relevant_first() -> None:
    links = [
        "https://example.com/contact",
        "https://example.com/konta/osobiste/otworz",
        "https://example.com/help",
    ]

    ordered = _prioritize_links_for_goal(links, "otworz konto osobiste")

    assert ordered[0] == "https://example.com/konta/osobiste/otworz"
