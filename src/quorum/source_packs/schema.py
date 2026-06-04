"""Pydantic schema for country source packs.

A source pack is a YAML file under this package that tells the data spine where a
country's official statistics live. The schema mirrors the contributor contract
documented in CONTRIBUTING ("Contribution path 2"): a pack carries country
identity plus a list of official sources, each optionally exposing a machine API.

These models cross the boundary between on-disk YAML and engine code, so they are
validated on load: a malformed pack fails at load time with a clear error rather
than producing a half-populated context block at dispatch time.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SourceType = Literal["statistics", "central_bank", "regulator", "intergovernmental"]
ApiFormat = Literal["json", "xml", "csv", "sdmx"]
ApiAuth = Literal["none", "token", "registration"]
Reliability = Literal["primary", "secondary"]
UpdateFrequency = Literal["annual", "quarterly", "monthly", "weekly", "daily"]


class SourceApi(BaseModel):
    """Machine-readable API description for a source.

    Present only when a source exposes a programmatic endpoint. ``spine_tool``
    links the source to a callable in ``data_spine.TOOL_REGISTRY`` when the spine
    can query it directly; sources without a wired tool are still recorded so a
    worker knows the API exists and the fact-check gate can reach it.
    """

    model_config = ConfigDict(extra="forbid")

    base_url: str
    format: ApiFormat
    auth: ApiAuth = "none"
    spine_tool: str | None = None


class Source(BaseModel):
    """A single official data source within a pack."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    type: SourceType
    url: str
    api: SourceApi | None = None
    coverage: list[str] = Field(default_factory=list)
    reliability: Reliability = "primary"
    update_frequency: UpdateFrequency | None = None


class SourcePack(BaseModel):
    """A country's official-source map.

    Loaded from ``<alpha-2>.yaml``. Exposes the three accessors the orchestrator
    depends on: :attr:`data_quality_score`, :meth:`tool_names`, and
    :meth:`context_block`.
    """

    model_config = ConfigDict(extra="forbid")

    country: str
    country_name: str
    language: str
    notes: str | None = None
    sources: list[Source] = Field(min_length=1)

    @property
    def data_quality_score(self) -> int:
        """A 0-100 heuristic for how well this pack can ground an engagement.

        The score rewards breadth and machineability of official coverage, the
        two things that most determine whether a worker can source claims rather
        than infer them. It is a planning signal for the orchestrator (which
        regions are well-covered), not a statement about the underlying
        economies. Components:

        - source count, capped (more official angles cross-check better);
        - share of sources with a machine API (queryable beats human-only);
        - share of sources wired to a spine tool (directly fetchable);
        - presence of the three pillars a complete pack should have:
          a statistics office, a central bank, and at least one regulator;
        - breadth of distinct coverage topics.
        """
        sources = self.sources
        total = len(sources)
        if total == 0:
            return 0

        with_api = sum(1 for s in sources if s.api is not None)
        with_tool = sum(1 for s in sources if s.api is not None and s.api.spine_tool)
        types = {s.type for s in sources}
        topics = {topic for s in sources for topic in s.coverage}

        breadth = min(total, 5) / 5 * 30
        api_share = (with_api / total) * 25
        tool_share = (with_tool / total) * 20
        pillars = sum(
            (
                "statistics" in types,
                "central_bank" in types,
                "regulator" in types,
            )
        ) / 3 * 15
        topic_breadth = min(len(topics), 10) / 10 * 10

        return round(breadth + api_share + tool_share + pillars + topic_breadth)

    def tool_names(self) -> list[str]:
        """Return the spine tool names this pack can drive, in sorted order.

        These are the ``data_spine.*`` handles a worker contract may include for
        an engagement in this region. Sources whose API is not wired to a spine
        tool contribute no entry; duplicates (several sources sharing a tool) are
        collapsed.
        """
        names = {
            s.api.spine_tool
            for s in self.sources
            if s.api is not None and s.api.spine_tool
        }
        return sorted(names)

    def context_block(self) -> str:
        """Render the pack as a Markdown block for injection into a contract.

        The orchestrator inlines this into expert task contracts so a worker
        knows, without loading YAML, which official sources exist for the region,
        what each covers, and how it is reached. Format is stable and terse: a
        header line, an optional notes line, then one bullet per source.
        """
        lines = [f"## Official sources — {self.country_name} ({self.country})"]
        lines.append(f"Primary publication language: {self.language}.")
        if self.notes:
            lines.append(f"Note: {self.notes.strip()}")
        lines.append("")
        for source in self.sources:
            lines.append(self._render_source(source))
        return "\n".join(lines).rstrip()

    @staticmethod
    def _render_source(source: Source) -> str:
        coverage = ", ".join(source.coverage) if source.coverage else "general"
        header = (
            f"- {source.name} [{source.type}, {source.reliability}] — {source.url}"
        )
        detail = f"  coverage: {coverage}"
        if source.update_frequency:
            detail += f"; updated {source.update_frequency}"
        if source.api is not None:
            api_bits = f"{source.api.format} API, auth: {source.api.auth}"
            if source.api.spine_tool:
                api_bits += f", spine tool: {source.api.spine_tool}"
            detail += f"\n  api: {source.api.base_url} ({api_bits})"
        return f"{header}\n{detail}"
