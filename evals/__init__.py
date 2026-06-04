"""Quorum evaluation harness.

Two capabilities sit here, both *outside* an engagement (the in-engagement
quality gates live in :mod:`quorum.quality`):

- :mod:`evals.scorecard` grades a finished report — an LLM-as-judge rubric
  (:func:`~evals.scorecard.score_report`) plus a deterministic, model-free
  structural read (:func:`~evals.scorecard.heuristic_metrics`).
- :mod:`evals.skillopt` treats a ``SKILL.md`` body as a tunable parameter and
  searches for a rewrite that scores higher (:func:`~evals.skillopt.optimize`).

Only the model-free pieces are safe to pull onto a plain import path; the judge
and the optimizer reach for the provider stack lazily, when actually called.
"""

from __future__ import annotations

from .scorecard import (
    JUDGE_SYSTEM,
    SCORE_DIMENSIONS,
    heuristic_metrics,
    score_report,
)
from .skillopt import OptimizationResult, optimize

__all__ = [
    "JUDGE_SYSTEM",
    "SCORE_DIMENSIONS",
    "OptimizationResult",
    "heuristic_metrics",
    "optimize",
    "score_report",
]
