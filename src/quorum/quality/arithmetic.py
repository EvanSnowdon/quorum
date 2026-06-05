"""Deterministic arithmetic verification of the valuation section.

The sixth partner review found a return-grade defect the existing gates could
not catch: the valuation section's own DCF table computed an enterprise value
of 2,107M and an NPV of 1,607M, while the summary, the House View, and the
verdict all quoted an unsupported 1,020M / 520M — with a third enterprise
value floating in the same section — and the reconciliation layer then
*endorsed* the wrong figure by calling the freshly computed one "an old,
uncorrected number". Root cause: every adjudication and reconciliation step
resolves numeric conflicts by assertion — a model reads two numbers and rules
on them — and a model ruling on arithmetic can rule the wrong way. The same
review found a share comparison built on mismatched denominators: the volume
target was derived from a segment SAM of 0.26M units while the SOM band it
was judged against was computed on the overall SAM of 2.29M units, so the
"target falls inside the SOM" claim compared apples to oranges.

This module closes both holes with the one tool a model cannot out-argue:
re-running the arithmetic in Python.

Three functions and one report type:

- :func:`extract_financials` — one lead-model call that reads the valuation
  section and emits a strict JSON object: the explicit-year UFCF series, the
  discount rate, the undiscounted terminal value, the initial investment, the
  claimed EV / NPV / terminal share, and the SOM chain (TAM, overall and
  segment SAM, SOM band, target volume, stated share, and which denominator
  the stated share names). Missing items are ``null``. The model extracts;
  it never computes.
- :func:`parse_financials` — a pure function that strips code fences, decodes
  the JSON, and normalises the fields. It returns ``None`` when the output is
  not decodable or carries no recomputable core (no cash-flow series and no
  claimed headline value — e.g. a market-level valuation with no DCF), so the
  orchestrator can skip the gate cleanly at depths that price no play.
- :func:`verify` — pure Python, no model. It rebuilds the present value of
  each explicit year, the discounted terminal value, EV, NPV, the terminal
  value's share of EV, and the explicit-horizon (ex-terminal) NPV; compares
  each claimed figure against the recomputation under a relative tolerance;
  and audits the SOM chain — whether the SOM band is the named SAM times the
  stated share, what share the target implies on the segment and on the
  overall denominator, which denominator the stated share actually matches,
  and whether the target sits inside the band *on a single denominator*. A
  band built on one denominator and a target derived on another is flagged as
  a defect even when the raw numbers happen to overlap.
- :class:`VerificationReport` — the result: ``ok``, the ``recomputed``
  figures, the ``discrepancies`` list, and a :meth:`VerificationReport.markdown`
  renderer producing the verified-figures table the orchestrator writes under
  ``gates/`` and injects into the final House View and the editor as the
  authoritative record any prose claim must match.

v0.6.1 adds an economic-sanity layer on top of the internal-consistency
checks. A real v0.6.0 deliverable was internally consistent and still
economically incredible: its implied exit multiple (6.7x) sat above the peer
range it itself quoted (3.8-5.2x, median 4.8x), its mature-year EBIT margin
exceeded every comparable's current margin with no structural reason on the
record, its disclosed unmodeled per-vehicle items annualised to two orders of
magnitude more than the explicit-horizon NPV, and all of it was raised only
as prose caveats no gate enforced. :func:`verify` therefore also runs four
deterministic sanity checks over fields :func:`extract_financials` now
carries (peer multiples, the implied exit multiple, the base margin path
against peer current margins with a structural-reason flag, unmodeled
per-vehicle items against the explicit-horizon NPV, and the year-5 volume
against the year-3 SOM anchor). Checks (i) exit multiple above the peer
range and (ii) mature margin above every comparable without a stated
structural reason are *defects* — they enter ``discrepancies`` and trigger
the same pin-point correction round as an arithmetic mismatch. Checks (iii)
unmodeled items the explicit horizon cannot absorb and (iv) a volume
trajectory far beyond the SOM anchor are *flags* — they enter
``sanity_flags`` and render in the report without failing it, because the
honest response is disclosure-in-place, not a number change. A check any of
whose inputs the section does not state is skipped and recorded as not
assessable, never silently passed.

The orchestrator runs the gate after the valuation section clears its
fact-check; on a failed verification it dispatches one pin-point correction
through the revision mechanism and verifies the corrected text once more. The
recomputed figures, not the prose, are authoritative throughout.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from ..llm import LLM

# Default relative tolerance for comparing a claimed figure against its
# recomputation. Three percent absorbs rounding in a published table (values
# quoted to the nearest million, a rate quoted to one decimal) while failing
# anything that points at a different calculation: the defect this gate was
# built for was a 2x-3x divergence, not a rounding residue.
_DEFAULT_TOLERANCE = 0.03

# Output budget for the extraction call: a strict JSON object over a couple
# dozen scalar fields plus short year/peer series. Read at call time is
# unnecessary — the payload is small by construction.
_EXTRACT_MAX_TOKENS = 2000

_EXTRACT_SYSTEM = """\
You are a financial-data extractor on a Quorum engagement. You read one
valuation section and transcribe its stated figures into a strict JSON
object. You transcribe only: you never compute, infer, reconcile, or correct
a number, and you never add a figure the section does not state. Where the
section states the same quantity more than once with different values, take
the value from the DCF table or calculation itself (the figure with shown
arithmetic), not from a summary sentence. A field the section does not state
is null.

