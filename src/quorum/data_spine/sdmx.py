"""Generic SDMX connector for the data spine.

Most of the statistical bodies the spine routes to — Eurostat, the ECB, the
BIS, the OECD, the UN, and the World Bank — publish their series through SDMX,
the ISO standard for exchanging statistical data and metadata. A single
connector that speaks SDMX-JSON therefore covers a large share of the official
sources a source pack can declare with ``format: sdmx``, which is why several
packs (see ``eu.yaml``) record SDMX endpoints without a dedicated spine tool:
they are waiting on this client.

This module provides that client as a usable skeleton. :class:`SdmxClient`
fetches an SDMX-JSON dataset for a flow and a series key, then flattens the
observations into the spine's standard ``{"year", "value", "source", "url"}``
rows so SDMX series read the same as World Bank or IMF series downstream.

Scope and limitations
---------------------
SDMX is dimensional: a dataset is an N-dimensional cube, and turning that cube
back into flat rows means walking the ``structure.dimensions`` block and the
index arrays each observation key points into. The parser here implements the
common case the spine needs first — a time-keyed series with a single value per
period — and resolves the time dimension robustly. Full expansion of every
non-time dimension into labelled columns (so a caller can tell two series in the
same response apart by their dimension values) is marked with TODOs where the
work belongs; the structure is read far enough to locate time and observation
values correctly, which is what the standard ``{year, value}`` shape requires.

SDMX-JSON references:
- Specification: https://github.com/sdmx-twg/sdmx-json
- Eurostat dissemination API: https://wikis.ec.europa.eu/display/EUROSTATHELP
- ECB Data Portal API: https://data.ecb.europa.eu/help/api/overview
"""

from __future__ import annotations

from typing import Any

import requests

REQUEST_TIMEOUT = 30

# Base URLs for the SDMX-REST services the spine most often targets. Each serves
# SDMX-JSON when asked for it (via the Accept header set in fetch()). Agencies
# differ in path layout below the base; see each provider's API guide for the
# exact ``{flow}/{key}`` grammar a request expects.
EUROSTAT_BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1"
ECB_BASE_URL = "https://data-api.ecb.europa.eu/service"
BIS_BASE_URL = "https://stats.bis.org/api/v1"
OECD_BASE_URL = "https://sdmx.oecd.org/public/rest"

# Agencies whose SDMX-REST "data" resource is reached under a ``/data`` segment
# (``{base}/data/{flow}/{key}``). Others (notably the ECB) place the flow
# directly under the base (``{base}/data/{flow}/{key}`` vs ``{base}/{resource}``)
# — the path builder accounts for the two layouts the spine targets today.
_DATA_SEGMENT_AGENCIES = {"ESTAT", "OECD", "BIS"}

# SDMX-JSON is requested through content negotiation; the structure-specific
# variant keeps dimension metadata inline with the data, which the flattener
# needs to find the time dimension.
_SDMX_JSON_ACCEPT = "application/vnd.sdmx.data+json;version=1.0.0, application/json"


