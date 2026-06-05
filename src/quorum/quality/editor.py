"""Chief-editor gate.

The final gate owns the editorial voice of the deliverable, not its body. In
v0.1 the editor rewrote the whole report in one completion, which capped the
deliverable at the provider's output ceiling and truncated long engagements.
In v0.2 the editor produces only the three blocks that genuinely require
editorial judgment — the executive summary, the reconciliation of the red
team's arguments, and the scenario analysis — and the orchestrator assembles
the final report programmatically (:mod:`quorum.output.report`), embedding the
fact-checked sections and the red-team memo verbatim. Body text never passes
through a second model rewrite, so it can no longer be truncated or silently
altered. Since v0.3 the editor also receives the synthesis gate's outputs:
the House View ruling binds the executive summary to the single selected
play, and the conflict scan lets the reconciliation settle baseline-figure
disputes on the record. Since v0.4 the sections the editor reads are the
*revised* sections from the synthesis loop's revision round, the House View
is the final one written against that revised body, and both the executive
summary and the scenario analysis are bound to its "Canonical figures"
table — citing a different value for a canonical quantity is a defect, and
the honest-conclusion rule bars the summary from gating a play the corrected
numbers have already killed. Since v0.4.1 the House View the editor receives
may carry an "Amendments after red-team review" section — the synthesis
gate's post-red-team correction of the canonical record — and the
reconciliation's ACCEPT entries must point to those amendments rather than
restating problems the amendment already fixed. Since v0.6 the editor also
receives the deterministic arithmetic verifier's verified-figures table when
the valuation section carried a recomputable build: the table is mandatory
context, and the recomputed figures outrank any prose claim — a summary
figure that contradicts them is a defect.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..llm import LLM
from .synthesis import _ARITHMETIC_AUTHORITY_RULE

if TYPE_CHECKING:  # avoid a runtime import cycle with the orchestrator
    from ..orchestrator import Engagement

# Delimiter the first editorial call must emit between its two blocks. Chosen
# to be improbable in prose and trivial to split on.
_BLOCK_DELIMITER = "<<<QUORUM-BLOCK-BREAK>>>"

# Per-section character budget when condensing sections for the editor's
# context. Generous enough to keep every section's argument and closing
# figures; the cap exists to protect the prompt from pathological lengths,
# not to summarize.
_SECTION_CHAR_BUDGET = 6000

_SYSTEM = """\
You are the chief editor on a Quorum engagement, working in the tradition of
the Minto Pyramid Principle: lead with the answer, then marshal the support
beneath it. The body sections and the red team's memo are embedded in the
report verbatim by the assembly pipeline; you write only the editorial blocks
you are asked for. Do not rewrite, summarize, or re-emit the sections
themselves.

Rules in force:
- Preserve every claim's [DATA]/[INFERENCE] label and confidence score in
  anything you write; do not launder an inference into a fact.
- Keep the reader's time sacred. Cut anything that does not serve a decision.
- Never use internal module names, analyst keys, field names, or any other
  internal identifier in your output; refer to sections only by the
  human-readable titles given in the material. The ban explicitly covers:
  skill directory names (hyphenated identifiers such as a "seven-powers-analyst"
  — say "the Seven Powers analysis" instead), engine file paths and artifact
  names (anything like gates/, engagements/, or a *.md filename), and
  production-line jargon (seat, adjudication order, pipeline, orchestrator).
  Use client-facing consulting language throughout: "the supervising
  partner's ruling", "the dissenting memo", "the engagement bundle".
- Confidence is weakest-link, not multiplicative: a derived claim's
  confidence is the minimum of its inputs, written as min(0.7, 0.6) = 0.6;
  never write it as a product and never multiply confidence labels as if
  they were probabilities."""


@dataclass
class EditorialBlocks:
    """The three editor-authored blocks of a v0.2 report.

    Everything else in the deliverable is assembled from fact-checked working
    papers and the red-team memo without a second model pass.
    """

    executive_summary: str
    reconciliation: str
    scenarios: str


def _condense(sections: dict[str, str]) -> str:
    """Render the sections for the editor's context, capped per section.

    Sections enter the deliverable verbatim through the assembly pipeline;
    here they are only *context* for the editorial blocks, so a hard cap per
    section is safe. Truncation is marked inline so the editor knows the tail
    was cut rather than absent.
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


