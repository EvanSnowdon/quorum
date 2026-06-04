"""Red-team gate.

The second quality gate attacks the argument rather than the facts. It reads
the full set of drafted sections and produces a "Dissenting View": the
strongest case against the report's thesis, the weakest evidence it leans on,
the risks that would invalidate it, and the evidence that would force a
different conclusion. The editor must either answer each point or accept it
explicitly in the report's limitations.
"""

from __future__ import annotations

from ..llm import LLM

_SYSTEM = """\
You are the red team on a Quorum engagement. Your job is to attack the
report's argument, not to be agreeable. Assume the analysts are competent and
still wrong somewhere; find where. Attack reasoning, assumptions, and the
source mix — not spelling.

Be specific and adversarial. Cite the sections you are challenging. A vague
objection is useless; name the claim, the flaw, and what would settle it."""


def challenge(sections: dict[str, str], llm: LLM) -> str:
    """Return a "Dissenting View" memo over the drafted sections.

    ``sections`` maps each analyst key to its drafted section. The memo is
    written to be dropped into the report verbatim.
    """
    body = "\n\n".join(f"## Section: {key}\n{text}" for key, text in sections.items())
    prompt = (
        "Read every section below, then write a memo titled \"Dissenting View\" "
        "with exactly these parts:\n\n"
        "1. The five strongest arguments against the report's central thesis.\n"
        "2. The weakest data the report relies on (name the specific claims and "
        "why they are weak).\n"
        "3. The key risks that would invalidate the conclusions.\n"
        "4. What evidence, if found, would overturn the thesis.\n\n"
        "Keep it concrete and reference the sections by name.\n\n"
        "----- BEGIN SECTIONS -----\n"
        f"{body}\n"
        "----- END SECTIONS -----"
    )
    return llm.complete(system=_SYSTEM, prompt=prompt, max_tokens=4096)
