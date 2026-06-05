"""Tests for the v0.3 staffing and prompt discipline in ``crews.yaml``.

The partner review of a standard-tier report found that the framework seats
were each publishing rival where-to-play recommendations, and that the
valuation seat's "Base" case drifted from the scenario baseline. The fixes are
encoded as roster changes (the Ansoff and Blue Ocean seats leave the standard
tier) and seat ``brief`` instructions (input-lens discipline for the framework
seats, SAM/SOM reconciliation for the strategy seat, Upside/Base naming for
the valuation seats). This module asserts those invariants hold. Parsed
straight from the packaged YAML — no model, no engine import beyond locating
the file.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

# Seats whose brief must carry the input-lens / decision-rights discipline.
_DISCIPLINED_INPUT_SEATS = (
    "growth_horizons",
    "growth_vectors",
    "market_creation",
    "firm_power",
)

# Seats removed from the standard tier in v0.3 (framework sprawl) but kept on
# the due_diligence tier under the strategy-discipline brief.
_TRIMMED_FROM_STANDARD = ("growth_vectors", "market_creation")


@pytest.fixture(scope="module")
def crews(repo_root: Path) -> dict:
    """Parse and return the packaged ``crews.yaml`` as a dict."""
    path = repo_root / "src" / "quorum" / "crews.yaml"
    assert path.is_file(), f"crews.yaml not found at {path}"
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(config, dict), "crews.yaml did not parse to a mapping"
    return config


@pytest.fixture(scope="module")
def analysts(crews: dict) -> dict:
    """The ``analysts`` mapping from crews.yaml."""
    specs = crews.get("analysts")
    assert isinstance(specs, dict) and specs, "crews.yaml has no 'analysts' mapping"
    return specs


def _roster(crews: dict, tier: str) -> list:
    tiers = crews.get("tiers", {})
    assert tier in tiers, f"crews.yaml missing tier {tier!r}"
    roster = tiers[tier].get("roster")
    assert roster, f"tier {tier!r} has an empty roster"
    return roster


def test_standard_roster_excludes_trimmed_framework_seats(crews: dict) -> None:
    """The Ansoff and Blue Ocean seats are not staffed at the standard tier.

    Partner review: at standard depth these two lenses contributed less than
    the contradictory where-to-play recommendations they introduced.
    """
    roster = _roster(crews, "standard")
    present = [seat for seat in _TRIMMED_FROM_STANDARD if seat in roster]
    assert not present, f"standard roster still staffs trimmed seats: {present}"


def test_due_diligence_roster_keeps_trimmed_framework_seats(crews: dict) -> None:
    """The trimmed seats remain on the due_diligence roster.

    They were removed from standard for framework sprawl, not retired: at
    decision-grade depth they run as input lenses under the discipline brief.
    """
    roster = _roster(crews, "due_diligence")
    missing = [seat for seat in _TRIMMED_FROM_STANDARD if seat not in roster]
    assert not missing, f"due_diligence roster lost seats: {missing}"


def test_trimmed_seats_are_still_declared_analysts(analysts: dict) -> None:
    """The trimmed seats keep their analyst declarations (skills stay staffed).

    Removing them from a roster must not orphan ``ansoff-analyst`` or
    ``blue-ocean-analyst`` — the canonical-skill coverage check depends on the
    seat definitions remaining in the ``analysts`` mapping.
    """
    missing = [seat for seat in _TRIMMED_FROM_STANDARD if seat not in analysts]
    assert not missing, f"trimmed seats no longer declared: {missing}"


@pytest.mark.parametrize(
    "seat",
    [*_DISCIPLINED_INPUT_SEATS, "strategy_choice", "valuation", "unit_economics"],
)
def test_disciplined_seats_have_nonempty_briefs(analysts: dict, seat: str) -> None:
    """Each seat carrying a v0.3 discipline rule declares a non-empty brief."""
    spec = analysts.get(seat)
    assert isinstance(spec, dict), f"analyst {seat!r} not declared"
    brief = spec.get("brief")
    assert brief and str(brief).strip(), f"analyst {seat!r} has no brief"


@pytest.mark.parametrize("seat", _DISCIPLINED_INPUT_SEATS)
def test_input_seats_briefs_carry_the_strategy_discipline(
    analysts: dict, seat: str
) -> None:
    """Framework-seat briefs route implications to the entry-strategy decision.

    The exact wording may evolve; the load-bearing phrase is the closing-list
    title the House View looks for when adjudicating the lenses.
    """
    brief = str(analysts[seat].get("brief", ""))
    assert "Implications for the entry-strategy decision" in brief, (
        f"analyst {seat!r} brief lacks the entry-strategy implications closing"
    )


def test_strategy_choice_brief_reconciles_against_sizing(analysts: dict) -> None:
    """The strategy seat's brief demands explicit SAM/SOM reconciliation."""
    brief = str(analysts["strategy_choice"].get("brief", ""))
    assert "SAM/SOM" in brief, "strategy_choice brief lacks SAM/SOM reconciliation"


@pytest.mark.parametrize("seat", ["valuation", "unit_economics"])
def test_valuation_briefs_enforce_upside_naming(analysts: dict, seat: str) -> None:
    """Valuation-seat briefs name optimistic scenarios "Upside", never "Base"."""
    brief = str(analysts[seat].get("brief", ""))
    assert "Upside" in brief, f"analyst {seat!r} brief lacks the Upside/Base rule"
