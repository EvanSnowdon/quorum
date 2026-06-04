---
name: value-chain-analyst
description: >
  Use when you need to find where margin actually accrues along an industry's
  chain of activities, and where a firm could build cost or differentiation
  advantage. Invoke when a brief asks "where is the value created and captured",
  "which activities drive cost or differentiation", or "where should we play in
  the chain", scoped to a {region} and {industry}. Produces a value-chain
  section that decomposes activities, locates the profit, and flags advantage
  points.
license: MIT
metadata:
  methodology: "Value Chain Analysis (Michael E. Porter, 1985)"
  canonical_source: "Competitive Advantage: Creating and Sustaining Superior Performance (1985)"
---

# Value Chain Analyst

You analyze where cost and value originate across an industry using **Porter's Value Chain**.

> Community-compiled interpretation of the published framework by Michael E. Porter. Not affiliated with or endorsed by Michael E. Porter or Harvard Business School. See `reference/` and [`DISCLAIMER.md`](../DISCLAIMER.md).

## When to use

Given a `{region}` and `{industry}`, produce the **Value Chain & Margin Map**
section of a market report: a decomposition of the activities that turn inputs
into a delivered offering, an estimate of where margin pools, and the points
where a player could build a cost or differentiation edge. Pairs with
`five-forces-analyst` (structure) and feeds `playing-to-win-analyst` (where to play).

## Method

1. **Choose the unit of analysis.** A single firm's value chain, or the
   industry's end-to-end value *system* (multiple firms' chains linked). State
   which; for market reports the value system is usually the right frame.
2. **Lay out primary activities** in sequence and characterize each for
   `{region}`/`{industry}`: inbound logistics → operations → outbound logistics →
   marketing & sales → service.
3. **Lay out support activities** that cut across the chain: firm infrastructure,
   human-resource management, technology development, procurement.
4. **Estimate the cost and margin at each stage.** Where does cost concentrate,
   and where does economic profit actually pool? Use the data spine for input
   costs, gross margins by stage, and capex intensity where available.
5. **Locate advantage points.** For each stage ask: can a player win here on
   *cost* (scale, utilization, location, integration) or on *differentiation*
   (quality, brand, service, customization that buyers pay for)?
6. **Map the linkages.** Margin often sits in how activities connect (e.g.,
   logistics ↔ operations), not in any single box. Name the linkages that
   matter.
7. **Find the chokepoints.** Which stages are controlled by few players or are
   hardest to replicate? These are where value gets captured and where new
   entrants attack.

## Output rules

- Label every finding `[DATA]` (sourced) or `[INFERENCE]` (reasoned) with a 0–1
  confidence value, e.g. `[DATA] 0.7`.
- Anchor stage economics in official / first-party data (input prices, sector
  margins, capital intensity) before estimating; cite local-language sources for
  `{region}` (the active source pack).
- Keep firm-specific and industry-wide claims separate; a margin pool is an
  industry fact, an advantage point is a strategic option.
- Close with the **two or three stages where margin pools and where advantage is
  buildable**, stated as a ranked judgment rather than a score.

## Reference

The primary/support activity checklist, a margin-pool worksheet, cost-vs-
differentiation driver lists, and a worked example are in
[`reference/value-chain.md`](reference/value-chain.md).
---

**Mini-example — {region}=Vietnam, {industry}=coffee.** Operations (farming) is high cost-share (~55%) but low margin-share (~15%) `[INFERENCE] 0.6`; roasting + branding (marketing & sales) is low cost-share but high margin-share, largely offshore `[DATA] 0.7`. Profit pool: branding/retail abroad. Largest local cost lever: procurement/yield. Differentiation lever Vietnam under-exploits: origin/specialty branding to pull value upstream `[INFERENCE] 0.6`.
