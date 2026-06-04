# Quorum Architecture

This document describes the engineering design of the Quorum engagement
engine. The audience is contributors working on the engine core; for the
product-level overview, see the top-level [README](../README.md).

## Overview

Quorum is an orchestrator-worker system. A single lead agent — the engagement
manager — owns scoping, decomposition, dispatch, and assembly. A pool of
worker agents — the methodology experts and quality-gate reviewers — each
execute one bounded task and return one artifact. Workers never talk to each
other; all coordination flows through the orchestrator and the filesystem.

```
CLI ──► Engagement Manager (lead model)
              │  decompose brief into task contracts
              ├──► Expert workers (worker model, parallel)
              │         │  query data spine, write working papers
              │         ▼
              │    engagements/<id>/workpapers/*.md
              ├──► Quality gates (sequential: fact-check → red team → editor)
              ▼
        engagements/<id>/report.md
```

Two models are in play: a **lead model** for the engagement manager and the
chief editor (defaults to `claude-opus-4-6`), and a **worker model** for
experts and the first two gates (defaults to `claude-sonnet-4-6`). With
`QUORUM_PROVIDER=openai` the default for both roles is `gpt-4o-mini`. All of
this is overridable via `QUORUM_MODEL`, `QUORUM_LEAD_MODEL`,
`QUORUM_WORKER_MODEL`, and `QUORUM_BASE_URL` (any OpenAI-compatible endpoint,
including local servers).

## The four-element task contract

Every unit of work the orchestrator dispatches is a task contract with exactly
four elements. This is the system's central discipline: a worker receives a
contract, not a conversation.

| Element | Contents |
|---|---|
| `objective` | The single question this worker must answer, with the engagement context (region, industry, depth) inlined. One objective per contract — if the orchestrator needs two answers, it issues two contracts. |
| `output_format` | The exact structure of the artifact: section headings, required tables, the claim-labeling rules, maximum length. Workers that return free-form prose are a bug. |
| `tools` | The explicit tool allowlist for this task: which data-spine endpoints, whether web search is permitted, whether the memory layer may be read. Anything not listed is unavailable. |
| `boundaries` | What the worker must not do: scope exclusions, tool-call budget for this task, hard rules ("do not estimate figures the spine can provide", "do not read other workers' output"). |

Contracts are Pydantic models, validated before dispatch. The contract — not
the worker's system prompt — is the source of truth for what a task may
consume and must produce.

## Compute tiers

Depth is the user's lever for trading cost against rigor. Each tier sets the
expert headcount and the per-expert tool-call budget; the orchestrator
enforces both.

| Tier | Experts (≈) | Tool calls per expert (≈) | Intended use |
|---|---|---|---|
| `scan` | 6 | 4 | First look at a market; orientation, not decisions |
| `standard` | 14 | 10 | The default; a full methodology sweep with sourced data |
| `due_diligence` | 26 | 18 | Decision-grade; multiple experts per framework, deeper spine queries, expanded red-team pass |

The expert roster per tier is defined in `crews.yaml` (which skills run at
which depth, and with what budget multipliers). The numbers above are
calibration targets, not hard constants — `crews.yaml` is the source of
truth.

Budgets are enforced, not advisory: when a worker exhausts its tool-call
budget it must conclude with what it has and flag unresolved questions in a
dedicated section of its working paper, which the orchestrator surfaces to the
red-team gate.

## Artifacts on disk, pointers in context

Workers write their full output to disk and return only a lightweight pointer
to the orchestrator:

```
{ "artifact": "workpapers/five-forces.md",
  "status": "complete",
  "headline": "Supplier power is the binding constraint; entry barriers eroding",
  "open_questions": 2,
  "data_claims": 31, "inference_claims": 9 }
```

The orchestrator plans against pointers and headlines; it reads a full
artifact into context only when a gate or the assembly step requires it. This
keeps the lead model's context proportional to the number of tasks, not the
volume of their output, and it means every intermediate product survives the
run for auditing.

Engagement directory layout:

```
engagements/2026-06-04T1530-cn-electric-vehicles/
├── brief.md            # resolved scope and task plan
├── workpapers/         # one file per expert
├── spine/              # raw responses from data-spine queries (the source ledger)
├── gates/              # fact-check findings, red-team memo, editor notes
└── report.md           # the deliverable
```

## Skills and progressive disclosure

Each methodology expert is defined by a `SKILL.md` under `analyst-skills/`.
Skills load progressively:

1. **Frontmatter only** at planning time. The orchestrator selects experts by
   reading each skill's `name` and `description` — a few hundred tokens for
   the whole library.
