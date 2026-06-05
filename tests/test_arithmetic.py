"""Tests for the deterministic arithmetic verifier.

:func:`~quorum.quality.arithmetic.parse_financials` and
:func:`~quorum.quality.arithmetic.verify` are the pure halves of the
arithmetic gate: parsing tolerates model slop (code fences, formatted
numbers, missing keys) and refuses to hand the verifier anything without a
recomputable core, while the verifier rebuilds the DCF and the SOM chain in
pure Python and compares the section's claims against the recomputation.
These tests pin that contract: a self-consistent DCF verifies clean; a
claimed EV several times off its own arithmetic fails with the correct
recomputed figures (the defect this gate was built for); a SOM comparison
holds on a single denominator and fails when the band and the target sit on
different SAMs; the economic-sanity layer turns an out-of-range exit
multiple and an unjustified margin premium into defects, flags unmodeled
items the explicit horizon cannot absorb and a volume trajectory beyond the
SOM anchor, and records unstated inputs as not assessable instead of
passing or failing them; and unparseable or DCF-free extractions resolve to
``None`` so the orchestrator skips the gate instead of guessing. No model
is involved.
"""

from __future__ import annotations

import math


def _dcf(claimed_ev: float, claimed_npv: float, claimed_share: float) -> dict:
    """A five-year DCF whose true arithmetic the tests recompute by hand.

    UFCF 100/150/200/250/300 at a 10% rate discounts to ~722.17; an
    undiscounted terminal value of 3,000 over five years discounts to
    ~1,862.76; EV ~2,584.93; less a 500 investment, NPV ~2,084.93; terminal
    share ~72.1%.
    """
    return {
        "currency_unit": "USD millions",
        "explicit_years": [
            {"year": 2026, "ufcf": 100.0},
            {"year": 2027, "ufcf": 150.0},
            {"year": 2028, "ufcf": 200.0},
            {"year": 2029, "ufcf": 250.0},
            {"year": 2030, "ufcf": 300.0},
        ],
        "discount_rate": 0.10,
        "terminal_value_undiscounted": 3000.0,
        "terminal_discount_years": 5,
        "initial_investment": 500.0,
        "claimed_ev": claimed_ev,
        "claimed_npv": claimed_npv,
        "claimed_terminal_share": claimed_share,
        "som_chain": {},
    }


def test_self_consistent_dcf_verifies_clean() -> None:
    """Claims matching the section's own arithmetic produce ok=True."""
    from quorum.quality.arithmetic import verify

    report = verify(_dcf(claimed_ev=2585.0, claimed_npv=2085.0, claimed_share=0.72))
    assert report.ok, report.discrepancies
    assert report.discrepancies == []
    assert math.isclose(report.recomputed["ev"], 2584.93, rel_tol=1e-3)
    assert math.isclose(report.recomputed["npv"], 2084.93, rel_tol=1e-3)
    assert math.isclose(report.recomputed["terminal_share"], 0.7206, rel_tol=1e-3)
    assert math.isclose(report.recomputed["ex_terminal_npv"], 222.17, rel_tol=1e-2)


def test_claimed_ev_far_off_fails_with_correct_recomputation() -> None:
    """An EV stated at a fraction of its own arithmetic is the return-grade
    defect this gate exists for: not ok, and the recomputed figures carry
    the authoritative values."""
    from quorum.quality.arithmetic import verify

    report = verify(_dcf(claimed_ev=1020.0, claimed_npv=520.0, claimed_share=0.72))
    assert not report.ok
    assert math.isclose(report.recomputed["ev"], 2584.93, rel_tol=1e-3)
    assert math.isclose(report.recomputed["npv"], 2084.93, rel_tol=1e-3)
    joined = " ".join(report.discrepancies)
    assert "1,020" in joined and "520" in joined
    rendered = report.markdown()
    assert "DISCREPANCIES FOUND" in rendered
    assert "2,584.9" in rendered  # the verified table carries the recomputation


def test_claims_within_tolerance_pass() -> None:
    """Rounding to the nearest published figure is not a discrepancy."""
    from quorum.quality.arithmetic import verify

    report = verify(_dcf(claimed_ev=2600.0, claimed_npv=2100.0, claimed_share=0.73))
    assert report.ok, report.discrepancies


def test_som_chain_on_a_single_denominator_holds() -> None:
    """Target and band both on the segment SAM: the comparison is valid and
    the implied shares recompute on both denominators."""
    from quorum.quality.arithmetic import verify

    report = verify(
        {
            "currency_unit": None,
            "explicit_years": [],
            "discount_rate": None,
            "terminal_value_undiscounted": None,
            "terminal_discount_years": None,
            "initial_investment": None,
            "claimed_ev": None,
            "claimed_npv": None,
            "claimed_terminal_share": None,
            "som_chain": {
                "tam": None,
                "sam_overall": 2290000.0,
                "sam_segment": 260000.0,
                "som_low": 13000.0,
                "som_high": 26000.0,
                "target_volume": 18000.0,
                "stated_share_pct": 6.9,
                "share_denominator": "segment",
            },
        }
    )
    assert report.ok, report.discrepancies
    assert report.recomputed["target_in_som_band"] is True
    assert report.recomputed["som_band_denominator"] == "segment"
    assert math.isclose(report.recomputed["target_share_of_segment"], 0.0692, rel_tol=1e-2)
    assert math.isclose(report.recomputed["target_share_of_overall"], 0.00786, rel_tol=1e-2)


