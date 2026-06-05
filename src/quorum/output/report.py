"""Report assembly: render the deliverable ``report.md``.

The chief-editor gate owns the editorial blocks; this module owns the
structure and, as of v0.2, the assembly itself. :func:`assemble_report`
composes the deliverable deterministically — executive summary first (pyramid
principle), the fact-checked body sections embedded verbatim, the scenario
analysis, the reconciliation, the red team's dissent verbatim, then the
appendices: a claim-label legend, a limitations section, and a sources ledger
when one exists. Keeping the skeleton here means the ordering, headings, and
required appendices are consistent across every engagement and testable
without invoking a model — and no model output ceiling can truncate the body.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

LABEL_LEGEND = (
    "Every factual claim is labeled `[DATA; confidence]` (traceable to an "
    "official source or cited reference) or `[INFERENCE; confidence]` (reasoned "
    "from labeled data, with its inputs stated). Confidence is one of high, "
    "medium, or low."
)


class ReportSection(BaseModel):
    """One body section of a report: a heading and its Markdown content."""

    model_config = ConfigDict(extra="forbid")

    heading: str
    body: str
    level: int = 2


class ReportMeta(BaseModel):
    """Engagement identity rendered into the report header."""

    model_config = ConfigDict(extra="forbid")

    region: str
    industry: str
    depth: str
    engagement_id: str
    generated_on: date = Field(default_factory=date.today)


class ReportDocument(BaseModel):
    """A complete report ready to render to ``report.md``.

    ``executive_summary`` leads (written last but placed first). ``sections`` are
    the body in reading order. ``sources`` is the ledger of every source cited;
    ``limitations`` is the signed-off caveats section the red-team gate feeds.
    """

    model_config = ConfigDict(extra="forbid")

    meta: ReportMeta
    title: str
    executive_summary: str
    sections: list[ReportSection] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    limitations: str = ""

    def render(self) -> str:
        """Render the whole document to a Markdown string."""
        parts = [
            self._render_header(),
            self._render_summary(),
            *(_render_section(section) for section in self.sections),
            self._render_sources(),
            self._render_limitations(),
            self._render_legend(),
        ]
        return "\n\n".join(part for part in parts if part).rstrip() + "\n"

    def _render_header(self) -> str:
        meta = self.meta
        return (
            f"# {self.title}\n\n"
            f"**Region:** {meta.region}  \n"
            f"**Industry:** {meta.industry}  \n"
            f"**Depth:** {meta.depth}  \n"
            f"**Engagement:** {meta.engagement_id}  \n"
            f"**Generated:** {meta.generated_on.isoformat()}"
        )

    def _render_summary(self) -> str:
        return f"## Executive summary\n\n{self.executive_summary.strip()}"

    def _render_sources(self) -> str:
        if not self.sources:
            return "## Sources\n\nNo external sources were cited in this report."
        lines = ["## Sources", ""]
        lines.extend(f"{i}. {source}" for i, source in enumerate(self.sources, start=1))
        return "\n".join(lines)

    def _render_limitations(self) -> str:
        body = self.limitations.strip() or (
            "No material limitations were recorded for this engagement."
        )
        return f"## Limitations\n\n{body}"

    def _render_legend(self) -> str:
        return f"## How to read the claims\n\n{LABEL_LEGEND}"


def _render_section(section: ReportSection) -> str:
    hashes = "#" * max(2, section.level)
    return f"{hashes} {section.heading}\n\n{section.body.strip()}"


def collect_sources(*source_lists: list[str]) -> list[str]:
    """Merge and de-duplicate source URLs/names, preserving first-seen order.

    The orchestrator passes the source lists from each working paper; this keeps
    the report's ledger free of duplicates while remaining stable across runs.
    """
    seen: set[str] = set()
    ordered: list[str] = []
    for source_list in source_lists:
        for source in source_list:
            if source and source not in seen:
                seen.add(source)
                ordered.append(source)
    return ordered


def assemble_report(
    meta: ReportMeta,
    title: str,
    scope_summary: str,
    executive_summary: str,
    sections: list[ReportSection],
    scenarios: str,
    reconciliation: str,
    dissent: str,
    limitations: str = "",
    sources: list[str] | None = None,
) -> str:
    """Assemble the v0.2 deliverable deterministically — no model involved.

    The fact-checked ``sections`` and the red team's ``dissent`` memo are
    embedded verbatim; only ``executive_summary``, ``reconciliation``, and
    ``scenarios`` are editor-authored. Assembling in code is what guarantees
    the body can never be truncated by a provider's output ceiling and the
    dissent can never be paraphrased away.

    Top-level order: header (with a Scope Lock summary line) — executive
    summary — body sections in roster order — scenario analysis —
    reconciliation — dissenting view — appendix (claim legend, limitations,
    sources if any).
    """
    header = (
        f"# {title}\n\n"
        f"**Region:** {meta.region}  \n"
        f"**Industry:** {meta.industry}  \n"
        f"**Depth:** {meta.depth}  \n"
        f"**Engagement:** {meta.engagement_id}  \n"
        f"**Generated:** {meta.generated_on.isoformat()}"
    )
    if scope_summary.strip():
        header += f"  \n**Scope:** {scope_summary.strip()}"

    parts: list[str] = [
        header,
        f"## Executive Summary\n\n{executive_summary.strip()}",
        *(_render_section(section) for section in sections),
        f"## Scenario Analysis\n\n{scenarios.strip()}",
        f"## Reconciliation\n\n{reconciliation.strip()}",
        f"## Dissenting View\n\n{dissent.strip()}",
        "## Appendix",
        f"### How to read the claims\n\n{LABEL_LEGEND}",
        "### Limitations\n\n"
        + (
            limitations.strip()
            or "No material limitations were recorded for this engagement."
        ),
    ]
    if sources:
        lines = ["### Sources", ""]
        lines.extend(f"{i}. {source}" for i, source in enumerate(sources, start=1))
        parts.append("\n".join(lines))
    return "\n\n".join(part for part in parts if part).rstrip() + "\n"


def scope_summary_line(plan: str, max_chars: int = 240) -> str:
    """Extract a one-line Scope Lock summary from the research plan.

    The engagement plan opens with a ``Scope Lock`` block (enforced by the
    engagement-manager skill). This pulls the block's content lines and
    flattens them into a single header-friendly line, capped at ``max_chars``.
    If no Scope Lock is found, returns an empty string and the header omits
    the scope line rather than inventing one.
    """
    lines = plan.splitlines()
    start = None
    for i, line in enumerate(lines):
        if "scope lock" in line.strip().lstrip("#*- ").lower():
            start = i + 1
            break
    if start is None:
        return ""
    collected: list[str] = []
    for line in lines[start:]:
        stripped = line.strip()
        if stripped.startswith("#"):
            break  # next heading ends the block
        if stripped:
            collected.append(stripped.lstrip("-* ").strip())
    summary = "; ".join(collected)
    if len(summary) > max_chars:
        summary = summary[: max_chars - 1].rstrip() + "…"
    return summary
