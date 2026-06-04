"""Web retrieval: the spine's gap-filler for questions official APIs can't answer.

The data spine answers with official statistics first; when it has no series for
a question and the task contract permits web access, a worker falls back to
secondary web sources (see docs/architecture.md, "The data spine", resolution
step 2). This module is that fallback's read side: a search-and-scrape interface
over a hosted crawler, returning results in a shape the worker can cite and the
fact-check gate can re-verify.

The default backend is Firecrawl (https://firecrawl.dev), a hosted scraping and
search API that returns clean Markdown for a URL and ranked results for a query.
It is an optional dependency: ``firecrawl-py`` is imported lazily inside the
client so importing this module — and the package — never requires it, and a
deployment without a configured key degrades to "nothing found" with a clear
reason rather than raising. This mirrors the memory layer, which also returns
empty results on a cold start instead of forcing every caller to special-case
the absence of a backend.

Configuration (environment):
- ``FIRECRAWL_API_KEY`` — the Firecrawl key. Absent, every call returns empty.
- ``QUORUM_WEB_BACKEND`` — reserved selector for future backends; only
  ``firecrawl`` is implemented today.

A secondary web source never silently overrides an official one: results here
carry their ``url`` and ``source`` so the worker labels them as the secondary
evidence they are, and the gate can fetch the same URL to check the claim.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

# Result cap for a single search, to bound how much a worker pulls into context
# from one query. The orchestrator's per-task tool-call budget bounds the number
# of queries; this bounds the breadth of each.
DEFAULT_SEARCH_LIMIT = 5
_API_KEY_ENV = "FIRECRAWL_API_KEY"


@dataclass
class SearchResult:
    """One web search hit.

    ``url`` and ``title`` identify the page; ``snippet`` is the short excerpt the
    backend returned for ranking; ``source`` records which backend produced it so
    a citation can name it. ``markdown`` is populated only when the backend
    returned page content inline with the search result; otherwise a worker
    calls :meth:`WebRetriever.scrape` to fetch it.
    """

    url: str
    title: str = ""
    snippet: str = ""
    source: str = "firecrawl"
    markdown: str = ""

    def as_dict(self) -> dict[str, Any]:
        """Return the result as a plain dict for serialization into context."""
        return {
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "source": self.source,
            "markdown": self.markdown,
        }


@dataclass
class WebRetriever:
    """Search-and-scrape client over a hosted crawler, defaulting to Firecrawl.

    The client reads its key from the environment by default; pass ``api_key``
    explicitly to override. It is safe to construct unconditionally: construction
    does no I/O and imports no optional dependency. When no key is available the
    client is *unconfigured* — :meth:`available` returns ``False`` and every
    query returns an empty result with the reason recorded — so callers can wire
    it into a contract's tool list and let it no-op gracefully where the
    deployment has no web backend.
    """

    api_key: str | None = field(default=None)
    backend: str = "firecrawl"
    search_limit: int = DEFAULT_SEARCH_LIMIT

    def __post_init__(self) -> None:
        if self.api_key is None:
            self.api_key = os.environ.get(_API_KEY_ENV)
        # The instantiated backend client is created lazily on first use and
        # cached here; None until then, or when the backend is unavailable.
        self._client: Any | None = None

    def available(self) -> bool:
        """Return whether a backend is configured and importable.

        True only if a key is present and the backend SDK can be imported.
        Callers can check this before a query to decide whether to bother, though
        the query methods themselves also degrade safely when it is False.
        """
        return bool(self.api_key) and self._load_client() is not None

    def search(self, query: str) -> list[dict[str, Any]]:
        """Search the web for ``query`` and return ranked results.

        Returns a list of result dicts (see :class:`SearchResult.as_dict`),
        capped at :attr:`search_limit`. Returns an empty list when the backend is
        unconfigured or the call fails, never raising — a failed web lookup is a
        gap to report in a working paper, not a crash in the engine.
        """
        client = self._load_client()
        if client is None:
            return []
        try:
            raw = client.search(query, limit=self.search_limit)
        except Exception:
            # Network, auth, quota, or SDK-shape errors all degrade to "no
            # results"; the worker reports the gap rather than the engine failing.
            return []
        return [r.as_dict() for r in _parse_search(raw, self.backend)[: self.search_limit]]

    def scrape(self, url: str) -> str:
        """Fetch one page and return its content as Markdown.

        Returns the page rendered to Markdown, or an empty string when the
        backend is unconfigured or the fetch fails. Markdown (not raw HTML) is
        the unit the rest of the pipeline reads, matching the memory store and
        the report format.
        """
        client = self._load_client()
        if client is None:
            return ""
        try:
            raw = client.scrape_url(url)
        except Exception:
            return ""
        return _parse_markdown(raw)

    def _load_client(self) -> Any | None:
        """Lazily construct and cache the backend client, or return None.

        The optional dependency is imported here, on first use, so neither
        ``import quorum`` nor merely constructing a :class:`WebRetriever` pulls in
        ``firecrawl-py``. Returns None — leaving the retriever a safe no-op — when
        no key is set, the backend is unknown, or the SDK is not installed.
        """
        if self._client is not None:
            return self._client
        if not self.api_key:
            return None
        if self.backend != "firecrawl":
            # TODO: route alternative backends (e.g. an MCP web-search server, a
            #   self-hosted SearXNG) here behind the same search()/scrape()
            #   surface, selected by QUORUM_WEB_BACKEND. Firecrawl is the only
            #   implementation today.
            return None
        try:
            from firecrawl import FirecrawlApp  # type: ignore[import-not-found]
        except ImportError:
            return None
        self._client = FirecrawlApp(api_key=self.api_key)
        return self._client


# Module-level convenience wrappers over a default, environment-configured
# retriever, so a caller that wants a one-shot lookup need not manage an
# instance. They share the same graceful-degradation contract as the methods.
def search(query: str) -> list[dict[str, Any]]:
    """Search the web via a default environment-configured retriever."""
    return WebRetriever().search(query)


def scrape(url: str) -> str:
    """Scrape one URL to Markdown via a default environment-configured retriever."""
    return WebRetriever().scrape(url)


def _parse_search(raw: Any, backend: str) -> list[SearchResult]:
    """Normalize a backend search payload into :class:`SearchResult` objects.

    Firecrawl returns either a list of hit dicts or a ``{"data": [...]}`` wrapper
    depending on SDK version; both are accepted. Entries without a URL are
    dropped. Defensive throughout so an unexpected shape yields no results rather
    than an exception.
    """
    items = raw.get("data") if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        return []
    results: list[SearchResult] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        url = item.get("url") or item.get("sourceURL")
        if not url:
            continue
        results.append(
            SearchResult(
                url=str(url),
                title=str(item.get("title", "")),
                snippet=str(item.get("description") or item.get("snippet") or ""),
                source=backend,
                markdown=str(item.get("markdown", "")),
            )
        )
    return results


def _parse_markdown(raw: Any) -> str:
    """Extract Markdown text from a backend scrape payload, defensively.

    Firecrawl returns ``{"markdown": "...", ...}`` or, in some SDK versions, a
    nested ``{"data": {"markdown": "..."}}``. A plain string is returned as-is.
    Anything else yields an empty string.
    """
    if isinstance(raw, str):
        return raw
    if not isinstance(raw, dict):
        return ""
    if isinstance(raw.get("markdown"), str):
        return raw["markdown"]
    data = raw.get("data")
    if isinstance(data, dict) and isinstance(data.get("markdown"), str):
        return data["markdown"]
    return ""


__all__ = [
    "DEFAULT_SEARCH_LIMIT",
    "SearchResult",
    "WebRetriever",
    "scrape",
    "search",
]