Output exactly one JSON object and nothing else — no prose, no markdown
fences, no commentary."""

_EXTRACT_SCHEMA = """\
{
  "currency_unit": <string: the currency and scale figures are stated in, e.g. "USD millions", or null>,
  "explicit_years": [
    {"year": <int: calendar year or year index>, "ufcf": <number: that year's unlevered free cash flow>}
  ],
  "discount_rate": <number: the discount rate (WACC) as a decimal fraction, e.g. 0.142 for 14.2%, or null>,
  "terminal_value_undiscounted": <number: the terminal value before discounting, or null>,
  "terminal_discount_years": <number: how many years the terminal value is discounted (usually the count of explicit years), or null>,
  "initial_investment": <number: the upfront investment the NPV nets off, or null>,
  "claimed_ev": <number: the enterprise value the section states, or null>,
  "claimed_npv": <number: the net present value the section states, or null>,
  "claimed_terminal_share": <number: the terminal value's stated share of EV, as a decimal fraction or percent, or null>,
  "peer_multiple_median": <number: the peer-comparable exit/valuation multiple median the section states, or null>,
  "peer_multiple_low": <number: lower end of the stated peer multiple range, or null>,
  "peer_multiple_high": <number: upper end of the stated peer multiple range, or null>,
  "implied_exit_multiple": <number: the exit multiple the section states its terminal value implies, or null>,
  "base_margin_path": [
    {"year": <int: calendar year or year index>, "ebit_margin_pct": <number: the base case's EBIT margin for that year, as stated>}
  ],
  "peer_current_margins": [
    {"name": <string: the comparable company's name>, "ebit_margin_pct": <number: its current EBIT margin as the section states it (negative if loss-making)>}
  ],
  "margin_premium_justified": <true if the section states a concrete structural reason (a demonstrated cost advantage, a different business model with shown economics) for its mature margin exceeding the comparables; false if it states none; null if no margin comparison is made>,
  "unmodeled_per_vehicle_low": <number: lower end of the stated per-unit cost of items disclosed as not modeled, or null>,
  "unmodeled_per_vehicle_high": <number: upper end of that per-unit range, or null>,
  "year5_volume": <number: the final explicit-year unit volume the section states, or null>,
  "som_year3": <number: the year-3 (or nearest stated mid-horizon) SOM volume anchor the section states, or null>,
  "som_chain": {
    "tam": <number or null>,
    "sam_overall": <number: the overall-market SAM, or null>,
    "sam_segment": <number: the selected play's segment SAM, or null>,
    "som_low": <number: lower end of the SOM band IN UNITS (never a percent; if the section states the band only in percent, convert via the named SAM, else null), or null>,
    "som_high": <number: upper end of the SOM band IN UNITS (same rule), or null>,
    "target_volume": <number: the play's target volume or value compared against the SOM, or null>,
    "stated_share_pct": <number: the share percentage the section states for the SOM or the target, or null>,
    "share_denominator": <"overall" | "segment" | "unclear": which SAM the stated share is expressed against>
  }
}"""


def extract_financials(valuation_text: str, llm: LLM, retry_note: str = "") -> str:
    """Extract the valuation section's stated figures as strict JSON.

    One lead-model completion over the section text, returning the raw model
    output — :func:`parse_financials` owns decoding and tolerance. The prompt
    binds the model to transcription: every field is a figure the section
    states (with the DCF table outranking a summary sentence when the two
    disagree, since the table is what the verifier recomputes against), and
    anything unstated is ``null``. ``retry_note`` is the orchestrator's
    bounded-retry channel: when a first output fails to parse, one retry runs
    with a note saying so, and a second failure makes the orchestrator skip
    the gate rather than guess.
    """
    note = f"{retry_note}\n\n" if retry_note else ""
    prompt = (
        f"{note}"
        "Read the valuation section below and output one JSON object with "
        "exactly this shape (a field the section does not state is null):\n\n"
        f"{_EXTRACT_SCHEMA}\n\n"
        "Numbers are plain JSON numbers in the section's stated unit — no "
        "thousands separators, no currency symbols, no strings. Express the "
        "discount rate as a decimal fraction. List explicit_years in "
        "chronological order, one entry per projected year in the DCF, with "
        "each year's unlevered free cash flow. If the section presents no "
        "DCF (for example a market-level view with no cash-flow build), set "
        "explicit_years to an empty list and the unstated fields to null. "
        "base_margin_path and peer_current_margins follow the same rule: "
        "transcribe what the section states, in order, and leave the list "
        "empty when the section states nothing. margin_premium_justified is "
        "the one judgment field: true only when the section states a "
        "concrete structural reason (a demonstrated cost advantage, a "
        "different business model with shown economics) for its mature "
        "margin exceeding the comparables — a bare claim that the entrant "
        "will execute better is not a structural reason.\n\n"
        "----- BEGIN VALUATION SECTION -----\n"
        f"{valuation_text}\n"
        "----- END VALUATION SECTION -----"
    )
    return llm.complete(system=_EXTRACT_SYSTEM, prompt=prompt, max_tokens=_EXTRACT_MAX_TOKENS)


_FENCE_RE = re.compile(r"^```[a-zA-Z]*\s*$")

_SOM_KEYS = (
    "tam",
    "sam_overall",
    "sam_segment",
    "som_low",
    "som_high",
    "target_volume",
    "stated_share_pct",
)


def _strip_fences(raw: str) -> str:
    """Drop surrounding markdown code fences from a model output."""
    lines = raw.strip().splitlines()
    if lines and _FENCE_RE.match(lines[0]):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _to_number(value: object) -> float | None:
    """Coerce one extracted field to a float, tolerating model slop.

    Accepts ints and floats as-is; strings are cleaned of thousands
    separators, currency markers, percent signs, and surrounding whitespace
    before conversion. Anything else — or a string that still does not parse
    — resolves to ``None``: a field the extraction could not state cleanly is
    treated as unstated rather than guessed at.
    """
    if isinstance(value, bool):  # bool is an int subclass; never a figure
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "").replace("%", "")
        cleaned = re.sub(r"[^\d.eE+-]", "", cleaned)
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def parse_financials(raw: str) -> dict | None:
    """Parse the extraction output into a normalised dict, or ``None``.

    Pure function. Strips markdown code fences, decodes the JSON, and
    normalises every field: numeric fields pass through :func:`_to_number`
    (so a stray ``"2,107"`` survives), missing keys default to ``None``, the
    year and margin series keep only entries with a usable value, the
    economic-sanity fields (peer multiples, the margin paths, the unmodeled
    per-unit range, the volume anchors, the ``margin_premium_justified``
    flag) are normalised in the same spirit, and the SOM chain is always a
    dict with every key present. Returns ``None`` when the output is not
    decodable JSON, decodes to something other than an object, or carries no
    recomputable core — no explicit-year series *and* no claimed EV or NPV —
    which is the shape a market-level valuation with no DCF produces, and
    the orchestrator's signal to skip the gate.
    """
    try:
        data = json.loads(_strip_fences(raw))
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict):
        return None

    years: list[dict[str, float]] = []
    raw_years = data.get("explicit_years")
    if isinstance(raw_years, list):
        for entry in raw_years:
            if not isinstance(entry, dict):
                continue
            ufcf = _to_number(entry.get("ufcf"))
            if ufcf is None:
                continue
            year = _to_number(entry.get("year"))
            years.append({"year": year, "ufcf": ufcf})

    margins: list[dict[str, float]] = []
    raw_margins = data.get("base_margin_path")
    if isinstance(raw_margins, list):
        for entry in raw_margins:
            if not isinstance(entry, dict):
                continue
            margin = _to_number(entry.get("ebit_margin_pct"))
            if margin is None:
                continue
            margins.append({"year": _to_number(entry.get("year")), "ebit_margin_pct": margin})

    peers: list[dict[str, object]] = []
    raw_peers = data.get("peer_current_margins")
    if isinstance(raw_peers, list):
        for entry in raw_peers:
            if not isinstance(entry, dict):
                continue
            margin = _to_number(entry.get("ebit_margin_pct"))
            if margin is None:
                continue
            name = entry.get("name")
            peers.append(
                {
                    "name": name.strip() if isinstance(name, str) and name.strip() else "peer",
                    "ebit_margin_pct": margin,
                }
            )

    justified = data.get("margin_premium_justified")
    if not isinstance(justified, bool):
        justified = None

    raw_som = data.get("som_chain")
    som_source = raw_som if isinstance(raw_som, dict) else {}
    som: dict[str, object] = {key: _to_number(som_source.get(key)) for key in _SOM_KEYS}
    denominator = som_source.get("share_denominator")
    if isinstance(denominator, str) and denominator.strip().lower() in ("overall", "segment"):
        som["share_denominator"] = denominator.strip().lower()
    else:
        som["share_denominator"] = "unclear"

    fin = {
        "currency_unit": (
            data["currency_unit"].strip()
            if isinstance(data.get("currency_unit"), str) and data["currency_unit"].strip()
            else None
        ),
        "explicit_years": years,
        "discount_rate": _to_number(data.get("discount_rate")),
        "terminal_value_undiscounted": _to_number(data.get("terminal_value_undiscounted")),
        "terminal_discount_years": _to_number(data.get("terminal_discount_years")),
        "initial_investment": _to_number(data.get("initial_investment")),
        "claimed_ev": _to_number(data.get("claimed_ev")),
        "claimed_npv": _to_number(data.get("claimed_npv")),
        "claimed_terminal_share": _to_number(data.get("claimed_terminal_share")),
        "peer_multiple_median": _to_number(data.get("peer_multiple_median")),
        "peer_multiple_low": _to_number(data.get("peer_multiple_low")),
        "peer_multiple_high": _to_number(data.get("peer_multiple_high")),
        "implied_exit_multiple": _to_number(data.get("implied_exit_multiple")),
        "base_margin_path": margins,
        "peer_current_margins": peers,
        "margin_premium_justified": justified,
        "unmodeled_per_vehicle_low": _to_number(data.get("unmodeled_per_vehicle_low")),
        "unmodeled_per_vehicle_high": _to_number(data.get("unmodeled_per_vehicle_high")),
        "year5_volume": _to_number(data.get("year5_volume")),
        "som_year3": _to_number(data.get("som_year3")),
        "som_chain": som,
    }
    if not fin["explicit_years"] and fin["claimed_ev"] is None and fin["claimed_npv"] is None:
        return None  # no recomputable core: nothing to verify, skip the gate
    return fin


@dataclass
class VerificationReport:
    """The arithmetic verifier's result over one valuation section.

    ``ok`` is True when every claimed figure the section states matches its
    recomputation within tolerance, the SOM chain holds on a single
    denominator, and the economic-sanity defect checks pass. ``recomputed``
    carries the rebuilt figures — these, not the prose, are authoritative
    downstream. ``discrepancies`` lists every mismatch and sanity defect in
    plain language; ``sanity_flags`` lists the sanity findings that warrant
    disclosure rather than a number change (an explicit horizon that cannot
    absorb the disclosed unmodeled items, a volume trajectory far beyond the
    SOM anchor); ``not_assessable`` records the sanity checks whose inputs
    the section does not state, so an unrun check is never read as a passed
    one. :meth:`markdown` renders the verified-figures table and the
    economic-sanity record the orchestrator writes under ``gates/`` and
    injects into the final House View and the editor.
    """

    ok: bool
    recomputed: dict = field(default_factory=dict)
    discrepancies: list[str] = field(default_factory=list)
    currency_unit: str | None = None
    sanity_flags: list[str] = field(default_factory=list)
    not_assessable: list[str] = field(default_factory=list)

    def markdown(self) -> str:
        """Render the verified figures, the discrepancies, and the sanity record."""
        unit = f" ({self.currency_unit})" if self.currency_unit else ""
        lines = ["## Arithmetic verification", ""]
        if self.ok:
            lines.append(
                "Status: VERIFIED — every stated headline figure matches its "
                "recomputation within tolerance, the share comparisons hold "
                "on a single denominator, and the economic-sanity checks "
                "that could be run found no defect."
            )
        else:
            lines.append(
                "Status: DISCREPANCIES FOUND — the recomputed figures below "
                "are authoritative; any prose claim that contradicts them is "
                "superseded."
            )
        lines += ["", f"Verified figures (authoritative){unit}:", ""]
        lines.append("| Quantity | Recomputed value |")
        lines.append("|---|---|")
        for label, key, kind in (
            ("PV of explicit-year cash flows", "pv_explicit", "amount"),
            ("PV of terminal value", "pv_terminal", "amount"),
            ("Enterprise value (EV)", "ev", "amount"),
            ("Initial investment", "initial_investment", "amount"),
            ("Net present value (NPV = EV - initial investment)", "npv", "amount"),
            ("Terminal value share of EV", "terminal_share", "share"),
            ("Explicit-horizon NPV (no terminal value)", "ex_terminal_npv", "amount"),
            ("Discount rate applied", "discount_rate", "share"),
            ("Target share of segment SAM", "target_share_of_segment", "share"),
            ("Target share of overall SAM", "target_share_of_overall", "share"),
        ):
            value = self.recomputed.get(key)
            if value is None:
                continue
            lines.append(f"| {label} | {_fmt(value, kind)} |")
        in_band = self.recomputed.get("target_in_som_band")
        if in_band is not None:
            basis = self.recomputed.get("som_band_denominator") or "stated"
            verdict = "inside" if in_band else "OUTSIDE"
            lines.append(
                f"| Target vs SOM band (single-denominator test, {basis} SAM) "
                f"| {verdict} the band |"
            )
        lines.append("")
        if self.discrepancies:
            lines.append("Discrepancies against the section's stated figures:")
            lines.append("")
            lines.extend(f"- {item}" for item in self.discrepancies)
        else:
            lines.append("No discrepancies: the stated figures recompute.")
        if self.sanity_flags or self.not_assessable:
            lines.append("")
            lines.append("Economic sanity:")
            lines.append("")
            lines.extend(f"- {item}" for item in self.sanity_flags)
            lines.extend(f"- Not assessable: {item}" for item in self.not_assessable)
        lines.append("")
        lines.append(
            "These figures were recomputed deterministically from the "
            "section's own stated inputs; they prevail over any prose claim, "
            "summary figure, or reconciliation note that states otherwise."
        )
        return "\n".join(lines)


def _fmt(value: float, kind: str) -> str:
    """Format one recomputed value for the markdown table."""
    if kind == "share":
        return f"{value * 100:.1f}%"
    if value == int(value) and abs(value) < 1e15:
        return f"{int(value):,}"
    return f"{value:,.1f}"


def _as_fraction(value: float | None) -> float | None:
    """Normalise a rate or share that may be stated as a percent.

    Sections state rates both ways ("0.142" and "14.2"); a value above 1 is
    read as a percentage. Values at or below 1 pass through unchanged.
    """
    if value is None:
        return None
    return value / 100.0 if value > 1.0 else value


def _close(claimed: float, recomputed: float, tolerance: float, scale: float | None = None) -> bool:
    """Whether a claimed figure matches its recomputation within tolerance.

    Relative comparison against the larger magnitude in play; ``scale``, when
    given, widens the base so a quantity derived from a larger one (NPV from
    EV) is judged at the parent's materiality rather than exploding near
    zero.
    """
    base = max(abs(claimed), abs(recomputed), abs(scale) if scale is not None else 0.0)
    if base == 0.0:
        return True
    return abs(claimed - recomputed) <= tolerance * base


def verify(fin: dict, tolerance: float = _DEFAULT_TOLERANCE) -> VerificationReport:
    """Recompute the valuation's arithmetic and audit the SOM chain.

    Pure Python; no model. From the parsed extraction it rebuilds: the
    present value of each explicit year's UFCF (year *n* discounted *n*
    periods), the discounted terminal value, EV as their sum, NPV as EV less
    the initial investment, the terminal value's share of EV, and the
    explicit-horizon NPV with no terminal value. Each claimed figure the
    section states is compared against its recomputation under ``tolerance``
    (relative; the NPV comparison is scaled by EV so a near-zero NPV is
    judged at the valuation's materiality). The SOM chain is audited on the
    denominator question: what share the target implies on the segment and
    on the overall SAM, which denominator the stated share actually matches,
    whether the named SAM times the stated share reproduces the target, and
    whether the target sits inside the SOM band on a single denominator — a
    band whose arithmetic matches the overall SAM while the play is
    segment-scoped fails that test outright, because the in-band claim then
    compares shares of two different markets.

    On top of the internal-consistency checks, four deterministic
    economic-sanity checks run over the section's own stated benchmarks
    (:func:`_verify_economics`): an implied exit multiple above the stated
    peer range and a mature EBIT margin above every stated comparable
    without a structural reason are defects that enter ``discrepancies``;
    disclosed unmodeled items the explicit horizon cannot absorb and a
    year-5 volume far beyond the year-3 SOM anchor enter ``sanity_flags``.
    A check missing any input is skipped and recorded in ``not_assessable``.
    """
    recomputed: dict = {}
    discrepancies: list[str] = []
    sanity_flags: list[str] = []
    not_assessable: list[str] = []

    rate = _as_fraction(fin.get("discount_rate"))
    years = fin.get("explicit_years") or []

    pv_explicit: float | None = None
    pv_terminal: float | None = None
    ev: float | None = None
    npv: float | None = None

    if rate is not None and years:
        recomputed["discount_rate"] = rate
        pv_explicit = sum(
            entry["ufcf"] / (1.0 + rate) ** (index + 1) for index, entry in enumerate(years)
        )
        recomputed["pv_explicit"] = pv_explicit

        tv = fin.get("terminal_value_undiscounted")
        if tv is not None:
            horizon = fin.get("terminal_discount_years")
            periods = horizon if horizon is not None else float(len(years))
            pv_terminal = tv / (1.0 + rate) ** periods
            recomputed["pv_terminal"] = pv_terminal

        ev = pv_explicit + (pv_terminal or 0.0)
        recomputed["ev"] = ev
        if pv_terminal is not None and ev:
            recomputed["terminal_share"] = pv_terminal / ev

        investment = fin.get("initial_investment")
        if investment is not None:
            recomputed["initial_investment"] = investment
            npv = ev - investment
            recomputed["npv"] = npv
            recomputed["ex_terminal_npv"] = pv_explicit - investment

    claimed_ev = fin.get("claimed_ev")
    if claimed_ev is not None and ev is not None and not _close(claimed_ev, ev, tolerance):
        discrepancies.append(
            f"Stated enterprise value {claimed_ev:,.0f} does not recompute: "
            f"the section's own cash flows and discount rate yield "
            f"{ev:,.0f}."
        )
    claimed_npv = fin.get("claimed_npv")
    if claimed_npv is not None and npv is not None and not _close(
        claimed_npv, npv, tolerance, scale=ev
    ):
        discrepancies.append(
            f"Stated NPV {claimed_npv:,.0f} does not recompute: EV "
            f"{ev:,.0f} less the initial investment "
            f"{fin.get('initial_investment'):,.0f} yields {npv:,.0f}."
        )
    claimed_share = _as_fraction(fin.get("claimed_terminal_share"))
    recomputed_share = recomputed.get("terminal_share")
    if (
        claimed_share is not None
        and recomputed_share is not None
        and abs(claimed_share - recomputed_share) > tolerance
    ):
        discrepancies.append(
            f"Stated terminal-value share of EV {claimed_share * 100:.1f}% "
            f"does not recompute: the discounted terminal value is "
            f"{recomputed_share * 100:.1f}% of EV."
        )

    _verify_som(fin.get("som_chain") or {}, tolerance, recomputed, discrepancies)
    _verify_economics(fin, recomputed, discrepancies, sanity_flags, not_assessable)

    return VerificationReport(
        ok=not discrepancies,
        recomputed=recomputed,
        discrepancies=discrepancies,
        currency_unit=fin.get("currency_unit"),
        sanity_flags=sanity_flags,
        not_assessable=not_assessable,
    )


def _verify_som(
    som: dict, tolerance: float, recomputed: dict, discrepancies: list[str]
) -> None:
    """Audit the SOM chain in place; the share-of-what discipline in code.

    Computes the target's implied share on each available denominator,
    determines which denominator the stated share actually matches, checks
    that the named SAM times the stated share reproduces the target, infers
    which denominator the SOM band's arithmetic sits on, and runs the
    in-band test only as a single-denominator comparison. Mismatches land in
    ``discrepancies``; every rebuilt figure lands in ``recomputed``.
    """
    sam_segment = som.get("sam_segment")
    sam_overall = som.get("sam_overall")
    target = som.get("target_volume")
    som_low = som.get("som_low")
    som_high = som.get("som_high")
    stated_share = _as_fraction(som.get("stated_share_pct"))
    declared = som.get("share_denominator") or "unclear"

    share_of_segment: float | None = None
    share_of_overall: float | None = None
    if target is not None and sam_segment:
        share_of_segment = target / sam_segment
        recomputed["target_share_of_segment"] = share_of_segment
    if target is not None and sam_overall:
        share_of_overall = target / sam_overall
        recomputed["target_share_of_overall"] = share_of_overall

    # Which denominator does the stated share's own arithmetic match?
    matched: str | None = None
    if stated_share is not None:
        candidates = []
        if share_of_segment is not None and _close(stated_share, share_of_segment, tolerance):
            candidates.append("segment")
        if share_of_overall is not None and _close(stated_share, share_of_overall, tolerance):
            candidates.append("overall")
        if len(candidates) == 1:
            matched = candidates[0]
            recomputed["stated_share_matches_denominator"] = matched
            if declared in ("overall", "segment") and declared != matched:
                discrepancies.append(
                    f"The stated share {stated_share * 100:.1f}% is described "
                    f"against the {declared} SAM but its arithmetic matches "
                    f"the {matched} SAM ({_share_text(matched, share_of_segment, share_of_overall)})."
                )
        elif not candidates and (share_of_segment is not None or share_of_overall is not None):
            discrepancies.append(
                f"The stated share {stated_share * 100:.1f}% matches neither "
                f"denominator: the target implies "
                f"{_both_shares_text(share_of_segment, share_of_overall)}."
            )

    # Units guard: a band extracted in percent (both bounds <= 100) compared
    # against a unit-scale target would fail as OUTSIDE for the wrong reason
    # (this shipped once: target 30,000 vs a "2-5" percent band). Normalize a
    # percent band to units via the available SAM before any inference or
    # in-band test; with no SAM to convert against, drop the band rather than
    # fabricate a verdict.
    if (
        som_low is not None
        and som_high is not None
        and target is not None
        and max(som_low, som_high) <= 100 < target
    ):
        conv_sam = sam_segment if sam_segment is not None else sam_overall
        if conv_sam is not None:
            som_low = conv_sam * som_low / 100.0
            som_high = conv_sam * som_high / 100.0
            recomputed["som_band_normalized"] = (
                "band stated in percent; converted to units via the "
                + ("segment" if sam_segment is not None else "overall")
                + " SAM"
            )
        else:
            discrepancies.append(
                "The SOM band is stated in percent while the target is in "
                "units, and no SAM is stated to convert against; restate the "
                "band in units. The in-band test was not run."
            )
            som_low = som_high = None

    # Which denominator is the SOM band built on? Inferred from the band's own
    # arithmetic against the stated share, falling back to the declaration.
    band_basis: str | None = None
    if som_low is not None and som_high is not None:
        if stated_share is not None:
            if sam_segment and _in_band(sam_segment * stated_share, som_low, som_high, tolerance):
                band_basis = "segment"
            elif sam_overall and _in_band(
                sam_overall * stated_share, som_low, som_high, tolerance
            ):
                band_basis = "overall"
        if band_basis is None and declared in ("overall", "segment"):
            band_basis = declared
        if band_basis is not None:
            recomputed["som_band_denominator"] = band_basis

        if target is not None:
            # The play is segment-scoped whenever a segment SAM exists; an
            # in-band verdict on a band built against the overall market then
            # compares shares of two different denominators.
            segment_scoped = sam_segment is not None and (
                sam_overall is None or not _close(sam_segment, sam_overall, tolerance)
            )
            if band_basis == "overall" and segment_scoped:
                recomputed["target_in_som_band"] = False
                overall_text = (
                    f" ({sam_overall:,.0f})" if sam_overall is not None else ""
                )
                discrepancies.append(
                    "Denominator mismatch in the SOM comparison: the SOM band "
                    f"({som_low:,.0f}-{som_high:,.0f}) is computed on the "
                    f"overall SAM{overall_text} while the play is "
                    f"segment-scoped (segment SAM {sam_segment:,.0f}); "
                    "judging the target against this band compares shares of "
                    "two different markets. The single-denominator reading: "
                    f"the target of {target:,.0f} is "
                    f"{(target / sam_segment) * 100:.1f}% of the segment SAM "
                    f"and {_overall_share_text(target, sam_overall)} of the "
                    "overall SAM; the band must be restated on the segment "
                    "SAM before any in-band claim is made."
                )
            else:
                in_band = som_low <= target <= som_high or _in_band(
                    target, som_low, som_high, tolerance
                )
                recomputed["target_in_som_band"] = in_band
                if not in_band:
                    discrepancies.append(
                        f"The target of {target:,.0f} falls outside the SOM "
                        f"band ({som_low:,.0f}-{som_high:,.0f}) on its own "
                        "denominator."
                    )


# Volume-anchor threshold for sanity check (iv): a final-explicit-year volume
# more than this multiple of the year-3 SOM anchor is flagged as a trajectory
# the sizing work does not support. Two is a mild default by design — a play
# can credibly double off its mid-horizon anchor inside two further years of
# ramp, but a larger jump means the late-year volumes ride on growth the
# SOM never sized, and the reader should see that stated rather than implied.
_VOLUME_ANCHOR_MULTIPLE = 2.0


def _verify_economics(
    fin: dict,
    recomputed: dict,
    discrepancies: list[str],
    sanity_flags: list[str],
    not_assessable: list[str],
) -> None:
    """Run the deterministic economic-sanity checks in place.

    Four checks over the section's own stated benchmarks, each skipped — and
    recorded as not assessable — when any input it needs is unstated:

    (i)   implied exit multiple above the stated peer range: a defect — the
          terminal value asserts an exit richer than every comparable the
          section itself quotes.
    (ii)  mature-year EBIT margin above every stated comparable's current
          margin without a stated structural reason
          (``margin_premium_justified`` is not true): a defect — the base
          case assumes economics no peer demonstrates.
    (iii) the disclosed unmodeled per-unit items, annualised at the low end
          (low x year-5 volume), at or above the explicit-horizon NPV: a
          flag — the explicit horizon cannot absorb the items the section
          itself discloses, so the conclusion rests entirely on the terminal
          value surviving them.
    (iv)  year-5 volume above :data:`_VOLUME_ANCHOR_MULTIPLE` times the
          year-3 SOM anchor: a flag — the late-year volume trajectory runs
          beyond what the sizing work anchored.

    Defects join ``discrepancies`` (they fail the report and trigger the
    same pin-point correction round as an arithmetic mismatch); flags join
    ``sanity_flags`` (they render in the report's Economic sanity record
    without failing it, because the honest fix is disclosure in place, not a
    different number).
    """
    # (i) Implied exit multiple vs the stated peer range.
    implied = fin.get("implied_exit_multiple")
    peer_high = fin.get("peer_multiple_high")
    if implied is None or peer_high is None:
        not_assessable.append(
            "implied exit multiple vs the peer range (the section does not "
            "state both the implied multiple and the peer range)."
        )
    else:
        recomputed["implied_exit_multiple"] = implied
        if implied > peer_high:
            median = fin.get("peer_multiple_median")
            peer_low = fin.get("peer_multiple_low")
            range_text = (
                f"{peer_low:,.1f}x-{peer_high:,.1f}x"
                if peer_low is not None
                else f"up to {peer_high:,.1f}x"
            )
            median_text = f", median {median:,.1f}x" if median is not None else ""
            discrepancies.append(
                f"The implied exit multiple of {implied:,.1f}x sits above the "
                f"peer range the section itself states ({range_text}"
                f"{median_text}): the terminal value asserts an exit richer "
                "than every quoted comparable. State an alternative terminal "
                "value anchored at the peer median multiple, with its "
                "resulting NPV, alongside the base figure."
            )

    # (ii) Mature-year EBIT margin vs every stated comparable's current margin.
    margins = fin.get("base_margin_path") or []
    peers = fin.get("peer_current_margins") or []
    if not margins or not peers:
        not_assessable.append(
            "mature-year EBIT margin vs comparable current margins (the "
            "section does not state both the base margin path and the "
            "comparables' current margins)."
        )
    else:
        mature = margins[-1]["ebit_margin_pct"]
        peer_best = max(p["ebit_margin_pct"] for p in peers)
        recomputed["mature_ebit_margin_pct"] = mature
        recomputed["peer_best_ebit_margin_pct"] = peer_best
        if mature > peer_best and fin.get("margin_premium_justified") is not True:
            best_name = next(
                p["name"] for p in peers if p["ebit_margin_pct"] == peer_best
            )
            discrepancies.append(
                f"The base case's mature EBIT margin of {mature:,.1f}% "
                f"exceeds every stated comparable's current margin (best: "
                f"{best_name} at {peer_best:,.1f}%) and the section states "
                "no structural reason for the premium. Reduce the mature "
                "margin to the comparable anchor, or state the concrete "
                "structural reason (a demonstrated cost advantage, a "
                "different business model with shown economics) and lower "
                "the confidence accordingly."
            )

    # (iii) Disclosed unmodeled items, annualised at the low end, vs the
    # explicit-horizon NPV. Uses the recomputed ex-terminal NPV so the
    # comparison sits on the verifier's own arithmetic.
    unmodeled_low = fin.get("unmodeled_per_vehicle_low")
    year5_volume = fin.get("year5_volume")
    ex_terminal = recomputed.get("ex_terminal_npv")
    if unmodeled_low is None or year5_volume is None or ex_terminal is None:
        not_assessable.append(
            "unmodeled items vs the explicit-horizon NPV (the section does "
            "not state the per-unit unmodeled range, the final-year volume, "
            "or a recomputable explicit-horizon build)."
        )
    else:
        annualised_low = unmodeled_low * year5_volume
        recomputed["unmodeled_annualised_low"] = annualised_low
        if annualised_low >= ex_terminal:
            sanity_flags.append(
                f"The disclosed unmodeled items annualise to at least "
                f"{annualised_low:,.0f} at the final explicit-year volume — "
                f"at or above the explicit-horizon NPV of {ex_terminal:,.0f}: "
                "the explicit horizon cannot absorb unmodeled items, so any "
                "positive conclusion rests entirely on the terminal value "
                "surviving them. The report must state this dependence where "
                "the verdict is drawn."
            )

    # (iv) Year-5 volume vs the year-3 SOM anchor.
    som_year3 = fin.get("som_year3")
    if year5_volume is None or som_year3 is None or som_year3 <= 0:
        not_assessable.append(
            "final-year volume vs the SOM anchor (the section does not "
            "state both the final explicit-year volume and the year-3 SOM "
            "anchor)."
        )
    elif year5_volume > som_year3 * _VOLUME_ANCHOR_MULTIPLE:
        sanity_flags.append(
            f"The final explicit-year volume of {year5_volume:,.0f} is more "
            f"than {_VOLUME_ANCHOR_MULTIPLE:,.0f}x the year-3 SOM anchor of "
            f"{som_year3:,.0f}: the late-year volume trajectory runs beyond "
            "what the sizing work anchored, and the assumption carrying the "
            "excess must be stated next to the volumes."
        )


def _in_band(value: float, low: float, high: float, tolerance: float) -> bool:
    """Whether a value sits inside a band, with tolerance at the edges."""
    slack = tolerance * max(abs(low), abs(high))
    return (low - slack) <= value <= (high + slack)


def _share_text(
    matched: str, share_of_segment: float | None, share_of_overall: float | None
) -> str:
    value = share_of_segment if matched == "segment" else share_of_overall
    return f"{value * 100:.1f}% of the {matched} SAM" if value is not None else matched


def _both_shares_text(
    share_of_segment: float | None, share_of_overall: float | None
) -> str:
    parts = []
    if share_of_segment is not None:
        parts.append(f"{share_of_segment * 100:.1f}% of the segment SAM")
    if share_of_overall is not None:
        parts.append(f"{share_of_overall * 100:.2f}% of the overall SAM")
    return " and ".join(parts) if parts else "no computable share"


def _overall_share_text(target: float, sam_overall: float | None) -> str:
    if not sam_overall:
        return "an indeterminable share"
    return f"{(target / sam_overall) * 100:.2f}%"
