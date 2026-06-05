"""Tests for the three-phase dispatch configuration.

Phase semantics live in ``crews.yaml`` (an optional ``phase`` per seat) and in
the crew loader (a seat with no declared phase is phase 1). These tests pin
both: every declared phase is 1, 2, or 3 (fact base, strategy, pricing &
critique), the valuation seat runs in a later phase than the strategy-choice
seat it prices, and the loader applies the phase-1 default. No model is
involved.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

_VALID_PHASES = (1, 2, 3)


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


def test_declared_phases_are_one_two_or_three(analysts: dict) -> None:
    """Every ``phase`` declared in crews.yaml is 1, 2, or 3 — no fourth phase."""
    offenders = {
        key: spec.get("phase")
        for key, spec in analysts.items()
        if "phase" in spec and spec["phase"] not in _VALID_PHASES
    }
    assert not offenders, f"analysts declare phases outside {{1, 2, 3}}: {offenders}"


def test_valuation_runs_after_strategy_choice(analysts: dict) -> None:
    """The valuation seat is dispatched in a later phase than strategy choice.

    Valuation prices the named entry plays the strategy-choice seat proposes;
    running them in the same phase (or valuation earlier) would mean valuing a
    strategy that does not exist yet.
    """
    valuation = analysts.get("valuation")
    strategy_choice = analysts.get("strategy_choice")
    assert valuation is not None, "crews.yaml has no 'valuation' seat"
    assert strategy_choice is not None, "crews.yaml has no 'strategy_choice' seat"
    valuation_phase = int(valuation.get("phase", 1))
    strategy_phase = int(strategy_choice.get("phase", 1))
    assert valuation_phase > strategy_phase, (
        f"valuation (phase {valuation_phase}) must run after "
        f"strategy_choice (phase {strategy_phase})"
    )


def test_strategy_choice_runs_after_fact_base(analysts: dict) -> None:
    """Strategy choice is a phase-2 seat: it chooses against the checked fact base.

    The fact-base seats (sizing, structure, demand) carry no ``phase`` and so
    default to 1; strategy choice must come strictly after them.
    """
    strategy_choice = analysts.get("strategy_choice")
    assert strategy_choice is not None, "crews.yaml has no 'strategy_choice' seat"
    assert int(strategy_choice.get("phase", 1)) == 2, "strategy_choice must be phase 2"
    for fact_seat in ("market_sizing", "industry_structure", "demand_jobs"):
        spec = analysts.get(fact_seat)
        assert spec is not None, f"crews.yaml has no {fact_seat!r} seat"
        assert int(spec.get("phase", 1)) == 1, f"{fact_seat} must stay in phase 1"


def test_critics_run_in_the_critique_phase(analysts: dict) -> None:
    """The strategy critics run in phase 3, after the plays they critique exist."""
    for key in ("strategy_critic", "strategy_critic_contra"):
        spec = analysts.get(key)
        assert spec is not None, f"crews.yaml has no {key!r} seat"
        assert int(spec.get("phase", 1)) == 3, f"{key} must be a phase-3 seat"


def test_loader_defaults_missing_phase_to_one() -> None:
    """``load_crew`` builds seats with no declared ``phase`` as phase 1.

    The default lives in the loader, not the YAML: a roster written before
    phases existed must keep running as an all-phase-1 crew.
    """
    from quorum.orchestrator import ManagingPartner

    crew = ManagingPartner().load_crew("standard")
    by_key = {analyst.key: analyst for analyst in crew}

    # market_sizing declares no phase in crews.yaml; the loader must default it.
    assert "market_sizing" in by_key, "standard roster is missing market_sizing"
    assert by_key["market_sizing"].phase == 1

    # Every staffed seat lands in one of the three phases.
    assert all(analyst.phase in _VALID_PHASES for analyst in crew)

    # The declared later-phase seats survive the loader with phases intact.
    if "strategy_choice" in by_key:
        assert by_key["strategy_choice"].phase == 2
    if "valuation" in by_key:
        assert by_key["valuation"].phase == 3
