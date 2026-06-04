# TAM / SAM / SOM — Reference

## Layer definitions

| Layer | Definition | Bound by |
|---|---|---|
| **TAM** (Total Addressable Market) | Total revenue if every potential buyer in scope bought | Category + region |
| **SAM** (Serviceable Available Market) | The slice of TAM the company can serve | Business model, channel, geography, segment |
| **SOM** (Serviceable Obtainable Market) | The slice of SAM realistically winnable in a period | Competition, capacity, ramp |

TAM ⊇ SAM ⊇ SOM, always. State the reference year and currency for all three.

## Top-down worksheet

Start broad, apply filters, cite each:
1. Anchor: a published aggregate (e.g., population, number of target firms, total category spend in {region}).
2. Filter 1: share that fits the category (e.g., % of households with the relevant need).
3. Filter 2: share reachable by the model/channel.
4. Result: top-down TAM (→ then SAM with serviceability filters).

Each filter is a multiplier with a source. Document them in a table so the chain is auditable.

## Bottom-up worksheet

Build from unit economics:
- Potential buyers (N) × adoption/penetration × units per buyer per year × price = annual market value.
- Use the smallest primitive you can source reliably (per-store, per-user, per-firm), then scale.

Bottom-up is usually more credible for new or niche categories; top-down for mature ones with good aggregate stats.

## Reconciliation protocol

1. Put top-down TAM and bottom-up TAM side by side.
2. If within ~20–30%, treat as corroborated; report the range.
3. If they diverge widely, diagnose: different category boundary? double counting? stale or wrong price? one-off vs recurring? Fix the error; do not average two numbers you don't understand.
4. Report the reconciled figure with the residual uncertainty stated.

## Common errors

- **The "1% of a huge market" fallacy** — deriving SOM as an arbitrary small share of TAM. SOM must come from competitive and capacity reality.
- **Boundary drift** — TAM defined more broadly than SAM/SOM in a way that inflates the headline.
- **Double counting** — summing channels or segments that overlap.
- **Mixing one-time and recurring revenue** without saying which.
- **Currency/year ambiguity** — always label both; deflate or convert consistently.

## Worked example (≈170 words)

**Market:** Subscription dog-grooming-at-home service, {region}, base year stated.

- **Top-down** `[DATA] 0.7`: households in {region} = H `[DATA]`; dog-owning households ≈ 28% `[DATA]` → owning HH; urban (serviceable) ≈ 55% `[INFERENCE]`; willing-to-pay-premium ≈ 20% `[INFERENCE]`. Multiply by annual spend/HH (≈ price × visits) → **SAM**.
- **Bottom-up** `[INFERENCE] 0.6`: serviceable dog-owning urban HH × adoption × (visits/yr) × price-per-visit → annual value.
- **TAM** `[DATA] 0.6`: all dog-owning HH × grooming spend, regardless of channel/urbanity.
- **Reconciliation** `[INFERENCE] 0.6`: bottom-up SAM came in ~25% below top-down; gap traced to an overstated urban premium-willingness filter — adjusted down, figures now within range.
- **SOM** `[INFERENCE] 0.5`: SAM × realistic 3-yr share given two incumbents and van-fleet capacity — single-digit %, not a round "1% of TAM".

**Key swing assumption:** premium willingness-to-pay share. Reported as a low/base/high range, base case stated with currency and year.
