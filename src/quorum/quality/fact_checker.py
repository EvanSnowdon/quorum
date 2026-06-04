"""Fact-check gate.

The first quality gate re-reads a drafted section and audits its evidence
discipline: are cited figures actually attributed, are claims labeled
[DATA]/[INFERENCE] with a confidence score, is any inference dressed up as
fact, does the arithmetic in tables hold. It is a checker, not a co-author: it
must not introduce new facts or rewrite the analysis.
"""

from __future__ import annotations

from ..llm import LLM

_SYSTEM = """\
You are a fact-checker on a Quorum engagement. You audit one drafted section
for evidence discipline. You do not add facts, soften conclusions, or rewrite
the analysis — you verify and report.

Check, in order:
1. Sourcing — every figure traces to a stated source; flag any unattributed
   number.
2. Labeling — every factual statement is tagged [DATA] or [INFERENCE] with a
   0.0-1.0 confidence score; flag missing or malformed labels.
3. Mislabeling — no [INFERENCE] claim is presented as [DATA]; flag any
   reasoned figure dressed as sourced fact.
4. Arithmetic — totals, shares, and growth rates in tables are internally
   consistent; flag any that do not add up.

Introducing a new fact or estimate is itself a violation; never do it."""


def fact_check(section_md: str, llm: LLM) -> str:
    """Return a findings list for one section draft.

    Output is a markdown findings list, each item carrying a severity, so the
    editor can decide what blocks delivery and what is accepted as a limitation.
    """
    prompt = (
        "Audit the section below. Return a markdown list of findings; for each, "
        "give a severity (blocking / major / minor), quote the offending text, "
        "and state the issue. If a category is clean, say so in one line. Do "
        "not edit or rewrite the section.\n\n"
        "----- BEGIN SECTION -----\n"
        f"{section_md}\n"
        "----- END SECTION -----"
    )
    return llm.complete(system=_SYSTEM, prompt=prompt)
