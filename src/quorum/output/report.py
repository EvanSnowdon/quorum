"""Report assembly: render the deliverable ``report.md``.

The chief-editor gate owns the editorial blocks; this module owns the
structure and, as of v0.2, the assembly itself. :func:`assemble_report`
composes the deliverable deterministically. As of v0.3 the deliverable is a
three-part document so a reader can stop at the decision without wading
through 2,000 lines of working papers:

- **Part I — The Decision**: executive summary, the House View ruling (the
  single selected play, the adjudication of the framework recommendations,
  and the volume bridge), the scenario analysis, and the reconciliation of
  the red team's arguments.
- **Part II — Working Papers**: every fact-checked body section, embedded
  verbatim in roster order.
- **Part III — Challenge**: the red team's dissenting memo, verbatim.
- **Appendix**: a fixed client-facing "About this deliverable" method note,
  the claim-label legend, the limitations section, and a sources ledger when
  one exists.

The report title is the document's only H1; the three parts are H2 headings
and every section under a part renders one level deeper, keeping the heading
tree legal. Keeping the skeleton here means the ordering, headings, and
required appendices are consistent across every engagement and testable
without invoking a model — and no model output ceiling can truncate the body.
"""

from __future__ import annotations

import re
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

LABEL_LEGEND = (
    "Every factual claim is labeled `[DATA; confidence]` (traceable to an "
    "official source or cited reference) or `[INFERENCE; confidence]` (reasoned "
    "from labeled data, with its inputs stated). Confidence is one of high, "
    "medium, or low."
)

# Fixed client-facing method note that opens the appendix, ahead of the claims
# legend. Inserted by the assembler — never model-authored — so the description
# of how the work was produced is identical on every engagement and names no
# internal file, tool, or identifier.
ABOUT_THIS_DELIVERABLE = (
    "This report was produced by several methodology analysts drafting their "
    "sections in parallel and independently, each section then fact-checked "
    "line by line for sourcing and labeling discipline. Conflicts between "
    "sections were put before the supervising partner, whose ruling selected "
    "a single direction and ordered the affected sections revised before the "
    "view you read here was finalised. An independent red team then argued "
    "the strongest case against the report's conclusions; their dissenting "
    "memo is reproduced in full in Part III, and the response to every one of "
    "their arguments is on the record in Part I. All headline conclusions are "
    "bound to the single authoritative figures table in the House View. "
    "Headline financial figures are additionally recomputed deterministically "
    "from the section's own stated inputs; where prose and recomputation "
    "disagree, the recomputed figures prevail."
)

