"""Synthesis gate: conflict scan, adjudication, revision orders, House View.

The framework seats deliberately run in parallel and never read each other,
which keeps them independent but lets them disagree: a real v0.2 deliverable
carried five mutually incompatible where-to-play recommendations and a
valuation whose volumes did not match the sizing section. v0.3 added the
conflict scan and a House View ruling — but the ruling lived only at the top
of the report, above sections it never changed, so a v0.3 deliverable still
shipped a DCF pricing three rejected plays under the selected play's banner
and a House View quoting a SAM its own conflict ruling had re-derived. The
partner review's verdict: the ruling must become an *input to rewriting*, not
a layer above the contradiction.

v0.4 therefore runs the gate as a loop, in four steps:

1. :func:`find_conflicts` — a forensic pass over the full set of checked
   sections that lists, with severities, where they contradict one another.
2. :func:`adjudicate` — the supervising partner's adjudication draft. Given
   the sections and the conflict list, it commits to a *single* selected
   play, rules on every conflict, adjudicates every framework recommendation
   — and closes with a machine-readable ``REVISION ORDERS:`` block naming
   every section whose content the rulings overturned and what it must fix.
3. :func:`parse_revision_orders` — a pure parser that turns the orders block
   into a ``{section title: instruction}`` map the orchestrator dispatches
   as revision contracts. The ordered seats rewrite their sections under the
   adjudication's corrected assumptions.
4. :func:`final_house_view` — once the ordered sections are revised, the
   partner writes the *final* House View against the revised body. It opens
   with a "Canonical figures" table — the single authoritative set of
   headline numbers (SAM, SOM, implied volumes, target band, corrected
   margins, key unit costs) every other part of the report must match.

All four artifacts persist under ``gates/`` and flow downstream: the red team
attacks the final ruling alongside the *revised* sections, and the editor's
executive summary is bound to the Canonical figures table rather than to
whichever stale number a pre-revision draft happened to state.

v0.4.1 closes the last structural gap the partner review found: the revision
loop ran entirely *before* the red team, so a canonical-grade error the red
team caught afterwards — a SOM priced at the market-average ASP instead of
the selected play's own ASP, spawning a phantom "structural problem" out of
the definitional gap between volume share and revenue share — had no
write-back channel. The error was flagged in Part III and never fixed in
Part I. Two measures close it: the final House View prompt now carries
denominator-discipline and band-ASP-coherence rules (prevention), and
:func:`amend_canonical` runs after the red team as a bounded, table-level
correction step (cure) — it amends the Canonical figures and gate tables when
the memo proves a canonical-grade error, and returns the House View untouched
otherwise.

v0.5 adds two disciplines the next partner review demanded. First, an
independence rule against circular sizing: a real volume bridge had derived a
segment size by dividing the play's volume target by its assumed share (one
leg still on a superseded target), then judged the target against the SOM
built on it — the rule now binds the adjudication, the final House View, the
conflict scan (class f), the fact-checker, and the sizing skill. Second, a
stale-figure sweep (:func:`stale_figures` / :func:`resolve_stale`): after the
House View (and its amendment, when one occurs) is final, the sweep lists
superseded values still stated as current in the body; the orchestrator
turns the list into one round of pin-point revision orders confined to the
named sections.

v0.6 subordinates the loop's prose to deterministic arithmetic. A real
deliverable carried three enterprise values in one valuation section — the
DCF table's own 2,107M, an unsupported 1,020M quoted by the summary and the
verdict, and a stray 4,213M — and the reconciliation layer endorsed the
wrong one by asserting the recomputable figure was "old". The arithmetic
verifier (:mod:`~quorum.quality.arithmetic`) now recomputes the DCF and the
SOM chain in pure Python before the synthesis loop runs; its
verified-figures table enters :func:`final_house_view` as a mandatory input
(the ``arithmetic`` parameter) under the rule that recomputed figures
outrank prose, and a share-of-what discipline binds the House View, the
amendment pass, the conflict scan's core-input checklist, and the
fact-checker: every percentage names its denominator, and a target judged
against a SOM built on a different SAM is a defect, not a fit.

v0.6.1 adds the Decision-NPV discipline. A real v0.6.0 Canonical figures
table led with the gross DCF NPV the report's own prose called misleading,
carried the effect of the disclosed unmodeled items only as a qualitative
"Negative", and designated no row as the one the verdict rests on. The
discipline now binds the final House View and the amendment pass: the table
must carry a numeric "NPV including unmodeled items" row (a range is
acceptable), exactly one NPV row is marked "(Decision NPV — authoritative
for the verdict)", that designation must not fall on the gross
unmodeled-items-excluded base when the terminal value carries more than 70%
of EV, and the verdict — and the editor's executive summary of it — quotes
the Decision NPV row.
"""

from __future__ import annotations

import os
import re

from ..llm import LLM

# Per-section character budget when rendering sections for the synthesis
# prompts. The scan needs each section's figures and recommendations, not its
# every paragraph; the cap protects the prompt from pathological lengths
# without summarising — truncation is marked inline.
_SECTION_CHAR_BUDGET = 9000


def _max_tokens() -> int:
    """Output budget for each synthesis completion.

    The v0.3 adjudication artifacts ran at 4096 tokens and a real ruling was
    cut inside its volume bridge. 5000 keeps comfortably under the tightest
    provider ceiling in the supported set while giving the adjudication room
    to finish its orders block and the final House View room for its
    Canonical figures table. Overridable per deployment via
    QUORUM_SYNTHESIS_MAX_TOKENS; read at call time so a test or a deployment
    can change it without re-importing the module.
    """
    return int(os.getenv("QUORUM_SYNTHESIS_MAX_TOKENS", "5000"))


