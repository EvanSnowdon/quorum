---
name: five-forces-analyst
description: >
  Use when you need to assess the structural attractiveness and profit potential
  of an industry — not a single company. Invoke this skill when a brief asks
  "how attractive is the X market", "what determines profitability in this
  sector", or "who captures the margin", scoped to a given {region} and
  {industry}. Produces an industry-structure section that rates each of Porter's
  five competitive forces and names the binding constraint on profit.
license: MIT
metadata:
  methodology: "Porter's Five Forces (Michael E. Porter, 1979 / 2008)"
  canonical_source: "Competitive Strategy (1980); 'The Five Competitive Forces That Shape Strategy', HBR (2008)"
---

# Five Forces Analyst

You analyze the structural profitability of an industry using **Porter's Five Forces**.

> Community-compiled interpretation of the published framework by Michael E. Porter. Not affiliated with or endorsed by Michael E. Porter or Harvard Business School. See `reference/` and [`DISCLAIMER.md`](../DISCLAIMER.md).

## When to use

Given a `{region}` and `{industry}`, produce the **Industry Structure & Profit Pool**
section of a market report. Use this when the question is about the *industry's*
attractiveness, where economic profit pools sit, and what would have to change for
them to shift — distinct from a single firm's advantage (use `seven-powers-analyst`)
or a macro scan (use `pestel-analyst`).

## Method

1. **Define the industry boundary first.** State the relevant product/service,
   the geographic scope (`{region}`), and the buyer and supplier groups. Most
   misuse comes from drawing the boundary too wide or too narrow; record the
   choice explicitly.
2. **Rate each force Low / Medium / High** for its strength as a *threat to
   incumbent profitability*, with the underlying drivers cited:
   - **Threat of new entrants** — economies of scale, capital intensity, switching
     costs, access to distribution, regulation, expected retaliation.
   - **Bargaining power of suppliers** — concentration, substitute inputs, forward-
     integration threat, importance of the industry as a customer.
   - **Bargaining power of buyers** — concentration, price sensitivity, switching
     costs, backward-integration threat, product differentiation.
   - **Threat of substitutes** — relative price-performance of alternatives outside
     the industry, buyer propensity to switch.
   - **Rivalry among existing competitors** — industry growth, fixed-cost structure,
     exit barriers, concentration, differentiation.
3. **Identify the binding constraint.** Name the one or two forces that most
   depress industry profit. Not all forces matter equally; say which dominate.
4. **Map the profit pool.** Where in the chain does economic profit actually
   accrue today, and which force explains that distribution?
5. **Assess trajectory.** For each force, is it strengthening or weakening over a
   3–5 year horizon, and what driver moves it? Structure is not static.
6. **Translate to attractiveness.** Convert the force ratings into an overall
   read on whether this industry can sustain above-cost-of-capital returns, and
   for whom.

## Output rules

- Label every finding `[DATA]` (with a source) or `[INFERENCE]` (reasoned),
  followed by a 0–1 confidence value, e.g. `[DATA] 0.8` or `[INFERENCE] 0.5`.
  Derived-claim confidence is the minimum of its inputs (weakest-link rule),
  written as min(0.7, 0.6) = 0.6; never write it as a product and never
  multiply confidence labels as if they were probabilities.
- Prefer official / first-party figures for concentration ratios, margins, and
  capital intensity (the data spine). When citing, use the local-language source
  appropriate to `{region}` (the active source pack). Structural figures such
  as concentration ratios (CR-n, HHI) must state their year vintage at every
  citation; when the same figure is cited more than once, use the same year
  and the same source each time — never mix vintages of the same ratio.
- Distinguish industry-level structure from firm-level position; do not let one
  dominant incumbent's results stand in for the industry.
- **Competing-set discipline.** When an adjacent powertrain or technology form
  competes in the target price band (PHEV/EREV against BEV, or the reverse)
  with overlapping prices, it belongs in the substitutes and rivalry
  assessment — a scope choice such as a BEV-only TAM never excludes it from
  the competitive-intensity read. The market-definition denominator and the
  competing set are separate scopes: size on the locked definition, rate the
  forces on everything the buyer actually cross-shops.
- **Self-citation.** Other sections of this engagement are not data sources.
  When using a conclusion from another section of the same report, restate its
  underlying source, or label the claim `[INFERENCE]` with a cross-reference
  note — never `[DATA]`.
- Close with an **overall attractiveness rating on a 1–5 scale** (1 = brutal,
  5 = highly attractive) and a one-sentence statement of the binding constraint.

## Reference

Force-by-force driver checklists, the Low/Med/High rating rubric, common
boundary-definition errors, and a worked example are in
[`reference/five-forces.md`](reference/five-forces.md).
---

**Mini-example — {region}=China, {industry}=express parcel delivery.** Rivalry — **High** `[DATA] Top-5 carriers ~75% share yet sustained price war; volumes rising but unit price falling for 3 yrs (source: State Post Bureau 2024) [0.8]`. Buyer power — **High** `[INFERENCE]` (e-commerce platforms route huge volumes and dictate price) [0.7]. Binding constraint: rivalry × platform buyer power. **Overall attractiveness: 2/5** — scale leaders survive on cost; structural margin is thin.
