"""Tests for the revision-orders parser in the synthesis loop.

:func:`~quorum.quality.synthesis.parse_revision_orders` is the pure function
that turns the adjudication draft's closing ``REVISION ORDERS:`` block into a
``{section title: instruction}`` map the orchestrator dispatches as revision
contracts. These tests pin its contract: well-formed multi-line blocks parse
in full, the heading and the ``none`` sentinel tolerate case and whitespace,
a ``- none`` block and an absent block both yield an empty dict, and prose
after the block is never swallowed. No model is involved.
"""

from __future__ import annotations


def test_parses_a_regular_multi_order_block() -> None:
    """A well-formed block maps each title to its instruction, verbatim."""
    from quorum.quality.synthesis import parse_revision_orders

    text = (
        "PART 3 — Volume bridge ...\n\n"
        "REVISION ORDERS:\n"
        "- Valuation & Economics: Rebuild the DCF on Play 1's corrected "
        "revenue base of CNY 2.7B, dropping the rejected plays.\n"
        "- Strategy Quality Assessment: Re-assess the single selected play "
        "against the corrected SAM of 119B.\n"
    )
    orders = parse_revision_orders(text)
    assert orders == {
        "Valuation & Economics": (
            "Rebuild the DCF on Play 1's corrected revenue base of CNY 2.7B, "
            "dropping the rejected plays."
        ),
        "Strategy Quality Assessment": (
            "Re-assess the single selected play against the corrected SAM of "
            "119B."
        ),
    }


def test_heading_tolerates_case_whitespace_and_emphasis() -> None:
    """The heading matches case-insensitively, with padding and markdown bold."""
    from quorum.quality.synthesis import parse_revision_orders

    text = (
        "Closing remarks.\n\n"
        "  **Revision Orders:**  \n"
        "-   Where-to-Play / How-to-Win (Entry Plays) :  Narrow the section "
        "to the selected play only.\n"
    )
    orders = parse_revision_orders(text)
    assert orders == {
        "Where-to-Play / How-to-Win (Entry Plays)": (
            "Narrow the section to the selected play only."
        )
    }


def test_titles_keep_internal_colons_intact() -> None:
    """Only the first colon splits title from instruction."""
    from quorum.quality.synthesis import parse_revision_orders

    text = (
        "REVISION ORDERS:\n"
        "- Unit Economics & Profitability: Use the corrected cell cost: "
        "$85/kWh, not $70/kWh.\n"
    )
    orders = parse_revision_orders(text)
    assert orders == {
        "Unit Economics & Profitability": (
            "Use the corrected cell cost: $85/kWh, not $70/kWh."
        )
    }


def test_none_sentinel_yields_empty_dict() -> None:
    """A block carrying only the ``- none`` sentinel parses to no orders."""
    from quorum.quality.synthesis import parse_revision_orders

    assert parse_revision_orders("REVISION ORDERS:\n- none\n") == {}
    # Case, padding, a trailing period, and emphasis are tolerated.
    assert parse_revision_orders("revision orders:\n-   None.  \n") == {}
    assert parse_revision_orders("REVISION ORDERS:\n- **none**\n") == {}


def test_missing_block_yields_empty_dict() -> None:
    """An adjudication with no orders block yields no orders, not an error."""
    from quorum.quality.synthesis import parse_revision_orders

    assert parse_revision_orders("PART 1 — The selected play is Play 1.") == {}
    assert parse_revision_orders("") == {}


def test_parsing_stops_at_the_first_non_list_line() -> None:
    """Prose after the block is never swallowed into an order."""
    from quorum.quality.synthesis import parse_revision_orders

    text = (
        "REVISION ORDERS:\n"
        "- Valuation & Economics: Reprice the selected play.\n"
        "These orders are binding on the named sections.\n"
        "- Not An Order: this trailing item must not be parsed.\n"
    )
    orders = parse_revision_orders(text)
    assert orders == {"Valuation & Economics": "Reprice the selected play."}


def test_malformed_lines_are_skipped_not_guessed() -> None:
    """A list item with no colon (or an empty instruction) is dropped."""
    from quorum.quality.synthesis import parse_revision_orders

    text = (
        "REVISION ORDERS:\n"
        "- this line has no separator and is not an order\n"
        "- Market Size & Growth:   \n"
        "- Valuation & Economics: Rebuild on the corrected SAM.\n"
    )
    orders = parse_revision_orders(text)
    assert orders == {"Valuation & Economics": "Rebuild on the corrected SAM."}


def test_blank_lines_inside_the_block_are_tolerated() -> None:
    """Blank lines between orders do not end the block."""
    from quorum.quality.synthesis import parse_revision_orders

    text = (
        "REVISION ORDERS:\n\n"
        "- Valuation & Economics: Reprice the selected play.\n\n"
        "- Strategy Quality Assessment: Re-grade against the selected play.\n"
    )
    orders = parse_revision_orders(text)
    assert set(orders) == {"Valuation & Economics", "Strategy Quality Assessment"}
