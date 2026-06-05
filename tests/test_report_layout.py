"""Tests for the three-part report layout and the scope summary line.

:func:`~quorum.output.report.assemble_report` is a pure function: given the
editorial blocks, the House View, the checked sections, and the dissent, it
must produce the v0.3 three-part document in a fixed order with a legal
heading tree. These tests assemble a report from fake data and assert the
structure — part order, House View placement, heading levels, no duplicated
section titles, the appendix at the tail — plus the rewritten
:func:`~quorum.output.report.scope_summary_line` parser. No model is involved.
"""

from __future__ import annotations

import pytest


@pytest.fixture()
def assembled() -> str:
    """A report assembled from fake data, shared across the layout tests."""
    from quorum.output.report import ReportMeta, ReportSection, assemble_report

    return assemble_report(
        meta=ReportMeta(
            region="cn",
            industry="electric vehicles",
            depth="standard",
            engagement_id="2026-06-05T0000-cn-electric-vehicles",
        ),
        title="Electric Vehicles in China — Market Report",
        scope_summary="NEV (BEV+PHEV+FCEV) · mainland China · ref. year 2024 · CNY",
        executive_summary="Entry is advisable only if the gates below are met.",
        house_view=(
            "# House View\n\nThe firm selects Play B (mid-band D2C entry).\n\n"
            "| Framework / Section | Its recommendation | Adopted / Rejected / "
            "Reframed | Reason |\n|---|---|---|---|\n"
            "| Growth Outlook (Three Horizons) | Phase entry over H1-H2 | "
            "Adopted | Matches capital plan |"
        ),
        sections=[
            ReportSection(
                heading="Market Size & Growth",
                body="# Market Size & Growth\n\nTAM is CNY 2.9T. [DATA] 0.8",
            ),
            ReportSection(
                heading="Industry Structure & Profit Pool",
                body="Rivalry is intense. [INFERENCE] 0.7",
            ),
        ],
        scenarios="Base case: 8% share by 2030 (subjective).",
        reconciliation="Argument 1: ACCEPTED; the share target is revised down.",
        dissent="# Dissenting View\n\n1. The cost advantage is unproven.",
        limitations="Findings files accompany this report.",
        sources=["CAAM 2024 sales bulletin"],
    )


def test_parts_appear_in_order(assembled: str) -> None:
    """Part I, Part II, Part III, and the Appendix appear once each, in order."""
    markers = [
        "## Part I — The Decision",
        "## Part II — Working Papers",
        "## Part III — Challenge",
        "## Appendix",
    ]
    positions = [assembled.find(marker) for marker in markers]
    assert all(pos >= 0 for pos in positions), (
        f"missing part heading(s): "
        f"{[m for m, p in zip(markers, positions) if p < 0]}"
    )
    assert positions == sorted(positions), "part headings out of order"
    for marker in markers:
        assert assembled.count(marker) == 1, f"duplicated part heading: {marker}"


def test_house_view_sits_between_summary_and_scenarios(assembled: str) -> None:
    """Within Part I, the House View follows the executive summary."""
    summary = assembled.find("### Executive Summary")
    house = assembled.find("### House View")
    scenarios = assembled.find("### Scenario Analysis")
    reconciliation = assembled.find("### Reconciliation")
    part_two = assembled.find("## Part II — Working Papers")
    assert -1 not in (summary, house, scenarios, reconciliation)
    assert summary < house < scenarios < reconciliation < part_two


def test_house_view_is_optional() -> None:
    """An empty house_view omits the heading instead of rendering a stub."""
    from quorum.output.report import ReportMeta, assemble_report

    report = assemble_report(
        meta=ReportMeta(
            region="cn", industry="x", depth="scan", engagement_id="id"
        ),
        title="X in China — Market Report",
        scope_summary="",
        executive_summary="Summary.",
        sections=[],
        scenarios="Scenarios.",
        reconciliation="Reconciliation.",
        dissent="Dissent.",
    )
    assert "### House View" not in report
    assert "## Part I — The Decision" in report


def test_sections_render_under_part_two_one_level_deeper(assembled: str) -> None:
    """Body sections render as H3 under Part II, with duplicate titles stripped."""
    part_two = assembled.find("## Part II — Working Papers")
    part_three = assembled.find("## Part III — Challenge")
    body = assembled[part_two:part_three]
    assert "### Market Size & Growth" in body
    assert "### Industry Structure & Profit Pool" in body
    # The working paper's own leading H1 title must not survive as a
    # duplicate: the heading text appears exactly once, in the assembler's H3.
    assert body.count("Market Size & Growth") == 1


