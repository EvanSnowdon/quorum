"""Output layer: claim labeling, source ledgers, and report assembly.

This package owns how engine artifacts are written and how the deliverable is
structured. Three concerns:

- :mod:`.claims` — the ``[DATA]`` / ``[INFERENCE]`` labeling discipline: render
  labeled claims and lint prose for unlabeled ones (Design rule 6).
- :mod:`.source_ledger` — render data-spine observations into an auditable,
  human-readable source trail for working papers and the report appendix.
- :mod:`.report` — assemble the standard ``report.md`` skeleton: executive
  summary first, body sections, then the sources, limitations, and legend
  appendices.
- :mod:`.export` — convert the rendered report to formats beyond Markdown
  (``export_report``), the hand-off point the CLI uses for non-Markdown output.

The writing side and the gate-checking side share these functions so they can
never drift: a claim rendered here is a claim the linter here will accept.
"""

from __future__ import annotations

from .claims import (
    Claim,
    ClaimLabel,
    Confidence,
    claim_from_observation,
    find_unlabeled_lines,
    format_label,
    has_label,
)
from .export import (
    KNOWN_UNIMPLEMENTED_FORMATS,
    SUPPORTED_FORMATS,
    UnsupportedFormatError,
    export_report,
    markdown_to_html,
    report_to_json,
)
from .report import (
    LABEL_LEGEND,
    ReportDocument,
    ReportMeta,
    ReportSection,
    assemble_report,
    collect_sources,
    scope_summary_line,
)
from .source_ledger import (
    format_observation,
    format_series,
    unique_source_urls,
)

__all__ = [
    "KNOWN_UNIMPLEMENTED_FORMATS",
    "LABEL_LEGEND",
    "SUPPORTED_FORMATS",
    "Claim",
    "ClaimLabel",
    "Confidence",
    "ReportDocument",
    "ReportMeta",
    "ReportSection",
    "UnsupportedFormatError",
    "assemble_report",
    "claim_from_observation",
    "collect_sources",
    "export_report",
    "scope_summary_line",
    "find_unlabeled_lines",
    "format_label",
    "format_observation",
    "format_series",
    "has_label",
    "markdown_to_html",
    "report_to_json",
    "unique_source_urls",
]
