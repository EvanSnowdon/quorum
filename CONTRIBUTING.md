# Contributing to Quorum

Thanks for considering a contribution. This document covers environment setup,
code standards, the two contribution paths we care most about, and how the PR
process works.

We commit to a **first response on every PR and issue within 48 hours.**

## Development environment

Requirements: Python 3.11+.

```bash
git clone https://github.com/EvanSnowdon/quorum.git
cd quorum
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Run the checks before pushing:

```bash
ruff check src tests
ruff format --check src tests
pytest
```

## Code standards

- **Formatting and linting** are enforced by `ruff` (config lives in
  `pyproject.toml`, line length 100). Run `ruff format` before committing.
- **Type annotations are required** on all public functions and methods.
  Internal helpers should be annotated too unless the types are trivially
  obvious.
- **Pydantic models** for anything that crosses a boundary: task contracts,
  source-pack schemas, gate verdicts, CLI config.
- Keep functions small and side effects explicit. The orchestrator is the only
  component allowed to coordinate state; workers must be pure given their task
  contract.
- Tests go in `tests/`, named `test_<module>.py`. New behavior needs a test;
  bug fixes need a regression test.
- Commit messages: imperative mood, one logical change per commit. No strict
  conventional-commits requirement, but `area: summary` prefixes
  (e.g. `skills: add ...`, `spine: fix ...`) are appreciated.

## Contribution path 1: a new methodology skill

This is the highest-leverage contribution and requires no Python. A skill is a
directory under `analyst-skills/` containing a single `SKILL.md`.

### Step 1 — Pick a methodology and check fit

Good candidates are published, citable strategy or analysis frameworks with a
distinct point of view (think: a framework with a book, a canonical HBR
article, or an equivalent public source behind it). Open an issue with the
`skill-proposal` label first so we can confirm there is no overlap with the
existing fifteen and agree on a directory name.

### Step 2 — Create the directory

Directory names are lowercase, hyphen-separated, and end in a role noun
(`-analyst`, `-critic`, `-editor`, `-manager`):

```
analyst-skills/
└── your-methodology-analyst/
    └── SKILL.md
```

### Step 3 — Write the frontmatter

`SKILL.md` opens with a YAML frontmatter block. All five fields are required:

```yaml
---
name: your-methodology-analyst
description: >
  One or two sentences stating what the skill analyzes, when an agent should
  invoke it, and what it produces. This is what the agent's skill router reads,
  so make the trigger conditions concrete.
license: MIT
metadata:
  methodology: "Name of the framework (Author, Year)"
  canonical_source: "Book or article title the public form is drawn from"
---
```

### Step 4 — Write the skill body

Follow the structure used by the existing skills:

1. **Role** — one paragraph: who this analyst is and the stance they take.
2. **Core questions** — the ordered question set the methodology exists to
   answer. This is the heart of the skill.
3. **Method** — step-by-step procedure, including what evidence to look for at
   each step and the evidence standard (`[DATA]` vs `[INFERENCE]` labeling,
   confidence levels).
4. **Failure modes** — the well-known ways this framework gets misapplied, and
   how the analyst should guard against each.
5. **Output format** — the exact section structure of the analyst's working
   paper.
6. **DISCLAIMER** — required, verbatim pattern:

   > DISCLAIMER: This skill encodes the published, public form of
   > [methodology] as described in [canonical source]. It is not affiliated
   > with, endorsed by, or a reproduction of proprietary material from
   > [author/firm].

Keep the body under roughly 500 lines. The engine loads skill bodies
progressively — frontmatter first, body on activation — so a focused skill
outperforms an exhaustive one.

### Step 5 — Self-test and submit

Install the skill into your own agent and run it against at least two real
industries. Include both transcripts (or links to gists) in the PR description
so reviewers can judge output quality, not just prose quality.

## Contribution path 2: a new country source pack

Source packs teach the data spine where a country's official statistics live.
One YAML file per country under `src/quorum/source_packs/`, named by ISO
3166-1 alpha-2 code (`de.yaml`, `br.yaml`, `jp.yaml`).

### Step 1 — Survey the official landscape

Identify the country's primary statistical agency, central bank, and the main
sector regulators. Official sources only — national statistics offices,
central banks, ministries, and intergovernmental bodies (UN, World Bank, IMF,
OECD, Eurostat). News outlets and commercial aggregators do not belong in a
source pack.

### Step 2 — Write the YAML

Schema (all top-level fields required unless marked optional):

```yaml
# src/quorum/source_packs/de.yaml
country: DE                 # ISO 3166-1 alpha-2, uppercase
country_name: Germany
language: de                # primary publication language, ISO 639-1
notes: >                    # optional: quirks reviewers/users should know
  Destatis GENESIS API requires free registration for bulk queries.

sources:
  - id: destatis            # unique within the file, lowercase snake_case
    name: Federal Statistical Office (Destatis)
    type: statistics        # statistics | central_bank | regulator | intergovernmental
    url: https://www.destatis.de
    api:                    # optional: omit the block if no machine API exists
      base_url: https://www-genesis.destatis.de/genesisWS/rest/2020
      format: json          # json | xml | csv | sdmx
      auth: token           # none | token | registration
    coverage:               # what the spine should route to this source
      - demographics
      - industry_production
      - trade
      - prices
    reliability: primary    # primary | secondary
    update_frequency: monthly   # optional: annual | quarterly | monthly | weekly
```

The `coverage` vocabulary is open but reuse existing terms where possible —
grep the other packs before inventing a new one.

### Step 3 — Verify and submit

For every source with an `api` block, include one working sample request and
its (truncated) response in the PR description. For sources without an API,
confirm the URL resolves and state where on the site the data lives. A pack
needs at least three sources to be accepted: the national statistics office,
the central bank, and one more.

## Pull request process

1. Fork, branch from `main` (`skill/...`, `pack/...`, `fix/...`, `feat/...`).
2. Make the change; keep PRs to one logical unit. Run `ruff` and `pytest`
   locally.
3. Open the PR with a description of what changed and why. For skills and
   source packs, include the self-test evidence described above.
4. A maintainer responds within 48 hours — either a review, a question, or a
   timeline. Two approvals required for changes to the engine core; one for
   skills, source packs, and docs.
5. Squash-merge is the default. Your commit lands with your authorship intact.

If a PR sits without maintainer response past 48 hours, ping it — that is on
us, not you.

## Reporting bugs and proposing features

Use the issue templates. For engine bugs, include the depth tier, provider,
and the engagement ID (the directory name under `engagements/`) — never paste
API keys or full reports containing material you cannot share.

## License

By contributing you agree your contributions are licensed under the MIT
License that covers the project.
