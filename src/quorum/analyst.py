"""Analysts and the task contracts they execute.

An :class:`Analyst` pairs a methodology (:class:`~quorum.skills_loader.Skill`)
with a role and the report section it owns. The orchestrator dispatches work to
an analyst as a :class:`TaskContract` — the four-element unit of work
(objective, output format, tools, boundaries) that is the system's source of
truth for what a task may consume and must produce.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field

from .llm import LLM
from .skills_loader import load_skill

# Global evidence rules appended to every analyst's system prompt. These hold
# regardless of methodology and mirror the discipline enforced by the gates.
_GLOBAL_RULES = """\
Firm-wide rules, in force for every analyst:

- Ground every number. Each factual statement carries a source inline, drawn
  from the engagement's data pack or a cited reference. Do not state a figure
  you cannot attribute.
- Label every claim. Prefix factual statements with [DATA] (traceable to a
  source) or [INFERENCE] (reasoned from labeled data), and append a confidence
  score from 0.0 to 1.0. An [INFERENCE] claim must name the inputs it reasons
  from.
- Stay MECE within your section: mutually exclusive points, collectively
  exhaustive coverage of your remit, no overlap with sibling sections.
- Write only your assigned section. Do not draft an executive summary, restate
  another analyst's section, or wander outside your objective.
- When the data pack cannot answer a question, say so plainly rather than
  filling the gap with an unlabeled guess."""


class TaskContract(BaseModel):
    """The four-element contract dispatched to an analyst.

    This is the Anthropic task-contract pattern: a worker receives a contract,
    not a conversation. The orchestrator validates the contract before dispatch
    and treats it — not the system prompt — as authoritative.
    """

    objective: str = Field(
        description="The single question this analyst must answer, with engagement context inlined."
    )
    output_format: str = Field(
        description="The exact structure of the working paper: headings, tables, length cap."
    )
    tools: list[str] = Field(
        default_factory=list,
        description="The tool allowlist for this task. Anything not listed is unavailable.",
    )
    boundaries: str = Field(
        description="Scope exclusions, tool-call budget, and hard 'do not' rules for this task."
    )


@dataclass
class Analyst:
    """A methodology expert: a skill plus the role and section it is staffed on.

    ``key`` is the stable identifier used in ``crews.yaml`` and as the working
    paper filename. ``skill`` is the *name* of the methodology skill (a
    directory under ``analyst-skills/``); the body is loaded lazily at dispatch
    time so the orchestrator can plan a crew without paying for every skill
    body up front. ``tools`` is the default allowlist for the role; the
    orchestrator may narrow it per contract.

    ``phase`` places the seat in the two-phase dispatch: phase 1 establishes
    the strategic picture, phase 2 (valuation, critique) runs after phase 1 is
    fact-checked, with the checked sections in context. ``brief`` is an
    optional seat-specific instruction the orchestrator appends to the
    contract objective.
    """

    key: str
    role: str
    section: str
    skill: str
    tools: list[str]
    phase: int = 1
    brief: str = ""

    def system_prompt(self) -> str:
        """Assemble the analyst's system prompt.

        The skill body is the methodology core; the role framing and the
        firm-wide evidence rules wrap it. The body is read here, on dispatch --
        progressive disclosure means the full methodology text enters context
        only when this analyst is actually staffed on a task, and only into this
        worker's prompt. The contract carries the specifics of the task itself
        and is supplied separately at :meth:`run` time.
        """
        skill = load_skill(self.skill)
        return (
            f"You are the {self.role} on a Quorum engagement. You own the "
            f'"{self.section}" section of the report and nothing else.\n\n'
            "Your methodology is defined by the following skill. Treat it as the "
            "authoritative procedure for your analysis:\n\n"
            f"{skill.body}\n\n"
            f"{_GLOBAL_RULES}"
        )

    def run(self, contract: TaskContract, context: str, llm: LLM) -> str:
        """Execute one task contract and return the section draft.

        The four contract elements are laid out explicitly for the model so the
        objective, required output shape, available tools, and boundaries are
        unambiguous. ``context`` carries the engagement's data pack excerpt and
        any recalled memory.

        Note on tools: a worker-side tool-calling loop is not implemented in
        v0.1. ``contract.tools`` is surfaced here as a context hint — it tells
        the analyst which sources are considered in scope — but the analyst
        reasons over the supplied ``context`` rather than issuing live calls.
        Wiring an execution loop that lets analysts query the data spine
        directly is tracked on the roadmap.
        """
        tools = ", ".join(contract.tools) if contract.tools else "none"
        prompt = (
            "## Objective\n"
            f"{contract.objective}\n\n"
            "## Output format\n"
            f"{contract.output_format}\n\n"
            "## Tools in scope\n"
            f"{tools}\n\n"
            "## Boundaries\n"
            f"{contract.boundaries}\n\n"
            "## Engagement context\n"
            f"{context}\n\n"
            "Write your section now, following the output format exactly."
        )
        # TODO: tool-call loop. Expose the tools named in `contract.tools` to the
        # model, execute them under the boundary budget, and write each official
        # response to the source ledger for the fact-check gate. For now the
        # analyst reasons over the inlined context in a single turn.
        return llm.complete(system=self.system_prompt(), prompt=prompt)
