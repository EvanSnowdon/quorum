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
              │  decompose brief into task contracts (Scope Lock first)
              ├──► Phase-1 experts (fact base, parallel)      ─► fact-check
              ├──► Phase-2 experts (strategy, with checked    ─► fact-check
              │         fact-base sections in context)
              ├──► Phase-3 experts (valuation & critique,     ─► fact-check
              │         with checked strategy sections in context)
              │         │  query data spine, write working papers
              │         ▼
              │    engagements/<id>/workpapers/*.md
              ├──► Synthesis loop (conflict scan ─► adjudication + revision
              │         orders ─► ordered seats rewrite ─► final House View
              │         with Canonical figures)
              ├──► Red team (revised sections + House View) ─► canonical
              │         amendment (one bounded pass) ─► editor (blocks)
              ▼
        engagements/<id>/report.md   (assembled in code, three parts,
                                      sections and dissent verbatim)
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
3. **Chief editor** (lead model). Owns the editorial voice, not the body: it
   writes the executive summary (gated, pyramid-style), the reconciliation of
   the red team's arguments (accept-and-adjust or rebut-with-citation, never
   silence), and the scenario analysis. The body sections and the red-team
   memo enter the deliverable verbatim through programmatic assembly (below).

A report that cannot clear a gate ships with the failure documented rather
than silently lowered standards: gate verdicts are part of the deliverable
bundle.

## Synthesis gate and three-phase dispatch

Both rules below were motivated by review of real deliverables: parallel
framework seats produced mutually incompatible where-to-play recommendations,
and the valuation's volumes did not match the sizing section — with no stage
of the pipeline responsible for noticing.

**Three-phase dispatch** (v0.3, generalising the v0.2 two-phase split). Seats
in `crews.yaml` carry an optional `phase` (1 by default): **1 = fact base**
(sizing, structure, demand, macro), **2 = strategy** (where-to-play choices
made against the checked fact base), **3 = pricing & critique** (valuation,
unit economics, strategy critics). The orchestrator groups the staffed crew by
phase and runs the phases in ascending order: each phase's analysts run in
parallel, are fact-checked, and only then does the next phase dispatch — with
the checked earlier sections in its contracts' context (sizing/structure/
demand in full entering phase 2; the strategy sections plus sizing in full
entering phase 3; everything else as a one-line gist). The point is causal
order: strategy chooses against real SAM/SOM and structure, and valuation
prices the specific plays actually proposed, never a hypothetical generic
entrant. The tier headcount cap is applied before the grouping; a tier whose
budget trims away a whole phase simply skips it, and a roster with no
strategy seat (the scan tier) degrades valuation to a stated market-level
view.

**Synthesis gate** (v0.3). After every phase is checked, two lead-model
passes force the parallel sections to converge before the red team runs. A
*conflict scan* lists where the sections contradict one another — segment and
price-band clashes, volume targets outside the sizing section's SAM/SOM,
numerical contradictions about the same entity, mutually exclusive strategic
claims — each graded High/Med/Low and numbered contiguously. The *House View*
is then the supervising partner's ruling: it commits the report to a
**single selected play** (ruling explicitly on every High conflict),
adjudicates every framework recommendation in a table (Adopted / Rejected /
Reframed, with reasons), and bridges the play's volume targets back to
SAM/SOM. Both artifacts land under `gates/`; the House View is embedded
verbatim in the deliverable's Part I, the red team attacks it alongside the
sections, and the editor's executive summary is required to carry the
selected play rather than inventing another direction.

**Revision loop** (v0.4). Partner review of a real v0.3 deliverable showed
the ruling layer was not enough: the House View ruled at the top while the
sections beneath it still carried the pre-ruling numbers (a DCF pricing
rejected plays, the ruling itself quoting a superseded SAM). The fix makes
the ruling an input to rewriting — a closed loop:

```
conflict scan ─► adjudication draft (rulings + REVISION ORDERS) ─► ordered
seats rewrite in parallel ─► fact-check, swap in, archive originals ─►
final House View (Canonical figures) over the revised body
```

The adjudication draft (`gates/adjudication.md`) closes with a
machine-readable `REVISION ORDERS:` block — one order per section whose
content the rulings overturned. The orchestrator parses the block
(`quality.parse_revision_orders`), maps each ordered section title back to
its analyst seat, and re-dispatches the ordered seats concurrently under
revision contracts: rewrite the section under the rulings and the corrected
canonical assumptions, rerun the models on the selected play's inputs, no
re-arguing the verdict. Each revision is fact-checked and **replaces** its
section; the pre-revision draft is archived as `gates/<seat>.pre-revision.md`
for the audit trail, and an order naming a seat the depth tier did not staff
is recorded under `gates/` and skipped. The *final* House View
(`gates/house_view.md`) is then written against the revised body and opens
with a **Canonical figures** table (SAM, SOM, implied volumes, target band,
corrected margins, key unit costs) that the executive summary and the
scenario analysis are required to match. Rulings may not be decided by
comparing self-assigned confidence scores — adjudication goes back to source
tier, recency, and recomputable derivations — and an honest-conclusion rule
binds the final ruling and the summary: a play whose corrected base case
destroys value with every decision gate passed must be called dead, not
gated, with an alternative direction or a no-entry call stated instead.
Synthesis completions run under `QUORUM_SYNTHESIS_MAX_TOKENS` (default
5000) with one bounded truncation retry; a persistent truncation lands a
warning under `gates/` and the run continues.

Because the revision loop runs *before* the red team, v0.4.1 adds one
bounded amendment pass after it (`quality.amend_canonical`): when the
red-team memo demonstrates a canonical-grade error in the final House View —
a wrong pricing basis, a derivation that does not recompute, or a gate table
that ignores its own coherence check — the pass re-emits the House View with
only the Canonical figures table, the gate table, and the directly affected
inline figures corrected, closing with an "Amendments after red-team review"
section, and the pre-amendment text is archived as
`gates/house_view.pre-amendment.md`. When the memo proves no such error the
pass answers with a `NO AMENDMENT REQUIRED` sentinel and the House View
passes through byte-identical; exactly one round runs and the red team is
not re-run against the amended text, so the correction cannot oscillate with
the challenge.

v0.5 hardens the loop's entry and exit. On entry, the strategy seat's brief
and the adjudication carry a structural **pre-screen**: candidate plays must
span the attractive spaces the engagement's own profit-pool and
growth-outlook analyses name, a candidate that is structurally loss-making
for a sub-scale entrant (or whose cost position overlaps the cost leader's
core) fails the screen, and the adjudication may not re-confirm a condemned
play — it must order a re-selection or rule a direction-level no-go with the
named follow-up engagement. On exit, once the canonical record is final, a
**stale-figure sweep** (`quality.stale_figures` / `quality.resolve_stale`)
runs whenever a revision round or an amendment replaced anything: leftover
superseded values still stated as current in the body are listed under
`gates/stale_figures.md` and fixed in one round of pin-point revision orders
confined to the named sections (pre-fix texts archived as
`gates/<seat>.pre-stale-fix.md`; anything the round misses is recorded as a
limitation, with the Canonical figures table prevailing).

v0.6 adds **deterministic arithmetic verification**
(`quality/arithmetic.py`): before the synthesis loop reads the valuation
section, its stated figures are extracted to strict JSON and the DCF and
the SOM chain are recomputed in pure Python — present values, EV, NPV,
terminal share, the explicit-horizon NPV, and the share each comparison
implies on each denominator. A prose claim that contradicts the
recomputation triggers one pin-point correction (verified once more), and
the verified-figures table (`gates/arithmetic.md`) enters the final House
View and the editor as authoritative over any prose claim — a numeric
conflict is settled by re-running the arithmetic, never by a model's
assertion.

**Programmatic assembly.** The final `report.md` is assembled in code
(`output/report.py`), not rewritten by a model, as a three-part document:
**Part I — The Decision** (executive summary, House View, scenario analysis,
reconciliation), **Part II — Working Papers** (the fact-checked sections
verbatim, in roster order, under their human-readable titles), **Part III —
Challenge** (the red team's memo verbatim), then the appendix. The title is
the only H1; parts are H2 and the sections beneath them H3. The editor's
three blocks are the only model-authored assembly text, produced in at most
two completions, so no provider output ceiling can truncate the body and no
rewrite can paraphrase the dissent away. Worker drafts additionally pass a
truncation heuristic at landing: a draft whose final line ends mid-sentence
gets a `gates/<seat>.truncation-warning.md` and an inline note to its
fact-checker. Internal analyst keys never appear in the deliverable; they
survive only as working-paper filenames inside the engagement bundle.

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
