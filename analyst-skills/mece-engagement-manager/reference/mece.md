# MECE Engagement Structuring — Reference

## Question-sharpening test

A well-formed key question is **specific, answerable, and decision-linked**. Before decomposing, confirm:
- **Single question, not many** — one governing question (sub-questions live in the tree).
- **Bounded** — `{region}`, `{industry}`, segment, time horizon, and effort budget stated.
- **Decision-linked** — name the decision the answer informs (enter / invest / reposition / exit).
- **Answerable with evidence** — not a matter of pure opinion.

Bad: "Tell us about the {industry} market." Good: "Should we enter the {region} {industry} market in the next 18 months, and if so, with what go-to-market?"

## MECE rules

A set of branches is **MECE** when:
- **Mutually Exclusive** — branches do not overlap; a given issue/fact belongs to exactly one.
- **Collectively Exhaustive** — together they cover the whole question; nothing material is left out.

**Common MECE violations**
| Violation | Symptom | Fix |
|---|---|---|
| Overlap | The same issue analyzed under two branches | Re-cut so each fact has one home |
| Gap | A material driver has no branch | Add the missing branch (or a "other, specified" branch) |
| Mixed logic at one level | Children mix, e.g., geographies *and* customer types | Pick one cut per level; nest the other below |
| False parallelism | A grab-bag list with no organizing principle | State the decomposition logic, then re-cut |
| Too many branches | 7+ children — usually overlapping or trivial | Group into 2–4 parents |

## The four standard decomposition logics (pick one per question; can nest)

1. **Deductive / argument tree** — the question becomes a logical chain. Classic market-entry: *Is it attractive? → Can we win? → Is it worth it (returns)?* Each is then decomposed.
2. **Component (structural) tree** — break the system into parts: value-chain stages, P&L lines, customer journey steps. Good for "where is the problem/value?".
3. **Stakeholder tree** — by actor: customers, competitors, suppliers, regulators, channel. Good for ecosystem questions.
4. **Lever / driver tree** — by what moves the metric: e.g., Revenue = volume × price; volume = reach × conversion × frequency. Good for quantified "how do we grow X?".

State the logic explicitly — readers (and MECE) depend on it.

## Standard market-entry / attractiveness tree (template)

```
KEY QUESTION: Should we enter {region} {industry}, and how should we win?
├─ 1. Is the market attractive?
│   ├─ Macro context & external forces ............ pestel-analyst → Macro Environment
│   ├─ Industry structure & profit pool ........... five-forces-analyst → Competitive Landscape
│   ├─ Market size & growth ....................... tam-sam-som-analyst → Market Size & Growth
│   └─ Demand, jobs & disruption risk ............. jtbd-disruption-analyst → Technology & Trends
├─ 2. Where does value sit and who can win it?
│   ├─ Where margin accrues along the chain ....... value-chain-analyst → Value Chain & Supply
│   ├─ Durable advantage / moats ................. seven-powers-analyst → Strategic Options
│   ├─ Uncontested space / segmentation .......... blue-ocean-analyst → Market Segmentation
│   └─ Market evolution over time ................ three-horizons-analyst → Technology & Trends
└─ 3. How would WE win, and is it worth it?
    ├─ Strategy (the five choices) ............... playing-to-win-analyst → Strategy / Business Model
    ├─ Growth vectors ........................... ansoff-analyst → Growth Strategy
    ├─ Go-to-market / adoption .................. crossing-the-chasm-analyst → GTM / Local Insights
    ├─ Financial value / returns ............... valuation-analyst → Financial & Investment
    └─ Adversarial review of the above ......... good-strategy-critic → Red Team / Strategy
[ASSEMBLY] pyramid-editor → Report Structure / Executive Summary
```
Adapt branches to the brief — drop, add, or re-weight — but keep each level MECE.

## Analyst-to-section coverage map (full library)

| Branch theme | Analyst | Report section |
|---|---|---|
| Macro forces | pestel-analyst | Macro Environment |
| Industry structure | five-forces-analyst | Competitive Landscape |
| Margin location | value-chain-analyst | Value Chain & Supply |
| Demand & disruption | jtbd-disruption-analyst | Technology & Trends |
| Time-phased growth | three-horizons-analyst | Technology & Trends |
| Market sizing | tam-sam-som-analyst | Market Size & Growth |
| Uncontested space | blue-ocean-analyst | Market Segmentation |
| Go-to-market | crossing-the-chasm-analyst | GTM / Local Insights |
| Durable advantage | seven-powers-analyst | Strategic Options |
| Strategy build | playing-to-win-analyst | Strategy / Business Model |
| Growth vectors | ansoff-analyst | Growth Strategy |
| Valuation | valuation-analyst | Financial & Investment |
| Adversarial review | good-strategy-critic | Red Team / Strategy |
| Structuring & edit | pyramid-editor | Editor / Report Structure |

After mapping, scan for **coverage gaps** (a branch with no analyst) and **redundancies** (a branch claimed by two — resolve by giving the lead analyst the branch and the other a defined sub-angle).

## Impact × uncertainty prioritization grid

|  | Low uncertainty | High uncertainty |
|---|---|---|
| **High impact** | Verify quickly (it's pivotal but fairly settled) | **Deepest work** — the crux of the engagement |
| **Low impact** | Note briefly | Light scan; flag as a watch item |

Depth tiers map onto this: a `scan` covers mainly the high-impact row at low depth; `due_diligence` adds breadth and pushes the high-impact/high-uncertainty cell hard.

## Dependency sequencing (typical)

- `pestel` and `tam-sam-som` and `five-forces` → run early; they feed almost everything.
- `value-chain`, `jtbd-disruption`, `seven-powers` → mid; consume structure/sizing.
- `playing-to-win`, `ansoff`, `crossing-the-chasm`, `valuation` → late; consume the above.
- `good-strategy-critic` → after a strategy exists, to attack it.
- `pyramid-editor` → last, to assemble.
Run branches with no dependency on each other in parallel.

## Worked engagement plan (≈190 words)

**Brief:** "A regional bank wants to know whether to launch an SME-lending business in {region}."

**Key question** `[INFERENCE] 0.8`: "Is SME lending in {region} attractive and winnable for this bank in 24 months, and at what return?" Decision: launch / don't. Logic: deductive (attractive? → can we win? → worth it?).

**Top-level MECE branches** (no overlap; jointly cover the decision):
1. **Attractive?** — macro & rate environment (`pestel`), lender competitive structure (`five-forces`), SME credit demand & non-consumption (`jtbd-disruption`), market size & growth (`tam-sam-som`).
2. **Winnable?** — where margin sits in SME lending (`value-chain`), the bank's potential moats — cost of funds, data, switching costs (`seven-powers`), underserved segments (`blue-ocean`).
3. **Worth it / how?** — the strategy (`playing-to-win`), launch GTM & adoption (`crossing-the-chasm`), and the P&L/returns (`valuation`), then red-teamed (`good-strategy-critic`).

**Priority:** Branch 1 sizing × structure and Branch 2 cost-of-funds advantage are high-impact/high-uncertainty → deepest work. Macro is high-impact/low-uncertainty → verify fast.

**Sequence:** Branch 1 first (parallel within it) → Branch 2 → Branch 3 → critic → `pyramid-editor` assembles.

**Coverage check:** all branches owned; no double-owned branch. Gap flagged: regulatory capital treatment — assign to `pestel`/`valuation` jointly.
