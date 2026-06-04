"""Exact-match retrieval over the markdown-in-git memory store."""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict

MEMORY_DIRNAME = ".quorum-memory"

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def slugify_industry(industry: str) -> str:
    """Normalize an industry name to the slug used in memory and engagement paths.

    Lowercases, replaces any run of non-alphanumeric characters with a single
    hyphen, and trims leading/trailing hyphens. ``"Electric Vehicles"`` and
    ``"electric_vehicles"`` both yield ``"electric-vehicles"``, matching the
    engagement-directory convention ``<region>-<industry-slug>``.
    """
    return _SLUG_STRIP.sub("-", industry.strip().lower()).strip("-")


class MemoryHit(BaseModel):
    """A single retrieved memory document.

    ``kind`` is one of ``market``, ``sources`` or ``index``; ``path`` is the file
    the content came from (useful for citing or appending later); ``content`` is
    the raw Markdown.
    """

    model_config = ConfigDict(extra="forbid")

    kind: str
    key: str
    path: Path
    content: str


class MemoryRetriever:
    """Read-only accessor for one ``.quorum-memory/`` store.

    Construct it with the directory that contains (or will contain) the store —
    typically the user's working directory. All lookups are exact-match and
    return ``None`` (or an empty list) when the store or the specific file is
    absent, so callers never need to special-case a cold start.
    """

    def __init__(self, base_dir: Path | str) -> None:
        self._root = Path(base_dir).resolve() / MEMORY_DIRNAME

    @property
    def root(self) -> Path:
        """The resolved path to the ``.quorum-memory/`` directory."""
        return self._root

    def exists(self) -> bool:
        """Return whether a memory store is present at this location."""
        return self._root.is_dir()

    def market_notes(self, region: str, industry: str) -> MemoryHit | None:
        """Return notes for the exact region x industry, or None.

        Looks up ``markets/<region>-<industry-slug>.md``. Region is lowercased;
        the industry is slugified with :func:`slugify_industry`.
        """
        key = f"{region.strip().lower()}-{slugify_industry(industry)}"
        path = self._root / "markets" / f"{key}.md"
        return self._read(kind="market", key=key, path=path)

    def source_notes(self, region: str) -> MemoryHit | None:
        """Return source-reliability notes for a region, or None.

        Looks up ``sources/<region>.md``.
        """
        key = region.strip().lower()
        path = self._root / "sources" / f"{key}.md"
        return self._read(kind="sources", key=key, path=path)

    def engagement_index(self) -> MemoryHit | None:
        """Return the ``engagements.md`` index, or None if absent."""
        path = self._root / "engagements.md"
        return self._read(kind="index", key="engagements", path=path)

    def gather(self, region: str, industry: str) -> list[MemoryHit]:
        """Return all memory relevant to an engagement, in injection order.

        Collects the matching market notes, the region's source notes, and the
        engagement index, skipping any that are absent. This is the bundle the
        orchestrator inlines into expert contracts at scoping time.
        """
        hits = [
            self.market_notes(region, industry),
            self.source_notes(region),
            self.engagement_index(),
        ]
        return [hit for hit in hits if hit is not None]

    def list_markets(self) -> list[str]:
        """Return the keys of all market notes present, sorted.

        Each key has the form ``<region>-<industry-slug>``. Useful for surfacing
        what the store already covers; not a substitute for exact lookup.
        """
        markets_dir = self._root / "markets"
        if not markets_dir.is_dir():
            return []
        return sorted(p.stem for p in markets_dir.glob("*.md"))

    def _read(self, kind: str, key: str, path: Path) -> MemoryHit | None:
        if not path.is_file():
            return None
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return None
        return MemoryHit(kind=kind, key=key, path=path, content=content)
