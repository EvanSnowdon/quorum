# Quorum protocol adapters

This directory exposes Quorum to other agents and agent hosts over open
protocols, so the firm can be commissioned as a *tool* rather than only as a CLI.

- **MCP (Model Context Protocol)** — `mcp_server.py` publishes Quorum as an MCP
  server with two tools. This is the supported, runnable adapter.
- **A2A (Agent-to-Agent)** — notes below on framing Quorum as an A2A agent. The
  MCP server is the substrate; A2A is the inter-agent envelope around it.

## What the MCP server exposes

| Tool | Signature | Cost | Needs API key |
|---|---|---|---|
| `list_analyst_skills` | `() -> list[{name, description}]` | reads skill frontmatter only | no |
| `run_engagement` | `(region, industry, depth="standard") -> str` | runs a full engagement | yes |

`run_engagement` returns the final report as Markdown. `depth` is one of `scan`,
`standard`, or `due_diligence`.

## Install

The server is written against the official MCP Python SDK (`FastMCP`), which is
an optional dependency:

```bash
pip install -e .            # Quorum itself
pip install "mcp[cli]"      # the MCP SDK (a.k.a. the 'fastmcp' package)
```

Set a provider key in the environment the server will run in (see `.env.example`
at the repo root):

```bash
export ANTHROPIC_API_KEY=sk-...     # or OPENAI_API_KEY, or a local-model base URL
```

## Run it directly

The reference build speaks **stdio**, which is what desktop agent hosts launch
and connect to:

```bash
python -m protocols.mcp_server
```

If the MCP SDK is not installed, the process prints an actionable install message
and exits non-zero rather than throwing a traceback.

## Connect from Claude Desktop

Add Quorum to the host's MCP server map. On macOS this file is
`~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "quorum": {
      "command": "python",
      "args": ["-m", "protocols.mcp_server"],
      "cwd": "/absolute/path/to/quorum",
      "env": {
        "ANTHROPIC_API_KEY": "sk-..."
      }
    }
  }
}
```

Restart Claude Desktop. The `quorum` tools then appear in the host, and you can
ask it to "list the analyst skills" or "run a standard engagement on the US
cybersecurity market" and the model will call the corresponding tool.

If you installed Quorum into a virtual environment, point `command` at that
environment's interpreter (e.g. `/absolute/path/to/quorum/.venv/bin/python`) so
the server starts with the dependencies on its path.

## Connect from Claude Code

Claude Code reads the same MCP server schema. Register the server with the CLI:

```bash
claude mcp add quorum -- python -m protocols.mcp_server
```

or add it to the project's `.mcp.json`:

```json
{
  "mcpServers": {
    "quorum": {
      "command": "python",
      "args": ["-m", "protocols.mcp_server"],
      "env": { "ANTHROPIC_API_KEY": "sk-..." }
    }
  }
}
```

## A2A (Agent-to-Agent) integration

MCP connects an agent to *tools*; A2A connects an agent to *other agents* as
peers. Quorum fits the A2A model cleanly: it is a long-running specialist worker
that accepts a brief and returns a structured deliverable.

To front Quorum as an A2A agent, wrap the same two capabilities behind an A2A
**Agent Card** and task endpoint:

- **Agent Card** — advertise the firm: a `run_engagement` skill (inputs
  `region`, `industry`, `depth`; output a Markdown report) and a
  `list_analyst_skills` skill (no inputs; output the methodology catalog). Mark
  `run_engagement` as long-running so callers poll for completion.
- **Task lifecycle** — map an incoming A2A task to one `run_engagement` call.
  Stream status while analysts run (scoping → dispatch → quality gates →
  assembly), then return the report as the task artifact. The per-expert working
  papers and quality-gate findings the orchestrator writes to the engagement
  bundle can be attached as supplementary artifacts.
- **Reuse the core** — both protocols call the same
  `quorum.orchestrator.ManagingPartner`; the adapter is a thin transport layer.
  Keep engagement logic in the core so MCP and A2A never diverge.

A2A is delivery-framing only — it does not change what Quorum produces or how it
sources and labels claims.
