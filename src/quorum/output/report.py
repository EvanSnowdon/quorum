"""Report assembly: render the deliverable ``report.md``.

The chief-editor gate owns the deliverable's prose; this module owns its
structure. It assembles the standard Quorum report skeleton — executive summary
first (pyramid principle), then the body sections, then the appendices the
product promises: a sources ledger so every figure is traceable, a claim-label
legend, and a signed limitations section. Keeping the skeleton here means the
ordering, headings, and required appendices are consistent across every
engagement and testable without invoking a model.
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
