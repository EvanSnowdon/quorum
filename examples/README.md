# Example engagements

Sample deliverables showing the standard Quorum report format:
conclusion-first structure (Pyramid Principle), `[DATA]` / `[INFERENCE]`
labeling with confidence scores, scenario analysis, a mandatory dissenting
view from the red team, and a data & confidence appendix.

| File | Engagement | Depth | Provenance |
|---|---|---|---|
| [`cn-electric-vehicles.md`](cn-electric-vehicles.md) | Electric vehicles · China | standard | **Real end-to-end run** on the v0.2 pipeline (deepseek-chat, single command, ~27k words; gated conclusion + reconciliation; metadata in the file header) |
| [`us-cybersecurity.md`](us-cybersecurity.md) | Cybersecurity services · United States | scan | Hand-written format illustration (abridged) |

> Scan-tier figures draw on model knowledge and are labeled hypotheses, not
> verified facts; treat the examples as format and rigor references, not
> research. Run your own engagement for current numbers:
>
> ```bash
> quorum --region CN --industry "electric vehicles" --depth standard
> ```