# Fixed lead-in under the Reconciliation heading. The reconciliation answers a
# memo the reader has not yet seen (the memo sits in Part III, two hundred
# pages later in a real deliverable); this one italic line, inserted by the
# assembler rather than authored by a model, tells the reader where the
# prosecution's case lives before the defence begins.
RECONCILIATION_LEAD_IN = (
    "*This section responds to the red team's memo, reproduced in full in "
    "Part III — Challenge. Readers who want the prosecution's case first "
    "should read Part III before this response.*"
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


# Display names for the bundled region packs, used in the report title. An
# unknown code falls back to its upper-cased form rather than failing.
REGION_DISPLAY_NAMES = {
    "cn": "China",
    "us": "the United States",
    "eu": "the European Union",
    "jp": "Japan",
    "gb": "the United Kingdom",
    "global": "Global Markets",
}


def display_region(code: str) -> str:
    """Return a human-readable region name for a pack code (``cn`` -> China)."""
    return REGION_DISPLAY_NAMES.get(code.strip().lower(), code.strip().upper())


def _strip_duplicate_title(body: str, heading: str) -> str:
    """Drop a leading Markdown heading that repeats the section's own title.

    Analysts open their working papers with an H1 title; the assembler adds
    its own section heading, which would otherwise render the title twice.
    Only a *leading* heading whose text matches the section heading
    (case-insensitively, ignoring leading hashes) is removed — everything else
    is embedded verbatim.
    """
    lines = body.strip().splitlines()
    if lines:
        first = lines[0].strip()
        # Prefix match: working-paper titles often extend the section heading
        # ("Industry Structure & Profit Pool — <engagement>"); the leading
        # heading is dropped whenever it begins with the section's title.
        if first.startswith("#") and first.lstrip("#").strip().lower().startswith(
            heading.strip().lower()
        ):
            lines = lines[1:]
            while lines and not lines[0].strip():
                lines = lines[1:]
    return "\n".join(lines).strip()


def _render_section(section: ReportSection) -> str:
    hashes = "#" * max(2, section.level)
    body = _strip_duplicate_title(section.body, section.heading)
    return f"{hashes} {section.heading}\n\n{body}"


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
    house_view: str = "",
    limitations: str = "",
    sources: list[str] | None = None,
) -> str:
    """Assemble the three-part v0.3 deliverable deterministically — no model.

    The fact-checked ``sections``, the supervising partner's ``house_view``
    ruling, and the red team's ``dissent`` memo are embedded verbatim; only
    ``executive_summary``, ``reconciliation``, and ``scenarios`` are
    editor-authored. Assembling in code is what guarantees the body can never
    be truncated by a provider's output ceiling and the dissent can never be
    paraphrased away.

    Document order: header (with a Scope Lock summary line) — Part I, The
    Decision (executive summary, House View, scenario analysis,
    reconciliation) — Part II, Working Papers (the body sections in roster
    order, rendered one heading level deeper than their declared ``level`` so
    they nest under the part) — Part III, Challenge (the dissenting view,
    verbatim) — Appendix (the fixed "About this deliverable" method note,
    claim legend, limitations, sources if any). The
    title is the document's only H1; the parts are H2. The Reconciliation
    opens with :data:`RECONCILIATION_LEAD_IN`, a fixed assembler-inserted
    line pointing the reader at the Part III memo it responds to.
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
        "## Part I — The Decision",
        "### Executive Summary\n\n"
        + _strip_duplicate_title(executive_summary, "Executive Summary"),
    ]
    if house_view.strip():
        parts.append("### House View\n\n" + _strip_duplicate_title(house_view, "House View"))
    parts.extend(
        [
            "### Scenario Analysis\n\n"
            + _strip_duplicate_title(scenarios, "Scenario Analysis"),
            f"### Reconciliation\n\n{RECONCILIATION_LEAD_IN}\n\n"
            + _strip_duplicate_title(reconciliation, "Reconciliation"),
            "## Part II — Working Papers",
            *(
                _render_section(
                    section.model_copy(update={"level": section.level + 1})
                )
                for section in sections
            ),
            "## Part III — Challenge",
            "### Dissenting View\n\n" + _strip_duplicate_title(dissent, "Dissenting View"),
            "## Appendix",
            f"### About this deliverable\n\n{ABOUT_THIS_DELIVERABLE}",
            f"### How to read the claims\n\n{LABEL_LEGEND}",
            "### Limitations\n\n"
            + (
                limitations.strip()
                or "No material limitations were recorded for this engagement."
            ),
        ]
    )
    if sources:
        lines = ["### Sources", ""]
        lines.extend(f"{i}. {source}" for i, source in enumerate(sources, start=1))
        parts.append("\n".join(lines))
    return "\n\n".join(part for part in parts if part).rstrip() + "\n"


# Field labels recognised inside a Scope Lock block, mapped to the order and
# rendering they take in the header's one-line summary. Matching is by line
# prefix after markdown decoration is stripped, case-insensitive.
_SCOPE_FIELD_LABELS = (
    "market definition",
    "denominator",
    "geographic boundary",
    "geography",
    "reference year",
    "currency",
)

_MD_EMPHASIS_RE = re.compile(r"[*_`]+")


def _clean_markdown_inline(text: str) -> str:
    """Strip markdown emphasis markers and collapse whitespace for header use."""
    return " ".join(_MD_EMPHASIS_RE.sub("", text).split()).strip()


def scope_summary_line(plan: str, max_chars: int = 240) -> str:
    """Compose a one-line Scope Lock summary for the report header.

    The engagement plan opens with a ``Scope Lock`` block (enforced by the
    engagement-manager skill) whose lines name the binding fields — market
    definition, denominator basis, reference year, currency, geographic
    boundary. This parses those field lines and joins their values into a
    clean header line such as ``NEV (BEV+PHEV+FCEV) · mainland China · ref.
    year 2024 · CNY``, with all markdown emphasis stripped.

    If no recognisable field lines are found, it falls back to the block's
    first sentence (cleaned of emphasis markers and any dangling ellipsis)
    rather than flattening the whole block and chopping it mid-token — the
    v0.2 behaviour that left broken ``**`` runs in the header. If the plan
    has no Scope Lock at all, returns an empty string and the header omits
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
    block: list[str] = []
    for line in lines[start:]:
        stripped = line.strip()
        if stripped.startswith("#"):
            break  # next heading ends the block
        if stripped:
            block.append(stripped.lstrip("-*+ ").strip())
    if not block:
        return ""

    # Parse "Label: value" field lines for the known Scope Lock fields.
    fields: dict[str, str] = {}
    for raw in block:
        cleaned = _clean_markdown_inline(raw)
        if ":" not in cleaned:
            continue
        label, _, value = cleaned.partition(":")
        label_key = label.strip().lower()
        value = value.strip()
        if not value:
            continue
        for known in _SCOPE_FIELD_LABELS:
            if label_key.startswith(known) or known in label_key:
                fields.setdefault(known, value)
                break

    pieces: list[str] = []
    if "market definition" in fields:
        pieces.append(_first_clause(fields["market definition"]))
    elif "denominator" in fields:
        pieces.append(_first_clause(fields["denominator"]))
    geography = fields.get("geographic boundary") or fields.get("geography")
    if geography:
        pieces.append(_first_clause(geography))
    if "reference year" in fields:
        pieces.append(f"ref. year {_first_clause(fields['reference year'])}")
    if "currency" in fields:
        pieces.append(_first_clause(fields["currency"]))

    if pieces:
        summary = " · ".join(pieces)
    else:
        # Fallback: the block's first sentence, cleaned — never a hard chop
        # that strands markdown markers in the header.
        first = _clean_markdown_inline(block[0])
        sentence_end = first.find(". ")
        summary = first[: sentence_end + 1] if sentence_end > 0 else first

    if len(summary) > max_chars:
        cut = summary[:max_chars].rstrip()
        # Retreat to the last separator or space so no token is split.
        for sep in (" · ", "; ", ", ", " "):
            pos = cut.rfind(sep)
            if pos > max_chars // 2:
                cut = cut[:pos]
                break
        summary = cut.rstrip(" ;,·") + " …"
    return summary.strip()


