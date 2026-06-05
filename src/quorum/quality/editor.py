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
altered.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..llm import LLM

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
  human-readable titles given in the material."""


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
) -> EditorialBlocks:
    """Produce the three editorial blocks for the assembled report.

    ``sections`` maps each **human-readable section title** to its
    fact-checked text; ``dissent`` is the red team's full memo, including its
    "Decision gates" part. Two completions are made — (1) reconciliation plus
    executive summary, (2) scenario analysis — so no single output needs to
    carry the whole report and the provider's output ceiling stops being a
    truncation risk.

    The reconciliation is written first within the first call so the
    executive summary can be required to reflect its outcomes: a gated
    conclusion ("entry is advisable only if the following preconditions are
    met ...") rather than a flat yes/no that ignores accepted objections.
    """
    header = (
        f"Engagement: {engagement.industry} in {engagement.region}, "
        f"depth {engagement.depth}, written in {engagement.language}.\n\n"
    )
    context = (
        "----- BEGIN FACT-CHECKED SECTIONS (context only; embedded verbatim "
        "elsewhere) -----\n"
        f"{_condense(sections)}\n"
        "----- END SECTIONS -----\n\n"
        "----- BEGIN RED-TEAM MEMO (reproduced verbatim elsewhere) -----\n"
        f"{dissent}\n"
        "----- END RED-TEAM MEMO -----"
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
        "open.\n\n"
        "BLOCK 2 — Executive Summary. Pyramid-style: the conclusion first, then "
        "the key supporting findings. The conclusion must be gated, not a flat "
        "yes/no: state the necessary preconditions for entry (drawn from the "
        "decision gates that remain open), and that absent a credible plan to "
        "meet them, entry is not advised. The summary must be consistent with "
        "Block 1 — every accepted argument's adjustment shows up here.\n\n"
        + context
    )
    first = llm.complete(system=_SYSTEM, prompt=prompt_one, max_tokens=4096)
    reconciliation, summary = _split_blocks(first)

    # Call 2: scenario analysis, independent of the first call's output.
    prompt_two = (
        header
        + "Write a Scenario Analysis block: optimistic, base, and pessimistic "
        "cases, each with the assumptions that separate it from the others and "
        "what it implies for the gated conclusion. Mark any scenario "
        "probability \"(subjective)\". Do not restate the sections.\n\n"
        + context
    )
    scenarios = llm.complete(system=_SYSTEM, prompt=prompt_two, max_tokens=2048)

    return EditorialBlocks(
        executive_summary=summary.strip(),
        reconciliation=reconciliation.strip(),
        scenarios=scenarios.strip(),
    )


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
    lowered = text.lower()
    for marker in ("## executive summary", "# executive summary", "executive summary"):
        index = lowered.find(marker)
        if index > 0:
            return text[:index], text[index:]
    return text, (
        "Executive summary could not be separated from the reconciliation "
        "output; see the Reconciliation section for the editor's full text."
    )
