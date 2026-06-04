"""World Bank Open Data client.

The World Bank Indicators API is keyless and returns annual observations for a
country and indicator code. Responses are a two-element JSON array: a metadata
object followed by the list of observations (or ``null`` when the query matches
nothing). Each observation we surface carries its own ``source`` and ``url`` so
a fact-check pass can trace any figure back to the exact request that produced
it.

API reference: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392
"""

from __future__ import annotations

from typing import Any

import requests

API_ROOT = "https://api.worldbank.org/v2"
SOURCE_NAME = "World Bank"
REQUEST_TIMEOUT = 30

# Frequently requested indicators, keyed by a short stable handle. Values are the
# World Bank series codes. Callers may pass any valid code to indicator(); these
# exist so the orchestrator and source packs can reference common series without
# hard-coding opaque identifiers across the codebase.
COMMON_INDICATORS: dict[str, str] = {
    "gdp_current_usd": "NY.GDP.MKTP.CD",
    "gdp_growth_pct": "NY.GDP.MKTP.KD.ZG",
    "gdp_per_capita_usd": "NY.GDP.PCAP.CD",
    "gni_current_usd": "NY.GNP.MKTP.CD",
    "inflation_cpi_pct": "FP.CPI.TOTL.ZG",
    "population_total": "SP.POP.TOTL",
    "population_growth_pct": "SP.POP.GROW",
    "unemployment_pct": "SL.UEM.TOTL.ZS",
    "labor_force_total": "SL.TLF.TOTL.IN",
    "exports_pct_gdp": "NE.EXP.GNFS.ZS",
    "imports_pct_gdp": "NE.IMP.GNFS.ZS",
    "fdi_net_inflows_usd": "BX.KLT.DINV.CD.WD",
    "manufacturing_pct_gdp": "NV.IND.MANF.ZS",
    "services_pct_gdp": "NV.SRV.TOTL.ZS",
    "internet_users_pct": "IT.NET.USER.ZS",
    "mobile_subscriptions_per_100": "IT.CEL.SETS.P2",
    "urban_population_pct": "SP.URB.TOTL.IN.ZS",
}


def indicator(
    country: str,
    code: str,
    start: int = 2015,
    end: int = 2025,
) -> list[dict[str, Any]]:
    """Return annual observations for one indicator and country.

    ``country`` accepts an ISO 3166-1 alpha-2 or alpha-3 code (the API resolves
    both). ``code`` is a World Bank series code such as ``NY.GDP.MKTP.CD``;
    handles from ``COMMON_INDICATORS`` are resolved automatically.

    Each returned dict has ``year`` (int), ``value`` (float or None),
    ``source`` and ``url``. Observations with a null value are kept so the caller
    can distinguish "no data reported" from "year omitted". Returns an empty list
    when the country or indicator is unknown, or when the API yields no series.
    """
    resolved_code = COMMON_INDICATORS.get(code, code)
    url = (
        f"{API_ROOT}/country/{country}/indicator/{resolved_code}"
        f"?format=json&per_page=200&date={start}:{end}"
    )
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError):
        return []

    observations = _extract_observations(payload)
    results: list[dict[str, Any]] = []
    for entry in observations:
        if not isinstance(entry, dict):
            continue
        year = _parse_year(entry.get("date"))
        if year is None:
            continue
        results.append(
            {
                "year": year,
                "value": _parse_value(entry.get("value")),
                "source": SOURCE_NAME,
                "url": url,
            }
        )
    results.sort(key=lambda row: row["year"])
    return results


def latest_value(
    country: str,
    code: str,
    start: int = 2015,
    end: int = 2025,
) -> dict[str, Any] | None:
    """Return the most recent observation with a non-null value, or None.

    Convenience for callers that need a single current figure rather than a
    series (for example, "current GDP") without re-implementing the scan.
    """
    series = indicator(country, code, start=start, end=end)
    for row in reversed(series):
        if row["value"] is not None:
            return row
    return None


def _extract_observations(payload: Any) -> list[Any]:
    """Pull the observation list out of a World Bank payload, defensively.

    The documented success shape is ``[metadata, [observations]]``. Unknown
    countries return ``[metadata, null]``; malformed or error responses may be a
    dict or a single-element list. Anything that is not the expected two-element
    array with a list body yields no observations.
    """
    if not isinstance(payload, list) or len(payload) < 2:
        return []
    body = payload[1]
    if not isinstance(body, list):
        return []
    return body


def _parse_year(raw: Any) -> int | None:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _parse_value(raw: Any) -> float | None:
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None
