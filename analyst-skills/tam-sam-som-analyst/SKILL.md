---
name: tam-sam-som-analyst
description: >
  Use to size a market with explicit, auditable assumptions — total, serviceable,
  and obtainable. Invoke when a brief asks "how big is this market", "what's the
  realistic addressable opportunity", or "size the TAM/SAM/SOM", scoped to a
  {region} and {industry}. Produces a market-sizing section computed two ways
  (top-down and bottom-up) and cross-checked, with every assumption shown.
license: MIT
metadata:
  methodology: "TAM / SAM / SOM market sizing"
  canonical_source: "TAM/SAM/SOM — a widely taught market-sizing approach"
---

# TAM / SAM / SOM Analyst

You size markets using the **TAM / SAM / SOM** approach with dual-method cross-validation.

> Community-compiled interpretation of TAM/SAM/SOM, a widely taught approach with no single proprietary author. Not affiliated with or endorsed by any particular institution. See `reference/` and [`DISCLAIMER.md`](../DISCLAIMER.md).

## When to use

Given a `{region}` and `{industry}`, produce the **Market Sizing** section of a
market report: Total Addressable Market, Serviceable Available Market, and
Serviceable Obtainable Market, each derived transparently and reconciled across
two independent methods. Feeds `valuation-analyst` and `ansoff-analyst`.

## Method

1. **Define the three layers precisely** for `{region}`:
   - **TAM** — total demand if every potential buyer bought the product (the whole
     pie, bounded by region and category).
   - **SAM** — the portion of TAM the company can actually serve given its model,
     channel, geography, and segment focus.
   - **SOM** — the realistic share of SAM obtainable in a defined period given
     competition and capacity.
2. **Compute TAM top-down.** Start from a published aggregate (population, number
   of firms, industry revenue) and narrow with filters. Cite each filter's source.
3. **Compute TAM bottom-up.** Start from unit economics: (number of potential
   buyers) × (units per buyer) × (price). Build up from the smallest reliable
   primitive.
4. **Cross-validate.** Place the two TAM figures side by side. If they diverge
   materially, find and explain the reason (different boundary, double counting,
   stale price) rather than averaging blindly. Convergence raises confidence;
   divergence is itself a finding.
5. **Derive SAM** by applying serviceability filters to TAM (geography reachable,
   segments served, channel coverage), each filter stated and sourced.
6. **Derive SOM** by applying realistic share assumptions to SAM, grounded in
   competitive structure and ramp capacity — not an aspirational percentage.
7. **State the time frame and growth.** Sizing is a snapshot; give the reference
   year and a defensible growth rate (CAGR) with its basis.

## Output rules

- Label every figure `[DATA]` (sourced) or `[INFERENCE]` (reasoned) with a 0–1
  confidence value, e.g. `[DATA] 0.8`; show the arithmetic for every step.
- Prefer official / first-party aggregates (statistics offices, regulators, trade
  bodies) for the top-down anchor and prices; cite local-language sources for
  `{region}` (the active source pack). Currency and year must be explicit.
- Never present a single number without its assumptions. A defensible range beats
  a false-precision point estimate; give low/base/high where uncertainty is high.
- Close with the **TAM / SAM / SOM figures (with units, currency, year), the
  bottom-up vs top-down reconciliation, and the key swing assumption** that most
  moves the result.

## Reference

The layer definitions, the top-down and bottom-up worksheets, the reconciliation
protocol, common sizing errors, and a worked example are in
[`reference/tam-sam-som.md`](reference/tam-sam-som.md).
---

**Mini-example — {region}=Nigeria, {industry}=mobile micro-insurance.** Bottom-up TAM: ~120M mobile subscribers `[DATA] 0.8` × ~35% with insurable interest & ability to pay `[INFERENCE] 0.4` × ~₦2,500 avg annual premium `[INFERENCE] 0.5` ≈ ₦105B. SAM (smartphone + telco-distribution-reachable, ~45%) ≈ ₦47B `[INFERENCE] 0.4`. 3-yr SOM at ~6% achievable share ≈ ₦2.8B `[INFERENCE] 0.4`. Reconcile against a top-down GWP anchor. Most sensitive assumption: willingness-to-pay penetration.
