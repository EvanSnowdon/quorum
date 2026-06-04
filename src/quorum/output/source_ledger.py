"""Source ledger rendering: turn spine observations into an auditable trail.

The data spine preserves raw responses under ``engagements/<id>/spine/`` so the
fact-check gate can re-verify any figure. This module renders those observations
into compact, human-readable ledger entries for inclusion in working papers and
the report's sources appendix — one line per figure, each naming the source and
the exact URL that produced it. The format is the bridge between the
data-spine output shape (``{"year", "value", "source", "url"}``) and the report
layer's source list.
"""

from __future__ import annotations

from typing import Any


def format_observation(observation: dict[str, Any]) -> str:
    """Render one spine observation as a single ledger line.

    Example: ``2022: 18,316,765,021,690 — World Bank
    (https://api.worldbank.org/v2/...)``. A null value renders as ``n/a`` so an
    absent year is visible rather than dropped.
    """
    year = observation.get("year", "?")
    value = _format_value(observation.get("value"))
    source = observation.get("source", "unknown source")
    url = observation.get("url")
    line = f"{year}: {value} — {source}"
    if url:
        line += f" ({url})"
    return line


def format_series(label: str, observations: list[dict[str, Any]]) -> str:
    """Render a labeled series of observations as a Markdown block.

    Produces a heading line for ``label`` followed by one bullet per
    observation. An empty series renders an explicit "no data" line so gaps are
    reported rather than hidden — the spine never lets absence pass silently.
    """
    if not observations:
        return f"**{label}**\n- no official series available"
    lines = [f"**{label}**"]
    lines.extend(f"- {format_observation(obs)}" for obs in observations)
    return "\n".join(lines)


def unique_source_urls(observations: list[dict[str, Any]]) -> list[str]:
    """Return the distinct, non-empty source URLs in a set of observations.

    Order is first-seen, so a working paper's ledger and the report's source
    appendix stay stable. Falls back to the source name when an observation has
    no URL.
    """
    seen: set[str] = set()
    ordered: list[str] = []
    for obs in observations:
        ref = obs.get("url") or obs.get("source")
        if ref and ref not in seen:
            seen.add(ref)
            ordered.append(ref)
    return ordered


def _format_value(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float) and value.is_integer():
        return f"{int(value):,}"
    if isinstance(value, (int, float)):
        return f"{value:,}"
    return str(value)
