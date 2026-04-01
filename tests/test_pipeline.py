"""Tests for action-runner URL matching and goal-relevance helpers."""
from __future__ import annotations

import pytest

from web2spec.pipeline import _extract_goal_tokens, _is_goal_relevant, _prioritize_links_for_goal
from web2spec.models import PageSnapshot, SemanticElement


# ---------------------------------------------------------------------------
# _extract_goal_tokens
# ---------------------------------------------------------------------------

def test_extract_goal_tokens_filters_stop_words() -> None:
    tokens = _extract_goal_tokens("Open a personal account for the user")
    assert "the" not in tokens
    assert "for" not in tokens
    assert "open" in tokens
    assert "personal" in tokens
    assert "account" in tokens


def test_extract_goal_tokens_empty_returns_empty() -> None:
    assert _extract_goal_tokens(None) == []
    assert _extract_goal_tokens("") == []


def test_extract_goal_tokens_deduplicates() -> None:
    tokens = _extract_goal_tokens("konto konto konto")
    assert tokens.count("konto") == 1


# ---------------------------------------------------------------------------
# _is_goal_relevant
# ---------------------------------------------------------------------------

def _make_snapshot(url="https://example.com/", title="", headings=None, markdown="") -> PageSnapshot:
    return PageSnapshot(
        url=url,
        depth=0,
        title=title,
        headings=headings or [],
        elements=[],
        internal_links=[],
        template_key="test-key",
        markdown=markdown,
    )


def test_is_goal_relevant_matches_url_token() -> None:
    snapshot = _make_snapshot(url="https://bank.pl/konto-osobiste")
    assert _is_goal_relevant(snapshot, "konto osobiste") is True


def test_is_goal_relevant_no_goal_always_true() -> None:
    snapshot = _make_snapshot()
    assert _is_goal_relevant(snapshot, None) is True
    assert _is_goal_relevant(snapshot, "") is True


def test_is_goal_relevant_unrelated_page_is_false() -> None:
    snapshot = _make_snapshot(
        url="https://bank.pl/about",
        title="About us",
        markdown="Corporate history and team.",
    )
    assert _is_goal_relevant(snapshot, "otwórz konto osobiste") is False


# ---------------------------------------------------------------------------
# _prioritize_links_for_goal (link scoring)
# ---------------------------------------------------------------------------

def test_prioritize_links_puts_goal_relevant_first() -> None:
    links = [
        "https://bank.pl/about",
        "https://bank.pl/konto-osobiste",
        "https://bank.pl/kontakt",
    ]
    ordered = _prioritize_links_for_goal(links, "konto osobiste")
    assert ordered[0] == "https://bank.pl/konto-osobiste"


def test_prioritize_links_no_goal_preserves_order() -> None:
    links = ["https://a.com/x", "https://a.com/y"]
    assert _prioritize_links_for_goal(links, None) == links


# ---------------------------------------------------------------------------
# decide_next_links URL matching  (unit-tested via helper logic)
# ---------------------------------------------------------------------------

def _match_urls(llm_urls: list[str], valid_internal: set[str], link_map: dict[str, str]) -> list[str]:
    """Mirrors the matching logic in Analyst.decide_next_links for unit testing."""
    result: list[str] = []
    for url in llm_urls:
        if url in valid_internal:
            if url not in result:
                result.append(url)
            continue
        matched = next((u for u in valid_internal if url and (u.endswith(url) or url in u)), None)
        if matched and matched not in result:
            result.append(matched)
            continue
        if url in link_map and link_map[url] not in result:
            result.append(link_map[url])
    return result


def test_match_urls_exact_match() -> None:
    valid = {"https://bank.pl/konto", "https://bank.pl/kredyt"}
    result = _match_urls(["https://bank.pl/konto"], valid, {})
    assert result == ["https://bank.pl/konto"]


def test_match_urls_suffix_match() -> None:
    valid = {"https://bank.pl/konto-osobiste"}
    result = _match_urls(["/konto-osobiste"], valid, {})
    assert result == ["https://bank.pl/konto-osobiste"]


def test_match_urls_label_reverse_lookup() -> None:
    valid = {"https://bank.pl/oferta"}
    link_map = {"Sprawdź ofertę": "https://bank.pl/oferta"}
    result = _match_urls(["Sprawdź ofertę"], valid, link_map)
    assert result == ["https://bank.pl/oferta"]


def test_match_urls_no_match_returns_empty() -> None:
    valid = {"https://bank.pl/konto"}
    result = _match_urls(["https://bank.pl/nieznane"], valid, {})
    assert result == []


def test_match_urls_deduplicates() -> None:
    valid = {"https://bank.pl/konto"}
    result = _match_urls(["https://bank.pl/konto", "/konto"], valid, {})
    assert result == ["https://bank.pl/konto"]