2. **Full body** at dispatch time. When a contract is issued, the complete
   skill body (role, core questions, method, failure modes, output format) is
   injected into that worker's system prompt — and only that worker's.

This is why skill bodies are capped at roughly 500 lines: a skill is a lens,
not an encyclopedia. The same files install standalone into Claude Code,
Codex, Gemini CLI, and other skills-compatible agents, which is the Layer 1
product; the engine consumes the identical artifact, so a skill improved for
one layer improves both.

## The data spine

The spine is the engine's grounding layer: a router in front of official
statistics APIs, configured by per-country source packs
(`src/quorum/source_packs/*.yaml`).

Resolution order:

1. **Official APIs first.** National statistics offices, central banks,
   regulators, and intergovernmental bodies (World Bank, IMF, OECD, UN,
   Eurostat), as mapped in the relevant source pack.
2. **Web sources fill gaps.** When the spine has no official series for a
   question (and the contract permits web access), workers may use secondary
   sources — but a secondary source can never silently override an official
   one.
3. **Absence is reported.** If neither yields an answer, the gap is stated in
   the working paper. The spine never invents and never lets a worker invent.

Every factual claim in every artifact carries one of two labels:

- `[DATA]` — traceable to a spine response or cited source; the raw response
  is preserved under `spine/` so the fact-check gate can re-verify.
- `[INFERENCE]` — derived by reasoning from labeled data; must state its
  inputs.

Both labels carry a confidence level (`high` / `medium` / `low`). The
fact-check gate samples `[DATA]` claims against the ledger; the red team
attacks low-confidence `[INFERENCE]` chains first.

## Memory layer

Quorum persists institutional memory as markdown in git, under
`.quorum-memory/` in the user's working directory (gitignored by default in
this repo; users may commit theirs):

```
.quorum-memory/
├── markets/cn-electric-vehicles.md   # rolling notes per region×industry
├── sources/cn.md                     # which sources proved reliable, quirks, dead ends
└── engagements.md                    # index of past runs with one-line outcomes
```

At scoping time the orchestrator reads any matching market and source notes
and inlines the relevant portions into expert contracts; at close, it appends
a short update. Plain markdown was a deliberate choice over a vector store for
v0: diffable, auditable, mergeable across a team via git, and trivially
editable when the memory is wrong. Retrieval beyond exact region×industry
matching is roadmap work (see [roadmap](roadmap.md)).

## Quality gates

Three sequential gates stand between assembly and delivery. Each consumes the
draft plus the artifacts it needs, and produces a written verdict under
`gates/`.

1. **Fact-checker** (worker model). Samples `[DATA]` claims and re-verifies
   them against the `spine/` ledger; checks that no `[INFERENCE]` claim is
   dressed as data; verifies arithmetic in tables. Output: a findings list
   with severities. Blocking findings return the draft to the orchestrator for
   repair.
2. **Red team** (worker model, separate instance with an adversarial brief).
   Attacks the argument rather than the facts: unstated assumptions,
   survivorship in the source mix, conclusions that outrun their confidence
   labels, the strongest case for the opposite recommendation. Output: a memo.
   The editor must either address each point or explicitly accept the risk in
   the report's limitations section.
3. **Chief editor** (lead model). Owns the deliverable: enforces pyramid
   structure (the `pyramid-editor` skill), reconciles contradictions between
   working papers, prunes anything that doesn't serve the reader, writes the
   executive summary last, and signs off on the limitations section.

A report that cannot clear a gate ships with the failure documented rather
than silently lowered standards: gate verdicts are part of the deliverable
bundle.

## Module map

```
src/quorum/
├── cli.py            # entry point (quorum --region --industry --depth)
├── orchestrator.py   # engagement manager: plan, dispatch, assemble
├── contracts.py      # task-contract models and validation
├── workers.py        # worker runtime: skill loading, budget enforcement
├── spine.py          # data-spine router and claim ledger
├── gates.py          # fact-check, red-team, editor passes
├── memory.py         # markdown-in-git memory layer
├── providers.py      # anthropic / openai / local model adapters
├── crews.yaml        # tier → roster → budget configuration
└── source_packs/     # per-country official-source maps
analyst-skills/        # the 15 SKILL.md methodology experts
```

## Design rules

Contributors to the engine core should preserve these invariants:

1. Workers are stateless and isolated: contract in, artifact out, no shared
   context between workers.
2. All coordination goes through the orchestrator; all persistence goes
   through the engagement directory.
3. Budgets are enforced by the runtime, not requested in prompts.
4. Anything that crosses a process or model boundary is a validated Pydantic
   model.
5. The skill file is the expert. No expert behavior may live only in Python.
6. A claim without a label is a lint error in the gate pipeline, not a style
   issue.
