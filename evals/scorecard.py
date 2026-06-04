"""Report scorecard: LLM-as-judge grading plus an offline heuristic baseline.

Quorum ships a quality pipeline (fact-check, red team, chief editor) that runs
*inside* an engagement. This module is the layer *outside* the engagement: it
grades a finished report so the firm can compare runs, regression-test a skill
change, and drive the optimization loop in :mod:`evals.skillopt`.

Two graders are provided, deliberately at different cost/fidelity points:

``score_report``
    A RACE/FACT-style LLM-as-judge. It hands the whole report to a model under a
    rubric and parses a strict JSON verdict back. This is the high-fidelity
    signal, but it costs a model call and is non-deterministic, so it is never
    on the import path of a unit test.

``heuristic_metrics``
    A pure-Python structural read of the same report — claim-label counts,
    citation count, word count, section count. No model, no network, fully
    deterministic. It is the cheap proxy the test suite and a CI smoke check can
    rely on, and a useful sanity floor next to the judge's verdict.

The judge rubric mirrors the RACE family of report-quality evals (relevance,
coverage, structure) crossed with the FACT axis (citation and factual
discipline) that Quorum cares about specifically, plus a localization axis for
the firm's region-first sourcing rule.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # avoid importing the provider stack on this module's import path
    from quorum.llm import LLM

# The six axes the judge scores, each 0-100. Kept as a module constant so the
# parser, the prompt, and any caller averaging the scores all agree on the keys.
SCORE_DIMENSIONS: tuple[str, ...] = (
    "coverage",
    "depth",
    "structure",
    "citation_accuracy",
    "factual_consistency",
    "localization",
)

JUDGE_SYSTEM = """\
You are a senior quality reviewer at a strategy consulting firm, grading a
market-research report a junior team produced. You are exacting and unsentimental:
a competent-looking report with shallow analysis or unsourced numbers scores low,
not middling. You grade only what is on the page; you do not reward intent.

Score the report on each axis from 0 to 100 (100 = partner-ready, 50 = usable
with rework, 0 = unusable):

- coverage: Are the questions a decision-maker would ask actually answered —
  market size, demand, competition, economics, risks — with no large blind spot?
- depth: Does the analysis reason to a conclusion, or only describe? Reward
  mechanisms, trade-offs, and a defended thesis; penalize list-making.
- structure: Is it built on the pyramid principle — answer first, support
  beneath — with a clean, MECE section flow and no repetition?
- citation_accuracy: Is every figure attributed to a named source, and do the
  [DATA] / [INFERENCE] labels carry confidence and match what they tag?
- factual_consistency: Do the numbers, shares, and growth rates agree across
  sections and within tables, with no internal contradictions?
- localization: Does it use region-appropriate, ideally first-party local
  sources and reflect the specific market, rather than generic global filler?

