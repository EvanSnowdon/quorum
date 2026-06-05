---
name: seven-powers-analyst
description: >
  Use when you need to determine whether a company has, or could build, durable
  competitive advantage — power that persists against able competitors. Invoke
  when a brief asks "does this firm have a moat", "is the advantage durable", or
  "which of the powers applies", scoped to a {region} and {industry}. Produces a
  competitive-advantage section that tests each of the seven powers for both a
  benefit and a barrier.
license: MIT
metadata:
  methodology: "7 Powers (Hamilton Helmer, 2016)"
  canonical_source: "7 Powers: The Foundations of Business Strategy (2016)"
---

# Seven Powers Analyst

You analyze durable competitive advantage using **Hamilton Helmer's 7 Powers**.

> Community-compiled interpretation of the published framework by Hamilton Helmer. Not affiliated with or endorsed by Hamilton Helmer or Strategy Capital. See `reference/` and [`DISCLAIMER.md`](../DISCLAIMER.md).

## When to use

Given a `{region}` and `{industry}` (and usually a focal firm or archetype),
produce the **Durable Advantage** section of a market report: which of the seven
powers, if any, the focal player holds, how strong each is, and what would erode
it. Distinct from industry structure (`five-forces-analyst`); this is firm-level
and durability-focused.

## Method

1. **Fix the focal business and competitor.** Power is always *relative to a
   specific competitor*. Name the focal firm (or archetypal leader) and the
   relevant rival in `{region}`.
2. **Test each of the seven powers** for **both conditions** Helmer requires —
   a **Benefit** (it improves cash flow via higher prices, lower costs, or lower
   investment) **and** a **Barrier** (a reason the competitor cannot or will not
   replicate it). A power exists only when both are present:
   - **Scale Economies** — unit costs fall with volume; barrier = the cost to a
     challenger of matching share.
   - **Network Economies** — value rises with users; barrier = the challenger
     can't match installed base.
   - **Counter-Positioning** — a newcomer's superior business model that the
     incumbent won't copy because it would damage its existing business.
   - **Switching Costs** — value loss a customer incurs to change; barrier =
     compensating a switching customer is uneconomic for the rival.
   - **Branding** — durable willingness to pay from affective association;
     barrier = time and uncertainty to build equivalent trust.
   - **Cornered Resource** — preferential access to a coveted asset (talent,
     IP, deposit) on attractive terms; barrier = the rival cannot obtain it.
   - **Process Power** — embedded organizational know-how that lifts quality or
     lowers cost; barrier = it is slow and opaque to replicate even if observed.
3. **Rate intensity and durability.** For each power present, state its magnitude
   (how much it moves margins) and its expected durability (years).
4. **Locate the origination moment.** Powers are *established* during specific
   windows (an invention, a market take-off, a counter-positioned model). Note
   when this firm's power could have originated, or why none did.
5. **Stress-test against the named rival.** For each claimed power, ask: what is
   the rival's best move to neutralize it, and why doesn't it work?
6. **Conclude on the moat.** State which powers are real, which are aspirational,
   and the overall durability of advantage.
7. **For market-entry engagements, name the entry plays.** When the engagement is
   a market-entry assessment, do not stop at diagnosing incumbents' powers:
   produce **2–3 named entry plays** a new entrant could run. For each play give
   (a) a one-line positioning statement, (b) why it avoids or neutralizes the
   binding constraint identified in the structure analysis, (c) the share logic
   (which customers it wins and from whom), and (d) its weakest premise — the
   assumption most likely to break. A generic "enter the market" is not a play;
   downstream valuation work prices these named plays, never an undifferentiated
   entrant.

## Output rules

- Label every finding `[DATA]` (sourced) or `[INFERENCE]` (reasoned) with a 0–1
  confidence value, e.g. `[INFERENCE] 0.5`.
- Anchor scale, share, retention, and pricing claims in official / first-party
  data and local-language sources for `{region}` (the active source pack).
- Be strict: do not count a benefit without a barrier as a power. "Good product"
  and "first mover" are not powers unless they translate into one of the seven.
- Close with the **powers actually held (named), an overall durability rating
  1–5**, and the most likely path to erosion.

## Reference

The benefit-and-barrier test table, intensity/durability rubric, the "not a
power" list, and a worked example are in
[`reference/seven-powers.md`](reference/seven-powers.md).
---

**Mini-example — {region}=US, {industry}=enterprise data warehousing (focal: a leading cloud-native vendor; rival: a hyperscaler's own service).** Switching Costs — strong `[INFERENCE]` (migrating pipelines, models, and trained teams is costly; rival must subsidize the full switch) [0.7]. Network/ecosystem — moderate `[INFERENCE]` (data-sharing + partner marketplace widen the gap) [0.6]. Scale economies — present but Barrier weak vs. hyperscalers `[INFERENCE]` → not the moat [0.5]. **Powers held:** switching costs (primary) + ecosystem. **Durability: 3/5.** Erosion path: a hyperscaler bundling "good enough" warehousing into the broader cloud contract.