_CONFLICT_SYSTEM = """\
You are the synthesis reviewer on a Quorum engagement. The sections below were
written by independent analysts who never read each other's work. Your sole
job is to find where they contradict one another — across sections, not
within one. You do not resolve conflicts, take sides, add facts, or rewrite
anything; you list the contradictions so the supervising partner can rule on
them.

Hunt specifically for these seven classes of conflict:

(a) Target-segment or price-band contradictions — sections recommending
    mutually incompatible customer segments, price tiers, or positioning
    (e.g. one section targets the premium band while another targets the
    budget band as *the* entry point).
(b) Volume or share targets inconsistent with the market-sizing section —
    any unit-volume, revenue, or market-share goal that falls outside, or
    silently ignores, the SAM/SOM ranges the sizing section established.
(c) Numerical contradictions about the same entity — the same quantity
    (e.g. the number of public charging points, a competitor's share, a
    cost figure) stated with materially different values in different
    sections.
(d) Mutually exclusive strategic claims — recommendations that cannot both
    be executed or both be true (e.g. "avoid head-on competition with the
    leader" versus "win share directly from the leader's core segment").
(e) Price-band or pricing-basis drift — the same play's revenue, SOM, or
    share figures priced on different bases in different sections (one
    section using the play's own ASP, another the market-average ASP), or
    a section's stated price band that the play's ASP falls outside of.
(f) Circular derivation — one section's output used as the input for the
    same quantity in another section (e.g. a strategy section's volume
    target divided by an assumed share to produce the "segment size" that
    a sizing or bridging passage then treats as an independent market
    figure, against which the same target is finally judged). The
    contradiction is between the figure's claimed status (an independent
    market measurement) and its actual provenance (the target itself).
(g) Core-input checklist — Always cross-check these core inputs across
    sections before concluding: average selling price / ASP, market
    concentration (CR-n), penetration rates, reference year, segment
    shares, share denominators (overall vs segment). Any of these stated
    with different values, different years, or different bases across
    sections is a conflict even if no section's argument visibly depends on
    the discrepancy.

Number the conflicts sequentially and contiguously (Conflict 1, Conflict 2,
...), ordered by importance. If you merge or delete a candidate conflict
while drafting, renumber the survivors — the final list must run 1..N with
no gaps and no skipped numbers, because the partner's rulings and the
engagement record cite conflicts by these numbers.

Your list is reviewed verbatim by the supervising partner and may be quoted in
the deliverable. Refer to sections only by the human-readable titles given in
the material; never use internal module names, analyst keys, field names, or
any other internal identifier. Preserve [DATA]/[INFERENCE] labels when quoting
claims."""

# Adjudication primitives shared by the adjudication draft and the final
# House View: how the partner is permitted to decide between contradicting
# sections. Comparing self-assigned confidence labels is explicitly banned —
# two scores stamped by the same pipeline differ by noise, not by evidence.
_ADJUDICATION_PRIMITIVES = """\
How to rule on a contradiction — the adjudication primitives:
- It is PROHIBITED to decide a conflict by comparing the sections'
  self-assigned confidence scores (a 0.85 against a 0.80 stamped by the same
  pipeline is noise, not evidence). Confidence labels are a hint about where
  to look, never a basis for a ruling.
- A ruling must go back to the underlying evidence: (1) source tier —
  official first-party sources outrank industry associations, which outrank
  media reports, which outrank model priors; (2) recency — a newer figure
  from an equal-tier source outranks a stale one; (3) whether the derivation
  chain can be recomputed — a figure whose arithmetic you can rebuild from
  stated inputs outranks an unsupported assertion.
- When neither side's evidence dominates, say so and rule on the conservative
  side, stating that the conflict is resolved by judgment, not by evidence."""

# Pricing-basis discipline for the Canonical figures table. Motivated by a
# real v0.4 deliverable: the table priced the selected play's SOM at the
# market-average ASP (CNY 178k) instead of the play's own ASP (CNY 115k),
# and the definitional gap between volume share and revenue share was then
# flagged downstream as an independent "structural problem" — a phantom
# defect double-counting the discount positioning the play had chosen.
_CANONICAL_DISCIPLINE = """\
Canonical-table discipline (non-negotiable):
- Denominator discipline: the selected play's SOM and revenue in the
  Canonical figures table must be priced at THAT PLAY'S OWN ASP, never at
  the market-average ASP; the table must state the pricing basis next to
  the affected values ("at play ASP <currency> <amount>"). Under a discount
  positioning, "X% volume share corresponds to a lower revenue share" is
  true by definition; state it as a one-sentence note where the figures
  appear, and NEVER list it as a separate structural problem, risk, or
  fatal flaw — doing so double-counts the play's own pricing choice.
- Band-ASP coherence: the target price band and the play's ASP must be
  mutually consistent — the ASP sits inside the band (mid-band, or with an
  explicit one-line reason when it hugs an edge), and every price-band
  statement in the report follows the Canonical figures table."""

# Denominator discipline for share figures. Motivated by a real v0.5
# deliverable: the volume target was derived from the selected play's
# segment SAM (0.26M units) while the SOM band it was judged against was
# computed on the overall SAM (2.29M units) — the "target falls inside the
# SOM" claim compared shares of two different markets and stood as comfort.
_SHARE_DENOMINATOR_DISCIPLINE = """\
Share-of-what discipline (non-negotiable): every percentage must name its
denominator; the selected play's SOM and any target-vs-SOM comparison must
use the play's own segment SAM as denominator; quoting an overall-market SOM
beside a segment-level target is a defect."""