def compile_report(
    engagement: "Engagement",
    sections: dict[str, str],
    dissent: str,
    llm: LLM,
    house_view: str = "",
    conflicts: str = "",
    arithmetic: str = "",
) -> EditorialBlocks:
    """Produce the three editorial blocks for the assembled report.

    ``sections`` maps each **human-readable section title** to its
    fact-checked text; ``dissent`` is the red team's full memo, including its
    "Decision gates" part. ``house_view`` is the supervising partner's House
    View ruling (single selected play, adjudication table, volume bridge) and
    ``conflicts`` is the cross-section conflict scan that fed it; both enter
    the editor's context so the executive summary can be required to carry
    the selected play and the reconciliation can settle any baseline-figure
    conflict on the record. ``arithmetic``, when supplied, is the
    deterministic arithmetic verifier's verified-figures table: it enters
    the context as a mandatory input and the system prompt gains the rule
    that the recomputed figures outrank any prose claim — a summary figure
    contradicting them is a defect. Two completions are made — (1)
    reconciliation plus executive summary, (2) scenario analysis — so no
    single output needs to carry the whole report and the provider's output
    ceiling stops being a truncation risk.

    The reconciliation is written first within the first call so the
    executive summary can be required to reflect its outcomes: a gated
    conclusion ("entry is advisable only if the following preconditions are
    met ...") rather than a flat yes/no that ignores accepted objections.
    """
    header = (
        f"Engagement: {engagement.industry} in {engagement.region}, "
        f"depth {engagement.depth}, written in {engagement.language}.\n\n"
    )
    synthesis_block = ""
    if arithmetic.strip():
        synthesis_block += (
            "----- BEGIN ARITHMETIC VERIFICATION (deterministic "
            "recomputation; authoritative over prose) -----\n"
            f"{arithmetic}\n"
            "----- END ARITHMETIC VERIFICATION -----\n\n"
        )
    if house_view.strip():
        synthesis_block += (
            "----- BEGIN HOUSE VIEW (the supervising partner's binding "
            "ruling; reproduced verbatim elsewhere) -----\n"
            f"{house_view}\n"
            "----- END HOUSE VIEW -----\n\n"
        )
    if conflicts.strip():
        synthesis_block += (
            "----- BEGIN CROSS-SECTION CONFLICT SCAN (context only) -----\n"
            f"{conflicts}\n"
            "----- END CONFLICT SCAN -----\n\n"
        )
    context = (
        synthesis_block
        + "----- BEGIN FACT-CHECKED SECTIONS (context only; embedded verbatim "
        "elsewhere) -----\n"
        f"{_condense(sections)}\n"
        "----- END SECTIONS -----\n\n"
        "----- BEGIN RED-TEAM MEMO (reproduced verbatim elsewhere) -----\n"
        f"{dissent}\n"
        "----- END RED-TEAM MEMO -----"
    )

    house_summary_rule = ""
    house_reconciliation_rule = ""
    house_scenario_rule = ""
    if house_view.strip():
        house_summary_rule = (
            " The summary must carry the House View's single selected play as "
            "the report's direction — do not propose a different play, hedge "
            "between plays, or revive a recommendation the House View "
            "rejected; if the red team's accepted arguments qualify the play, "
            "express that as conditions on the same play, not a new one. "
            "Every figure the summary cites must match the House View's "
            "\"Canonical figures\" table where the table carries that "
            "quantity — quoting a different value for a canonical quantity is "
            "a defect. Where that table marks one NPV row \"(Decision NPV — "
            "authoritative for the verdict)\", the summary's verdict sentence "
            "must quote that row's value — leading with a different NPV the "
            "table carries only as context is a defect. Honest-conclusion "
            "rule, non-negotiable: if the "
            "corrected base case is negative or value-destroying even with "
            "every decision gate passed, the summary must say plainly that "
            "the play does not work as constructed and carry the House "
            "View's alternative direction or no-entry recommendation; gates "
            "manage genuine uncertainty and must never be presented as a "
            "path to a play the report's own corrected numbers have killed."
        )
        house_scenario_rule = (
            " Every figure a scenario cites for a quantity carried in the "
            "House View's \"Canonical figures\" table must match that table; "
            "scenario-specific deviations from a canonical figure must be "
            "stated as explicit assumption changes against it, never as "
            "silently different baselines."
        )
        house_reconciliation_rule = (
            " If the conflict scan records a valuation-baseline contradiction "
            "(for example the valuation section's own Base case disagreeing "
            "with a scenario-analysis Base case), the reconciliation must "
            "state explicitly which baseline the report's headline figures "
            "follow; unless a ruling says otherwise, the red-team-corrected "
            "scenario baseline is authoritative. If the House View carries an "
            "\"Amendments after red-team review\" section, the ACCEPT entry "
            "for each memo argument that section answers must point to the "
            "corresponding amendment (\"corrected in the House View "
            "Amendments\") — do not invent new qualifying claims to salvage a "
            "problem the amendment has already corrected away."
        )

    system = _SYSTEM
    if arithmetic.strip():
        system += "\n- " + _ARITHMETIC_AUTHORITY_RULE.replace("\n", "\n  ")
        system += (
            "\n- When you mark a figure as confirmed by the deterministic "
            "recomputation, prefer the client-facing tag "
            "\"(recomputation-verified)\" over any wording that names an "
            "internal verification artifact or step."
        )

    # Call 1: reconciliation, then the executive summary that depends on it.
    prompt_one = (
        header
        + "Write two blocks, in this order, separated by the exact line "
        f"{_BLOCK_DELIMITER} on its own:\n\n"
        "BLOCK 1 — Reconciliation. Address every Argument in the red-team memo, "
        "one numbered item per argument, in order. For each: either ACCEPT it "
        "and state exactly how the report's conclusion is adjusted as a result, "
        "or REBUT it with a cited reason drawn from the sections. Silence on "
        "an argument is not permitted. Then address the memo's Decision gates: "
        "state which gates the evidence currently satisfies and which remain "
        "open. Block 1 must be complete in itself: never defer to, reference, "
        "or promise content from Block 2 (no \"the summary will reflect "
        "this\")." + house_reconciliation_rule + "\n\n"
        "BLOCK 2 — Executive Summary. Pyramid-style: the conclusion first, then "
        "the key supporting findings. The conclusion must be gated, not a flat "
        "yes/no: state the necessary preconditions for entry (drawn from the "
        "decision gates that remain open), and that absent a credible plan to "
        "meet them, entry is not advised. The summary must be consistent with "
        "Block 1 — every accepted argument's adjustment shows up here."
        + house_summary_rule + "\n\n"
        + context
    )
    first = llm.complete(system=system, prompt=prompt_one, max_tokens=4096)
    reconciliation, summary = _split_blocks(first)
    if not _summary_is_sound(summary):
        # One bounded retry with the structural requirement restated. A broken
        # summary slot (delimiter skipped, or the fallback split landing inside
        # the reconciliation) is a delivery-blocking defect, so it is worth a
        # second completion rather than a placeholder.
        retry = llm.complete(
            system=system,
            prompt=(
                header
                + "Your previous attempt did not yield a separable executive "
                "summary. Write ONLY the Executive Summary block now — "
                "pyramid-style, conclusion first, gated, consistent with the "
                "reconciliation below. Do not write reconciliation items, "
                "ACCEPT/REBUT entries, or any block label."
                + house_summary_rule
                + "\n\n----- RECONCILIATION (already final) -----\n"
                + reconciliation
                + "\n----- END RECONCILIATION -----\n\n"
                + context
            ),
            max_tokens=2048,
        )
        if _summary_is_sound(retry):
            summary = retry
        else:
            summary = (
                "The executive summary could not be produced in a separable "
                "form on this run. The authoritative conclusion is stated in "
                "the House View (Part I); the verdict there prevails."
            )

    # Call 2: scenario analysis, independent of the first call's output.
    prompt_two = (
        header
        + "Write a Scenario Analysis block: optimistic, base, and pessimistic "
        "cases, each with the assumptions that separate it from the others and "
        "what it implies for the gated conclusion. Mark any scenario "
        "probability \"(subjective)\". Do not restate the sections."
        + house_scenario_rule + "\n\n"
        + context
    )
    scenarios = llm.complete(system=system, prompt=prompt_two, max_tokens=2048)

    return EditorialBlocks(
        executive_summary=_strip_block_label(summary),
        reconciliation=_strip_block_label(reconciliation),
        scenarios=_strip_block_label(scenarios),
    )


