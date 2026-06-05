"""Quality gates: fact-check, red team, chief editor.

Three sequential gates stand between section drafts and the delivered report.
Each is a single function so the orchestrator can wire them into the run
without holding gate state. As of v0.2 the editor returns
:class:`~quorum.quality.editor.EditorialBlocks` — the executive summary, the
reconciliation, and the scenario analysis — and the orchestrator assembles the
deliverable in code, embedding sections and the red-team memo verbatim.
"""

from __future__ import annotations

from .editor import EditorialBlocks, compile_report
from .fact_checker import fact_check
from .red_team import challenge

__all__ = ["fact_check", "challenge", "compile_report", "EditorialBlocks"]