# Decision-NPV discipline for the Canonical figures table. Motivated by a
# real v0.6.0 deliverable: the table's headline row was the gross DCF NPV
# (8,297M) that the report's own prose called misleading, the effect of the
# disclosed unmodeled items was carried only as a qualitative "Negative", and
# no row was designated as the one the verdict rests on — so the number the
# report disowned still led every summary of it.
_DECISION_NPV_DISCIPLINE = """\
Decision-NPV discipline (non-negotiable):
- The Canonical figures table must carry a row labeled exactly
  "NPV including unmodeled items", with a NUMERIC value — a figure or a
  range derived from the sections' own stated per-unit costs and volumes,
  never a bare qualitative word such as "Negative". Where only a range is
  supportable, state the range with its derivation basis.
- Exactly ONE NPV row in the table is marked with this exact tag:
  "(Decision NPV — authoritative for the verdict)". The tag is appended to
  that row's own label — do NOT add a second, duplicate row repeating the
  same quantity with the tag. One quantity, one row, tag attached. That row
  is the number the verdict is computed on; every other NPV row is context.
- When the terminal value carries more than 70% of the enterprise value,
  the Decision NPV must NOT be the gross DCF base figure that excludes the
  disclosed unmodeled items — designate the row that includes them (or a
  terminal-value-honest alternative) instead. A report must never disown a
  figure in prose and keep it as the headline.
- The verdict, and any executive summary of it, must quote the Decision NPV
  row — not a different NPV the table carries as context."""

# Authority rule appended to the final House View's and the editor's system
# prompts when the deterministic arithmetic verifier ran: a numeric conflict
# with the recomputation is settled by the recomputation, never by prose.
# Shared so the two prompts state the rule in identical words.
_ARITHMETIC_AUTHORITY_RULE = """\
The arithmetic verifier's recomputed figures are authoritative over any
prose claim; a House View or summary figure that contradicts them is a
defect."""

# Independence discipline for market denominators. Motivated by a real v0.4.1
# deliverable: the House View's volume bridge sized the sub-CNY-80k segment by
# dividing the play's own volume target by its assumed share (25,000 ÷ 0.8% =
# 3.1M units — and one leg still used the superseded 38,000 target), computed
# a SOM from that segment, and then judged the target against the SOM — while
# the report's own gate G7 prohibited deriving the addressable market from the
# volume target. The bridge had manufactured the market the target needed.
_INDEPENDENCE_DISCIPLINE = """\
Independence discipline (non-negotiable):
- No segment size, SAM, or SOM denominator may be derived by dividing a
  volume target by an assumed share ("segment = target units / assumed
  share"). That arithmetic is circular: it manufactures the denominator the
  target needs and then validates the target against it.
- Every step of the volume bridge must state the independent basis of its
  denominator (historical registrations or sales for that segment,
  comparable-model shares within the segment, official segment statistics)
  next to the figure.
- If a section's figure is a target-divided-by-share derivation, REFUSE to
  adopt it: name the offending derivation directly below the bridge, use an
  independently based figure instead where one exists, and where none exists
  state plainly that the segment cannot be independently sized — with the
  confidence lowered and at most an order-of-magnitude bound — rather than
  letting the circular value stand in."""

# Honesty rule shared by the final House View and the editor's summary: a
# play that the corrected numbers kill is dead, and gates cannot revive it.
_HONEST_CONCLUSION_RULE = """\
Honest-conclusion rule (non-negotiable): if the corrected base case remains
negative or value-destroying even when every decision gate passes, you must
say plainly that the selected play does not work as constructed. Then either
point to a concrete alternative where-to-play — including a direction
previously rejected if the corrected numbers now favour it — or recommend
not entering. Decision gates exist to manage genuine uncertainty; they must
never be used to keep alive a play the firm's own corrected numbers have
already killed."""

# The adjudication's re-direction authority (below) lets the partner order
# the strategy seat to re-select the play when the engagement's own structural
# analysis condemns it — the revision loop already supports rewriting a
# section under an order, so a re-selection order is dispatched like any
# other. This does NOT conflict with the post-red-team amendment pass's
# "must not change the selected play" rule: re-direction happens at the
# adjudication stage, *before* the final House View exists, where changing
# the play is exactly the partner's job; the amendment pass runs after the
# red team, where the play is settled and only the canonical record may be
# corrected. Two different stages, two different change budgets.
_ADJUDICATE_SYSTEM = (
    """\
You are the supervising partner on a Quorum engagement, writing the
adjudication draft that precedes the revision round. The framework sections
below were drafted independently and the conflict scan lists where they
disagree. Your draft turns a stack of parallel analyses into one set of
binding rulings: the firm commits to a single selected play, every conflict
is ruled on, every framework recommendation is adopted, rejected, or
reframed — and every section whose content your rulings overturn receives a
written revision order. The ordered sections will be rewritten against your
rulings before the final House View is produced, so an order you fail to
issue is a contradiction that ships.

"""
    + _ADJUDICATION_PRIMITIVES
    + """

"""
    + _INDEPENDENCE_DISCIPLINE
    + """

Re-direction authority (binding): if the selected play is condemned by the
engagement's own structural analysis (a loss-making base case for a
sub-scale entrant, no credible cost or differentiation path), the
adjudication must not simply confirm the condemnation. It must either
(a) issue a revision order to the strategy seat to re-select among the
alternative directions the analyses themselves point to (e.g. higher-margin
horizons, faster-growing spaces), with the same rigor as the original
choice; or (b) rule that the engagement's conclusion is a direction-level
no-go and name the specific follow-up engagement (region x segment) that
should be run next. Proving a condemned play condemned a second time is not
an acceptable outcome.

Rules in force:
- Rule on conflicts; do not paper over them. Every High-importance conflict
  in the scan gets an explicit ruling with a reason.
- Commit to exactly ONE selected play. Naming two plays, hedging between
  plays, or deferring the choice is a failure of this section's purpose.
- Preserve every [DATA]/[INFERENCE] label and confidence score in anything
  you quote or restate; do not launder an inference into a fact.
- Do not introduce new facts or figures; reason only from the sections and
  the conflict scan. Re-deriving a figure from inputs the sections state
  (e.g. recomputing a SAM after ruling on its inputs) is permitted and must
  show its arithmetic.
- Write in the third person ("the firm's view is", "the selected play is");
  never use the first person.
- Never use internal module names, analyst keys, field names, or any other
  internal identifier; refer to sections only by their human-readable titles."""
)

