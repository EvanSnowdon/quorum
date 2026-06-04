# Quorum Analyst Skills

**Fifteen named strategy and analysis methodologies, packaged as portable,
auditable agent skills.**

Each skill is a single, plain-text `SKILL.md` that teaches an AI agent to apply a
well-known consulting framework with real rigor — the right questions, a
step-by-step method, a strict evidence standard, and a defined output. Install
them into Claude Code, Codex, Gemini CLI, or any skills-compatible agent and use
each one on its own, or let the [Quorum](../README.md) engagement engine staff
them together as a multi-agent consulting firm.

> **Standalone or orchestrated.** Every skill works by itself — point an agent at
> a `{region}` and `{industry}` and ask for the analysis. The same skills are
> also the staff of the Quorum firm, where an engagement manager decomposes a
> brief and dispatches them in parallel against an official-statistics data
> spine, then routes the drafts through fact-checking, red-team, and editorial
> review.

## Install

Install the whole library into any skills-compatible agent:

```bash
npx skills add EvanSnowdon/quorum
```

Or, inside **Claude Code**, add it as a plugin marketplace:

```
/plugin marketplace add EvanSnowdon/quorum
```

Then invoke any analyst directly — for example:

> "Run a five-forces analysis on the European battery-recycling market."

and the `five-forces-analyst` skill drives the structure, evidence rules, and
output format.

## The fifteen analysts

Each row is a directory under `analyst-skills/` containing a `SKILL.md` plus a
`reference/` folder with the detailed rubric and a full worked example
(progressive disclosure — the agent loads the body first, the reference on
demand).

| Skill | Methodology | Associated author(s) | Report section |
|---|---|---|---|
| [`five-forces-analyst`](five-forces-analyst/) | Five Forces — industry structure & profit pools | Michael E. Porter | Competitive Landscape |
| [`value-chain-analyst`](value-chain-analyst/) | Value Chain — where margin accrues | Michael E. Porter | Value Chain & Supply |
| [`jtbd-disruption-analyst`](jtbd-disruption-analyst/) | Jobs-to-be-Done & Disruptive Innovation | Clayton M. Christensen | Technology & Trends |
| [`seven-powers-analyst`](seven-powers-analyst/) | 7 Powers — durable advantage | Hamilton Helmer | Strategic Options |
| [`good-strategy-critic`](good-strategy-critic/) | Good Strategy / Bad Strategy — the kernel | Richard P. Rumelt | Red Team / Strategy |
| [`playing-to-win-analyst`](playing-to-win-analyst/) | Playing to Win — the strategy cascade | Roger L. Martin & A.G. Lafley | Strategy / Business Model |
| [`blue-ocean-analyst`](blue-ocean-analyst/) | Blue Ocean — value innovation & the ERRC grid | W. Chan Kim & Renée Mauborgne | Market Segmentation |
| [`crossing-the-chasm-analyst`](crossing-the-chasm-analyst/) | Crossing the Chasm — technology adoption lifecycle | Geoffrey A. Moore | GTM / Local Insights |
| [`pestel-analyst`](pestel-analyst/) | PESTEL — macro-environment scan | General practice | Macro Environment |
| [`tam-sam-som-analyst`](tam-sam-som-analyst/) | TAM / SAM / SOM — market sizing | General practice | Market Size & Growth |
| [`ansoff-analyst`](ansoff-analyst/) | Ansoff Growth Matrix — growth vectors | H. Igor Ansoff | Growth Strategy |
| [`three-horizons-analyst`](three-horizons-analyst/) | Three Horizons of Growth | Baghai, Coley & White (McKinsey) | Technology & Trends |
| [`pyramid-editor`](pyramid-editor/) | Minto Pyramid Principle — executive structuring | Barbara Minto | Editor / Report Structure |
| [`valuation-analyst`](valuation-analyst/) | DCF & comparable-companies valuation | General practice (e.g., Damodaran) | Financial & Investment |
| [`mece-engagement-manager`](mece-engagement-manager/) | MECE issue-tree decomposition & scoping | General practice | Engagement Manager / Orchestration |

## How a skill is built

Every skill follows the same shape, so they compose cleanly:

```
analyst-skills/
└── <name>/
    ├── SKILL.md            # frontmatter + concise, operational body
    └── reference/
        └── <framework>.md  # detailed rubric/scoring + full worked example
```

- **Frontmatter** — `name`, a trigger-optimized `description` ("Use when…"),
  `license: MIT`, and the methodology / canonical source.
- **`## When to use`** — given a `{region}` and `{industry}`, which report
  section this analyst produces, and when to reach for a sibling skill instead.
- **`## Method`** — the framework's steps, made specific and executable.
- **`## Output rules`** — one shared evidence standard: every finding is tagged
  `[DATA]` (sourced) or `[INFERENCE]` (reasoned) with a 0–1 confidence value,
  e.g. `[DATA] Top-4 firms hold 62% share (source: NBSC 2024) [0.88]`; official
  / first-party data is preferred; sources use the region's local language.
- **`## Reference`** — a pointer to the on-demand rubric and worked example.

## Contributing a new skill

New methodology skills are the highest-leverage contribution and need no code.

1. **Pick a published, citable framework** with a distinct point of view (a book,
   a canonical article, or equivalent public source). Open an issue first so we
   can confirm it doesn't overlap with the existing fifteen and agree on a
   directory name.
2. **Create the directory** — lowercase, hyphen-separated, ending in a role noun
   (`-analyst`, `-critic`, `-editor`, `-manager`), with a `SKILL.md` and a
   `reference/`.
3. **Match the format above** — trigger-optimized frontmatter, the four body
   sections, the shared `[DATA]`/`[INFERENCE]` evidence rule, and a condensed
   worked mini-example at the end of the body.
4. **Write the reference** — the detailed scoring rubric and one full worked
   example (deeper than the body's mini-example).
5. **Self-test** against at least two real industries and include the transcripts
   in your pull request, then submit.

See the repository's [CONTRIBUTING](../CONTRIBUTING.md) guide for the full
process and code standards.

## Compliance

These skills encode the **publicly known form of each framework** — the method,
not the prose, exhibits, or datasets of any book, article, or course. They are
**not affiliated with or endorsed by** any author, institution, or publisher;
named references are nominative only. They do **not** impersonate any individual.
Trademarks belong to their respective owners. Output is decision-support, not
professional advice. Full terms — including the takedown commitment — are in
[`DISCLAIMER.md`](DISCLAIMER.md).

## License

MIT. See the repository [LICENSE](../LICENSE).
