<p align="center">
  <img src="assets/logo.svg" alt="Quorum" width="160" />
</p>

<h1 align="center">Quorum</h1>

<p align="center">
  <strong>Your open-source consulting firm. Any market, any industry, in minutes.</strong>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <a href="#"><img src="https://img.shields.io/badge/CI-passing-brightgreen.svg" alt="CI"></a>
  <a href="#"><img src="https://img.shields.io/badge/PyPI-quorum--firm-orange.svg" alt="PyPI"></a>
  <a href="#"><img src="https://img.shields.io/badge/python-3.11%2B-blue.svg" alt="Python 3.11+"></a>
</p>

<p align="center">
  <a href="README.zh-CN.md">中文文档</a>
</p>

---

Quorum turns the playbooks of the world's best-known strategy thinkers into agent skills, then staffs them as a multi-agent consulting firm. Ask for any region and industry; get back a sourced, fact-checked, consulting-grade market report.

It ships in two layers:

- **Layer 1 — The Skills Library.** Fifteen self-contained methodology analysts (Porter's Five Forces, Jobs-to-be-Done, 7 Powers, Playing to Win, and more) packaged as plain-text `SKILL.md` files. Install them into Claude Code, Codex, Gemini CLI, or any skills-compatible agent and use each one standalone.
- **Layer 2 — The Firm.** A multi-agent engagement engine. You specify `region × industry × depth`; an engagement manager decomposes the brief, dispatches a parallel team of methodology experts grounded in official statistics, and routes every draft through fact-checking, red-team, and editorial gates before the final report lands on disk.

## Why Quorum

A single analyst-grade market report from a commercial research house typically costs **$800–$2,850** and takes days to procure. A Quorum engagement covering the same ground runs on roughly **$4 of model tokens** and finishes in minutes — with every claim labeled, sourced, and auditable.

| | Commercial report | Quorum |
|---|---|---|
| Price | $800–$2,850 per report | ~$4 in tokens (standard depth) |
| Turnaround | Days to weeks | Minutes |
| Coverage | Catalog-limited | Any region × any industry |
| Methodology | Opaque | Open, inspectable SKILL.md files |
| Sourcing | Trust the brand | Official-statistics-first, every claim tagged `[DATA]` or `[INFERENCE]` with confidence levels |
| Customization | None | Fork it. It's MIT. |

Quorum is not a replacement for proprietary expert networks or human judgment (see [Honest limitations](#honest-limitations)). It is a replacement for the long tail of overpriced, under-sourced market overviews.

## Quickstart

### Mode 1 — Skills only

Install the analyst skills into any skills-compatible agent:

```bash
npx skills add EvanSnowdon/quorum
```

Or, inside Claude Code:

```
/plugin marketplace add EvanSnowdon/quorum
```

Then invoke any analyst directly — for example, ask your agent to "run a five-forces analysis on the European battery recycling market" and the `five-forces-analyst` skill drives the structure, evidence standards, and output format.

### Mode 2 — The full firm

```bash
git clone https://github.com/EvanSnowdon/quorum.git
cd quorum
pip install -e .

export ANTHROPIC_API_KEY=sk-...   # or OPENAI_API_KEY, or point at a local model

quorum --region CN --industry "electric vehicles" --depth standard
```

The engagement runs end to end and writes a full report bundle to `engagements/<timestamp>-cn-electric-vehicles/`, including the final report, per-expert working papers, the source ledger, and quality-gate findings.

Quorum is model-agnostic. Defaults target Anthropic models; override with environment variables:

```bash
QUORUM_PROVIDER=openai          # anthropic | openai | local
QUORUM_MODEL=gpt-4o-mini        # single-model override
QUORUM_LEAD_MODEL=...           # orchestrator / editor model
QUORUM_WORKER_MODEL=...         # expert / analyst model
QUORUM_BASE_URL=...             # any OpenAI-compatible endpoint, incl. local servers
```

## Features

| Feature | Description |
|---|---|
| 15 methodology analysts | Canonical strategy frameworks as portable, auditable skills |
| Parallel expert teams | Orchestrator-worker architecture; experts run concurrently with explicit task contracts |
| Official data spine | Official statistics APIs queried first; web sources fill gaps, never replace primary data |
| Claim labeling | Every statement tagged `[DATA]` (sourced) or `[INFERENCE]` (reasoned), with confidence levels |
| Three quality gates | Fact-checker, red team, and chief editor review every report before delivery |
| Depth tiers | `scan`, `standard`, `due_diligence` — compute scales with the stakes |
| Engagement memory | Past engagements persist as markdown-in-git; the firm gets smarter about your markets |
| Model-agnostic | Anthropic, OpenAI, or any OpenAI-compatible local endpoint |
| Country source packs | Per-country YAML packs mapping official statistical sources; community-extensible |

## Architecture

```
                          ┌────────────────────────────┐
                          │   quorum CLI (entry point) │
                          │  region × industry × depth │
                          └─────────────┬──────────────┘
                                        │
                          ┌─────────────▼──────────────┐
                          │    Engagement Manager      │
                          │  (orchestrator: scoping,   │
                          │   MECE decomposition,      │
                          │   task contracts)          │
                          └─────────────┬──────────────┘
                ┌───────────────────────┼───────────────────────┐
                │                       │                       │
      ┌─────────▼─────────┐  ┌─────────▼─────────┐  ┌─────────▼─────────┐
      │  Expert Worker 1  │  │  Expert Worker 2  │  │  Expert Worker N  │
      │ (five-forces, ...)│  │ (jtbd, pestel,...)│  │ (valuation, ...)  │
      └─────────┬─────────┘  └─────────┬─────────┘  └─────────┬─────────┘
                │                      │                      │
                └──────────┬───────────┴──────────┬───────────┘
                           │                      │
                ┌──────────▼──────────┐  ┌────────▼─────────┐
                │     Data Spine      │  │   Memory Layer   │
                │ official stats APIs │  │ markdown-in-git  │
                │ [DATA]/[INFERENCE]  │  │ past engagements │
                └──────────┬──────────┘  └──────────────────┘
                           │
              ┌────────────▼────────────┐
              │      Quality Gates      │
              │  1. Fact-checker        │
              │  2. Red team            │
              │  3. Chief editor        │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │   engagements/<id>/     │
              │   report + working      │
              │   papers + source log   │
              └─────────────────────────┘
```

See [docs/architecture.md](docs/architecture.md) for the full engineering design, including the four-element task contract, compute tiers, and the artifact-pointer pattern.

## The Skills Library

Fifteen analysts, each a standalone `SKILL.md` encoding a named methodology — its core questions, evidence standards, common failure modes, and output structure:

| Skill | Methodology |
|---|---|
| `five-forces-analyst` | Porter's Five Forces — industry structure and profit pools |
| `value-chain-analyst` | Value chain analysis — where margin actually accrues |
| `jtbd-disruption-analyst` | Jobs-to-be-Done and disruption theory |
| `seven-powers-analyst` | Hamilton Helmer's 7 Powers — durable competitive advantage |
| `good-strategy-critic` | Rumelt's kernel — diagnosing bad strategy |
| `playing-to-win-analyst` | Lafley/Martin's strategy cascade |
| `blue-ocean-analyst` | Blue Ocean — value innovation and uncontested space |
| `crossing-the-chasm-analyst` | Moore's technology adoption lifecycle |
| `pestel-analyst` | Macro-environment scanning |
| `tam-sam-som-analyst` | Market sizing with explicit assumptions |
| `ansoff-analyst` | Growth vector analysis |
| `three-horizons-analyst` | McKinsey's three horizons of growth |
| `pyramid-editor` | Minto Pyramid Principle — executive-grade structuring |
| `valuation-analyst` | Comparables and DCF-style sanity checks |
| `mece-engagement-manager` | MECE decomposition and engagement scoping |

Each skill carries a `DISCLAIMER` noting it encodes the published, public form of the methodology — not proprietary content from its authors or their firms.

## Open Source vs. Cloud

Quorum follows an open-core model. Everything in this repository — the skills library, the engagement engine, the quality gates, the source packs — is MIT-licensed and self-hostable, forever. A hosted version with team workspaces, scheduled engagements, and managed data connectors is planned; see [docs/roadmap.md](docs/roadmap.md). Nothing in the open-source core will be moved behind the cloud offering.

## Honest limitations

We would rather you know these going in:

- **No proprietary content.** Quorum encodes the *published, public* form of each methodology. It does not and will not reproduce paywalled reports, proprietary databases, or expert-network calls.
- **Not a substitute for human judgment.** Reports are decision-support inputs, not decisions. High-stakes calls deserve a human who owns the outcome.
- **Data is only as good as the spine.** Coverage is strongest where official statistics are open and machine-readable. Gaps are flagged, not papered over.
- **Inference is labeled because inference can be wrong.** The `[INFERENCE]` tag exists so you know exactly which claims to pressure-test.

Where Quorum genuinely wins: breadth across public information, geographic coverage no analyst team can match, minutes instead of weeks, two orders of magnitude on cost, and full transparency into how every conclusion was reached.

## Contributing

The two highest-leverage contributions, in order:

1. **A new methodology skill.** Know a framework that deserves a seat at the table? The skill format is plain markdown with a small frontmatter block — no Python required.
2. **A country source pack.** Map the official statistical sources for a country we don't cover yet. One YAML file extends the firm's reach to an entire economy.

Both paths have step-by-step guides in [CONTRIBUTING.md](CONTRIBUTING.md). We commit to a first response on every PR and issue within 48 hours.

## License

MIT. See [LICENSE](LICENSE).
