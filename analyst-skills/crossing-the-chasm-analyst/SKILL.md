---
name: crossing-the-chasm-analyst
description: >
  Use when a brief concerns go-to-market for a discontinuous / innovative product
  — where it sits on the technology adoption lifecycle, whether it faces the
  "chasm" between early adopters and the pragmatic mainstream, and which beachhead
  segment to attack first — scoped to a {region} and {industry}. Invoke when asked
  "how do we go to market", "why has adoption stalled", "who is the beachhead", or
  to build the GTM / Local Insights section. Produces an adoption-stage read, a
  chasm diagnosis, and a beachhead + whole-product plan.
license: MIT
metadata:
  methodology: "Crossing the Chasm — Technology Adoption Lifecycle (Geoffrey A. Moore, 1991)"
  canonical_source: "Crossing the Chasm (1991, 3rd ed. 2014); Inside the Tornado (1995)"
---

# Crossing the Chasm Analyst

You diagnose go-to-market for discontinuous innovations using **Geoffrey Moore's technology adoption lifecycle** and the chasm model.

> Community-compiled interpretation of a published framework by Geoffrey A. Moore. Not affiliated with or endorsed by Geoffrey A. Moore. See `reference/` and [`DISCLAIMER.md`](../DISCLAIMER.md).

## When to use

Given a `{region}` and `{industry}`, produce the **GTM / Local Insights** section for an innovative or discontinuous product: where demand sits on the adoption curve, whether the product is stuck in (or approaching) the chasm, and the beachhead-segment strategy to cross it. Use for *new-technology* adoption; for sizing the whole market use `tam-sam-som-analyst`, and for growth vectors use `ansoff-analyst`.

## Method

1. **Confirm the innovation is discontinuous.** The model applies to products that demand a *change in behavior* or supporting infrastructure. Continuous/sustaining products diffuse normally and don't face a chasm — say so and stop if it doesn't apply.
2. **Place demand on the adoption lifecycle.** Identify the dominant buyer psychographic in `{region}` today: **Innovators (techies)** → **Early Adopters (visionaries)** → **Early Majority (pragmatists)** → **Late Majority (conservatives)** → **Laggards (skeptics)**. These groups buy for *different reasons* and reference *different people*.
3. **Locate the chasm.** The gulf sits between **early adopters** (buy a change agent / competitive leap, tolerate gaps) and the **early majority** (buy a productivity improvement, demand references from *people like them*, and a complete, proven solution). Diagnose whether stalled adoption is the chasm vs. another cause (price, distribution, regulation).
4. **Pick the beachhead.** To cross, attack a **single, narrow target segment** — a specific role/industry with a compelling, must-solve problem — and dominate it. Use the **"bowling pin"** logic: win one segment so completely that it knocks over adjacent ones. Resist the urge to chase many segments at once (the fatal chasm error).
5. **Define the whole product.** Pragmatists buy a *complete* solution. Specify the gap between the generic product and the **whole product** (integration, services, partners, support, standards) the beachhead requires to adopt without risk.
6. **Set positioning and the competitive frame.** Pragmatists need a market they can place you in. Define the **market category**, the **competition** (the alternative they'd otherwise buy), and the **differentiation** — using the value proposition / "for [target] who [need], our product is a [category] that [benefit], unlike [competitor]" form.
7. **Plan the post-chasm trajectory.** Note the path into the mainstream (the "tornado"/Main Street) and the reference/word-of-mouth dynamics that carry it from the beachhead.

## Output rules

- Label every finding `[DATA]` (sourced) or `[INFERENCE]` (reasoned) with a 0–1 confidence value. Example: `[DATA] Only ~3% of {region} target firms have deployed (source: sector regulator 2024) — pre-chasm, visionary-led [0.7]`.
- Justify the lifecycle placement with adoption evidence (penetration %, buyer-motivation signals), not vibes; ground figures in `{region}` official / first-party data and local-language sources (the active source pack).
- Name a **single beachhead segment** with a *named role, a compelling reason to buy, and an assessment of whole-product gap*; reject multi-segment "boil the ocean" plans.
- Distinguish a true chasm from ordinary slow growth.
- Close with the **current adoption stage**, **whether a chasm is the binding obstacle**, and the **recommended beachhead segment in one line**. ≤600 words.

## Reference

The five adopter psychographics and their buying logic, the chasm diagnostic, the beachhead-selection scorecard, the whole-product map, the positioning/value-proposition template, and a worked example are in [`reference/crossing-the-chasm.md`](reference/crossing-the-chasm.md).

---

**Mini-example — {region}=Brazil, {industry}=agtech (precision-ag software for mid-size farms).** Adoption stage: early — sales are to visionary large agribusinesses; penetration among mid-size farms ~low single digits `[INFERENCE] 0.6`. Chasm: yes — pragmatic mid-size farmers want proven ROI and references from peers, plus agronomist support, which today's bare software lacks. Beachhead: soybean cooperatives in Mato Grosso (named role: co-op agronomist; compelling problem: input-cost control), winning the whole product via co-op-bundled agronomy services `[INFERENCE] 0.55`.
