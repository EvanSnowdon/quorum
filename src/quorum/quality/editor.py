"""Chief-editor gate.

The final gate owns the deliverable. It assembles the validated sections and
the red team's dissent into a single report structured by the Minto Pyramid
Principle: the answer first, then the support, then the scenarios, then the
dissent in full, then the evidence appendix. It reconciles contradictions
between sections and writes the executive summary last.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..llm import LLM

if TYPE_CHECKING:  # avoid a runtime import cycle with the orchestrator
    from ..orchestrator import Engagement

_SYSTEM = """\
You are the chief editor on a Quorum engagement, working in the tradition of
the Minto Pyramid Principle: lead with the answer, then marshal the support
beneath it. You own the final report.

Your responsibilities:
- Open with an executive summary that states the conclusion first, then the
  key supporting findings. Write it last, but place it first.
- Reconcile contradictions between sections rather than printing both; where
  analysts genuinely disagree, say so and explain the call.
- Preserve every claim's [DATA]/[INFERENCE] label and confidence score; do not
  launder an inference into a fact.
- Keep the reader's time sacred. Cut anything that does not serve a decision.
- Carry the limitations forward honestly. The report's credibility rests on it."""


def compile_report(
    engagement: "Engagement",
    sections: dict[str, str],
    dissent: str,
    llm: LLM,
    max_tokens: int = 8000,
) -> str:
    """Assemble the final report from the sections and the dissent memo.

    The report follows a fixed top-level structure: executive summary
    (conclusion first), the body sections, a scenario analysis (optimistic /
    base / pessimistic), the red team's Dissenting View reproduced verbatim,
    and a data-and-confidence appendix.
    """
    body = "\n\n".join(f"### Section: {key}\n{text}" for key, text in sections.items())
    prompt = (
        f"Engagement: {engagement.industry} in {engagement.region}, "
        f"depth {engagement.depth}, written in {engagement.language}.\n\n"
        "Compile the working papers below into one report with this exact "
        "top-level structure:\n\n"
        "1. Executive Summary — the conclusion first, then the supporting "
        "findings, pyramid-style.\n"
        "2. Body — the analysis, organized into a clean section flow drawn from "
        "the working papers (merge overlaps, reconcile conflicts).\n"
        "3. Scenario Analysis — optimistic, base, and pessimistic cases with "
        "the assumptions that separate them.\n"
        "4. Dissenting View — reproduce the red team's memo below verbatim under "
        "this heading.\n"
        "5. Data & Confidence Appendix — the key [DATA] claims with sources and "
        "the load-bearing [INFERENCE] claims with their confidence scores.\n\n"
        "Preserve all claim labels and confidence scores throughout.\n\n"
        "----- BEGIN WORKING PAPERS -----\n"
        f"{body}\n"
        "----- END WORKING PAPERS -----\n\n"
        "----- BEGIN DISSENTING VIEW (reproduce verbatim in section 4) -----\n"
        f"{dissent}\n"
        "----- END DISSENTING VIEW -----"
    )
    return llm.complete(system=_SYSTEM, prompt=prompt, max_tokens=max_tokens)