_FINAL_HOUSE_VIEW_SYSTEM = (
    """\
You are the supervising partner on a Quorum engagement, writing the final
House View. The sections below have already been REVISED under your
adjudication draft's rulings and revision orders — they are the corrected
body of the report, not the contradictory first drafts. Your job now is to
state the firm's view against this revised body and to publish the single
authoritative set of headline figures the whole report follows.

"""
    + _ADJUDICATION_PRIMITIVES
    + """

"""
    + _CANONICAL_DISCIPLINE
    + """

"""
    + _SHARE_DENOMINATOR_DISCIPLINE
    + """

"""
    + _DECISION_NPV_DISCIPLINE
    + """

"""
    + _INDEPENDENCE_DISCIPLINE
    + """

"""
    + _HONEST_CONCLUSION_RULE
    + """

Rules in force:
- Stay consistent with the adjudication draft's selected play and rulings
  unless a revised section surfaces evidence that forces a stated change —
  in that case, state the change and the evidence in one place.
- Quote figures from the REVISED sections only; never restate a number the
  revision corrected.
- Preserve every [DATA]/[INFERENCE] label and confidence score in anything
  you quote or restate; do not launder an inference into a fact.
- Write in the third person; never use the first person.
- Never use internal module names, analyst keys, field names, or any other
  internal identifier; refer to sections only by their human-readable titles."""
)

# The heading that opens the machine-readable orders block. Parsing tolerates
# case and surrounding whitespace; the prompt asks for this exact spelling.
_REVISION_ORDERS_HEADING = "REVISION ORDERS:"

_ORDERS_HEADING_RE = re.compile(r"^\s*\**\s*revision orders\s*:?\s*\**\s*$", re.IGNORECASE)
_ORDER_LINE_RE = re.compile(r"^\s*[-*+]\s+(.*)$")


def _condense(sections: dict[str, str]) -> str:
    """Render the checked sections for a synthesis prompt, capped per section.

    Sections enter the deliverable verbatim through the assembly pipeline;
    here they are only *evidence* for the scan and the rulings, so a hard cap
    per section is safe. Truncation is marked inline so the model knows the
    tail was cut rather than absent.
    """
    parts = []
    for title, text in sections.items():
        body = text
        if len(body) > _SECTION_CHAR_BUDGET:
            body = (
                body[:_SECTION_CHAR_BUDGET]
                + "\n[... section continues; truncated for context ...]"
            )
        parts.append(f"### {title}\n{body}")
    return "\n\n".join(parts)


def find_conflicts(sections: dict[str, str], llm: LLM) -> str:
    """Scan the fact-checked sections for cross-section contradictions.

    ``sections`` maps each **human-readable section title** to its checked
    text. Returns a markdown conflict list covering the seven conflict classes
    (segment/price-band contradictions, volume-vs-sizing inconsistencies,
    numerical contradictions about the same entity, mutually exclusive
    strategic claims, price-band/pricing-basis drift, circular derivation,
    and the core-input cross-check over ASP, CR-n concentration, penetration
    rates, reference year, segment shares, and share denominators — overall
    versus segment),
    each entry carrying the sections involved, each side's
    position, and an importance grade — numbered contiguously from 1 so the
    rulings can cite conflicts by number. The list is written to ``gates/``
    and feeds :func:`adjudicate`; an honest "no conflicts found" beats an
    invented one, and the prompt says so.
    """
    prompt = (
        "Scan all the sections below against each other and return a markdown "
        "conflict list. For each conflict, give exactly these fields:\n\n"
        "- **Conflict:** one-sentence description of the contradiction.\n"
        "- **Sections involved:** the human-readable titles of every section "
        "party to it.\n"
        "- **Positions:** each side's claim or recommendation, quoted or "
        "tightly paraphrased, with its figures.\n"
        "- **Importance:** High / Med / Low — High when acting on one side "
        "would invalidate the other or move the headline recommendation.\n\n"
        "Order the list by importance, highest first, and number it "
        "sequentially and contiguously from Conflict 1 — if you merge or drop "
        "a candidate while drafting, renumber so the final list has no gaps "
        "and no skipped numbers. Check all seven conflict classes; if a class "
        "is clean, say so in one line. Always cross-check these core inputs "
        "across sections before concluding: average selling price / ASP, "
        "market concentration (CR-n), penetration rates, reference year, "
        "segment shares, share denominators (overall vs segment). If you "
        "find no conflicts at all, say "
        "so plainly — do not invent disagreements to fill the list.\n\n"
        "----- BEGIN FACT-CHECKED SECTIONS -----\n"
        f"{_condense(sections)}\n"
        "----- END SECTIONS -----"
    )
    return llm.complete(system=_CONFLICT_SYSTEM, prompt=prompt, max_tokens=_max_tokens())


