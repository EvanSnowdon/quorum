"""Tests that ``crews.yaml`` is internally consistent and on-canon.

The crew roster is the firm's org chart: every analyst seat must map to one of
the fifteen canonical methodology skills, and every seat must declare the three
fields the orchestrator reads when it staffs a crew (``role``, ``section``,
``skill``). The roster lists in each tier must reference only declared seats.
This is parsed straight from the packaged YAML — no model, no engine import
beyond locating the file.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from .conftest import CANONICAL_SKILLS

_REQUIRED_FIELDS = ("role", "section", "skill")


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


def test_every_analyst_skill_is_canonical(analysts: dict) -> None:
    """Each analyst's ``skill`` references one of the fifteen canonical skills."""
    offenders = {
        key: spec.get("skill")
        for key, spec in analysts.items()
        if spec.get("skill") not in CANONICAL_SKILLS
    }
    assert not offenders, f"analysts reference non-canonical skills: {offenders}"


def test_every_analyst_has_required_fields(analysts: dict) -> None:
    """Each analyst declares ``role``, ``section``, and ``skill``, all non-empty."""
    for key, spec in analysts.items():
        assert isinstance(spec, dict), f"analyst {key!r} is not a mapping"
        for field in _REQUIRED_FIELDS:
            value = spec.get(field)
            assert value and str(value).strip(), f"analyst {key!r} missing field {field!r}"


def test_sections_are_unique(analysts: dict) -> None:
    """No two analyst seats own the same report section.

    The orchestrator uses ``section`` as the report-section identity; a duplicate
    would mean two analysts writing the same section. crews.yaml states this
    invariant in its header, so it is enforced here.
    """
    sections = [spec["section"] for spec in analysts.values()]
    duplicates = {s for s in sections if sections.count(s) > 1}
    assert not duplicates, f"duplicate sections in crews.yaml: {duplicates}"


def test_canonical_skills_are_all_used(analysts: dict) -> None:
    """Every canonical skill is staffed by at least one seat.

    A canonical skill with no seat would be a methodology the firm ships but
    never deploys — a consistency gap between the library and the roster.
    """
    used = {spec.get("skill") for spec in analysts.values()}
    unused = CANONICAL_SKILLS - used
    assert not unused, f"canonical skills never staffed in crews.yaml: {unused}"


def test_tier_rosters_reference_declared_seats(crews: dict, analysts: dict) -> None:
    """Every key listed in a tier roster is a declared analyst seat."""
    tiers = crews.get("tiers", {})
    assert tiers, "crews.yaml has no 'tiers' mapping"
    for tier_name, tier in tiers.items():
        roster = tier.get("roster", [])
        unknown = [key for key in roster if key not in analysts]
        assert not unknown, f"tier {tier_name!r} references undeclared seats: {unknown}"


@pytest.mark.parametrize("tier_name", ["scan", "standard", "due_diligence"])
def test_each_effort_tier_has_a_roster(crews: dict, tier_name: str) -> None:
    """The three effort tiers each define a non-empty roster."""
    tiers = crews.get("tiers", {})
    tier = tiers.get(tier_name)
    assert tier, f"crews.yaml missing tier {tier_name!r}"
    roster = tier.get("roster")
    assert roster, f"tier {tier_name!r} has an empty roster"
