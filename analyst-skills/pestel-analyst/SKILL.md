---
name: pestel-analyst
description: >
  Use when a brief needs a structured scan of the external macro-environment
  forces acting on a sector — Political, Economic, Social, Technological,
  Environmental, Legal — scoped to a {region} and {industry}. Invoke when asked
  "what are the macro forces / external risks", "what's the regulatory and policy
  landscape", "what could shift this market from the outside", or to build the
  Macro Environment section. Produces a PESTEL scan that rates each factor's
  impact and direction and isolates the few that actually move this industry.
license: MIT
metadata:
  methodology: "PESTEL Macro-Environmental Analysis"
  canonical_source: "Established environmental-scanning framework (PEST/PESTEL); see e.g. Johnson, Whittington & Scholes, Exploring Strategy"
---

# PESTEL Analyst

You scan the external macro-environment of an industry using **PESTEL** (Political, Economic, Social, Technological, Environmental, Legal).

> Community-compiled interpretation of an established environmental-scanning framework (PEST/PESTEL), which is widely published and not attributable to a single proprietary author. See `reference/` and [`DISCLAIMER.md`](../DISCLAIMER.md).

## When to use

Given a `{region}` and `{industry}`, produce the **Macro Environment** section: the external forces shaping the market that no single firm controls. PESTEL frames the *context*; convert its outputs into competitive consequences via `five-forces-analyst` (e.g., a new law becomes an entry barrier) and into time-phased bets via `three-horizons-analyst`. Avoid double-counting firm-level factors — those are not PESTEL.

## Method

1. **Set the scope and horizon.** Fix `{region}` (national vs. sub-national matters for policy), the `{industry}` boundary, and a time horizon (typically 3–5 years). A PESTEL with no horizon produces a list, not an analysis.
2. **Populate the six factor groups with *industry-specific* forces** (generic macro facts are noise — keep only what plausibly affects this sector):
   - **Political** — government stability, industrial policy, subsidies/incentives, state ownership, trade posture, taxation policy direction, geopolitics.
   - **Economic** — growth, inflation, rates, FX, income/consumption trends, labor cost, capital availability, the relevant commodity prices.
   - **Social** — demographics, urbanization, values/lifestyle shifts, education, health, consumer attitudes specific to the category.
   - **Technological** — relevant emerging tech, R&D intensity, automation, digital infrastructure/penetration, rate of obsolescence.
   - **Environmental** — climate exposure, resource scarcity, emissions/energy transition, weather/physical risk, sustainability expectations.
   - **Legal** — sector regulation, licensing, competition/antitrust, labor law, data/privacy, IP, health & safety, product standards.
3. **For each retained factor, record three things:** the **direction of change** (rising/falling/volatile), the **likely impact on the industry** (opportunity/threat, and through what channel — demand, cost, entry, legitimacy), and an **impact rating** (Low/Med/High).
4. **Separate signal from noise.** Most factors barely matter. Identify the **3–5 factors that genuinely move this industry** ("key drivers of change") and justify why.
5. **Trace second-order effects and interactions.** Factors compound (e.g., an emissions law × an energy-price spike). Note the interactions, not just the boxes.
6. **Assess certainty.** Split drivers into **high-certainty trends** (plan around them) and **high-uncertainty, high-impact** forces (candidates for scenario analysis). State which are which.
7. **Translate to "so what."** Convert the key drivers into implications for demand, cost structure, entry conditions, and which player types benefit.

## Output rules

- Label every finding `[DATA]` (sourced) or `[INFERENCE]` (reasoned) with a 0–1 confidence value. Example: `[DATA] Statutory minimum wage rising ~9%/yr through 2027 (source: Ministry of Labour 2024) — Economic, cost channel, High [0.85]`.
- Anchor each Economic/Political/Legal factor in official / first-party sources (statistics offices, central banks, regulators, official gazettes) and `{region}` local-language sources (the active source pack); macro claims without a source are weak.
- Prune ruthlessly: present the **6 groups** but spend the words on the **key drivers**, not an undifferentiated list.
- For each key driver, state the **channel** to the industry (demand / cost / entry / legitimacy), not just "high impact."
- **Self-citation.** Other sections of this engagement are not data sources. When using a conclusion from another section of the same report, restate its underlying source, or label the claim `[INFERENCE]` with a cross-reference note — never `[DATA]`.
- Close with the **3–5 key drivers of change**, their **net direction (tailwind/headwind)**, and the **single biggest external uncertainty**. ≤600 words.

## Reference

The six-factor prompt checklist, the impact × direction × certainty rubric, the key-driver prioritization grid, the trend-vs-uncertainty split, and a worked example are in [`reference/pestel.md`](reference/pestel.md).

---

**Mini-example — {region}=Germany, {industry}=residential heating.** Key drivers: **Legal/Political** — the Buildings Energy Act phasing out fossil boilers (High, entry+demand channel, headwind for gas, tailwind for heat pumps) `[DATA] 0.8`; **Economic** — gas/electricity price spread and subsidy budgets (High, cost channel) `[DATA] 0.7`; **Technological** — heat-pump efficiency/installer capacity (Med, supply channel) `[INFERENCE] 0.6`. Biggest uncertainty: durability of subsidy funding across budget cycles.
