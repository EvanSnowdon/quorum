"""Claim labeling: the [DATA] / [INFERENCE] discipline, made mechanical.

Every factual sentence in a Quorum artifact must carry a label and a confidence
level (see docs/architecture.md, "The data spine"):

- ``[DATA]``  — traceable to a spine response or cited source.
- ``[INFERENCE]`` — derived by reasoning from labeled data; states its inputs.

This module gives the rest of the engine one place to render those labels
consistently and to check that prose carries them — the fact-check and editor
gates lint against the same functions workers use to write, so the writing side
and the checking side can never drift apart.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict


class ClaimLabel(str, Enum):
    """The two claim kinds the system recognizes."""

    DATA = "DATA"
    INFERENCE = "INFERENCE"


class Confidence(str, Enum):
    """Confidence attached to every labeled claim."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# Matches a label tag at the start of a claim line, e.g. "[DATA; high]" or
# "[INFERENCE; low]". Case-insensitive on the label and confidence words.
_LABEL_RE = re.compile(
    r"\[\s*(DATA|INFERENCE)\s*;\s*(high|medium|low)\s*\]",
    re.IGNORECASE,
)


class Claim(BaseModel):
    """A single labeled claim: the text plus its provenance.

    ``sources`` lists the URLs (or source names) backing a ``DATA`` claim;
    ``inputs`` lists the upstream claims or figures an ``INFERENCE`` reasons from.
    Both default empty so a claim can be constructed incrementally, but the
    gates expect a ``DATA`` claim to cite at least one source and an
    ``INFERENCE`` to state at least one input.
    """

    model_config = ConfigDict(extra="forbid")

    text: str
    label: ClaimLabel
    confidence: Confidence
    sources: list[str] = []
    inputs: list[str] = []

    def render(self) -> str:
        """Render the claim as a single labeled Markdown line.

        Form: ``[LABEL; confidence] text (sources: ...)`` for data, or
        ``[INFERENCE; confidence] text (from: ...)`` for inference. Provenance is
        appended only when present.
        """
        line = f"{format_label(self.label, self.confidence)} {self.text.strip()}"
        if self.label is ClaimLabel.DATA and self.sources:
            line += f" (sources: {', '.join(self.sources)})"
        elif self.label is ClaimLabel.INFERENCE and self.inputs:
            line += f" (from: {', '.join(self.inputs)})"
        return line

    def provenance_gap(self) -> str | None:
        """Return a human-readable reason the claim lacks provenance, or None.

        Used by the fact-check gate: a ``DATA`` claim with no sources or an
        ``INFERENCE`` with no stated inputs is a finding, not valid output.
        """
        if self.label is ClaimLabel.DATA and not self.sources:
            return "DATA claim cites no source"
        if self.label is ClaimLabel.INFERENCE and not self.inputs:
            return "INFERENCE claim states no inputs"
        return None


def format_label(label: ClaimLabel, confidence: Confidence) -> str:
    """Return the canonical tag string, e.g. ``[DATA; high]``."""
    return f"[{label.value}; {confidence.value}]"


def claim_from_observation(
    text: str,
    observation: dict[str, Any],
    confidence: Confidence = Confidence.HIGH,
) -> Claim:
    """Build a ``[DATA]`` claim from a data-spine observation.

    Accepts an observation dict as produced by the data-spine modules
    (``{"year", "value", "source", "url"}``) and wires its ``url``/``source``
    into the claim's provenance. Defaults to high confidence because spine
    observations come straight from an official API.
    """
    provenance = observation.get("url") or observation.get("source")
    sources = [provenance] if provenance else []
    return Claim(
        text=text,
        label=ClaimLabel.DATA,
        confidence=confidence,
        sources=sources,
    )


def find_unlabeled_lines(markdown: str) -> list[tuple[int, str]]:
    """Return prose lines that look like claims but carry no label.

    A line is considered a candidate claim if it is non-empty body text — not a
    heading, list bullet, table row, blockquote, or code fence — and contains no
    ``[DATA; ...]`` / ``[INFERENCE; ...]`` tag. Returns ``(line_number, text)``
    pairs (1-based). This is the lint the editor gate runs over a draft;
    Design rule 6 makes an unlabeled claim a pipeline error, not a style nit.
    """
    findings: list[tuple[int, str]] = []
    in_code_fence = False
    for index, raw in enumerate(markdown.splitlines(), start=1):
        line = raw.strip()
        if line.startswith("```"):
            in_code_fence = not in_code_fence
            continue
        if in_code_fence or not _is_prose(line):
            continue
        if not _LABEL_RE.search(line):
            findings.append((index, line))
    return findings


def has_label(line: str) -> bool:
    """Return whether a line carries a claim label tag."""
    return bool(_LABEL_RE.search(line))


def _is_prose(line: str) -> bool:
    if not line:
        return False
    if line.startswith(("#", ">", "|", "-", "*", "+")):
        return False
    # Numbered list items ("1." / "2)") are structure, not standalone claims.
    if re.match(r"^\d+[.)]\s", line):
        return False
    return True
