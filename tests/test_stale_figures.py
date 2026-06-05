"""Tests for the stale-figure sweep resolver in the synthesis loop.

:func:`~quorum.quality.synthesis.resolve_stale` is the pure function that
decides what the stale-figure sweep produced: an output beginning with the
``NO STALE FIGURES`` sentinel (or saying nothing at all) resolves to ``None``
— the body is clean and no fix round runs — while a well-formed listing
parses to one entry per stale value, each carrying the old value, the
current canonical value, the section it appears in, and where. These tests
pin that contract: sentinel variants (case, whitespace, markdown emphasis,
hyphenation, singular/plural, trailing punctuation) all resolve to ``None``;
a regular listing yields the section set the orchestrator dispatches fixes
to; malformed items are skipped rather than guessed; and an output with no
well-formed entry never triggers a fix round. No model is involved.
"""

from __future__ import annotations

LISTING = (
    "STALE FIGURES:\n"
    "- 38,000 units/year by 2028 | 15,000-25,000 units/year by 2028 | "
    "Where-to-Play / How-to-Win (Entry Plays) | target-share paragraph\n"
    "- SAM of CNY 142B | SAM of CNY 119B | Market Size & Growth | "
    "closing reconciliation table\n"
)


def test_exact_sentinel_resolves_to_none() -> None:
    """The bare sentinel line means a clean body: no entries, no fix round."""
    from quorum.quality.synthesis import resolve_stale

    assert resolve_stale("NO STALE FIGURES") is None


def test_sentinel_tolerates_case_whitespace_and_emphasis() -> None:
    """Case, padding, markdown bold, hyphens, plural, and a period all pass."""
    from quorum.quality.synthesis import resolve_stale

    variants = [
        "  no stale figures  ",
        "No Stale Figures.",
        "**NO STALE FIGURES**",
        "NO-STALE-FIGURES",
        "no stale figure",
        "> NO STALE FIGURES",
    ]
    for output in variants:
        assert resolve_stale(output) is None, output


def test_sentinel_followed_by_commentary_still_resolves_to_none() -> None:
    """A leading sentinel wins even when the model appends an explanation."""
    from quorum.quality.synthesis import resolve_stale

    output = (
        "NO STALE FIGURES\n\n"
        "Every figure in the body matches the Canonical figures table."
    )
    assert resolve_stale(output) is None


def test_empty_output_resolves_to_none() -> None:
    """A model that said nothing found nothing; no fix round on silence."""
    from quorum.quality.synthesis import resolve_stale

    assert resolve_stale("") is None
    assert resolve_stale("   \n\n  ") is None


def test_regular_listing_parses_every_entry() -> None:
    """A well-formed listing yields one entry per line with all four fields."""
    from quorum.quality.synthesis import resolve_stale

    entries = resolve_stale(LISTING)
    assert entries is not None and len(entries) == 2
    first, second = entries
    assert first == {
        "old": "38,000 units/year by 2028",
        "current": "15,000-25,000 units/year by 2028",
        "section": "Where-to-Play / How-to-Win (Entry Plays)",
        "location": "target-share paragraph",
    }
    assert second["section"] == "Market Size & Growth"
    assert second["old"] == "SAM of CNY 142B"
    assert second["current"] == "SAM of CNY 119B"


def test_listing_yields_the_section_set_for_dispatch() -> None:
    """The orchestrator dispatches fixes per named section; the set is exact."""
    from quorum.quality.synthesis import resolve_stale

    entries = resolve_stale(LISTING)
    assert entries is not None
    assert {e["section"] for e in entries} == {
        "Where-to-Play / How-to-Win (Entry Plays)",
        "Market Size & Growth",
    }


def test_fields_are_stripped_of_whitespace_and_emphasis() -> None:
    """Padding and markdown emphasis around fields never reach the entries."""
    from quorum.quality.synthesis import resolve_stale

    text = (
        "Stale Figures:\n"
        "-   **38,000 units**  |  25,000 units  |  *Valuation & Economics*  "
        "|  DCF inputs table  \n"
    )
    entries = resolve_stale(text)
    assert entries == [
        {
            "old": "38,000 units",
            "current": "25,000 units",
            "section": "Valuation & Economics",
            "location": "DCF inputs table",
        }
    ]


def test_missing_location_defaults_to_empty() -> None:
    """A three-field item is valid; the location field defaults to empty."""
    from quorum.quality.synthesis import resolve_stale

    text = "STALE FIGURES:\n- CNY 142B | CNY 119B | Market Size & Growth\n"
    entries = resolve_stale(text)
    assert entries == [
        {
            "old": "CNY 142B",
            "current": "CNY 119B",
            "section": "Market Size & Growth",
            "location": "",
        }
    ]


def test_malformed_items_are_skipped_not_guessed() -> None:
    """Items with fewer than three fields, or blank fields, are dropped."""
    from quorum.quality.synthesis import resolve_stale

    text = (
        "STALE FIGURES:\n"
        "- this line has no separators at all\n"
        "- only two fields | here\n"
        "-  | CNY 119B | Market Size & Growth\n"
        "- CNY 142B | CNY 119B | Market Size & Growth | table\n"
    )
    entries = resolve_stale(text)
    assert entries is not None and len(entries) == 1
    assert entries[0]["old"] == "CNY 142B"


def test_no_wellformed_entry_resolves_to_none() -> None:
    """Prose or a listing with only malformed items must not trigger a fix."""
    from quorum.quality.synthesis import resolve_stale

    assert resolve_stale("The sweep found some issues, see above.") is None
    assert resolve_stale("STALE FIGURES:\n- nothing parseable here\n") is None


def test_sentinel_mentioned_mid_text_is_not_a_sentinel() -> None:
    """Only a *leading* sentinel resolves to ``None``; a listing whose prose
    merely quotes the phrase later still parses."""
    from quorum.quality.synthesis import resolve_stale

    text = (
        "Had the body been clean this sweep would have answered "
        "NO STALE FIGURES; it found one leftover instead.\n"
        "- CNY 142B | CNY 119B | Market Size & Growth | summary line\n"
    )
    entries = resolve_stale(text)
    assert entries is not None and len(entries) == 1
    assert entries[0]["section"] == "Market Size & Growth"
