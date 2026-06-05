"""Tests for the two-phase dispatch configuration.

Phase semantics live in ``crews.yaml`` (an optional ``phase`` per seat) and in
the crew loader (a seat with no declared phase is phase 1). These tests pin
both: every declared phase is 1 or 2, the valuation seat runs in phase 2, and
the loader applies the phase-1 default. No model is involved.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


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


def test_declared_phases_are_one_or_two(analysts: dict) -> None:
    """Every ``phase`` declared in crews.yaml is 1 or 2 — no third phase exists."""
    offenders = {
        key: spec.get("phase")
        for key, spec in analysts.items()
        if "phase" in spec and spec["phase"] not in (1, 2)
    }
    assert not offenders, f"analysts declare phases outside {{1, 2}}: {offenders}"


def test_valuation_is_phase_two(analysts: dict) -> None:
    """The valuation seat is dispatched in phase 2.

    Valuation prices the named entry plays produced in phase 1; running it in
    phase 1 would mean valuing a strategy that does not exist yet.
    """
    valuation = analysts.get("valuation")
    assert valuation is not None, "crews.yaml has no 'valuation' seat"
    assert valuation.get("phase") == 2, "valuation must be a phase-2 seat"


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

    # Every staffed seat lands in one of the two phases.
    assert all(analyst.phase in (1, 2) for analyst in crew)

    # The declared phase-2 seat survives the loader with its phase intact.
    if "valuation" in by_key:
        assert by_key["valuation"].phase == 2
