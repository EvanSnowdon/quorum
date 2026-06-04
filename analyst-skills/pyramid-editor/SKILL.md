---
name: pyramid-editor
description: >
  Use to structure or restructure analysis into an executive-grade argument —
  conclusion first, logically grouped support. Invoke when a brief asks to "make
  this report land for executives", "tighten the logic", "write the executive
  summary", or when assembling and editing a final deliverable for a {region} and
  {industry} engagement. Produces a restructured document whose argument is
  answer-first, grouped, and MECE.
license: MIT
metadata:
  methodology: "Minto Pyramid Principle (Barbara Minto, 1978)"
  canonical_source: "The Minto Pyramid Principle: Logic in Writing, Thinking, and Problem Solving (1978)"
---

# Pyramid Editor

You structure executive-grade arguments using the **Minto Pyramid Principle**.

> Community-compiled interpretation of the published framework by Barbara Minto. Not affiliated with or endorsed by Barbara Minto or the Minto Pyramid Principle organization. See `reference/` and [`DISCLAIMER.md`](../DISCLAIMER.md).

## When to use

Given the working papers of a `{region}`/`{industry}` engagement, produce the
**final report structure and executive summary**: a single governing answer
supported by a grouped, MECE pyramid of arguments, written so an executive gets the
point first. This is an *editor* skill — it organizes and sharpens others'
analysis rather than generating new findings, and it is the last gate before
delivery.

## Method

1. **State the governing thought (answer first).** Identify the single main
   message the reader needs — the answer to their question — and put it at the
   top. If the material has no single answer, that is the first thing to fix.
2. **Build the introduction with SCQA.** Frame the question the document answers:
   **Situation** (accepted context) → **Complication** (what changed / the
   problem) → **Question** (the reader's implied question) → **Answer** (the
   governing thought). The body then answers that question.
3. **Group the supporting arguments.** Under the governing thought, place 2–5
   key-line arguments. Each group must be **MECE** — mutually exclusive
   (no overlap) and collectively exhaustive (no gaps).
4. **Enforce vertical logic.** Each level answers the "why?" or "how?" raised by
   the level above; the level above summarizes the level below. Reader questions
   are answered as they arise.
5. **Enforce horizontal logic.** Within a group, arguments are ordered either
   **deductively** (premise → premise → therefore) or **inductively** (a set of
   like ideas summarized by a single noun) — never a muddle of both.
6. **Summarize ideas, don't label them.** Each grouping headline must state the
   *insight* ("Supplier power is the binding constraint"), not a category
   ("Suppliers"). Empty headers are the most common pyramid failure.
7. **Write the executive summary last.** Distill the top of the pyramid into a
   summary that stands alone and carries the answer plus the key-line arguments.
8. **Reconcile contradictions.** Where working papers disagree, surface and
   resolve the conflict in the structure rather than letting both stand.

## Output rules

- Preserve every claim's original `[DATA]` / `[INFERENCE]` label and confidence;
  editing structure must not strip or alter evidence tags from the source papers.
- Do not invent findings. If the pyramid exposes a gap (a missing branch needed
  for collective exhaustiveness), flag it for an analyst rather than filling it.
- Headlines must be full-sentence insights; reject single-noun section labels.
- Output the **pyramid outline (governing thought → key-line arguments →
  support), the SCQA introduction, and a stand-alone executive summary**, plus a
  list of any logic gaps or contradictions found.

## Reference

The SCQA template, the MECE grouping rules, deductive-vs-inductive ordering, the
"summarize not label" rule, and a worked before/after example are in
[`reference/pyramid.md`](reference/pyramid.md).
---

**Mini-example — {region}=EU, {industry}=battery recycling engagement.** Governing thought: "Enter EU battery recycling now via a hub in Central Europe — structural demand is mandated, but margin depends on securing feedstock." SCQA intro frames the EOL-battery wave (S), the looming recycled-content mandate (C), "where and how to enter?" (Q), answer = the governing thought (A). Key lines (MECE): (1) demand is policy-locked, (2) profit pool sits in feedstock access + black-mass refining, (3) the winning move is feedstock contracts before capacity. Headlines are insights, not labels; every `[DATA]`/`[INFERENCE]` tag preserved.
