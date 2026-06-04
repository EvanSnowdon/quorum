"""Country source packs: the data spine's per-region routing tables.

Each ``<alpha-2>.yaml`` in this package maps one country's official statistics
landscape (statistics office, central bank, regulators, intergovernmental
series) onto the schema in :mod:`.schema`. The orchestrator loads a pack for the
engagement's region and uses it three ways: to gauge how well the region can be
grounded (:attr:`SourcePack.data_quality_score`), to derive the spine tools a
worker may call (:meth:`SourcePack.tool_names`), and to inline the source map
into expert contracts (:meth:`SourcePack.context_block`).

Packs are read from disk lazily and cached per region. The universal World Bank
and IMF series are available for every country regardless of pack contents; a
pack adds the national sources that those global series cannot supply.
"""

from __future__ import annotations

from pathlib import Path

from .schema import Source, SourceApi, SourcePack

_PACK_DIR = Path(__file__).resolve().parent
_CACHE: dict[str, SourcePack] = {}

# The fallback pack: a region-agnostic map of the keyless intergovernmental
# series (World Bank, IMF, OECD, UN) that apply to every country. ``load_pack``
# resolves to it when no country-specific pack exists, so an engagement on an
# uncovered region still gets the universal spine sources rather than nothing.
GLOBAL_REGION = "global"


class SourcePackNotFoundError(FileNotFoundError):
    """Raised when neither a region pack nor the global fallback can be loaded."""


def load_pack(region: str, fallback: bool = True) -> SourcePack:
    """Load and validate the source pack for ``region``.

    ``region`` is an ISO 3166-1 country code; alpha-2 is canonical (pack files
    are named ``us.yaml``, ``cn.yaml``, ...) but a small set of common alpha-3
    codes is accepted as a convenience. Matching is case-insensitive.

    When no pack exists for the region and ``fallback`` is true (the default),
    the region-agnostic :data:`GLOBAL_REGION` pack is returned so an uncovered
    region still resolves to the universal intergovernmental sources. Set
    ``fallback=False`` to require an exact region pack.

    Returns a validated :class:`SourcePack`. Raises
    :class:`SourcePackNotFoundError` if neither the region pack nor (when
    permitted) the global fallback exists, and ``pydantic.ValidationError`` if a
    pack file exists but does not satisfy the schema.
    """
    key = _normalize_region(region)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached

    path = _PACK_DIR / f"{key}.yaml"
    if not path.is_file():
        if fallback and key != GLOBAL_REGION:
            global_path = _PACK_DIR / f"{GLOBAL_REGION}.yaml"
            if global_path.is_file():
                pack = _parse_pack(global_path)
                # Cache under the requested key too: a second miss for the same
                # region resolves straight to the fallback without re-reading.
                _CACHE[key] = pack
                return pack
        available = ", ".join(available_regions()) or "<none>"
        raise SourcePackNotFoundError(
            f"no source pack for region '{region}'; available: {available}"
        )

    pack = _parse_pack(path)
    _CACHE[key] = pack
    return pack


def available_regions() -> list[str]:
    """Return the alpha-2 codes of all region packs shipped in this package.

    Excludes underscore-prefixed files (the ``_schema.yaml`` contributor
    template) and the region-agnostic ``global`` fallback, so the list reflects
    only the countries a user can name directly.
    """
    return sorted(
        p.stem
        for p in _PACK_DIR.glob("*.yaml")
        if not p.stem.startswith("_") and p.stem != GLOBAL_REGION
    )


def _parse_pack(path: Path) -> SourcePack:
    import yaml  # lazy: only needed when a pack is actually loaded

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return SourcePack.model_validate(raw)


_ALPHA3_TO_ALPHA2: dict[str, str] = {
    "usa": "us",
    "chn": "cn",
    "jpn": "jp",
    "gbr": "gb",
    "deu": "de",
}


def _normalize_region(region: str) -> str:
    key = region.strip().lower()
    if len(key) == 3 and key in _ALPHA3_TO_ALPHA2:
        return _ALPHA3_TO_ALPHA2[key]
    return key


__all__ = [
    "GLOBAL_REGION",
    "Source",
    "SourceApi",
    "SourcePack",
    "SourcePackNotFoundError",
    "available_regions",
    "load_pack",
]
