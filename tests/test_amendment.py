"""Tests for the post-red-team amendment resolver in the synthesis loop.

:func:`~quorum.quality.synthesis.resolve_amendment` is the pure function that
decides what the amendment pass produced: a model output beginning with the
``NO AMENDMENT REQUIRED`` sentinel resolves to the *original* House View,
byte-for-byte, while any substantive output is taken as the amended House
View. These tests pin that contract — sentinel variants (case, whitespace,
markdown emphasis, hyphenation, plural, trailing punctuation) all pass the
original through; an amended text replaces it; an empty output never wipes
the ruling; and a House View whose prose merely *mentions* the sentinel
phrase mid-document is not mistaken for one. No model is involved.
"""

from __future__ import annotations

ORIGINAL = (
    "## House View\n\n"
    "| Canonical figures | Value |\n|---|---|\n"
    "| SOM (at play ASP CNY 115k) | CNY 13.5B [INFERENCE] 0.6 |\n\n"
    "The firm selects Play 1.\n"
)


def test_sentinel_returns_the_original_verbatim() -> None:
    """The exact sentinel line passes the original through unchanged."""
    from quorum.quality.synthesis import resolve_amendment

    assert resolve_amendment(ORIGINAL, "NO AMENDMENT REQUIRED") == ORIGINAL


def test_sentinel_tolerates_case_whitespace_and_emphasis() -> None:
    """Case, padding, markdown bold, and a trailing period are all tolerated."""
    from quorum.quality.synthesis import resolve_amendment

    variants = [
        "  no amendment required  ",
        "No Amendment Required.",
        "**NO AMENDMENT REQUIRED**",
        "NO-AMENDMENT-REQUIRED",
        "No amendments required",
        "> NO AMENDMENT REQUIRED",
    ]
    for output in variants:
        assert resolve_amendment(ORIGINAL, output) == ORIGINAL, output


def test_sentinel_followed_by_commentary_still_resolves_to_original() -> None:
    """A leading sentinel wins even when the model appends an explanation —
    the deliverable carries the House View, never the sentinel or its gloss."""
    from quorum.quality.synthesis import resolve_amendment

    output = (
        "NO AMENDMENT REQUIRED\n\n"
        "The memo's arguments are risk judgments for the reconciliation; "
        "none demonstrates a canonical-grade error."
    )
    assert resolve_amendment(ORIGINAL, output) == ORIGINAL


def test_amended_text_replaces_the_original() -> None:
    """A substantive output is taken as the amended House View, stripped."""
    from quorum.quality.synthesis import resolve_amendment

    amended = (
        "## House View\n\n"
        "| Canonical figures | Value |\n|---|---|\n"
        "| SOM (at play ASP CNY 115k) | CNY 13.5B [INFERENCE] 0.6 |\n\n"
        "The firm selects Play 1.\n\n"
        "### Amendments after red-team review\n"
        "- SOM repriced at the play's own ASP per memo argument 2.\n"
    )
    assert resolve_amendment(ORIGINAL, f"\n{amended}\n") == amended.strip()


def test_empty_output_keeps_the_original() -> None:
    """An empty or whitespace-only output never erases the House View."""
    from quorum.quality.synthesis import resolve_amendment

    assert resolve_amendment(ORIGINAL, "") == ORIGINAL
    assert resolve_amendment(ORIGINAL, "   \n\n  ") == ORIGINAL


def test_verbatim_reemission_is_not_an_amendment() -> None:
    """A model that re-emits the original (modulo surrounding whitespace)
    resolves to the original object — callers detect amendment by equality,
    so an unchanged text must not masquerade as a change."""
    from quorum.quality.synthesis import resolve_amendment

    assert resolve_amendment(ORIGINAL, f"\n\n{ORIGINAL}\n") == ORIGINAL


def test_sentinel_mentioned_mid_text_is_not_a_sentinel() -> None:
    """Only a *leading* sentinel resolves to the original; prose that merely
    quotes the phrase later is a real amendment."""
    from quorum.quality.synthesis import resolve_amendment

    amended = (
        "## House View (amended)\n\n"
        "Had the memo proved nothing, this pass would have answered "
        "NO AMENDMENT REQUIRED; it proved a pricing-basis error instead.\n\n"
        "### Amendments after red-team review\n"
        "- Gate E removed per memo argument 4."
    )
    assert resolve_amendment(ORIGINAL, amended) == amended


def test_prefixed_judgement_before_an_amendment_is_kept() -> None:
    """A line that starts like prose ("No amendment to the play, but...")
    must not be swallowed by the sentinel match."""
    from quorum.quality.synthesis import resolve_amendment

    output = (
        "No amendment touches the selected play, but the SOM line is "
        "repriced.\n\n## House View\n...\n"
        "### Amendments after red-team review\n- Repriced per argument 2.\n"
    )
    assert resolve_amendment(ORIGINAL, output) == output.strip()