def adjudicate(
    sections: dict[str, str], conflicts: str, llm: LLM, retry_note: str = ""
) -> str:
    """Produce the adjudication draft — rulings plus revision orders.

    ``sections`` maps human-readable titles to checked text; ``conflicts`` is
    the verbatim output of :func:`find_conflicts`. The draft has four
    mandatory parts: the single selected play with an explicit ruling on
    every High-importance conflict, an adjudication table covering every
    section that proposed a direction, a volume bridge squaring the selected
    play's targets with the sizing section's SAM/SOM, and a closing
    ``REVISION ORDERS:`` block — one order per section whose content the
    rulings overturned or recomputed. The orders block is parsed by
    :func:`parse_revision_orders` and dispatched as revision contracts; the
    draft itself is archived under ``gates/adjudication.md`` and the *final*
    House View (:func:`final_house_view`) is written only after the ordered
    sections are revised. ``retry_note``, when supplied by the orchestrator's
    truncation retry, is prepended to the prompt.
    """
    note = f"{retry_note}\n\n" if retry_note else ""
    prompt = (
        f"{note}"
        "Write the adjudication draft, with exactly these four parts in this "
        "order:\n\n"
        "PART 1 — The selected play. Commit the firm to a single selected "
        "play. Default candidate: the play (or plays) proposed in the "
        "\"Where-to-Play\" style strategy section — but the choice is yours "
        "to make against the full evidence, and you must state why this play "
        "and not the alternatives. If the default candidate is condemned by "
        "the engagement's own structural analysis, exercise the re-direction "
        "authority: order the strategy seat to re-select among the directions "
        "the analyses point to, or rule a direction-level no-go and name the "
        "follow-up engagement — do not re-prove a known dead end. For every "
        "High-importance conflict in the "
        "conflict scan, give an explicit ruling: which side prevails and why, "
        "using the adjudication primitives (source tier, recency, "
        "recomputable derivation) — never a comparison of self-assigned "
        "confidence scores. A High conflict left unruled is a defect. Where "
        "a ruling changes a headline figure (e.g. a SAM recomputed on "
        "corrected inputs), state the corrected figure and its arithmetic "
        "once, here, and use only the corrected figure everywhere after.\n\n"
        "PART 2 — Adjudication of the framework recommendations. A markdown "
        "table with exactly these columns:\n\n"
        "| Framework / Section | Its recommendation | Adopted / Rejected / "
        "Reframed | Reason |\n\n"
        "One row per section that proposed a direction, target segment, "
        "growth move, or play — strategy-choice plays, growth-horizons "
        "phasing, growth-vector moves, uncontested-space (blue-ocean) "
        "opportunities, durable-advantage (powers-based) plays, and any "
        "other section that recommended a course of action. Every such "
        "section appears in the table; sections that only described the "
        "market without recommending a direction may be omitted. \"Adopted\" "
        "means the selected play carries it; \"Reframed\" means it survives "
        "in a narrowed or repositioned form you state; \"Rejected\" needs a "
        "reason grounded in the evidence or the ruling on a conflict.\n\n"
        "PART 3 — Volume bridge to the market sizing. Reconcile the selected "
        "play's volume, revenue, or share targets against the SAM and SOM in "
        "the \"Market Size\" style sizing section — as corrected by your "
        "Part 1 rulings, if any ruling moved them: state the play's implied "
        "volumes, the (corrected) SAM/SOM range, and whether the targets fit "
        "inside it. Apply the independence discipline: every denominator in "
        "the bridge carries its independent basis stated next to the figure, "
        "and a target-divided-by-assumed-share derivation supplied by any "
        "section is named and rejected, never adopted. If a target exceeds "
        "the SOM range, say so explicitly and "
        "either revise the target down or state the specific assumption that "
        "would have to hold for the excess to be credible — silently keeping "
        "an out-of-range target is prohibited.\n\n"
        "PART 4 — Revision orders. Close with a machine-readable block in "
        "exactly this format:\n\n"
        "REVISION ORDERS:\n"
        "- <Section Title>: <one-sentence revision instruction>\n"
        "- <Section Title>: <instruction>\n\n"
        "One order per section whose content your rulings overturned or "
        "recomputed. Use each section's exact human-readable title as it "
        "appears in the material. Issuing an order is MANDATORY for every "
        "section that still models, prices, or assesses a play or figure your "
        "rulings rejected or corrected — typically the valuation, the unit "
        "economics, the strategy-choice section, and the strategy-quality "
        "assessment when their content no longer matches the selected play or "
        "the corrected figures. Each instruction states what must change: "
        "which play to model, which corrected figures to use, what to drop. "
        "If, and only if, no section needs revision, write exactly:\n\n"
        "REVISION ORDERS:\n"
        "- none\n\n"
        "----- BEGIN CONFLICT SCAN -----\n"
        f"{conflicts}\n"
        "----- END CONFLICT SCAN -----\n\n"
        "----- BEGIN FACT-CHECKED SECTIONS -----\n"
        f"{_condense(sections)}\n"
        "----- END SECTIONS -----"
    )
    return llm.complete(system=_ADJUDICATE_SYSTEM, prompt=prompt, max_tokens=_max_tokens())


def parse_revision_orders(text: str) -> dict[str, str]:
    """Parse the ``REVISION ORDERS:`` block into ``{section title: instruction}``.

    Pure function over the adjudication draft. The block opens with a line
    reading ``REVISION ORDERS:`` (case-insensitive, surrounding whitespace
    and markdown emphasis tolerated) and contains one list item per order in
    the form ``- <Section Title>: <instruction>``. Parsing stops at the first
    non-blank line after the heading that is not a list item, so prose after
    the block is never swallowed. Returns an empty dict when the block is
    absent, contains only ``- none``, or contains no well-formed orders —
    the orchestrator treats an empty dict as "no revision round".

    Section titles are returned stripped of surrounding whitespace and
    markdown emphasis but otherwise verbatim; the orchestrator matches them
    against roster titles case-insensitively.
    """
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if _ORDERS_HEADING_RE.match(line):
            start = i + 1
            break
    if start is None:
        return {}
    orders: dict[str, str] = {}
    for line in lines[start:]:
        if not line.strip():
            continue
        match = _ORDER_LINE_RE.match(line)
        if match is None:
            break  # first non-list line ends the block
        item = match.group(1).strip()
        if item.strip("*_` ").lower() in ("none", "none."):
            continue
        title, sep, instruction = item.partition(":")
        if not sep or not instruction.strip():
            continue  # malformed order line; skip rather than guess
        clean_title = title.strip().strip("*_`").strip()
        if not clean_title:
            continue
        orders[clean_title] = instruction.strip()
    return orders


