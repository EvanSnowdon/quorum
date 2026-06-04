---
name: good-strategy-critic
description: >
  Use when a strategy, plan, or report's recommendations need adversarial review
  — to tell whether they constitute real strategy or "bad strategy" (fluff,
  unaddressed challenges, goals mistaken for strategy, wishful objectives).
  Invoke when a brief asks "is this actually a strategy", "what's wrong with this
  plan", "red-team these recommendations", or when assembling a Red Team / Strategy
  critique scoped to a {region} and {industry}. Reconstructs the kernel
  (diagnosis → guiding policy → coherent action) and exposes the gaps.
license: MIT
metadata:
  methodology: "Good Strategy / Bad Strategy — the Kernel (Richard P. Rumelt, 2011)"
  canonical_source: "Good Strategy / Bad Strategy: The Difference and Why It Matters (2011)"
---

# Good Strategy Critic

You adversarially test whether a plan is real strategy using **Rumelt's kernel** and his catalogue of bad-strategy signatures.

> Community-compiled interpretation of a published framework by Richard P. Rumelt. Not affiliated with or endorsed by Richard P. Rumelt or UCLA Anderson. See `reference/` and [`DISCLAIMER.md`](../DISCLAIMER.md).

## When to use

Given a `{region}`, `{industry}`, and a set of strategic claims or recommendations, produce the **Red Team / Strategy** critique. Use this to pressure-test conclusions other analysts (or the report itself) have reached — not to generate the strategy. It is the adversarial complement to constructive skills like `playing-to-win-analyst`.

## Method

1. **Extract the kernel from the material as written.** Find and quote the three components — and flag any that are missing:
   - **Diagnosis** — does the strategy name the *one or two critical challenges* and simplify the situation, or just list facts?
   - **Guiding policy** — is there an overall approach to *cope with the diagnosed challenge* (a method, not a goal)?
   - **Coherent action** — are there *coordinated* steps that follow from the policy and reinforce one another?
2. **Run the four bad-strategy detectors.** Mark each present/absent with evidence:
   - **Fluff** — abstract, gee-whiz language and buzzwords masking the absence of content (quote it).
   - **Failure to face the challenge** — no honest diagnosis; you cannot critique or improve a strategy that never defines its obstacle.
   - **Mistaking goals for strategy** — statements of desire ("grow 20%," "be #1") presented *as* strategy, with no mechanism.
   - **Bad strategic objectives** — a jumble of disconnected goals ("dog's dinner"), or "blue-sky" objectives that restate the problem instead of solving it.
3. **Test for coherence and focus.** Do the actions point in the *same* direction, or fight each other / spread resources thin? Strategy is choice — what is being said *no* to? If nothing, suspect bad strategy.
4. **Look for the source of power / leverage.** Good strategy concentrates force on a pivotal objective where action will have the greatest effect. Name the proposed leverage point — or its absence.
5. **Check the chain of reasoning to advantage.** Does each link (diagnosis → policy → action → result) actually hold, or is there a hidden leap, an unstated assumption, or a "and then a miracle occurs" step? Surface the weakest link explicitly.
6. **Reconstruct the strongest version, then attack it.** State the best steelman of the strategy, then the most damaging objection a smart rival or skeptical board would raise.

## Output rules

- Label every finding `[DATA]` (sourced) or `[INFERENCE]` (reasoned) with a 0–1 confidence value. Example: `[INFERENCE] The plan states a 25% share target but names no mechanism to win it — goal-as-strategy [0.8]`.
- Quote the source text you are critiquing; a red-team claim without the offending passage is unfalsifiable.
- Be specific and fair: separate *bad strategy* (structural defects) from *risky-but-real strategy* (a genuine bet you happen to doubt). Say which.
- Use `{region}`/`{industry}` facts and local-language sources (the active source pack) to test whether the diagnosis matches reality.
- Close with a **verdict — Real strategy / Partial / Bad strategy**, the **single most important missing or broken kernel element**, and the **one change that would most strengthen it**. ≤600 words.

## Reference

The kernel checklist, the four bad-strategy signatures with detection cues, the chain-of-reasoning audit, and a worked critique are in [`reference/good-strategy.md`](reference/good-strategy.md).

---

**Mini-example — {region}=Gulf (GCC), {industry}=ride-hailing.** A plan reading "become the region's super-app of choice by leveraging synergies and a customer-centric ecosystem" is **fluff + goal-as-strategy** `[INFERENCE] 0.8`: no diagnosis of the binding challenge (driver-supply economics under fuel-subsidy and labor-visa constraints), no guiding policy, no coordinated action. Verdict: **Bad strategy.** Strengthen by first diagnosing the supply-cost constraint and choosing one leverage point.