def test_dissent_is_verbatim_in_part_three(assembled: str) -> None:
    """Part III carries the dissent under a single Dissenting View heading."""
    part_three = assembled.find("## Part III — Challenge")
    appendix = assembled.find("## Appendix")
    challenge = assembled[part_three:appendix]
    assert "### Dissenting View" in challenge
    assert "The cost advantage is unproven." in challenge
    # The memo's own leading title was deduplicated, not repeated.
    assert challenge.count("Dissenting View") == 1


def test_single_h1_and_appendix_tail(assembled: str) -> None:
    """The title is the only H1, and the appendix closes the document."""
    h1_lines = [
        line for line in assembled.splitlines() if line.startswith("# ")
    ]
    assert h1_lines == ["# Electric Vehicles in China — Market Report"]
    appendix = assembled.find("## Appendix")
    assert appendix > assembled.find("## Part III — Challenge")
    tail = assembled[appendix:]
    assert "### About this deliverable" in tail
    assert "### How to read the claims" in tail
    assert "### Limitations" in tail
    assert "### Sources" in tail
    assert tail.index("### About this deliverable") < tail.index(
        "### How to read the claims"
    )
    assert tail.index("### How to read the claims") < tail.index("### Limitations")


def test_about_this_deliverable_is_client_clean(assembled: str) -> None:
    """The fixed method note carries no internal path, file, or jargon leak."""
    from quorum.output.report import ABOUT_THIS_DELIVERABLE

    assert ABOUT_THIS_DELIVERABLE in assembled
    for leak in ("gates/", "engagements/", ".md", "orchestrator", "pipeline"):
        assert leak not in ABOUT_THIS_DELIVERABLE, f"internal leak: {leak}"


def test_executive_summary_precedes_working_papers(assembled: str) -> None:
    """The decision part, summary included, comes before any working paper."""
    assert assembled.find("### Executive Summary") < assembled.find(
        "## Part II — Working Papers"
    )
    assert "Entry is advisable only if the gates below are met." in assembled


def test_scope_summary_line_parses_field_lines() -> None:
    """The header summary is built from parsed Scope Lock fields, markdown-free."""
    from quorum.output.report import scope_summary_line

    plan = (
        "# Engagement Plan\n\n"
        "## Scope Lock\n\n"
        "- **Market definition & denominator basis:** New Energy Vehicles "
        "(NEVs) — defined as BEVs, PHEVs, and FCEVs. All share figures use "
        "NEV units as the denominator.\n"
        "- **Reference year:** 2024 (all figures anchor to 2024).\n"
        "- **Currency:** CNY (nominal).\n"
        "- **Geographic boundary:** Mainland China (excludes HK, Macau, "
        "Taiwan).\n"
        "- **Excluded adjacent categories:** mild hybrids; ICE vehicles.\n\n"
        "## Central Question\n\nIs the market attractive?\n"
    )
    summary = scope_summary_line(plan)
    assert "New Energy Vehicles (NEVs)" in summary
    assert "Mainland China" in summary
    assert "ref. year 2024" in summary
    assert "CNY" in summary
    assert "**" not in summary, "markdown emphasis leaked into the header line"
    assert len(summary) <= 240


def test_scope_summary_line_fallback_is_clean() -> None:
    """Without recognisable fields, the first sentence is used — no broken markdown."""
    from quorum.output.report import scope_summary_line

    plan = (
        "## Scope Lock\n\n"
        "This engagement covers **premium robotics** in Japan. Everything "
        "else in this very long block restates assumptions at length and "
        "must not be chopped mid-token into the header.\n\n"
        "## Plan\n\nDetails follow.\n"
    )
    summary = scope_summary_line(plan)
    assert summary.startswith("This engagement covers premium robotics")
    assert "**" not in summary


def test_scope_summary_line_absent_lock_returns_empty() -> None:
    """A plan with no Scope Lock yields an empty summary, not an invented one."""
    from quorum.output.report import scope_summary_line

    assert scope_summary_line("# Plan\n\nNo lock here.\n") == ""