def final_house_view(
    sections: dict[str, str],
    adjudication: str,
    llm: LLM,
    retry_note: str = "",
    arithmetic: str = "",
) -> str:
    """Produce the final House View against the *revised* sections.

    ``sections`` maps human-readable titles to the post-revision text — the
    ordered seats have already rewritten their sections under the
    adjudication's rulings. ``adjudication`` is the verbatim adjudication
    draft. The result opens with a **Canonical figures** table — the single
    authoritative set of headline numbers the whole report follows — then
    restates the selected play, the conflict rulings, the adjudication table,
    and the volume bridge as they stand against the revised body. It is
    embedded in the deliverable's Part I and is the baseline the red team
    attacks and the executive summary must follow. ``retry_note``, when
    supplied by the orchestrator's truncation retry, is prepended to the
    prompt. ``arithmetic``, when supplied, is the deterministic arithmetic
    verifier's verified-figures table; it enters the prompt as a mandatory
    input and the system prompt gains the rule that the recomputed figures
    outrank any prose claim — the Canonical figures table must match them.
    """
    note = f"{retry_note}\n\n" if retry_note else ""
    arithmetic_block = ""
    if arithmetic.strip():
        arithmetic_block = (
            "----- BEGIN ARITHMETIC VERIFICATION (deterministic recomputation; "
            "authoritative over prose) -----\n"
            f"{arithmetic}\n"
            "----- END ARITHMETIC VERIFICATION -----\n\n"
        )
    prompt = (
        f"{note}"
        "Write the \"House View\" section against the REVISED sections below, "
        "with exactly these parts in this order:\n\n"
        "PART 1 — Canonical figures. Open with a markdown table titled "
        "\"Canonical figures\" carrying the single authoritative value (with "
        "its [DATA]/[INFERENCE] label) for each of: SAM; SOM (nominal and "
        "probability-weighted, where the sections distinguish them); the "
        "selected play's implied unit volumes; the target segment / price "
        "band; the corrected margin path; and the key unit costs the "
        "economics turn on. Take each value from the revised sections — never "
        "from a pre-revision figure. Apply the Canonical-table discipline: "
        "price the play's SOM and revenue at the play's own ASP with the "
        "basis stated in the table (\"at play ASP ...\"), keep the target "
        "price band consistent with that ASP, and where the play prices below "
        "market state the volume-share/revenue-share gap as a definitional "
        "note, not a problem. Apply the Decision-NPV discipline: the table "
        "carries a numeric \"NPV including unmodeled items\" row (a value or "
        "a range derived from the sections' stated per-unit costs and "
        "volumes — never a bare word like \"Negative\"); exactly one NPV row "
        "is marked \"(Decision NPV — authoritative for the verdict)\"; and "
        "where the terminal value carries more than 70% of enterprise value, "
        "that designation must not fall on the gross DCF base figure that "
        "excludes the disclosed unmodeled items. Immediately below the table "
        "state: "
        "\"All figures elsewhere in this report follow this table; where a "
        "section states a different value, this table prevails.\"\n\n"
        "PART 2 — The selected play and the rulings. Restate the single "
        "selected play and the rulings from the adjudication draft as they "
        "stand against the revised sections, noting any ruling the revisions "
        "made moot. If any conflict remains unresolved after revision, say so "
        "explicitly using the word \"unresolved\" and state what evidence "
        "would settle it.\n\n"
        "PART 3 — Adjudication of the framework recommendations. The same "
        "table format as the adjudication draft (| Framework / Section | Its "
        "recommendation | Adopted / Rejected / Reframed | Reason |), updated "
        "to reflect the revised sections.\n\n"
        "PART 4 — Volume bridge to the market sizing. Reconcile the selected "
        "play's targets against the Canonical figures' SAM/SOM; the bridge "
        "must use only Canonical figures. Apply the independence discipline "
        "to every step: each denominator carries its independent basis "
        "(historical segment registrations or sales, comparable-model shares, "
        "official segment statistics) stated next to the figure; a "
        "target-divided-by-assumed-share derivation must never appear as a "
        "bridge step, and where a section supplied one, name it directly "
        "below the bridge as a rejected circular derivation rather than "
        "adopting it.\n\n"
        "PART 5 — The verdict. Apply the honest-conclusion rule: state "
        "whether the corrected base case creates or destroys value with all "
        "gates passed, and conclude accordingly — including \"this play does "
        "not work as constructed\" with an alternative direction or a "
        "no-entry recommendation if that is what the corrected numbers say. "
        "The verdict sentence must quote the Canonical figures table's "
        "Decision NPV row — the row marked \"(Decision NPV — authoritative "
        "for the verdict)\" — not a different NPV the table carries as "
        "context.\n\n"
        f"{arithmetic_block}"
        "----- BEGIN ADJUDICATION DRAFT (your earlier rulings) -----\n"
        f"{adjudication}\n"
        "----- END ADJUDICATION DRAFT -----\n\n"
        "----- BEGIN REVISED SECTIONS -----\n"
        f"{_condense(sections)}\n"
        "----- END REVISED SECTIONS -----"
    )
    system = _FINAL_HOUSE_VIEW_SYSTEM
    if arithmetic.strip():
        system += "\n\n" + _ARITHMETIC_AUTHORITY_RULE
    return llm.complete(system=system, prompt=prompt, max_tokens=_max_tokens())