Return ONLY a JSON object, no prose around it, with exactly these keys: the six
axis names above (integer 0-100) and a "notes" key (a short string naming the
single biggest weakness and the single biggest strength). Do not wrap the JSON
in code fences or commentary."""

_JUDGE_INSTRUCTION = (
    "Grade the report below against the rubric in your instructions. Respond with "
    "the JSON verdict only.\n\n"
    "----- BEGIN REPORT -----\n"
    "{report}\n"
    "----- END REPORT -----"
)

# Pulls a JSON object out of a model reply even when it is fenced as ```json ...
# ``` or padded with stray prose. Non-greedy from the first brace to the last so
# a trailing sentence does not break the parse.
_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.S)
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.S)

# Heuristic patterns. The label tag is matched in both the firm's canonical
# `[DATA; high]` form and the looser `[DATA] 0.8` form some skill bodies emit,
# so the offline metric counts labels regardless of which the writer used.
_LABEL_RE = re.compile(r"\[\s*(DATA|INFERENCE)\b", re.IGNORECASE)
_DATA_LABEL_RE = re.compile(r"\[\s*DATA\b", re.IGNORECASE)
_INFERENCE_LABEL_RE = re.compile(r"\[\s*INFERENCE\b", re.IGNORECASE)
_URL_RE = re.compile(r"https?://\S+")
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+\S", re.M)


def score_report(report_md: str, llm: "LLM | None" = None) -> dict[str, Any]:
    """Grade a report with the LLM-as-judge rubric and return a parsed verdict.

    ``report_md`` is the rendered report. ``llm`` is an optional configured
    :class:`~quorum.llm.LLM`; when omitted, the firm's lead model is used, since
    judging is a lead-grade task. The return is a dict with the six integer axis
    scores from :data:`SCORE_DIMENSIONS`, a ``notes`` string, and an
    ``overall`` mean of the axes for convenience.

    The model is asked for strict JSON; :func:`_parse_verdict` is tolerant of the
    common ways a model wraps that JSON (code fences, leading prose). A reply
    that cannot be parsed at all raises :class:`ValueError` rather than returning
    a silently-wrong score — a broken judge must be visible to the caller.
    """
    if llm is None:
        from quorum.llm import LLM  # lazy: keep the provider stack off import

        llm = LLM.lead()

    prompt = _JUDGE_INSTRUCTION.format(report=report_md)
    raw = llm.complete(system=JUDGE_SYSTEM, prompt=prompt, max_tokens=1024)
    verdict = _parse_verdict(raw)
    verdict["overall"] = _overall(verdict)
    return verdict


def _parse_verdict(raw: str) -> dict[str, Any]:
    """Parse a judge reply into a normalized verdict dict.

    Tolerates a ```json``` fence and surrounding prose, then validates that the
    six axes are present and coerces them to clamped integers. ``notes`` is
    carried through as a string; any extra keys the model invents are dropped so
    the shape downstream is stable.
    """
    payload = _extract_json(raw)
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError(f"judge did not return parseable JSON: {exc}\nraw reply:\n{raw}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"judge returned a non-object JSON value: {data!r}")

    verdict: dict[str, Any] = {}
    for axis in SCORE_DIMENSIONS:
        if axis not in data:
            raise ValueError(f"judge verdict missing required axis {axis!r}; got {sorted(data)}")
        verdict[axis] = _clamp_score(data[axis])
    verdict["notes"] = str(data.get("notes", "")).strip()
    return verdict


def _extract_json(raw: str) -> str:
    """Return the JSON substring from a model reply, unwrapping fences first."""
    fenced = _FENCE_RE.search(raw)
    candidate = fenced.group(1) if fenced else raw
    block = _JSON_BLOCK_RE.search(candidate)
    if block is None:
        raise ValueError(f"no JSON object found in judge reply:\n{raw}")
    return block.group(0)


def _clamp_score(value: Any) -> int:
    """Coerce a score to an integer in [0, 100], rejecting non-numerics."""
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"score value is not numeric: {value!r}") from exc
    return max(0, min(100, round(number)))


def _overall(verdict: dict[str, Any]) -> float:
    """Mean of the six axis scores, rounded to one decimal."""
    scores = [verdict[axis] for axis in SCORE_DIMENSIONS]
    return round(sum(scores) / len(scores), 1)


def heuristic_metrics(report_md: str) -> dict[str, int]:
    """Compute deterministic structural metrics for a report, no model required.

    This is the offline counterpart to :func:`score_report`: it never calls a
    provider, so the test suite and a CI smoke check can assert against it. The
    metrics are blunt proxies for the judge's axes — they say whether a report
    *carries the machinery* of a disciplined report (labeled claims, citations,
    sections), not whether the analysis is good.

    Returned keys:

    - ``data_claims`` — count of ``[DATA...]`` label tags.
    - ``inference_claims`` — count of ``[INFERENCE...]`` label tags.
    - ``labeled_claims`` — total of the two above.
    - ``citations`` — count of ``http(s)://`` URLs (the citation proxy).
    - ``words`` — whitespace-delimited token count of the report.
    - ``sections`` — count of Markdown ATX headings (``#`` .. ``######``).
    """
    data_claims = len(_DATA_LABEL_RE.findall(report_md))
    inference_claims = len(_INFERENCE_LABEL_RE.findall(report_md))
    citations = len(_URL_RE.findall(report_md))
    words = len(report_md.split())
    sections = len(_HEADING_RE.findall(report_md))
    return {
        "data_claims": data_claims,
        "inference_claims": inference_claims,
        "labeled_claims": data_claims + inference_claims,
        "citations": citations,
        "words": words,
        "sections": sections,
    }