_BLOCK_LABEL_RE = re.compile(
    r"^\s*\**\s*block\s+\d+\s*[—–:-].*?\**\s*$", re.IGNORECASE
)


def _strip_block_label(text: str) -> str:
    """Drop a leading prompt-label echo such as ``**BLOCK 1 — Reconciliation**``.

    Models sometimes repeat the block labels used to structure the request.
    The labels are scaffolding, not content; the assembler supplies the real
    headings, so a leading label line is removed before assembly.
    """
    lines = text.strip().splitlines()
    while lines and _BLOCK_LABEL_RE.match(lines[0]):
        lines = lines[1:]
        while lines and not lines[0].strip():
            lines = lines[1:]
    return "\n".join(lines).strip()


def _split_blocks(text: str) -> tuple[str, str]:
    """Split the first editorial completion into (reconciliation, summary).

    The model is instructed to emit the delimiter between the two blocks. If
    it does not, fall back to splitting on an executive-summary heading; if
    that also fails, keep the whole text as the reconciliation and emit an
    explicit placeholder summary — a visible defect beats a silently
    misassembled report.
    """
    if _BLOCK_DELIMITER in text:
        first, _, second = text.partition(_BLOCK_DELIMITER)
        return first, second
    # Fallback: split on a *line-anchored* summary heading or block label only.
    # A mid-sentence mention ("the Executive Summary will reflect this") must
    # never be treated as the boundary — that failure mode shipped a
    # reconciliation fragment in the summary slot once.
    match = _SUMMARY_HEADING_RE.search(text)
    if match and match.start() > 0:
        return text[: match.start()], text[match.start() :]
    return text, (
        "Executive summary could not be separated from the reconciliation "
        "output; see the Reconciliation section for the editor's full text."
    )


# Line-anchored executive-summary boundary: a Markdown heading or a bare/bold
# "BLOCK 2 — Executive Summary" label at the start of a line. Prose mentions of
# the words "executive summary" inside a sentence do not match.
_SUMMARY_HEADING_RE = re.compile(
    r"^(?:#{1,3}\s*)?\**\s*(?:block\s+2\s*[—–:-]\s*)?executive\s+summary\s*\**\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# Telltales that reconciliation content leaked into the summary slot.
_RECONCILIATION_TELLTALE_RE = re.compile(
    r"^\s*\**\s*Argument\s+\d+|^\s*(?:ACCEPT|REBUT)\b|\bwill reflect this\b",
    re.IGNORECASE | re.MULTILINE,
)


def _summary_is_sound(summary: str) -> bool:
    """Reject a summary slot that is empty, a placeholder, or leaked memo items.

    The summary must read as a standalone conclusion: non-trivial length, no
    ACCEPT/REBUT reconciliation entries, no numbered red-team arguments, and no
    deferral phrasing ("Block 2 will reflect...").
    """
    text = summary.strip()
    if len(text) < 200:
        return False
    if "block 2" in text.lower():
        return False
    return not _RECONCILIATION_TELLTALE_RE.search(text)
