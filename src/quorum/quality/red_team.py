"""Red-team gate.

This gate attacks the argument rather than the facts. It reads the full set
of drafted sections — since v0.4, the *revised* sections that came out of the
synthesis loop's revision round — and the supervising partner's final House
View, and produces a "Dissenting View": the strongest case against the
report's thesis, the weakest evidence it leans on, the risks that would
invalidate it, the evidence that would force a different conclusion, and —
for the editor's decision-gate conclusion — the necessary preconditions for
entry distilled from that evidence, checked for internal coherence (a gate
set in which passing one gate makes another unsatisfiable is itself a
finding, as is a gate set propping up a play the report's own corrected
numbers have killed). Since v0.4.1 the coherence check self-executes: a gate
the check kills or finds redundant must be removed from (or redefined in) the
memo's own final gate list, with a "Gate-set changes" note recording the
disposition — a real v0.4 memo declared a gate dead and then presented it
intact, leaving the contradiction for the reader. The House View is a
first-class target: the choice of play and its volume bridge are attacked
alongside the sections. The editor must either answer each point or accept it
explicitly in the report's reconciliation, and the synthesis gate's
post-red-team amendment pass corrects the canonical record when the memo
proves a canonical-grade error.
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
your output. The ban explicitly covers: skill directory names (hyphenated
identifiers such as a "seven-powers-analyst" — say "the Seven Powers
analysis" instead), engine file paths and artifact names (anything like
gates/, engagements/, or a *.md filename), and production-line jargon (seat,
adjudication order, pipeline, orchestrator). Use client-facing consulting
language throughout: "the supervising partner's ruling", "the dissenting
memo", "the engagement bundle"."""


def challenge(sections: dict[str, str], llm: LLM, house_view: str | None = None) -> str:
    """Return a "Dissenting View" memo over the drafted sections.

    ``sections`` maps each **human-readable section title** (as it appears in
    the deliverable) to its drafted text — the caller must not pass internal
    analyst keys, because the memo is embedded verbatim in the report and the
    memo references sections by these titles. ``house_view``, when supplied,
    is the supervising partner's House View ruling: the single selected play,
    the adjudication of the framework recommendations, and the volume bridge.
    The red team attacks the ruling with the same hostility as the sections —
    the choice of play, the rejections, and the bridge arithmetic are all
    legitimate targets.

    The memo closes with a "Decision gates" part: the evidence that would
    overturn the thesis, recast as the necessary preconditions a go decision
    must satisfy. The editor builds the gated conclusion from it.
    """
    body = "\n\n".join(f"### {title}\n{text}" for title, text in sections.items())
    house_block = ""
    if house_view:
        house_block = (
            "----- BEGIN HOUSE VIEW (the supervising partner's ruling; attack "
            "it too) -----\n"
            f"{house_view}\n"
            "----- END HOUSE VIEW -----\n\n"
        )
    prompt = (
        "Read every section below, then write a memo titled \"Dissenting View\" "
        "with exactly these parts:\n\n"
        "1. The five strongest arguments against the report's central thesis"
        + (
            " — including, where warranted, the House View's choice of play, "
            "any framework recommendation it rejected too cheaply, and any "
            "gap in its volume bridge to the market sizing"
            if house_view
            else ""
        )
        + ".\n"
        "2. The weakest data the report relies on (name the specific claims and "
        "why they are weak).\n"
        "3. The key risks that would invalidate the conclusions.\n"
        "4. What evidence, if found, would overturn the thesis.\n"
        "5. Decision gates — distill part 4 into a checklist of necessary "
        "preconditions a go decision must satisfy before the report's "
        "recommendation is safe to act on. Each gate is one concrete, "
        "verifiable condition (what must be demonstrated, secured, or ruled "
        "out); state how many of the gates must hold, and which are "
        "non-negotiable. Then check the gate set for internal coherence: "
        "does passing one gate render another unsatisfiable or moot (for "
        "example, a cost gate whose ceiling, even when met, still cannot "
        "deliver the cost-advantage margin a second gate demands)? Name any "
        "such pair and say which gate the contradiction kills. Iron rule — "
        "the coherence check's verdicts must be APPLIED to the gate "
        "checklist this memo finally presents: a gate the check kills or "
        "finds redundant is removed from the list or redefined, never left "
        "standing, and immediately after the checklist a \"Gate-set "
        "changes\" note records each original gate and why it was removed "
        "or redefined. A memo whose final gate list still carries a gate "
        "its own coherence check killed is defective. Finally, test the "
        "surviving gates against the report's own corrected numbers: if the "
        "base case is negative or value-destroying even with every gate "
        "passed, say so — a gate set that exists only to keep a dead play "
        "on life support is itself the finding. This list is the raw "
        "material for the editor's gated conclusion.\n\n"
        "Keep it concrete and reference the sections by their titles as given.\n\n"
        f"{house_block}"
        "----- BEGIN SECTIONS -----\n"
        f"{body}\n"
        "----- END SECTIONS -----"
    )
    return llm.complete(system=_SYSTEM, prompt=prompt, max_tokens=4096)
