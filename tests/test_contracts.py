"""Tests for the task contract and the effort tiers.

:class:`~quorum.analyst.TaskContract` is the four-element unit of work the
orchestrator dispatches; :data:`~quorum.orchestrator.EFFORT` is the per-tier
compute budget. These tests pin both: that a contract carries exactly its four
fields, and that the three tiers exist with a monotonically increasing analyst
headcount (``scan`` < ``standard`` < ``due_diligence``). No model is involved.
"""

from __future__ import annotations

import pytest


def test_task_contract_constructs_with_four_fields() -> None:
    """A TaskContract holds objective, output_format, tools, and boundaries."""
    from quorum.analyst import TaskContract

    contract = TaskContract(
        objective="Size the China EV market for a standard engagement.",
        output_format="A markdown section titled 'Market Size & Growth' with a TAM/SAM/SOM table.",
        tools=["worldbank", "imf", "local_context"],
        boundaries="Write only this section. At most 10 tool calls. Label every claim.",
    )
    assert contract.objective.startswith("Size the China EV market")
    assert "Market Size & Growth" in contract.output_format
    assert contract.tools == ["worldbank", "imf", "local_context"]
    assert "At most 10 tool calls" in contract.boundaries


def test_task_contract_tools_default_empty() -> None:
    """``tools`` defaults to an empty allowlist when omitted."""
    from quorum.analyst import TaskContract

    contract = TaskContract(
        objective="Assess regulatory exposure.",
        output_format="A markdown section.",
        boundaries="Stay in scope.",
    )
    assert contract.tools == []


def test_task_contract_requires_core_fields() -> None:
    """Omitting a required field is a validation error, not a silent default.

    ``objective``, ``output_format``, and ``boundaries`` have no defaults; the
    contract must fail loudly if the orchestrator forgets one.
    """
    from pydantic import ValidationError

    from quorum.analyst import TaskContract

    with pytest.raises(ValidationError):
        TaskContract(output_format="x", boundaries="y")  # missing objective


def test_effort_has_three_tiers() -> None:
    """EFFORT defines exactly the three named compute tiers."""
    from quorum.orchestrator import EFFORT

    assert set(EFFORT) == {"scan", "standard", "due_diligence"}


def test_effort_tiers_carry_budget_keys() -> None:
    """Each tier declares both a headcount cap and a per-analyst tool budget."""
    from quorum.orchestrator import EFFORT

    for tier, budget in EFFORT.items():
        assert "max_analysts" in budget, f"{tier} missing max_analysts"
        assert "tool_calls" in budget, f"{tier} missing tool_calls"
        assert budget["max_analysts"] > 0
        assert budget["tool_calls"] > 0


def test_effort_max_analysts_is_monotonic() -> None:
    """max_analysts strictly increases scan < standard < due_diligence."""
    from quorum.orchestrator import EFFORT

    scan = EFFORT["scan"]["max_analysts"]
    standard = EFFORT["standard"]["max_analysts"]
    due_diligence = EFFORT["due_diligence"]["max_analysts"]
    assert scan < standard < due_diligence, (
        f"max_analysts not monotonic: scan={scan}, standard={standard}, "
        f"due_diligence={due_diligence}"
    )


def test_effort_tool_calls_is_monotonic() -> None:
    """The per-analyst tool-call budget also rises with depth."""
    from quorum.orchestrator import EFFORT

    scan = EFFORT["scan"]["tool_calls"]
    standard = EFFORT["standard"]["tool_calls"]
    due_diligence = EFFORT["due_diligence"]["tool_calls"]
    assert scan < standard < due_diligence
