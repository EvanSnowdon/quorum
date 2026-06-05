"""Quality gates: fact-check, synthesis loop, red team, chief editor.

Sequential gates stand between section drafts and the delivered report. Each
is a single function so the orchestrator can wire them into the run without
holding gate state. As of v0.2 the editor returns
:class:`~quorum.quality.editor.EditorialBlocks` — the executive summary, the
reconciliation, and the scenario analysis — and the orchestrator assembles the
deliverable in code, embedding sections and the red-team memo verbatim. v0.3
added the synthesis gate between fact-check and red team; v0.4 turns it into a
revision loop: a cross-section conflict scan
(:func:`~quorum.quality.synthesis.find_conflicts`), the supervising partner's
adjudication draft with machine-readable revision orders
(:func:`~quorum.quality.synthesis.adjudicate`, parsed by
:func:`~quorum.quality.synthesis.parse_revision_orders`), a revision round in
which the ordered seats rewrite their sections under the rulings, and the
final House View written against the revised body
(:func:`~quorum.quality.synthesis.final_house_view`), opening with the
Canonical figures table the rest of the report must follow. v0.4.1 adds a
post-red-team amendment step
(:func:`~quorum.quality.synthesis.amend_canonical`): when the red-team memo
proves a canonical-grade error (pricing basis, broken derivation, a gate
table ignoring its own coherence check), the Canonical figures and gate
tables are corrected once before the editor runs; otherwise the House View
passes through untouched. v0.5 adds the stale-figure sweep
(:func:`~quorum.quality.synthesis.stale_figures`, parsed by
:func:`~quorum.quality.synthesis.resolve_stale`): once the canonical record
is final, superseded values still stated as current in the body are listed
and fixed in one round of pin-point revision orders. v0.6 adds the
deterministic arithmetic verifier
(:mod:`~quorum.quality.arithmetic`): the valuation section's stated figures
are extracted to strict JSON (:func:`~quorum.quality.arithmetic.extract_financials`,
parsed by :func:`~quorum.quality.arithmetic.parse_financials`) and the DCF
and the SOM chain are recomputed in pure Python
(:func:`~quorum.quality.arithmetic.verify`) — a numeric conflict is settled
by re-running the arithmetic, never by a model's assertion, and the
verified-figures table is authoritative downstream. v0.6.1 extends the
verifier with deterministic economic-sanity checks (the implied exit
multiple against the section's own peer range, the mature margin against
the comparables' current margins, the disclosed unmodeled items against the
explicit-horizon NPV, the late-year volume against the SOM anchor) and adds
the Decision-NPV discipline to the synthesis loop: the Canonical figures
table designates exactly one NPV row as authoritative for the verdict, and
it must carry the disclosed unmodeled items numerically.
"""

from __future__ import annotations

from .arithmetic import (
    VerificationReport,
    extract_financials,
    parse_financials,
    verify,
)
from .editor import EditorialBlocks, compile_report
from .fact_checker import fact_check
from .red_team import challenge
from .synthesis import (
    adjudicate,
    amend_canonical,
    final_house_view,
    find_conflicts,
    parse_revision_orders,
    resolve_amendment,
    resolve_stale,
    stale_figures,
)

__all__ = [
    "fact_check",
    "extract_financials",
    "parse_financials",
    "verify",
    "VerificationReport",
    "find_conflicts",
    "adjudicate",
    "parse_revision_orders",
    "final_house_view",
    "amend_canonical",
    "resolve_amendment",
    "stale_figures",
    "resolve_stale",
    "challenge",
    "compile_report",
    "EditorialBlocks",
]
