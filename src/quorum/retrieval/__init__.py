"""Retrieval layer: the read side of the markdown-in-git memory store.

Quorum persists institutional memory as plain Markdown under ``.quorum-memory/``
in the user's working directory (see docs/architecture.md, "Memory layer"):

    .quorum-memory/
    ├── markets/<region>-<industry-slug>.md   # rolling notes per region x industry
    ├── sources/<region>.md                    # which sources proved reliable
    └── engagements.md                         # index of past runs

This package provides the lookups the orchestrator performs at scoping time:
fetch any prior notes for the exact region x industry being engaged, fetch the
region's source notes, and read the engagement index. Retrieval here is
deliberately exact-match only — indexed/semantic retrieval is Phase 2 roadmap
work — and every lookup degrades gracefully to "nothing found" so a first-ever
engagement on a market simply proceeds without memory.

The write side and the orchestrator's use of these results live in the engine
core (``memory.py``); this package stays read-only and free of engine imports so
it can be tested in isolation.

Alongside the memory store, :mod:`.web` provides the gap-filling web retrieval
the spine falls back to when no official series answers a question and the task
contract permits it. It is an optional path: its backend SDK is imported lazily
and an unconfigured deployment degrades to empty results, so importing this
package never requires a web backend to be installed.
"""

from __future__ import annotations

from . import web
from .memory_index import (
    MEMORY_DIRNAME,
    MemoryHit,
    MemoryRetriever,
    slugify_industry,
)
from .web import SearchResult, WebRetriever

__all__ = [
    "MEMORY_DIRNAME",
    "MemoryHit",
    "MemoryRetriever",
    "SearchResult",
    "WebRetriever",
    "slugify_industry",
    "web",
]
