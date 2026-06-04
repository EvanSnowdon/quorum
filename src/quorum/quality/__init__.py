"""Quality gates: fact-check, red team, chief editor.

Three sequential gates stand between section drafts and the delivered report.
Each is a single function so the orchestrator can wire them into the run
without holding gate state.
"""

from __future__ import annotations

from .editor import compile_report
from .fact_checker import fact_check
from .red_team import challenge

__all__ = ["fact_check", "challenge", "compile_report"]