# Sentinel the amendment pass emits when the red team proved no canonical-grade
# error: the exact phrase the prompt requests. Matching tolerates case,
# surrounding whitespace, markdown emphasis, hyphenation, and trailing
# punctuation — a lightweight exit so the model is never forced to re-emit a
# multi-thousand-word House View it does not intend to change.
NO_AMENDMENT_SENTINEL = "NO AMENDMENT REQUIRED"

_NO_AMENDMENT_RE = re.compile(r"^\s*no[\s-]+amendments?[\s-]+required\b", re.IGNORECASE)

_AMEND_SYSTEM = (
    """\
You are the supervising partner on a Quorum engagement, reviewing your own
final House View against the red team's memo. The revision loop has already
run; the rulings stand. Your sole question now is narrower: does the memo
demonstrate, with evidence, a canonical-grade error in the House View — a
wrong pricing basis (e.g. the selected play's SOM or revenue priced at the
market-average ASP instead of the play's own ASP), a number whose stated
derivation does not recompute, or a decision-gate set whose own coherence
check the gate table fails to apply? Rhetoric, judgment calls, and risk
arguments are the reconciliation's business, not yours; only a demonstrated
error in the canonical record qualifies.

"""
    + _CANONICAL_DISCIPLINE
    + """

"""
    + _SHARE_DENOMINATOR_DISCIPLINE
    + """

"""
    + _DECISION_NPV_DISCIPLINE
    + """

Rules in force:
- If no red-team argument proves a canonical-grade error, output exactly the
  line NO AMENDMENT REQUIRED and nothing else.
- If one does, output the COMPLETE amended House View. You may change ONLY
  the Canonical figures table, the decision-gate table, and the inline
  figures or pricing-basis notes those corrections directly touch. You must
  NOT change the selected play, reverse an adjudication ruling, soften the
  verdict, or rewrite prose the corrections do not touch — reproduce
  everything else verbatim.
- Close an amended House View with a section headed exactly
  "### Amendments after red-team review", listing each change as one item:
  what changed, the corrected value or basis, and the red-team argument
  (cited by its number in the memo) that forced it.
- Preserve every [DATA]/[INFERENCE] label and confidence score; write in the
  third person; never use internal module names, analyst keys, field names,
  or any other internal identifier."""
)


def resolve_amendment(original: str, model_output: str) -> str:
    """Resolve the amendment pass's output against the original House View.

    Pure function — the sentinel-handling half of :func:`amend_canonical`,
    factored out so it is testable without a model. If ``model_output``
    *begins* with the no-amendment sentinel (case, whitespace, markdown
    emphasis, hyphenation, and the singular/plural of "amendment" all
    tolerated), the ``original`` is returned byte-for-byte — the deliverable
    must carry the real House View, never the sentinel line. An empty or
    whitespace-only output also resolves to the original: a model that said
    nothing did not amend anything, and so did a model that re-emitted the
    original verbatim (modulo surrounding whitespace) — callers detect an
    amendment by comparing the result against the original, so an unchanged
    text must come back as the original object, not a re-stripped twin.
    Anything else is taken as the amended House View and returned stripped
    of leading/trailing whitespace.
    """
    candidate = model_output.strip()
    if not candidate or candidate == original.strip():
        return original
    head = candidate.lstrip("#*_`> ").strip()
    if _NO_AMENDMENT_RE.match(head):
        return original
    return candidate


def amend_canonical(house_view: str, dissent: str, llm: LLM, retry_note: str = "") -> str:
    """Amend the final House View's canonical record after the red team.

    ``house_view`` is the final House View (Canonical figures table, rulings,
    gate table, verdict); ``dissent`` is the red team's full memo. The pass
    asks one narrow question: did the memo demonstrate a canonical-grade
    error — pricing basis, a derivation that does not recompute, or a gate
    table that ignores its own coherence check? If not, the model answers
    with the ``NO AMENDMENT REQUIRED`` sentinel and the original text is
    returned unchanged (:func:`resolve_amendment` handles the resolution).
    If so, the model re-emits the complete House View with only the
    Canonical figures table, the gate table, and the directly affected
    inline figures changed — the selected play and the rulings are out of
    bounds — closing with an "### Amendments after red-team review" section
    that cites the memo arguments behind each change.

    The orchestrator runs this once, after the red team and before the
    editor, through the same truncation-retry guard as the other synthesis
    completions; ``retry_note`` is that guard's channel. Callers compare the
    return value with ``house_view`` to learn whether an amendment occurred.
    """
    note = f"{retry_note}\n\n" if retry_note else ""
    prompt = (
        f"{note}"
        "Review the red-team memo below against the final House View. Decide "
        "whether any memo argument demonstrates a canonical-grade error in "
        "the House View — a wrong pricing basis, a figure whose stated "
        "derivation does not recompute, or a decision-gate table that does "
        "not apply the memo's own gate-coherence findings.\n\n"
        "If NO argument demonstrates such an error, output exactly this line "
        "and nothing else:\n\n"
        "NO AMENDMENT REQUIRED\n\n"
        "If one does, output the complete amended House View: identical to "
        "the original except for the Canonical figures table, the "
        "decision-gate table, and the inline figures or pricing-basis notes "
        "the corrections directly touch — the selected play and the "
        "adjudication rulings must stand as written. End the amended House "
        "View with a \"### Amendments after red-team review\" section "
        "listing each change with its corrected value and the memo argument "
        "(by number) that forced it.\n\n"
        "----- BEGIN FINAL HOUSE VIEW -----\n"
        f"{house_view}\n"
        "----- END FINAL HOUSE VIEW -----\n\n"
        "----- BEGIN RED-TEAM MEMO -----\n"
        f"{dissent}\n"
        "----- END RED-TEAM MEMO -----"
    )
    output = llm.complete(system=_AMEND_SYSTEM, prompt=prompt, max_tokens=_max_tokens())
    return resolve_amendment(house_view, output)