def _first_clause(value: str, max_len: int = 90) -> str:
    """Reduce a Scope Lock field value to its leading clause for the header.

    Field values in real plans run long ("New Energy Vehicles (NEVs) — defined
    as ... All market size figures use ..."): only the part before the first
    full sentence break, dash break, or semicolon belongs in a one-line
    summary. A clause still longer than ``max_len`` is cut at a word boundary
    with an explicit ellipsis — never mid-token.
    """
    clause = value
    for sep in (". ", " — ", " – ", "; "):
        pos = clause.find(sep)
        if pos > 0:
            clause = clause[:pos]
    clause = clause.strip().rstrip(".;")
    # A break inside parentheses (e.g. after an "excl." abbreviation) strands
    # an open bracket; drop the unfinished parenthetical instead.
    if clause.count("(") > clause.count(")"):
        clause = clause[: clause.rfind("(")].rstrip(" ,;")
    if len(clause) > max_len:
        # Prefer dropping a whole trailing parenthetical over cutting inside
        # one ("Mainland China (excludes Hong Kong, ...)" -> "Mainland China").
        paren = clause.find("(")
        if 0 < paren <= max_len:
            clause = clause[:paren].rstrip(" ,;")
    if len(clause) > max_len:
        cut = clause[:max_len]
        space = cut.rfind(" ")
        if space > max_len // 2:
            cut = cut[:space]
        clause = cut.rstrip(" ,;") + " …"
    return clause
