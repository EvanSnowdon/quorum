"""Red-team gate.

The second quality gate attacks the argument rather than the facts. It reads
the full set of drafted sections and produces a "Dissenting View": the
strongest case against the report's thesis, the weakest evidence it leans on,
the risks that would invalidate it, the evidence that would force a different
conclusion, and — for the editor's decision-gate conclusion — the necessary
preconditions for entry distilled from that evidence. The editor must either
answer each point or accept it explicitly in the report's reconciliation.
"""

from __future__ import annotations

from ..llm import LLM

_SYSTEM = """\
You are the red team on a Quorum engagement. Your job is to attack the
report's argument, not to be agreeable. Assume the analysts are competent and
still wrong somewhere; find where. Attack reasoning, assumptions, and the
source mix — not spelling.

Be specific and adversarial. Cite the sections you are challenging. A vague
objection is useless; name the claim, the flaw, and what would settle it.

Your memo is reproduced verbatim in the client deliverable. Refer to sections
only by the human-readable titles given in the material; never use internal
module names, analyst keys, field names, or any other internal identifier in
your output."""


def challenge(sections: dict[str, str], llm: LLM) -> str:
    """Return a "Dissenting View" memo over the drafted sections.

    ``sections`` maps each **human-readable section title** (as it appears in
    the deliverable) to its drafted text — the caller must not pass internal
    analyst keys, because the memo is embedded verbatim in the report and the
    memo references sections by these titles.

    The memo closes with a "Decision gates" part: the evidence that would
    overturn the thesis, recast as the necessary preconditions a go decision
    must satisfy. The editor builds the gated conclusion from it.
    """
    body = "\n\n".join(f"### {title}\n{text}" for title, text in sections.items())
    prompt = (
        "Read every section below, then write a memo titled \"Dissenting View\" "
        "with exactly these parts:\n\n"
        "1. The five strongest arguments against the report's central thesis.\n"
        "2. The weakest data the report relies on (name the specific claims and "
        "why they are weak).\n"
        "3. The key risks that would invalidate the conclusions.\n"
        "4. What evidence, if found, would overturn the thesis.\n"
        "5. Decision gates — distill part 4 into a checklist of necessary "
        "preconditions a go decision must satisfy before the report's "
        "recommendation is safe to act on. Each gate is one concrete, "
        "verifiable condition (what must be demonstrated, secured, or ruled "
        "out); state how many of the gates must hold, and which are "
        "non-negotiable. This list is the raw material for the editor's "
        "gated conclusion.\n\n"
        "Keep it concrete and reference the sections by their titles as given.\n\n"
        "----- BEGIN SECTIONS -----\n"
        f"{body}\n"
        "----- END SECTIONS -----"
    )
    return llm.complete(system=_SYSTEM, prompt=prompt, max_tokens=4096)
