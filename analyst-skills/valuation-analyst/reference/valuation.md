# Valuation — Reference

## Frame first (decisions that govern everything after)

- **Enterprise vs. equity value.** EV = value of operations to all capital providers; Equity = EV − net debt − minorities − preferred + non-operating assets. Pick deliberately; multiples and cash flows must match (EV ↔ pre-financing flows/EBITDA; Equity ↔ net income/dividends).
- **Currency & date.** Value is as-of a date in a currency; state both.
- **Going concern vs. asset/liquidation.** DCF/comps assume going concern.

## DCF build

**1. Free cash flow to the firm (unlevered FCF):**
```
FCF = EBIT × (1 − tax rate)            (= NOPAT)
      + Depreciation & Amortization
      − Capital expenditure
      − Increase in net working capital
```
Project explicitly for 5–10 years. Each driver (revenue growth, margin, capex %, NWC %) stated and sourced; tie growth to the market sizing and margins to the value-chain/structure work.

**2. Discount rate — WACC:**
```
WACC = E/V × Ke + D/V × Kd × (1 − tax)
Ke (CAPM) = Rf + β × ERP   (+ size/country premia if used)
```
- **Rf** — local long-bond yield for `{region}` and currency (match currency of cash flows).
- **ERP** — equity risk premium; add a **country risk premium** for emerging `{region}`.
- **β** — relever an industry-average unlevered β to the target's capital structure: `βL = βU × [1 + (1−t)·D/E]`.
- **Kd** — current pre-tax cost of debt × (1 − tax).

**3. Terminal value (choose one, sanity-check both):**
```
Gordon growth:   TV = FCF(n)·(1+g) / (WACC − g)      [g ≤ long-run GDP growth]
Exit multiple:   TV = Metric(n) × peer multiple
```
TV often is >60% of value — check the *implied* growth (from an exit multiple) and the *implied* multiple (from g) are both sane.

**4. Bridge:** PV(explicit FCF) + PV(TV) = Enterprise Value → subtract net debt etc. → Equity Value → ÷ shares = per-share.

## Comparable companies

1. **Build a true peer set** — same `{industry}`, comparable size, growth, margin, capital intensity, and (ideally) `{region}`/listing. Note for each why it is or isn't comparable.
2. **Pick the right multiple:**
   - **EV/EBITDA** — capital-structure-neutral; default for cross-company.
   - **EV/Sales** — for unprofitable/early firms; pair with a margin caveat.
   - **P/E** — equity multiple; sensitive to leverage and accounting.
   - **Sector-specific** — EV/subscriber, EV/MW, EV/sqm, etc., where they drive value.
3. **Apply** the median/quartile peer multiple to the target's metric; prefer forward multiples; adjust for growth/margin differences (don't apply a high-grower's multiple to a no-grower).

## Cross-validation & reconciliation

Place DCF and comps side by side. A material gap is a *finding*: identify the driver (growth, margin, WACC, or the multiple/peer choice). Reconcile to a **range**, weighting the method better supported by data; never average blindly.

## Sensitivity table (mandatory)

Tornado or 2-way grid on the 2–3 highest-impact assumptions — almost always **WACC × terminal growth**, plus one operating driver (revenue CAGR or steady-state margin). Report the value *range* these produce.

## Common errors

- Currency/flow mismatch (e.g., equity multiple on EV, or local cash flows discounted at a USD rate).
- Terminal growth ≥ WACC, or g above long-run GDP (implies the firm eventually exceeds the economy).
- Ignoring country risk premium in emerging `{region}`.
- "Comps" that aren't comparable (different growth/margin/risk).
- False precision — a single point value instead of a sourced range.
- Double-counting non-operating assets or forgetting net debt in the bridge.

## Worked example (≈180 words)

**Target:** profitable mid-size packaged-food maker, {region}. **EV basis, local currency, valuation date stated.**

- **FCF (yr 1)** `[DATA] 0.6`: EBIT 120 × (1−0.25) = 90 NOPAT; +30 D&A −40 capex −10 ΔNWC = **70**. Revenue CAGR 6% tied to category sizing; EBIT margin held ~12%.
- **WACC** `[INFERENCE] 0.55`: Rf 7.0% (local 10-yr) + β 0.9 × ERP 6.5% (incl. country premium) = Ke 12.9%; Kd 9% × (1−0.25)=6.75%; 70/30 E/D → **WACC ≈ 11.0%**.
- **Terminal** `[INFERENCE] 0.5`: g = 3.5% (≤ GDP); TV = FCF(5)·1.035/(0.11−0.035). Implied exit EV/EBITDA cross-checked ≈ 8× (sane for the sector).
- **DCF EV** `[INFERENCE] 0.5`: ≈ 980 (illustrative).
- **Comps** `[DATA] 0.6`: peer median EV/EBITDA 8.5× × target EBITDA 150 = **EV ≈ 1,275**; target's lower growth argues a discount → ~8.0× → **≈ 1,200**.
- **Reconcile:** DCF ~980 vs comps ~1,200 → gap driven by conservative DCF growth/WACC; **range ≈ 1,000–1,200**, weighted toward the middle.
- **Sensitivity:** WACC ±1pt and g ±0.5pt swing EV ~±15%.

**DCF:** ~980. **Comps:** ~1,200. **Reconciled EV range:** ~1.0–1.2bn (local, as-of date). **Most sensitive to:** WACC × terminal growth.
