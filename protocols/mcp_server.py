"""Quorum as a Model Context Protocol (MCP) server.

This exposes the firm over MCP so any MCP-capable host — Claude Desktop, Claude
Code, or another agent runtime — can commission an engagement and inspect the
analyst library as first-class tools, without shelling out to the CLI.

Two tools are published:

``run_engagement(region, industry, depth)``
    Run a full engagement and return the final report markdown. This is the
    same path as ``quorum --region ... --industry ...``; it requires a provider
    API key in the server's environment.
``list_analyst_skills()``
    Return the available methodology analysts and their descriptions. This is a
    cheap, key-free call — it reads only the skill frontmatter — so a host can
    show the firm's capabilities before paying for a run.

Transport: the reference build speaks stdio, which is what Claude Desktop /
Claude Code launch and connect to. See ``protocols/README.md`` for the host
configuration and for the A2A (agent-to-agent) framing.

SDK note
--------
This server is written against the official ``mcp`` Python SDK and its
``FastMCP`` helper (``pip install "mcp[cli]"`` — the same package historically
distributed as ``fastmcp``). The SDK is an *optional* dependency of Quorum: the
import is deferred into :func:`build_server` so that importing this module, and
running the rest of the test suite, never requires MCP to be installed. If the
SDK is missing, :func:`main` exits with a clear, actionable message instead of a
raw ``ImportError``.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # for type checkers only; never imported at runtime here
    from mcp.server.fastmcp import FastMCP

# Keep depth choices in one place so the tool signature and any validation agree.
_DEPTHS = ("scan", "standard", "due_diligence")

_MISSING_SDK_MESSAGE = (
    "The Quorum MCP server requires the MCP Python SDK.\n"
    'Install it with:  pip install "mcp[cli]"\n'
    "(historically also distributed as the 'fastmcp' package).\n"
    "Then re-run this server, or point your MCP host at it per protocols/README.md."
)


def build_server() -> "FastMCP":
    """Construct and return the configured ``FastMCP`` server.

    The MCP SDK is imported here, not at module top, so this file is importable
    (and unit-testable) without the SDK present. Both tools are registered on the
    returned server; the caller runs it (see :func:`main`).

    Raises :class:`ModuleNotFoundError` if the SDK is absent — :func:`main`
    catches this and prints :data:`_MISSING_SDK_MESSAGE`.
    """
    from mcp.server.fastmcp import FastMCP

    server = FastMCP(
        "quorum",
        instructions=(
            "Quorum is an open-source AI consulting firm. Use run_engagement to "
            "commission a sourced, fact-checked market report for a region and "
            "industry; use list_analyst_skills to see the methodologies available "
            "before commissioning one."
        ),
    )

    @server.tool()
    def list_analyst_skills() -> list[dict[str, str]]:
        """List the methodology analysts the firm can staff.

        Returns one entry per skill with its ``name`` and ``description``. Reads
        only skill frontmatter — no model call, no API key required — so a host
        can render the firm's capabilities up front.
        """
        from quorum.skills_loader import skill_descriptions

        return [
            {"name": name, "description": description}
            for name, description in sorted(skill_descriptions().items())
        ]

    @server.tool()
    def run_engagement(region: str, industry: str, depth: str = "standard") -> str:
        """Run a Quorum engagement and return the final report as Markdown.

        Args:
            region: Region or ISO country code (e.g. ``CN``, ``US``, ``EU``).
            industry: Industry to analyze (e.g. ``electric vehicles``).
            depth: Compute tier — one of ``scan``, ``standard``, or
                ``due_diligence``. Higher tiers staff more analysts and run
                deeper queries. Defaults to ``standard``.

        Requires a provider API key (``ANTHROPIC_API_KEY`` or ``OPENAI_API_KEY``)
        in the server's environment; the engagement makes live model calls.
        """
        if depth not in _DEPTHS:
            raise ValueError(f"depth must be one of {_DEPTHS}; got {depth!r}")
        return _run_engagement_sync(region=region, industry=industry, depth=depth)

    return server


def _run_engagement_sync(region: str, industry: str, depth: str) -> str:
    """Run an engagement to completion and return the report markdown.

    The orchestrator is async; MCP tool callables are simplest as sync functions,
    so the event loop is driven here with :func:`asyncio.run`. Imports are local
    to keep the provider/orchestrator stack off this module's import path. The
    report is written to a temp file by the orchestrator and read back so the
    tool returns the report text itself, not a path the host cannot reach.
    """
    import tempfile
    from pathlib import Path

    from quorum.orchestrator import Engagement, ManagingPartner

    engagement = Engagement(region=region, industry=industry, depth=depth)
    with tempfile.TemporaryDirectory(prefix="quorum-mcp-") as tmp:
        out_path = Path(tmp) / "report.md"
        partner = ManagingPartner(workdir=Path(tmp) / "engagements")
        written: Path = asyncio.run(partner.run(engagement, out=out_path))
        return written.read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Entry point: build the server and serve over stdio.

    Returns a process exit code. If the MCP SDK is not installed, prints an
    actionable message and returns ``1`` rather than crashing with a traceback,
    so a host that launches this without the dependency gets a usable error.
    """
    _ = argv  # no flags yet; transport is stdio. Reserved for future options.

    # Load .env if present so the provider keys are available to run_engagement,
    # mirroring the CLI. Absence of python-dotenv is non-fatal.
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    try:
        server = build_server()
    except ModuleNotFoundError:
        print(_MISSING_SDK_MESSAGE)
        return 1

    # FastMCP.run() blocks, serving over stdio until the host disconnects.
    server.run()
    return 0


def _as_dicts(skills: Any) -> list[dict[str, str]]:  # pragma: no cover - reserved helper
    """Normalize a skills mapping to a list of dicts (kept for transport reuse)."""
    return [{"name": str(k), "description": str(v)} for k, v in dict(skills).items()]


if __name__ == "__main__":
    raise SystemExit(main())
