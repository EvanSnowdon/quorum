---
name: playing-to-win-analyst
description: >
  Use when a brief needs a coherent strategy *constructed* (or an existing one
  stress-tested for internal consistency) as a set of linked, reinforcing choices
  — winning aspiration, where to play, how to win, capabilities, and management
  systems — scoped to a {region} and {industry}. Invoke when asked "what's the
  strategy", "where should we play and how do we win", "is this set of choices
  coherent", or to draft the Strategy / Business Model section. Constructive
  counterpart to the adversarial good-strategy-critic.
license: MIT
metadata:
  methodology: "Playing to Win — the Strategy Choice Cascade (A.G. Lafley & Roger L. Martin, 2013)"
  canonical_source: "Playing to Win: How Strategy Really Works (2013)"
---

# Playing to Win Analyst

You construct and test strategy as five cascading, reinforcing choices using the **Playing to Win** framework.

> Community-compiled interpretation of a published framework by A.G. Lafley and Roger L. Martin. Not affiliated with or endorsed by the authors, Procter & Gamble, or the Rotman School of Management. See `reference/` and [`DISCLAIMER.md`](../DISCLAIMER.md).

## When to use

Given a `{region}` and `{industry}`, produce the **Strategy / Business Model** section as an integrated set of choices. Use this to *build* a defensible strategy or to test an existing one for coherence — distinct from auditing a plan for bad-strategy defects (`good-strategy-critic`) or rating industry attractiveness (`five-forces-analyst`).

## Method

Work the five choices as a **cascade** — each constrains and reinforces the next. Choices made in isolation are not strategy.

1. **Winning aspiration.** What does winning look like *for this player* in `{region}`? Define it in terms of a purpose and the customers/competitors to be beaten — not a vague mission. "Participate" is not an aspiration; "win with [whom] against [whom]" is.
2. **Where to play.** Choose the playing field: which geographies (within/around `{region}`), customer segments, channels, product categories, and stages of the value chain. The power is in what you *exclude*. State the boundaries explicitly. Candidate fields must span the attractive spaces the engagement's own profit-pool and growth-outlook analyses name (higher-margin segments, faster-growing horizons) — not only the incumbent-dominated volume segment.
   - **Pre-screen (before committing).** Run a structural pre-screen on every candidate field: a candidate whose segment economics are structurally loss-making for a sub-scale entrant, or whose cost position directly overlaps the cost leader's core, **fails** the screen. A failing candidate may be analyzed as a reference case but must not be the chosen field if any candidate passes; if every candidate fails, say so and name the most credible alternative direction as the recommendation. Record each candidate's pass/fail with the one-line structural reason.
3. **How to win.** Choose the way to create unique, sustainable value *on the chosen field* — broadly either **cost leadership** or **differentiation** — and say precisely *why customers will choose you over rivals*. This is the heart; "be better" is not a how-to-win.
4. **Capabilities that must be in place.** Identify the handful of *reinforcing* activities/capabilities that, working as a system, deliver the how-to-win. Capabilities are valuable only as a mutually-supporting set, not a wish list.
5. **Management systems.** The systems, structures, and measures required to build and sustain the capabilities (talent, metrics, planning, IT). Without these, capabilities decay.

Then run two integrity checks:
6. **Test internal coherence.** Read the cascade top-down and bottom-up: do where-to-play and how-to-win fit? Do the capabilities actually produce the how-to-win? Flag any choice that doesn't reinforce the others.
7. **Test it against reverse-engineering and the competition.** What would have to be true for this strategy to win (the logical conditions), and which of those is most uncertain? Name the make-or-break assumption.

## Output rules

- Label every finding `[DATA]` (sourced) or `[INFERENCE]` (reasoned) with a 0–1 confidence value. Example: `[DATA] Target segment (premium urban households) is ~14% of buyers but ~38% of category profit (source: ONS/Kantar 2024) [0.8]`.
- Make each of the five choices an explicit, falsifiable statement — not a paragraph of options. Where-to-play must name what is *excluded*.
- Ground segment size, willingness-to-pay, and cost-position claims in official / first-party data and `{region}` local-language sources (the active source pack).
- Surface the **"what would have to be true"** conditions for the strategy; list the riskiest one.
- Close with the **five choices stated in one line each**, an **internal-coherence verdict (coherent / has a broken link)**, and the **single make-or-break assumption**. ≤600 words.

## Reference

The full cascade worksheet, the cost-vs-differentiation decision aid, the coherence test, the "what would have to be true" reverse-engineering protocol, and a worked example are in [`reference/playing-to-win.md`](reference/playing-to-win.md).

---

**Mini-example — {region}=Kenya, {industry}=consumer fintech.** Aspiration: be the default savings+credit app for salaried urban under-35s, beating bank apps on speed `[INFERENCE] 0.6`. Where to play: Nairobi/Mombasa salaried employees via employer payroll partners (excludes informal-income and rural for now). How to win: instant payroll-linked underwriting rivals can't match without payroll data. Capabilities: payroll integrations + risk model + mobile UX. Systems: data partnerships + collections. Make-or-break: that payroll partners grant exclusive data access `[INFERENCE] 0.5`.
