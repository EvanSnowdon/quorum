"""Engagement memory: markdown-in-git institutional memory.

The firm persists what it learns as plain markdown files under
``.quorum-memory/`` so the record is diffable, auditable, mergeable across a
team via git, and trivially editable when it is wrong. Records are grouped by
*kind* (a subdirectory such as ``plans`` or ``reports``) and addressed by a
slugified *key*.

v0 is exact-match storage and retrieval only; a semantic index over the same
markdown files is roadmap work.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

_SLUG_STRIP = re.compile(r"[^a-z0-9-]")
_SLUG_DASHES = re.compile(r"-+")


def _slug(key: str) -> str:
    """Reduce a key to a filesystem-safe slug: lowercase, spaces to hyphens."""
    text = key.strip().lower().replace(" ", "-")
    text = _SLUG_STRIP.sub("", text)
    text = _SLUG_DASHES.sub("-", text).strip("-")
    return text or "untitled"


class EngagementMemory:
    """Read and write per-kind markdown records under a memory root."""

    def __init__(self, root: str | Path = "./.quorum-memory") -> None:
        self.root = Path(root)

    def _path(self, kind: str, key: str) -> Path:
        return self.root / _slug(kind) / f"{_slug(key)}.md"

    def remember(self, kind: str, key: str, content: str) -> Path:
        """Write ``content`` under ``kind``/``key``, stamping the save time.

        The file opens with an ISO-8601 UTC timestamp comment so a reader (or a
        future retrieval pass) can order records without parsing the body.
        Returns the path written.
        """
        path = self._path(kind, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).isoformat()
        path.write_text(f"<!-- saved: {stamp} -->\n\n{content}\n", encoding="utf-8")
        return path

    def recall(self, kind: str, key: str) -> str | None:
        """Return the stored content for ``kind``/``key``, or ``None`` if absent.

        The leading timestamp comment is stripped so callers get the content
        they wrote.
        """
        path = self._path(kind, key)
        if not path.is_file():
            return None
        text = path.read_text(encoding="utf-8")
        return re.sub(r"^<!-- saved: [^>]*-->\s*", "", text, count=1).strip()

    def list(self, kind: str) -> list[str]:
        """Return the slugified keys stored under ``kind``, sorted."""
        directory = self.root / _slug(kind)
        if not directory.is_dir():
            return []
        return sorted(p.stem for p in directory.glob("*.md"))

    # TODO: vector retrieval. v0 recalls by exact kind/key only. A semantic
    # index over the same markdown files (adjacent markets, prior sources, past
    # red-team findings) is planned for a later phase; the storage format stays
    # markdown-in-git and the index is additive.
