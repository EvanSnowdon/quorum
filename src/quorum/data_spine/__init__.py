"""Data spine: the engine's grounding layer over official statistics APIs.

Design
------
The spine puts numbers first and sources always. Every query goes to an official,
keyless API (World Bank, IMF) and every observation it returns carries its own
``source`` and ``url``, so any figure in a working paper can be traced back to
the exact request that produced it and re-verified by the fact-check gate.

The spine exposes its capabilities to the orchestrator as named tools rather than
as imported functions. ``TOOL_REGISTRY`` maps a dotted tool name to a query
callable; a task contract lists the tool names a worker may use, and the worker
runtime resolves each name through :func:`resolve`. This keeps the tool allowlist
in a contract a list of strings the orchestrator can validate, with no direct
coupling between worker code and provider modules.

Each registered callable shares the signature
``(country: str, code: str, start: int = 2015, end: int = 2025) -> list[dict]``
and returns observations as ``{"year", "value", "source", "url"}``. Provider
modules differ in country-code expectations (World Bank accepts alpha-2 or
alpha-3; IMF DataMapper expects alpha-3); the relevant source pack records which
identifier a source uses.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from . import imf, sdmx, worldbank

QueryFn = Callable[..., list[dict[str, Any]]]

TOOL_REGISTRY: dict[str, QueryFn] = {
    "data_spine.worldbank": worldbank.indicator,
    "data_spine.imf": imf.indicator,
}


def resolve(tool_name: str) -> QueryFn:
    """Return the query callable registered under ``tool_name``.

    Raises ``KeyError`` with the set of known tool names when ``tool_name`` is
    not registered, so a malformed contract fails loudly at dispatch rather than
    silently producing no data.
    """
    try:
        return TOOL_REGISTRY[tool_name]
    except KeyError as exc:
        known = ", ".join(sorted(TOOL_REGISTRY)) or "<none>"
        raise KeyError(f"unknown data-spine tool '{tool_name}'; known tools: {known}") from exc


def tool_names() -> list[str]:
    """Return the sorted list of registered data-spine tool names."""
    return sorted(TOOL_REGISTRY)


__all__ = ["TOOL_REGISTRY", "resolve", "tool_names", "worldbank", "imf", "sdmx"]