class SdmxClient:
    """A thin SDMX-JSON client over one agency's SDMX-REST service.

    Construct it with an agency id (``"ESTAT"``, ``"ECB"``, ``"BIS"``,
    ``"OECD"``, ...) and the agency's SDMX-REST base URL — the module-level
    ``*_BASE_URL`` constants supply the common ones. :meth:`fetch` then pulls a
    flow's data and returns spine-standard observation rows.

    The client is deliberately stateless beyond its configuration: each
    :meth:`fetch` is an independent request, and every failure mode (network
    error, non-JSON body, unexpected structure) degrades to an empty list rather
    than raising, matching the contract of the World Bank and IMF clients.
    """

    def __init__(self, agency: str, base_url: str) -> None:
        self.agency = agency.strip().upper()
        self.base_url = base_url.rstrip("/")

    def fetch(
        self,
        flow: str,
        key: str = "all",
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch one SDMX flow and return flattened observation rows.

        ``flow`` is the dataflow identifier (for Eurostat, the dataset code such
        as ``nama_10_gdp``; for the ECB, ``{resource}`` such as ``EXR``).
        ``key`` is the dot-separated series key selecting positions on the
        flow's dimensions (``"all"`` for the whole flow). ``params`` are extra
        query parameters — commonly ``startPeriod``/``endPeriod`` to bound the
        time range, or ``detail``/``dimensionAtObservation`` to shape the
        response.

        Each returned dict carries ``year`` (int), ``value`` (float or None),
        ``source`` (``"<AGENCY> (SDMX)"``) and ``url`` (the exact request),
        keeping SDMX series traceable and shaped like every other spine source.
        Returns an empty list on any error or unexpected payload.
        """
        url = self._build_url(flow, key)
        query = {"format": "jsondata", **(params or {})}
        try:
            response = requests.get(
                url,
                params=query,
                headers={"Accept": _SDMX_JSON_ACCEPT},
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError):
            return []

        return self._flatten(payload, source=f"{self.agency} (SDMX)", url=response.url)

    def _build_url(self, flow: str, key: str) -> str:
        """Assemble the SDMX-REST data URL for this agency's path layout.

        Agencies in :data:`_DATA_SEGMENT_AGENCIES` expose data under a ``/data``
        segment with the agency id in the flow reference; the ECB-style layout
        places the resource directly under the service root. Both are common in
        the wild, so the spine handles the two its packs declare today and leaves
        a TODO for agencies with a third convention.
        """
        flow = flow.strip("/")
        key = key.strip("/") or "all"
        if self.agency in _DATA_SEGMENT_AGENCIES:
            # e.g. https://.../sdmx/2.1/data/ESTAT,nama_10_gdp/<key>
            return f"{self.base_url}/data/{self.agency},{flow}/{key}"
        # ECB-style: https://data-api.ecb.europa.eu/service/data/EXR/<key>
        # TODO: add layouts for agencies that namespace by version or provider
        #   reference (``{agency},{flow},{version}``) as packs begin to need them.
        return f"{self.base_url}/data/{flow}/{key}"

    def _flatten(self, payload: Any, source: str, url: str) -> list[dict[str, Any]]:
        """Flatten an SDMX-JSON payload into spine-standard observation rows.

        Walks the documented SDMX-JSON shape: ``data.dataSets[].series`` maps a
        packed dimension key to a ``{observations: {<time-index>: [value, ...]}}``
        block, and ``data.structure.dimensions`` describes what those indices
        mean. The time dimension is located by role/id and used to turn each
        observation index back into a calendar year.
        """
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            return []

        structure = data.get("structure")
        if not isinstance(structure, dict):
            return []
        time_values = _time_dimension_values(structure)
        if not time_values:
            return []

        rows: list[dict[str, Any]] = []
        for series in _iter_series(data):
            observations = series.get("observations")
            if not isinstance(observations, dict):
                continue
            # TODO: resolve the series' non-time dimension positions against
            #   ``structure.dimensions.series`` and attach them as labelled
            #   fields so callers can disambiguate multiple series in one
            #   response. The standard {year, value} contract does not require
            #   it, so it is deferred rather than half-built here.
            for obs_index, obs_value in observations.items():
                year = _year_at(time_values, obs_index)
                if year is None:
                    continue
                rows.append(
                    {
                        "year": year,
                        "value": _first_value(obs_value),
                        "source": source,
                        "url": url,
                    }
                )

        rows.sort(key=lambda row: row["year"])
        return rows


def _iter_series(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return every series block across all datasets in the payload."""
    series_blocks: list[dict[str, Any]] = []
    datasets = data.get("dataSets")
    if not isinstance(datasets, list):
        return series_blocks
    for dataset in datasets:
        if not isinstance(dataset, dict):
            continue
        series = dataset.get("series")
        if isinstance(series, dict):
            series_blocks.extend(s for s in series.values() if isinstance(s, dict))
    return series_blocks


def _time_dimension_values(structure: dict[str, Any]) -> list[str]:
    """Return the ordered time-period codes for the dataset's time dimension.

    SDMX-JSON places observation-level dimensions under
    ``structure.dimensions.observation``. The time dimension is identified by
    its ``role`` of ``"time"`` (preferred) or, failing that, the conventional id
    ``TIME_PERIOD``. Each observation index keys into this dimension's ``values``
    array, whose entries carry the period ``id`` (e.g. ``"2023"``,
    ``"2023-Q1"``).
    """
    dimensions = structure.get("dimensions")
    if not isinstance(dimensions, dict):
        return []
    observation_dims = dimensions.get("observation")
    if not isinstance(observation_dims, list):
        return []

    time_dim = None
    for dim in observation_dims:
        if not isinstance(dim, dict):
            continue
        if dim.get("role") == "time" or dim.get("id") == "TIME_PERIOD":
            time_dim = dim
            break
    if time_dim is None:
        return []

    values = time_dim.get("values")
    if not isinstance(values, list):
        return []
    return [str(v.get("id")) for v in values if isinstance(v, dict) and v.get("id") is not None]


def _year_at(time_values: list[str], obs_index: Any) -> int | None:
    """Resolve an observation index to a calendar year via the time dimension.

    The index is a string position into ``time_values``; the period code at that
    position (``"2023"``, ``"2023-Q2"``, ``"2023-03"``) is parsed for its
    leading four-digit year. Quarter/month detail is dropped for the standard
    annual row shape — preserving sub-annual periods is a TODO tied to the
    dimension-expansion work above.
    """
    try:
        position = int(obs_index)
    except (TypeError, ValueError):
        return None
    if position < 0 or position >= len(time_values):
        return None
    period = time_values[position]
    head = period.split("-", 1)[0]
    try:
        return int(head)
    except (TypeError, ValueError):
        return None


def _first_value(raw: Any) -> float | None:
    """Return the numeric observation value from an SDMX observation array.

    An SDMX-JSON observation is an array whose first element is the value and
    whose later elements are attribute indices; only the value concerns the
    spine's row shape. A scalar (some serializers emit one) is accepted too.
    """
    candidate = raw[0] if isinstance(raw, list) and raw else raw
    if candidate is None:
        return None
    try:
        return float(candidate)
    except (TypeError, ValueError):
        return None


# Convenience constructors for the agencies whose base URLs ship with the spine.
def eurostat() -> SdmxClient:
    """Return an :class:`SdmxClient` for Eurostat (agency ``ESTAT``)."""
    return SdmxClient("ESTAT", EUROSTAT_BASE_URL)


def ecb() -> SdmxClient:
    """Return an :class:`SdmxClient` for the European Central Bank."""
    return SdmxClient("ECB", ECB_BASE_URL)


__all__ = [
    "BIS_BASE_URL",
    "ECB_BASE_URL",
    "EUROSTAT_BASE_URL",
    "OECD_BASE_URL",
    "SdmxClient",
    "ecb",
    "eurostat",
]