def test_som_band_on_overall_sam_against_segment_target_is_a_defect() -> None:
    """A band computed on the overall SAM judging a segment-scoped play is a
    denominator mismatch even when the raw numbers overlap — the in-band
    comfort is apples to oranges."""
    from quorum.quality.arithmetic import verify

    report = verify(
        {
            "currency_unit": None,
            "explicit_years": [],
            "discount_rate": None,
            "terminal_value_undiscounted": None,
            "terminal_discount_years": None,
            "initial_investment": None,
            "claimed_ev": None,
            "claimed_npv": None,
            "claimed_terminal_share": None,
            "som_chain": {
                "tam": None,
                "sam_overall": 2290000.0,
                "sam_segment": 260000.0,
                "som_low": 22900.0,
                "som_high": 68700.0,
                "target_volume": 40000.0,  # raw value sits inside the band
                "stated_share_pct": 1.7,
                "share_denominator": "overall",
            },
        }
    )
    assert not report.ok
    assert report.recomputed["som_band_denominator"] == "overall"
    assert report.recomputed["target_in_som_band"] is False
    joined = " ".join(report.discrepancies)
    assert "Denominator mismatch" in joined
    assert "15.4%" in joined  # the single-denominator (segment) reading


def test_parse_tolerates_fences_and_formatted_numbers() -> None:
    """Code fences, thousands separators, and percent-shaped strings all
    survive parsing; missing keys default rather than fail."""
    from quorum.quality.arithmetic import parse_financials

    raw = (
        "```json\n"
        "{\n"
        '  "currency_unit": "USD millions",\n'
        '  "explicit_years": [{"year": 2026, "ufcf": "1,250"}],\n'
        '  "discount_rate": "14.2%",\n'
        '  "claimed_ev": "2,107",\n'
        '  "claimed_npv": 1607\n'
        "}\n"
        "```"
    )
    fin = parse_financials(raw)
    assert fin is not None
    assert fin["explicit_years"] == [{"year": 2026.0, "ufcf": 1250.0}]
    assert fin["discount_rate"] == 14.2  # normalised to a fraction in verify()
    assert fin["claimed_ev"] == 2107.0
    assert fin["claimed_npv"] == 1607.0
    assert fin["terminal_value_undiscounted"] is None
    assert fin["som_chain"]["share_denominator"] == "unclear"


def test_parse_rejects_non_json() -> None:
    """Prose, or output that never closes its JSON, resolves to ``None``."""
    from quorum.quality.arithmetic import parse_financials

    assert parse_financials("The section presents no usable figures.") is None
    assert parse_financials('{"claimed_ev": 2107,') is None
    assert parse_financials("") is None


def test_parse_rejects_dcf_free_extraction() -> None:
    """Valid JSON with no cash-flow series and no claimed headline value is
    a market-level valuation with no DCF: ``None``, so the gate skips."""
    from quorum.quality.arithmetic import parse_financials

    raw = (
        '{"currency_unit": null, "explicit_years": [], "discount_rate": null,'
        ' "terminal_value_undiscounted": null, "terminal_discount_years": null,'
        ' "initial_investment": null, "claimed_ev": null, "claimed_npv": null,'
        ' "claimed_terminal_share": null, "som_chain": {}}'
    )
    assert parse_financials(raw) is None


def test_parse_keeps_a_claims_only_extraction() -> None:
    """A section that states headline figures without a year-by-year build
    still parses — the verifier then recomputes what it can."""
    from quorum.quality.arithmetic import parse_financials

    fin = parse_financials('{"claimed_ev": 1020, "claimed_npv": 520}')
    assert fin is not None
    assert fin["claimed_ev"] == 1020.0
    assert fin["explicit_years"] == []


def test_verify_with_no_recomputable_inputs_recomputes_nothing() -> None:
    """Claims alone cannot be disputed: the verifier neither invents inputs
    nor fails the section — the orchestrator treats an empty recomputation
    as a skip."""
    from quorum.quality.arithmetic import verify

    report = verify(
        {
            "currency_unit": None,
            "explicit_years": [],
            "discount_rate": None,
            "terminal_value_undiscounted": None,
            "terminal_discount_years": None,
            "initial_investment": None,
            "claimed_ev": 1020.0,
            "claimed_npv": 520.0,
            "claimed_terminal_share": None,
            "som_chain": {},
        }
    )
    assert report.ok
    assert report.recomputed == {}


