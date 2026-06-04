# Roadmap

Phases ship in order; a phase is done when its exit criteria hold, not when a
date arrives. Dates are intentionally absent pre-1.0.

## Phase 0 — The skills wedge (now)

Ship the Layer 1 product on its own merits: fifteen methodology analysts that
are useful the day you install them, with no engine required.

- The 15 `SKILL.md` analysts, each self-contained and individually installable
  (`npx skills add EvanSnowdon/quorum`, Claude Code plugin marketplace).
- Skill authoring guide and frontmatter spec in CONTRIBUTING.
- Repository scaffolding: docs, license, CI placeholder, packaging metadata.

Exit criteria: all 15 skills pass self-test transcripts on two real
industries each; install paths verified on at least two agent platforms.

## Phase 1 — MVP firm

The smallest engagement engine that earns the slogan: one command in, one
defensible report out.

- `quorum` CLI: `--region`, `--industry`, `--depth` end to end.
- Orchestrator with four-element task contracts; parallel expert dispatch;
  artifacts-on-disk with pointer returns.
- Data spine v1: World Bank and IMF as universal sources plus an initial set
  of country packs (target: US, CN, EU/Eurostat, JP, GB at launch);
  `[DATA]`/`[INFERENCE]` labeling enforced in worker output.
- All three quality gates operative (fact-check, red team, editor).
- The three compute tiers wired to `crews.yaml`.
- Memory layer v1: write-and-exact-match-read of market and source notes.
- Provider adapters: Anthropic, OpenAI, OpenAI-compatible local endpoints.

Exit criteria: a `standard` engagement on a G20 market completes unattended
in under 15 minutes and under $5 in tokens, and survives a manual audit of
20 sampled `[DATA]` claims with zero fabrications.

## Phase 2 — Depth and reach

Make the firm better at its job, not just bigger.

- **SDMX support** in the data spine — unlocks Eurostat, ECB, OECD, BIS, and
  most national statistics offices through one protocol, and makes community
  source packs dramatically cheaper to write.
- **Agent-protocol surface**: expose the firm and individual experts over MCP
  so other agents can hire Quorum as a tool; evaluate A2A as it stabilizes.
- **Memory retrieval**: move past exact region×industry matching to indexed
  retrieval across the memory layer (adjacent markets, prior sources, past
  red-team findings), while keeping markdown-in-git as the storage format.
- **Web UI**: local-first report viewer — engagement browser, claim-level
  source tracebacks, diff view between engagements on the same market.
- Source-pack coverage drive with the community: target 30+ countries.
- Eval harness: regression suite of reference engagements scored on sourcing
  accuracy, claim-label discipline, and gate effectiveness.

Exit criteria: a non-maintainer can add a working SDMX country pack in under
an hour; eval suite runs in CI and blocks regressions.

## Phase 3 — Hosted Quorum (open-core)

The cloud offering, for teams that want the firm without operating it. The
open-source core remains complete and self-hostable; the hosted line is
operational convenience and team features, never engine capability.

- Managed engagements: scheduled and recurring runs, watch-this-market alerts.
- Team workspaces: shared memory layer, report library, access control.
- Managed data connectors: maintained credentials and quota handling for
  rate-limited official APIs.
- Hosted report delivery and sharing.

Exit criteria: paying design partners running recurring engagements; a
published open-core boundary document the community has reviewed.

## Non-goals

For clarity, things Quorum will not pursue in any phase:

- Reproducing or reselling proprietary research content.
- Becoming a general-purpose agent framework — the engine stays
  purpose-built for engagements.
- Moving existing open-source functionality behind the hosted offering.
