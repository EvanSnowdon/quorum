"""IMF DataMapper client.

The IMF DataMapper API is keyless and serves the World Economic Outlook and
related datasets. A query for an indicator and country returns:

    {"values": {"<indicator>": {"<ISO3>": {"<year>": <number>, ...}}}}

An unknown indicator code does not error; the API instead returns its metadata
catalogue (a payload with ``countries``/``regions`` keys and no ``values``).
The client treats a missing ``values`` block, indicator, or country as "no
series" and returns an empty list. Every observation carries its ``source`` and
``url`` so figures remain traceable.

API reference: https://www.imf.org/external/datamapper/api/help
"""

from __future__ import annotations

from typing import Any

import requests

API_ROOT = "https://www.imf.org/external/datamapper/api/v1"
SOURCE_NAME = "IMF (World Economic Outlook)"
REQUEST_TIMEOUT = 30

# Common WEO indicators keyed by a short stable handle. DataMapper country keys
# are ISO 3166-1 alpha-3, so callers pass alpha-3 codes here (see indicator()).
COMMON_INDICATORS: dict[str, str] = {
    "gdp_growth_pct": "NGDP_RPCH",
    "gdp_current_usd_bn": "NGDPD",
    "gdp_per_capita_usd": "NGDPDPC",
    "gdp_ppp_share_world_pct": "PPPSH",
    "inflation_avg_pct": "PCPIPCH",
    "inflation_eop_pct": "PCPIEPCH",
    "unemployment_pct": "LUR",
    "govt_gross_debt_pct_gdp": "GGXWDG_NGDP",
    "govt_net_lending_pct_gdp": "GGXCNL_NGDP",
    "current_account_pct_gdp": "BCA_NGDPD",
    "population_millions": "LP",
}


def indicator(
    country: str,
    code: str,
    start: int = 2015,
    end: int = 2025,
) -> list[dict[str, Any]]:
    """Return annual observations for one indicator and country.

    ``country`` is an ISO 3166-1 alpha-3 code (DataMapper's key format, e.g.
    ``USA``, ``CHN``). ``code`` is a WEO indicator code such as ``NGDP_RPCH``;
    handles from ``COMMON_INDICATORS`` are resolved automatically.

    Each returned dict has ``year`` (int), ``value`` (float), ``source`` and
    ``url``. The result is filtered to the inclusive ``start``..``end`` range and
    sorted by year. Returns an empty list when the indicator or country is
    unknown, or when the payload carries no value block.
    """
    resolved_code = COMMON_INDICATORS.get(code, code)
    url = f"{API_ROOT}/{resolved_code}/{country}"
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError):
        return []

    series = _extract_series(payload, resolved_code, country)
    results: list[dict[str, Any]] = []
    for raw_year, raw_value in series.items():
        year = _parse_year(raw_year)
        if year is None or year < start or year > end:
            continue
        value = _parse_value(raw_value)
        if value is None:
            continue
        results.append(
            {
                "year": year,
                "value": value,
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
    """Return the most recent observation in range, or None.

    DataMapper series mix historical figures with WEO projections; callers that
    need a single recent number get the latest year within the requested window.
    """
    series = indicator(country, code, start=start, end=end)
    return series[-1] if series else None


def _extract_series(payload: Any, code: str, country: str) -> dict[str, Any]:
    """Pull the {year: value} mapping for one indicator/country, defensively.

    Guards every level: a non-dict payload, a missing ``values`` block (returned
    for unknown indicators), a missing indicator key, a missing country key, or a
    country entry that is not itself a mapping.
    """
    if not isinstance(payload, dict):
        return {}
    values = payload.get("values")
    if not isinstance(values, dict):
        return {}
    by_country = values.get(code)
    if not isinstance(by_country, dict):
        return {}
    series = by_country.get(country)
    if not isinstance(series, dict):
        return {}
    return series


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