def test_markdown_renders_the_verified_table() -> None:
    """The rendered report carries the status, the table, and the authority
    statement the House View and the editor are bound to."""
    from quorum.quality.arithmetic import verify

    rendered = verify(
        _dcf(claimed_ev=2585.0, claimed_npv=2085.0, claimed_share=0.72)
    ).markdown()
    assert "## Arithmetic verification" in rendered
    assert "Status: VERIFIED" in rendered
    assert "| Enterprise value (EV) |" in rendered
    assert "prevail over any prose claim" in rendered


def test_exit_multiple_above_peer_range_is_a_defect() -> None:
    """An implied exit multiple above the section's own stated peer range is
    an economic-sanity defect: the report fails and the discrepancy orders
    the peer-median-anchored alternative terminal value and NPV."""
    from quorum.quality.arithmetic import verify

    fin = _dcf(claimed_ev=2585.0, claimed_npv=2085.0, claimed_share=0.72)
    fin.update(
        {
            "implied_exit_multiple": 6.7,
            "peer_multiple_median": 4.8,
            "peer_multiple_low": 3.8,
            "peer_multiple_high": 5.2,
        }
    )
    report = verify(fin)
    assert not report.ok
    joined = " ".join(report.discrepancies)
    assert "6.7x" in joined and "5.2x" in joined and "4.8x" in joined
    assert "peer median" in joined
    rendered = report.markdown()
    assert "DISCREPANCIES FOUND" in rendered


def test_mature_margin_above_all_peers_unjustified_is_a_defect() -> None:
    """A mature EBIT margin above every stated comparable's current margin
    with no structural reason fails; the same numbers with the section's
    structural reason on the record pass."""
    from quorum.quality.arithmetic import verify

    fin = _dcf(claimed_ev=2585.0, claimed_npv=2085.0, claimed_share=0.72)
    fin.update(
        {
            "base_margin_path": [
                {"year": 2026, "ebit_margin_pct": -8.0},
                {"year": 2030, "ebit_margin_pct": 15.0},
            ],
            "peer_current_margins": [
                {"name": "Peer A", "ebit_margin_pct": -4.2},
                {"name": "Peer B", "ebit_margin_pct": -11.0},
            ],
            "margin_premium_justified": False,
        }
    )
    report = verify(fin)
    assert not report.ok
    joined = " ".join(report.discrepancies)
    assert "15.0%" in joined and "Peer A" in joined
    assert "structural reason" in joined

    fin["margin_premium_justified"] = True
    justified = verify(fin)
    assert justified.ok, justified.discrepancies


def test_unmodeled_items_beyond_explicit_horizon_is_flagged() -> None:
    """Disclosed unmodeled items annualised at the low end at or above the
    explicit-horizon NPV are flagged — the report stays ok (the honest fix
    is disclosure, not a different number) but the flag is on the record."""
    from quorum.quality.arithmetic import verify

    fin = _dcf(claimed_ev=2585.0, claimed_npv=2085.0, claimed_share=0.72)
    # Recomputed ex-terminal NPV is ~222.17; 0.02 per unit x 30,000 units
    # annualises to 600, well above what the explicit horizon delivers.
    fin.update(
        {
            "unmodeled_per_vehicle_low": 0.02,
            "unmodeled_per_vehicle_high": 0.035,
            "year5_volume": 30000.0,
        }
    )
    report = verify(fin)
    assert report.ok, report.discrepancies
    joined = " ".join(report.sanity_flags)
    assert "explicit horizon cannot absorb unmodeled items" in joined
    assert math.isclose(report.recomputed["unmodeled_annualised_low"], 600.0)
    rendered = report.markdown()
    assert "Economic sanity:" in rendered
    assert "cannot absorb unmodeled items" in rendered


def test_missing_sanity_inputs_are_not_assessable_not_defects() -> None:
    """Sanity checks with unstated inputs neither pass nor fail: the report
    stays ok, nothing lands in discrepancies or flags, and every skipped
    check is recorded as not assessable in the rendered record."""
    from quorum.quality.arithmetic import verify

    report = verify(_dcf(claimed_ev=2585.0, claimed_npv=2085.0, claimed_share=0.72))
    assert report.ok
    assert report.sanity_flags == []
    assert len(report.not_assessable) == 4  # all four checks lacked inputs
    rendered = report.markdown()
    assert "Not assessable:" in rendered
    assert "implied exit multiple" in rendered
    # Volume far beyond the SOM anchor is a flag, not a defect — and only
    # when both anchors are stated.
    fin = _dcf(claimed_ev=2585.0, claimed_npv=2085.0, claimed_share=0.72)
    fin.update({"year5_volume": 30000.0, "som_year3": 9000.0})
    anchored = verify(fin)
    assert anchored.ok
    assert any("SOM anchor" in flag for flag in anchored.sanity_flags)
