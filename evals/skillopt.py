"""Skill optimization: treat a ``SKILL.md`` body as a tunable parameter.

A Quorum analyst's behaviour is governed almost entirely by the prose in its
``SKILL.md`` — the method steps, the evidence rules, the output contract. That
makes the skill body a *parameter* of the system, and a parameter can be
optimized. This module is the closed loop that does it: propose a rewrite of a
skill, run it against a fixed set of evaluation contexts, score the resulting
reports, and keep the rewrite only if it measurably beats the incumbent.

The design is intentionally a "prompt-optimization as search" loop, in the
spirit of automated prompt search methods (APE / OPRO): the objective is a
black-box score, the proposer is itself an LLM, and acceptance is gated on a
quantitative delta rather than a vibe. Nothing here is heuristic about *whether*
to accept — only the proposal step is generative.

This is a skeleton: the orchestration, the accept/reject gate, and the I/O are
complete and readable, but the per-context evaluation that turns a candidate
skill into a scored report (:func:`_avg_score`) is left as a documented TODO so
the engine team can wire it to the real engagement runner. The loop is safe to
import and reason about today; it will not silently produce a wrong "winner"
because the gate refuses to accept a candidate it cannot score.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from quorum.skills_loader import load_skill

if TYPE_CHECKING:  # keep the provider stack off this module's import path
    from quorum.llm import LLM

_PROPOSER_SYSTEM = """\
You are optimizing the instructions a strategy analyst follows. You will be given
the current methodology text (a SKILL.md body) and the kinds of analysis it must
produce. Propose a single improved version of the SAME methodology.

Rules:
- Keep the method intact. You are sharpening instructions, not inventing a new
  framework or renaming the skill.
- Preserve every hard rule: the [DATA]/[INFERENCE] labeling with confidence, the
  source-first discipline, the MECE and output-format requirements.
- Improve clarity, specificity, and the rigor of the evidence and output rules.
  Cut vagueness; add precision a junior analyst could not misread.
- Return ONLY the rewritten methodology body. No preamble, no commentary, no code
  fences."""


@dataclass
class OptimizationResult:
    """The outcome of an optimization run for one skill.

    Carries enough to audit the loop: the chosen body, the score it earned, the
    baseline it had to beat, and the per-round trace of what was proposed and
    whether it was accepted.
    """

    skill_name: str
    best_body: str
    best_score: float
    baseline_score: float
    rounds: list[dict[str, object]]

    @property
    def improved(self) -> bool:
        """Whether the loop found a body strictly better than the baseline."""
        return self.best_score > self.baseline_score


def optimize(
    skill_name: str,
    test_contexts: list[str],
    rounds: int = 3,
    llm: "LLM | None" = None,
) -> str:
    """Optimize one skill's body against a fixed evaluation set and return it.

    The loop:

    1. Load the incumbent skill body and score it across ``test_contexts`` —
       this is the bar every candidate must clear.
    2. For ``rounds`` iterations, ask the proposer model for a rewrite of the
       *current best* body, score the candidate the same way, and accept it only
       if its average score is strictly higher. Acceptance is monotonic: the best
       body only ever moves uphill, so a bad proposal cannot regress the skill.
    3. Return the best body found. The caller decides whether to persist it over
       the original ``SKILL.md``; this function does not write to disk.

    ``test_contexts`` is the held-out evaluation set — each entry is an
    engagement-style brief or a rendered context the skill will be exercised on.
    ``llm`` defaults to the firm's lead model, which both proposes rewrites and
    (via the scorecard) judges them.

    Returns the best body as a string. When evaluation is not yet wired (the
    :func:`_avg_score` TODO), every candidate ties the baseline, no rewrite clears
    the strict-improvement bar, and the original body is returned unchanged —
    a safe no-op rather than a blind overwrite.
    """
    if llm is None:
        from quorum.llm import LLM  # lazy import: no provider cost unless we run

        llm = LLM.lead()

    incumbent = load_skill(skill_name)
    best_body = incumbent.body
    baseline_score = _avg_score(best_body, incumbent.description, test_contexts, llm)
    best_score = baseline_score

    trace: list[dict[str, object]] = []
    for round_index in range(1, rounds + 1):
        candidate = _propose(best_body, incumbent.description, test_contexts, llm)
        candidate_score = _avg_score(candidate, incumbent.description, test_contexts, llm)
        accepted = candidate_score > best_score
        if accepted:
            best_body = candidate
            best_score = candidate_score
        trace.append(
            {
                "round": round_index,
                "candidate_score": candidate_score,
                "best_score": best_score,
                "accepted": accepted,
            }
        )

    # The full result is assembled for callers that want the audit trail; the
    # public contract is the optimized body, so that is what is returned.
    _ = OptimizationResult(
        skill_name=skill_name,
        best_body=best_body,
        best_score=best_score,
        baseline_score=baseline_score,
        rounds=trace,
    )
    return best_body


def _propose(
    current_body: str,
    description: str,
    test_contexts: list[str],
    llm: "LLM",
) -> str:
    """Ask the proposer model for one improved version of ``current_body``.

    The contexts are summarized into the prompt so the rewrite is tuned to the
    work the skill actually has to do, not improved in the abstract.
    """
    context_brief = _summarize_contexts(test_contexts)
    prompt = (
        "## Skill purpose\n"
        f"{description}\n\n"
        "## Current methodology body\n"
        f"{current_body}\n\n"
        "## Analyses this skill must produce\n"
        f"{context_brief}\n\n"
        "Rewrite the methodology body per your instructions. Return the body only."
    )
    return llm.complete(system=_PROPOSER_SYSTEM, prompt=prompt, max_tokens=4096).strip()


def _summarize_contexts(test_contexts: list[str]) -> str:
    """Render the evaluation contexts as a compact bullet list for the proposer."""
    if not test_contexts:
        return "- (no specific contexts supplied; optimize for general rigor)"
    return "\n".join(f"- {context.strip()}" for context in test_contexts)


def _avg_score(
    body: str,
    description: str,
    test_contexts: list[str],
    llm: "LLM",
) -> float:
    """Average evaluation score for a candidate skill body across the contexts.

    This is the objective the optimizer climbs. For each context it must:

      1. Build an analyst that runs ``body`` as its methodology (an
         :class:`~quorum.analyst.Analyst` whose skill body is overridden with the
         candidate, dispatched under a :class:`~quorum.analyst.TaskContract`
         derived from the context), or run a full engagement via
         :class:`~quorum.orchestrator.ManagingPartner` for end-to-end scoring.
      2. Capture the produced section / report markdown.
      3. Score it with :func:`evals.scorecard.score_report` and read the
         ``overall`` axis (optionally weighting the axes this skill is meant to
         move, e.g. ``citation_accuracy`` for a sourcing-heavy method).

    The mean of those per-context overalls is the candidate's fitness.

    TODO: wire steps 1-3 to the engagement runner and the scorecard. Until then
    this returns a constant so the loop is exercisable and, critically, *safe*:
    a constant objective means no candidate ever strictly beats the baseline, so
    :func:`optimize` returns the original body untouched rather than accepting an
    unmeasured rewrite. Do not replace this with a random or always-improving
    stub — the acceptance gate's correctness depends on this being a real,
    comparable score once implemented.
    """
    # Placeholder objective. See the TODO above: returning a constant keeps the
    # accept-on-strict-improvement gate sound while evaluation is unimplemented.
    _ = (body, description, test_contexts, llm)
    return 0.0