# Sentinel the stale-figure sweep emits when no superseded value survives in
# the report body. Matching tolerates case, surrounding whitespace, markdown
# emphasis, hyphenation, and trailing punctuation, in the same spirit as the
# amendment sentinel — a lightweight exit for the common clean case.
NO_STALE_FIGURES_SENTINEL = "NO STALE FIGURES"

_NO_STALE_RE = re.compile(r"^\s*no[\s-]+stale[\s-]+figures?\b", re.IGNORECASE)

# One sweep entry per list line: `- <old> | <current> | <Section Title> | <where>`.
_STALE_LINE_RE = re.compile(r"^\s*[-*+]\s+(.*)$")

_STALE_SWEEP_SYSTEM = """\
You are the synthesis reviewer on a Quorum engagement, running the final
stale-figure sweep. The revision loop has run and the House View below is the
canonical record: its Canonical figures table (and its amendments, if any) is
the single authoritative set of headline values. Your sole job is to find,
in the report sections, figures that the canonical record SUPERSEDED but
that still appear in the body stated as if current — a leftover volume
target the adjudication revised, a SAM the rulings recomputed, a unit cost
the amendments corrected.

What counts as stale:
- A value for a quantity the canonical record states differently, presented
  in a section as the current value of that quantity.

What does NOT count:
- A value a section explicitly marks as historical or superseded ("the
  pre-revision target of X was revised to Y", "previously estimated at X").
- A genuinely different quantity that happens to share units (a competitor's
  volume is not the play's volume target).
- Ranges or scenario values the canonical record itself carries.

You list; you never rewrite, never invent figures, and never decide which
value is right — the canonical record has already decided. Refer to sections
only by their human-readable titles, exactly as given in the material."""


def stale_figures(
    sections: dict[str, str], canonical: str, llm: LLM, retry_note: str = ""
) -> str:
    """Sweep the revised sections for figures the canonical record superseded.

    ``sections`` maps human-readable titles to the post-revision section
    texts; ``canonical`` is the final House View as it stands (Canonical
    figures table, rulings, and the amendments section when the red team
    forced one). The sweep lists every superseded value still presented in a
    section as if current — old value, current canonical value, the section
    and where in it — in a machine-readable block:

        STALE FIGURES:
        - <old value> | <current value> | <Section Title> | <where it appears>

    or answers with the ``NO STALE FIGURES`` sentinel when the body is clean.
    :func:`resolve_stale` parses the output; the orchestrator turns a
    non-empty result into one round of pin-point revision orders.
    ``retry_note`` is the orchestrator's truncation-retry channel, prepended
    to the prompt when supplied.
    """
    note = f"{retry_note}\n\n" if retry_note else ""
    prompt = (
        f"{note}"
        "Compare the report sections below against the canonical House View "
        "and list every figure the canonical record superseded that a section "
        "still states as if current.\n\n"
        "If the sections are clean, output exactly this line and nothing "
        "else:\n\n"
        "NO STALE FIGURES\n\n"
        "Otherwise output exactly this block — a heading line and one list "
        "item per stale figure, four fields separated by ` | `:\n\n"
        "STALE FIGURES:\n"
        "- <old value> | <current canonical value> | <Section Title> | "
        "<where it appears in the section>\n\n"
        "Use each section's exact human-readable title as the third field. "
        "Quote the old value as it appears in the section text. Do not list "
        "values a section explicitly marks as superseded or historical, and "
        "do not list genuinely different quantities.\n\n"
        "----- BEGIN CANONICAL HOUSE VIEW (the authoritative record) -----\n"
        f"{canonical}\n"
        "----- END CANONICAL HOUSE VIEW -----\n\n"
        "----- BEGIN REPORT SECTIONS -----\n"
        f"{_condense(sections)}\n"
        "----- END SECTIONS -----"
    )
    return llm.complete(system=_STALE_SWEEP_SYSTEM, prompt=prompt, max_tokens=_max_tokens())


def resolve_stale(text: str) -> list[dict[str, str]] | None:
    """Parse the stale-figure sweep's output into entries, or ``None`` if clean.

    Pure function over the sweep output, in the tolerance style of
    :func:`resolve_amendment`. An output that *begins* with the
    ``NO STALE FIGURES`` sentinel (case, whitespace, markdown emphasis,
    hyphenation, and the singular/plural of "figure" all tolerated) resolves
    to ``None`` — so does an empty or whitespace-only output, since a model
    that said nothing found nothing. Otherwise every list item of the form
    ``- <old> | <current> | <Section Title> | <where>`` parses to a dict with
    keys ``old``, ``current``, ``section``, and ``location`` (the fourth
    field is optional and defaults to ``""``); fields are stripped of
    surrounding whitespace and markdown emphasis. Items with fewer than
    three fields are skipped rather than guessed. If no well-formed entry
    survives, the result is ``None`` — an unparseable sweep must not trigger
    a revision round on noise.
    """
    candidate = text.strip()
    if not candidate:
        return None
    head = candidate.lstrip("#*_`> ").strip()
    if _NO_STALE_RE.match(head):
        return None
    entries: list[dict[str, str]] = []
    for line in candidate.splitlines():
        match = _STALE_LINE_RE.match(line)
        if match is None:
            continue
        fields = [part.strip().strip("*_`").strip() for part in match.group(1).split("|")]
        if len(fields) < 3 or not all(fields[:3]):
            continue  # malformed entry; skip rather than guess
        entries.append(
            {
                "old": fields[0],
                "current": fields[1],
                "section": fields[2],
                "location": fields[3] if len(fields) > 3 else "",
            }
        )
    return entries or None
