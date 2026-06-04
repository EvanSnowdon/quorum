"""Source pack loading, fallback, and accessor contracts.

These tests exercise the three accessors the orchestrator depends on
(`data_quality_score`, `tool_names`, `context_block`) plus the region
resolution rules: case-insensitive lookup, the global fallback for uncovered
regions, and the strict mode that disables it. No network access is required —
packs are plain YAML files bundled with the package.
"""

from __future__ import annotations

import pytest

from quorum.source_packs import (
    GLOBAL_REGION,
    SourcePackNotFoundError,
    load_pack,
)
from quorum.source_packs.schema import SourcePack

BUNDLED_REGIONS = ("cn", "us", "eu", "jp", "gb", "global")


@pytest.mark.parametrize("region", BUNDLED_REGIONS)
def test_bundled_packs_load_and_validate(region: str) -> None:
    pack = load_pack(region)
    assert isinstance(pack, SourcePack)
    assert pack.sources, f"pack '{region}' must declare at least one source"


@pytest.mark.parametrize("region", ["CN", "Cn", "cn"])
def test_region_lookup_is_case_insensitive(region: str) -> None:
    pack = load_pack(region)
    assert pack.country.lower() == "cn"


def test_unknown_region_falls_back_to_global() -> None:
    pack = load_pack("zz")
    fallback = load_pack(GLOBAL_REGION)
    assert pack.country == fallback.country


def test_unknown_region_strict_mode_raises() -> None:
    with pytest.raises(SourcePackNotFoundError):
        load_pack("zz", fallback=False)


def test_data_quality_score_is_bounded_int() -> None:
    for region in BUNDLED_REGIONS:
        score = load_pack(region).data_quality_score
        assert isinstance(score, int)
        assert 0 <= score <= 100


def test_tool_names_shape() -> None:
    for region in BUNDLED_REGIONS:
        names = load_pack(region).tool_names()
        assert isinstance(names, list)
        assert names == sorted(names), "tool names must be returned sorted"
        for name in names:
            assert name.startswith("data_spine."), name


def test_context_block_mentions_region() -> None:
    pack = load_pack("cn")
    block = pack.context_block()
    assert pack.country_name in block
    assert pack.country in block
    # One bullet per source, so the block must be multi-line.
    assert len(block.splitlines()) > 2


def test_well_covered_regions_outscore_global_fallback() -> None:
    # The fallback pack only carries the universal intergovernmental series;
    # a complete national pack (statistics office + central bank + regulator)
    # should never score below it.
    global_score = load_pack(GLOBAL_REGION).data_quality_score
    for region in ("us", "gb", "eu", "jp", "cn"):
        assert load_pack(region).data_quality_score >= global_score
