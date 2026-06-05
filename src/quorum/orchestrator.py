"""The engagement manager: scope, dispatch, synthesize, revise, assemble.

:class:`ManagingPartner` is the lead agent. It reads the crew roster, scopes a
MECE research plan (opening with a binding Scope Lock), dispatches analysts in
ascending phases under task contracts — the fact base first, then strategy
against the checked fact base, then valuation and critique against the checked
strategy — runs each phase's drafts through the fact-check gate before the
next phase starts, runs the deterministic arithmetic gate over the checked
valuation section (its stated figures extracted to strict JSON, the DCF, the
SOM chain, and the economic-sanity checks recomputed in pure Python, a
prose-vs-recomputation contradiction triggering one pin-point correction
verified once more, with
the verified-figures table binding the rest of the run), then forces the
parallel framework sections to converge
through the synthesis *loop*: a cross-section conflict scan, the supervising
partner's adjudication draft with machine-readable revision orders, a parallel
revision round in which each ordered seat rewrites its section under the
rulings (the original draft is archived, the revision fact-checked and swapped
in; a rewritten valuation section is arithmetic-verified again), and a final
House View written against the revised body, opening with the
Canonical figures table the rest of the report follows. The red team attacks
the revised sections and the final ruling; when its memo proves a
canonical-grade error in that ruling, one bounded amendment pass corrects the
Canonical figures and gate tables (archiving the pre-amendment text) before
the editor runs, so a red-team catch is fixed in Part I instead of merely
flagged in Part III. Once the canonical record is final, a stale-figure
sweep lists any superseded value the body still states as current and turns
the list into one round of pin-point fixes confined to the named sections
(pre-fix texts archived; whatever the round misses is recorded as a
limitation, with the Canonical figures table prevailing). The report is
assembled in code, embedding the revised
sections, the House View as it finally stands, and the red-team memo
verbatim. Analysts run concurrently within a phase and never talk to each
other; all coordination flows through this class and the engagement
directory.
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import yaml
from pydantic import BaseModel

from . import quality
from .analyst import Analyst, TaskContract
from .llm import LLM
from .memory import EngagementMemory
from .output import report as report_output

# Per-tier compute budget. `max_analysts` caps how far down the crew roster the
# orchestrator staffs; `tool_calls` is the per-analyst tool-call budget the
# contract declares. These are enforced at dispatch, not requested in prompts.
EFFORT: dict[str, dict[str, int]] = {
    "scan": {"max_analysts": 6, "tool_calls": 4},
    "standard": {"max_analysts": 14, "tool_calls": 10},
    "due_diligence": {"max_analysts": 26, "tool_calls": 18},
}

_CREWS_PATH = Path(__file__).parent / "crews.yaml"
_MEMORY_RECALL_LIMIT = 2000

# Checked-section keys carried in FULL into the contracts of each later phase;
# everything else from earlier phases enters as title plus a one-line gist, so
# context stays proportional without hiding what was covered.
#
#   phase 2 (strategy): the fact base it must choose against — sizing,
#     structure, and demand.
#   phase 3 (valuation & critique): the strategy sections it prices and
#     attacks (the where-to-play seat plus the play-producing powers and
#     blue-ocean seats), plus sizing so volume assumptions stay anchored to
#     SAM/SOM. Everything else — structure included — enters as a gist.
#
# A phase with no entry here (and any phase beyond 3) inherits the deepest
# selection declared at or below it — the most strategy-complete digest
# available. Keys absent from a roster are simply skipped.
_FULL_TEXT_KEYS_BY_PHASE: dict[int, tuple[str, ...]] = {
    2: ("market_sizing", "industry_structure", "demand_jobs"),
    3: ("strategy_choice", "firm_power", "market_creation", "market_sizing"),
}

# Seats whose remit includes proposing named entry plays. If none of them runs
# in an earlier phase (e.g. a trimmed scan roster), later valuation seats run
# at market level instead of pricing plays that were never written.
_ENTRY_PLAY_KEYS = ("strategy_choice", "firm_power")

# Sentence-final characters for the truncation heuristic: a worker draft whose
# last content line ends in none of these — and is not a table row, list item,
# heading, or confidence-score trailer — most likely hit the output ceiling
# mid-sentence.
_SENTENCE_ENDINGS = tuple('.!?:)"\'»】」』。！？：”’…')

# A claim-label confidence trailer ("[DATA] 0.9", "[INFERENCE; 0.4]",
# "(confidence: 0.85)") is a legitimate line ending under the labeling
# discipline even though it closes on a digit.
_CONFIDENCE_TRAILER_RE = re.compile(r"\d\.\d+\s*[\])]*\s*$")


class _NullPack:
    """Stand-in source pack used when no pack is available for a region.

    The data engineer owns ``source_packs.load_pack`` and the real
    :class:`SourcePack`. Until a pack exists for a region -- or until the
    ``source_packs`` module ships at all -- the orchestration core must still
    run rather than crash. This satisfies the agreed ``SourcePack`` surface
    (``region``, ``data_quality_score``, ``tool_names()``, ``context_block()``)
    and tells analysts plainly that no curated local sources are available, so
    every figure they cannot ground falls back to a labelled ``[INFERENCE]``.
    """

    def __init__(self, region: str) -> None:
        self.region = region
        self.data_quality_score = 0

    def tool_names(self) -> list[str]:
        return []

    def context_block(self) -> str:
        return (
            f"No curated source pack is available for region {self.region!r}. "
            "No region-specific official sources are wired in. Rely on the "
            "universal data spine where the contract permits it, and clearly "
            "label any figure you cannot ground as [INFERENCE]."
        )


class Engagement(BaseModel):
    """The brief: a region, an industry, a depth, and an output language."""

    region: str
    industry: str
    depth: str = "standard"
    language: str = "en"

    @property
    def slug(self) -> str:
        """A filesystem-safe id for this engagement's working directory."""
        industry = "-".join(self.industry.lower().split())
        return f"{self.region.lower()}-{industry}"


class ManagingPartner:
    """Lead agent that runs an engagement end to end."""

    def __init__(
        self,
        lead: LLM | None = None,
        worker: LLM | None = None,
        workdir: str | Path = "./engagements",
    ) -> None:
        self.lead = lead or LLM.lead()
        self.worker = worker or LLM.worker()
        self.workdir = Path(workdir)
        self.memory = EngagementMemory()
        # Set per run; carries the resolved source pack into task contracts.
        self._pack: object = None

    def _load_pack(self, region: str) -> object:
        """Resolve the region's source pack, degrading gracefully.

        ``source_packs.load_pack`` is the data engineer's responsibility. The
        orchestration core does not hard-depend on it: if the module is not yet
        present, or has no pack for this region, or fails to load one, we fall
        back to a :class:`_NullPack` so the engagement still runs with the
        universal spine and honest labelling. The import lives here, on the
        execution path, rather than at module top so that ``import quorum`` and
        the test suite never break on a missing data layer.
        """
        try:
            from .source_packs import load_pack
        except ImportError:
            return _NullPack(region)
        try:
            return load_pack(region)
        except Exception:
            # A missing or malformed pack must not sink the engagement; proceed
            # with the universal spine and a null pack for local context.
            return _NullPack(region)

    def load_crew(self, depth: str = "standard") -> list[Analyst]:
        """Staff the crew for a depth tier from the packaged ``crews.yaml``.

        ``crews.yaml`` is the source of truth for staffing: an ``analysts`` map
        defines each seat, and ``tiers.<depth>.roster`` lists the seats to run
        for that tier, in priority order. The roster is then capped at the
        tier's :data:`EFFORT` headcount and trimmed from the tail — the budget
        is enforced here, not requested in a prompt.
        """
        config = yaml.safe_load(_CREWS_PATH.read_text(encoding="utf-8")) or {}
        specs = config.get("analysts", {})

        def build(key: str) -> Analyst:
            spec = specs[key]
            return Analyst(
                key=key,
                role=spec["role"],
                section=spec["section"],
                skill=spec["skill"],
                tools=list(spec.get("tools", [])),
                # A seat with no declared phase is a phase-1 seat.
                phase=int(spec.get("phase", 1)),
                brief=str(spec.get("brief", "")).strip(),
            )

        tier = EFFORT.get(depth, EFFORT["standard"])
        roster = config.get("tiers", {}).get(depth, {}).get("roster")
        if roster is None:
            # No explicit tier roster: fall back to declaration order, skipping
            # the orchestration-only seat that is not a report section.
            roster = [k for k in specs if k != "engagement_manager"]
        return [build(key) for key in roster[: tier["max_analysts"]]]

    def scope(self, engagement: Engagement, crew: list[Analyst]) -> str:
        """Produce a MECE research plan and persist it to memory.

        The plan opens with a Scope Lock — the binding market definition,
        denominator basis, reference year, currency, geographic boundary, and
        the adjacent categories explicitly excluded — then names the sections
        the staffed crew will cover and how they divide the brief without
        overlap. It is stored under ``plans`` so a later run on the same market
        can be compared against it.
        """
        roster = "\n".join(f"- {a.section} ({a.role}, skill: {a.skill})" for a in crew)
        system = self._scope_system()
        prompt = (
            f"Engagement: {engagement.industry} in {engagement.region}, "
            f"depth {engagement.depth}.\n\n"
            f"Staffed sections:\n{roster}\n\n"
            "Write the research plan. It must open with a \"Scope Lock\" block "
            "fixing: the market definition and the denominator basis for any "
            "share or penetration figure; the reference year all figures anchor "
            "to; the currency; the geographic boundary; and the adjacent "
            "categories excluded, each with its reason. Where overlapping "
            "category framings exist (e.g. BEV-only versus NEV for electric "
            "vehicles), adjudicate explicitly which one every section uses."
        )
        plan = self.lead.complete(system=system, prompt=prompt, max_tokens=2048)
        self.memory.remember("plans", f"{engagement.slug}-{engagement.depth}", plan)
        return plan

    def _scope_system(self) -> str:
        """Build the scoping system prompt from the engagement-manager skill.

        Scoping is the ``mece-engagement-manager`` skill's job. Its body is
        loaded here so the plan is driven by the methodology, not a prompt baked
        into Python -- the skill file is the expert. If the skill is not
        installed, fall back to a terse built-in instruction so the engine still
        runs against a partial skill library.
        """
        from .skills_loader import load_skill

        instruction = (
            "Produce a MECE research plan. Open with a \"Scope Lock\" block "
            "(market definition and denominator basis, reference year, currency, "
            "geographic boundary, excluded adjacent categories with reasons), "
            "then state the central question and show how the staffed sections "
            "divide it with no gaps and no overlap. Be concise; this is a plan, "
            "not the report."
        )
        try:
            body = load_skill("mece-engagement-manager").body
        except (FileNotFoundError, ValueError):
            return (
                "You are the managing partner scoping a market-research "
                f"engagement. {instruction}"
            )
        return (
            "You are the managing partner scoping a market-research engagement. "
            "Apply the engagement-manager methodology below.\n\n"
            f"{body}\n\n{instruction}"
        )

    def _pack_context(self) -> str:
        """Render the source pack's context block for the engagement context.

        Uses the agreed ``SourcePack.context_block()`` surface, falling back to
        ``str(pack)`` if a pack predates that method so the orchestrator keeps
        working against an older data layer.
        """
        block = getattr(self._pack, "context_block", None)
        if callable(block):
            return block()
        return str(self._pack)

    def _contract(
        self,
        engagement: Engagement,
        analyst: Analyst,
        tier: dict[str, int],
        has_entry_plays: bool = False,
    ) -> TaskContract:
        """Build the four-element contract for one analyst.

        The contract's tool allowlist is the analyst's default tools intersected
        with what the active source pack can actually serve, plus the universal
        spine endpoints; ``web_search`` and ``memory_read`` are never gated by a
        pack. This keeps a contract from authorising a local source the region
        has no pack for.

        A seat-specific ``brief`` from ``crews.yaml`` is appended to the
        objective. Later-phase seats running the valuation skill additionally
        carry the named-plays mandate when a play-producing strategy seat ran
        in an earlier phase (``has_entry_plays``): they price the entry plays
        actually proposed, never a generic entrant. At depths where no strategy
        seat is staffed, the mandate degrades to market-level valuation, stated
        as such.
        """
        pack_quality = getattr(self._pack, "data_quality_score", "unknown")
        objective = (
            f"Produce the \"{analyst.section}\" section for a {engagement.depth} "
            f"engagement on {engagement.industry} in {engagement.region}. "
            f"Available data pack quality score: {pack_quality}. Write in "
            f"{engagement.language}."
        )
        if analyst.brief:
            objective += f" {analyst.brief}"
        if analyst.phase > 1 and analyst.skill == "valuation-analyst":
            if has_entry_plays:
                objective += (
                    " Value each named entry play proposed in the fact-checked "
                    "strategy sections of the engagement context separately. "
                    "Valuing a generic, undifferentiated entrant is prohibited. "
                    "If a play's profitability assumptions conflict with the "
                    "industry-structure diagnosis (e.g. assumed margins above "
                    "what the structure supports), reconcile the conflict "
                    "explicitly or mark the play down."
                )
            else:
                objective += (
                    " No strategy seat proposed named entry plays at this "
                    "depth, so keep the valuation at market level and say so "
                    "explicitly; do not construct a generic entrant's "
                    "economics."
                )
        output_format = (
            f"A markdown section titled \"{analyst.section}\", structured per your "
            "skill's output format. Every claim labeled [DATA] or [INFERENCE] "
            "with a 0.0-1.0 confidence score; figures sourced inline; tables "
            "where the methodology calls for them."
        )
        boundaries = (
            f"Write only the \"{analyst.section}\" section. Make at most "
            f"{tier['tool_calls']} tool calls. Do not duplicate other sections "
            "or draft an executive summary. Do not state figures the data pack "
            "cannot support without labeling them [INFERENCE]."
        )
        return TaskContract(
            objective=objective,
            output_format=output_format,
            tools=self._resolve_tools(analyst.tools),
            boundaries=boundaries,
        )

    def _resolve_tools(self, requested: list[str]) -> list[str]:
        """Filter an analyst's default tools against the active source pack.

        Universal spine endpoints and non-pack tools (``web_search``,
        ``memory_read``) are always available. ``local_context`` and any
        pack-specific tool name are kept only if the active pack actually serves
        them, so a contract never authorises a local source the region has no
        pack for. If the pack does not expose ``tool_names()``, leave the
        request untouched and let the spine arbitrate at call time.
        """
        always = {"worldbank", "imf", "web_search", "memory_read"}
        names = getattr(self._pack, "tool_names", None)
        if not callable(names):
            return list(requested)
        available = set(names())
        return [t for t in requested if t in always or t in available]

    async def _synthesis_with_retry(
        self, produce: Callable[[str], str], label: str, gates_dir: Path
    ) -> str:
        """Run one synthesis completion with a single bounded truncation retry.

        The adjudication draft and the final House View are load-bearing: a
        ruling cut mid-sentence loses its orders block or its Canonical
        figures table. ``produce`` takes a retry note and returns the
        completion; the first attempt runs with an empty note. If the output
        fails the :func:`_looks_truncated` heuristic, exactly one retry runs
        with a note telling the model the previous output was cut
        mid-sentence and to re-send the full artifact more compactly. If the
        retry is also truncated, a warning lands under ``gates/`` and the
        run continues with the longer of the two outputs; a documented
        defect beats a crashed engagement.
        """
        first = await asyncio.to_thread(produce, "")
        if not _looks_truncated(first):
            return first
        retry_note = (
            "NOTE: your previous attempt at this artifact was cut off "
            "mid-sentence by the output ceiling. Re-send the COMPLETE "
            "artifact, written more compactly — shorter prose, no repeated "
            "material — without dropping any required part."
        )
        retry = await asyncio.to_thread(produce, retry_note)
        if not _looks_truncated(retry):
            return retry
        best = retry if len(retry) >= len(first) else first
        (gates_dir / f"synthesis.{label}.truncation-warning.md").write_text(
            f"The {label.replace('-', ' ')} output appears to end mid-sentence "
            "after one bounded retry — both completions likely hit the "
            "synthesis output ceiling (QUORUM_SYNTHESIS_MAX_TOKENS). The "
            "longer completion is embedded as written; treat its tail as "
            "incomplete.\n",
            encoding="utf-8",
        )
        return best

    def _revision_contract(
        self,
        engagement: Engagement,
        analyst: Analyst,
        instruction: str,
        tier: dict[str, int],
    ) -> TaskContract:
        """Build the revision contract for one ordered seat.

        The objective binds the seat to the adjudication: revise the section
        under the ruling and the corrected canonical assumptions, rerun any
        model on the selected play's corrected inputs, do not re-argue the
        verdict, keep the [DATA]/[INFERENCE] discipline. The seat's original
        working paper, the adjudication draft, and the conflict list travel
        in the context the caller assembles — the contract carries the
        instruction itself.
        """
        objective = (
            f"Revise your \"{analyst.section}\" section for the "
            f"{engagement.depth} engagement on {engagement.industry} in "
            f"{engagement.region}, under the supervising partner's "
            "adjudication. Your revision order is: "
            f"{instruction} "
            "Rework the section against the adjudication's rulings and the "
            "corrected canonical assumptions it states (selected play, "
            "corrected SAM/SOM, segment, margins, unit costs): rerun your "
            "models and tables on the corrected inputs for the selected play "
            "rather than patching old numbers in place. The adjudication is "
            "binding — do not re-argue, soften, or hedge against its rulings. "
            f"Write in {engagement.language}."
        )
        output_format = (
            f"The complete revised \"{analyst.section}\" section, structured "
            "per your skill's output format — a full replacement, not a "
            "delta or an errata note. Every claim labeled [DATA] or "
            "[INFERENCE] with a 0.0-1.0 confidence score; figures sourced "
            "inline; tables where the methodology calls for them."
        )
        boundaries = (
            f"Write only the revised \"{analyst.section}\" section. Make at "
            f"most {tier['tool_calls']} tool calls. Do not dispute the "
            "adjudication's rulings or restate rejected plays except to note "
            "their rejection where your method requires it. Do not duplicate "
            "other sections or draft an executive summary. Do not state "
            "figures the data pack cannot support without labeling them "
            "[INFERENCE]."
        )
        return TaskContract(
            objective=objective,
            output_format=output_format,
            tools=self._resolve_tools(analyst.tools),
            boundaries=boundaries,
        )

    async def _run_revisions(
        self,
        engagement: Engagement,
        crew: list[Analyst],
        titled: dict[str, str],
        orders: dict[str, str],
        adjudication: str,
        conflicts: str,
        tier: dict[str, int],
        engagement_dir: Path,
        gates_dir: Path,
        scope_lock: str,
    ) -> dict[str, str]:
        """Execute the revision round and return the revised section map.

        Each revision order's section title is mapped back to its analyst
        seat (the inverse of the title map used downstream); the ordered
        seats are re-dispatched in parallel under revision contracts whose
        context carries the seat's original working paper in full, the
        adjudication draft, and the conflict list. Each revision is
        fact-checked against the Scope Lock and *replaces* the section in
        the returned map; the pre-revision draft is archived under
        ``gates/<key>.pre-revision.md`` so the audit trail keeps both states.
        An order naming a section no staffed seat owns (a trimmed roster, or
        a title the model misspelled beyond case/whitespace) is skipped and
        recorded under ``gates/`` rather than failing the run.
        """
        by_title = {a.section.strip().lower(): a for a in crew}
        ordered: list[tuple[Analyst, str]] = []
        seen_keys: set[str] = set()
        skipped: list[str] = []
        for title, instruction in orders.items():
            analyst = by_title.get(title.strip().lower())
            if analyst is None or analyst.section not in titled:
                skipped.append(title)
                continue
            if analyst.key in seen_keys:
                continue  # duplicate order for the same seat; first one wins
            seen_keys.add(analyst.key)
            ordered.append((analyst, instruction))
        if skipped:
            lines = "\n".join(
                f"- \"{title}\": no staffed seat owns this section at depth "
                f"{engagement.depth}; the order was recorded and skipped."
                for title in skipped
            )
            (gates_dir / "revision-orders.skipped.md").write_text(
                "Revision orders that could not be dispatched:\n" + lines + "\n",
                encoding="utf-8",
            )
        if not ordered:
            return titled

        # Archive the originals before any revision lands: the audit copy is
        # always the pre-revision draft, never a half-replaced intermediate.
        for analyst, _ in ordered:
            (gates_dir / f"{analyst.key}.pre-revision.md").write_text(
                titled[analyst.section], encoding="utf-8"
            )

        async def revise(analyst: Analyst, instruction: str) -> tuple[str, str, str]:
            contract = self._revision_contract(engagement, analyst, instruction, tier)
            context = (
                "## Your original working paper (the section under revision)\n"
                f"{titled[analyst.section]}\n\n"
                "## The supervising partner's adjudication (binding)\n"
                f"{adjudication}\n\n"
                "## Cross-section conflict scan (the record the adjudication "
                "ruled on)\n"
                f"{conflicts}"
            )
            draft = await asyncio.to_thread(analyst.run, contract, context, self.worker)
            findings = await asyncio.to_thread(
                quality.fact_check, draft, self.worker, scope_lock
            )
            return analyst.key, draft, findings

        results = await asyncio.gather(*(revise(a, i) for a, i in ordered))
        revised = dict(titled)
        for (analyst, _), (key, draft, findings) in zip(ordered, results):
            (engagement_dir / f"{key}.md").write_text(draft, encoding="utf-8")
            (gates_dir / f"{key}.revision.factcheck.md").write_text(
                findings, encoding="utf-8"
            )
            if _looks_truncated(draft):
                (gates_dir / f"{key}.revision.truncation-warning.md").write_text(
                    f"The revised working paper for the \"{analyst.section}\" "
                    "section appears to end mid-sentence — its final line "
                    "does not close like prose, a table row, a list item, or "
                    "a heading. The revision likely hit the worker output "
                    "ceiling (QUORUM_WORKER_MAX_TOKENS). The section is "
                    "embedded as written; treat its tail as incomplete.\n",
                    encoding="utf-8",
                )
            revised[analyst.section] = draft
        return revised

    def _arithmetic_fix_contract(
        self, engagement: Engagement, analyst: Analyst
    ) -> TaskContract:
        """Build the pin-point contract for one arithmetic correction.

        Issued when the deterministic arithmetic verifier finds that the
        valuation section's stated headline figures do not recompute from
        its own inputs, that a share comparison mixes denominators, or that
        an economic-sanity defect stands (an implied exit multiple above the
        section's own peer range; a mature margin above every comparable
        with no structural reason). The seat's job is narrow: align every
        stated EV, NPV, terminal-value, and share figure with the verified
        figures table that travels in the context, so the DCF table and the
        section's summary statements can be derived from one another, and
        answer each sanity defect the way the report names — a
        peer-anchored alternative terminal value with its NPV beside an
        out-of-range exit multiple; a comparable-anchored margin or a
        stated structural reason with lowered confidence for a margin
        premium. The analysis, the inputs, and the structure otherwise
        stand; only what the verification disputes (and the minimal wording
        around it) changes. No tool calls — a correction against a supplied
        table needs no research.
        """
        objective = (
            f"Apply an arithmetic correction to your \"{analyst.section}\" "
            f"section for the {engagement.depth} engagement on "
            f"{engagement.industry} in {engagement.region}. A deterministic "
            "recomputation of your section's own stated inputs found the "
            "discrepancies listed in the verification report below. The "
            "recomputed figures are authoritative: correct every EV, NPV, "
            "terminal-value, and share reference in the section — in the "
            "tables, the summary, and the prose alike — to match the "
            "verified figures table, so that the DCF table and the "
            "section's summary statements can be derived from one another. "
            "Where a share comparison mixes denominators, restate it on the "
            "single denominator the report names. Where the report finds "
            "the implied exit multiple above the section's own stated peer "
            "range, present — alongside the base figure — an alternative "
            "terminal value anchored at the peer median multiple and the "
            "NPV that terminal value produces, both with shown arithmetic. "
            "Where the report finds the mature margin above every stated "
            "comparable's current margin with no structural reason, either "
            "reduce the mature margin to the comparable anchor and rerun "
            "the affected figures, or state the concrete structural reason "
            "the analysis itself establishes and lower the affected "
            "confidence scores accordingly. Keep the section's "
            "inputs, structure, and analysis otherwise; do not re-derive "
            "cash flows or change assumptions the verification did not "
            "dispute. "
            f"Write in {engagement.language}."
        )
        output_format = (
            f"The complete \"{analyst.section}\" section with the figures "
            "corrected — a full replacement, not a delta or an errata note. "
            "Preserve every [DATA]/[INFERENCE] label and confidence score; "
            "keep tables where the methodology calls for them."
        )
        boundaries = (
            f"Write only the \"{analyst.section}\" section. Change only the "
            "figures the verification report disputes (and the minimal "
            "surrounding wording a correction forces). Make no tool calls. "
            "Do not change the valuation's inputs, assumptions, or "
            "conclusions beyond what the corrected figures themselves "
            "require, and do not introduce a figure the verified figures "
            "table does not carry — except the peer-anchored alternative "
            "terminal value and NPV the report itself orders, which must "
            "show their arithmetic from the section's stated inputs."
        )
        return TaskContract(
            objective=objective,
            output_format=output_format,
            tools=[],
            boundaries=boundaries,
        )

    async def _run_arithmetic_gate(
        self,
        engagement: Engagement,
        crew: list[Analyst],
        titled: dict[str, str],
        engagement_dir: Path,
        gates_dir: Path,
        scope_lock: str,
        tag: str = "",
    ) -> tuple[dict[str, str], str, bool | None]:
        """Run the deterministic arithmetic gate over the valuation section.

        Returns the (possibly corrected) section map, the final verification
        report's markdown — empty when the gate was skipped — and the final
        verification status: ``True`` when the last verify pass found no
        discrepancy, ``False`` when discrepancies remain after the one
        correction round, ``None`` when the gate was skipped. The status is
        what the limitations appendix states; it reflects the *final* pass,
        never an intermediate artifact.
        The pipeline: extract the valuation section's stated figures to
        strict JSON with the lead model (one bounded retry on an
        unparseable output), recompute the DCF and the SOM chain in pure
        Python (:func:`quorum.quality.verify`), and when the recomputation
        contradicts the stated figures, dispatch one pin-point correction to
        the valuation seat with the verified figures as the authoritative
        record, fact-check it, swap it in (the pre-correction text archived
        under ``gates/``), and verify the corrected text once more. The
        final report lands as ``gates/arithmetic.md``; a section still
        failing after the correction round additionally lands a
        ``gates/arithmetic.unresolved.md`` marker, the limitation note
        records it, and the verified figures prevail over the prose. A
        section with no recomputable build (no DCF — e.g. a market-level
        valuation at scan depth) skips the gate with a one-line record under
        ``gates/`` instead of failing the run. ``tag`` suffixes the gate's
        artifact names so a post-revision re-run does not overwrite the
        first run's audit trail.
        """
        seat = next(
            (
                a
                for a in crew
                if a.skill == "valuation-analyst" and a.section in titled
            ),
            None,
        )
        suffix = f".{tag}" if tag else ""
        stale_note = (
            " Any earlier verification table in this bundle describes a "
            "superseded version of the section and is not authoritative."
            if tag
            else ""
        )
        if seat is None:
            (gates_dir / f"arithmetic{suffix}.skipped.md").write_text(
                "Arithmetic verification skipped: no valuation section was "
                f"staffed at this depth.{stale_note}\n",
                encoding="utf-8",
            )
            return titled, "", None

        async def extract(text: str) -> dict | None:
            raw = await asyncio.to_thread(
                quality.extract_financials, text, self.lead
            )
            fin = quality.parse_financials(raw)
            if fin is not None:
                return fin
            retry = await asyncio.to_thread(
                quality.extract_financials,
                text,
                self.lead,
                "NOTE: your previous output could not be parsed as the "
                "requested JSON object. Re-send ONLY the JSON object, with "
                "no prose and no markdown fences.",
            )
            return quality.parse_financials(retry)

        fin = await extract(titled[seat.section])
        if fin is None:
            (gates_dir / f"arithmetic{suffix}.skipped.md").write_text(
                "Arithmetic verification skipped: the valuation section "
                "states no recomputable cash-flow build (no DCF series and "
                f"no claimed headline value could be extracted).{stale_note}\n",
                encoding="utf-8",
            )
            return titled, "", None
        report = quality.verify(fin)
        if not report.recomputed:
            (gates_dir / f"arithmetic{suffix}.skipped.md").write_text(
                "Arithmetic verification skipped: the valuation section's "
                "stated figures do not include the inputs (cash-flow series "
                f"and discount rate) a recomputation needs.{stale_note}\n",
                encoding="utf-8",
            )
            return titled, "", None

        if not report.ok:
            # One pin-point correction against the verified figures, through
            # the revision mechanism: re-dispatch the valuation seat under a
            # narrow contract, fact-check the correction, archive the
            # pre-correction text, swap the correction in — then verify the
            # corrected text once more. The recomputed figures, not the
            # prose, are authoritative throughout.
            (gates_dir / f"{seat.key}.pre-arithmetic-fix{suffix}.md").write_text(
                titled[seat.section], encoding="utf-8"
            )
            (gates_dir / f"arithmetic{suffix}.pre-fix.md").write_text(
                report.markdown() + "\n", encoding="utf-8"
            )
            contract = self._arithmetic_fix_contract(engagement, seat)
            context = (
                "## Your current section text (the text under correction)\n"
                f"{titled[seat.section]}\n\n"
                "## Arithmetic verification report (the authoritative "
                "figures)\n"
                f"{report.markdown()}"
            )
            draft = await asyncio.to_thread(seat.run, contract, context, self.worker)
            findings = await asyncio.to_thread(
                quality.fact_check, draft, self.worker, scope_lock
            )
            (engagement_dir / f"{seat.key}.md").write_text(draft, encoding="utf-8")
            (gates_dir / f"{seat.key}.arithmetic-fix{suffix}.factcheck.md").write_text(
                findings, encoding="utf-8"
            )
            titled = dict(titled)
            titled[seat.section] = draft

            recheck = await extract(draft)
            if recheck is not None:
                rechecked = quality.verify(recheck)
                if rechecked.recomputed:
                    report = rechecked
            if not report.ok:
                (gates_dir / f"arithmetic{suffix}.unresolved.md").write_text(
                    "The valuation section's stated figures still contradict "
                    "the deterministic recomputation after one correction "
                    "round; the verified figures table prevails over the "
                    "prose. The discrepancies:\n"
                    + "\n".join(f"- {item}" for item in report.discrepancies)
                    + "\n",
                    encoding="utf-8",
                )

        markdown = report.markdown()
        (gates_dir / "arithmetic.md").write_text(markdown + "\n", encoding="utf-8")
        return titled, markdown, report.ok

    def _stale_fix_contract(
        self, engagement: Engagement, analyst: Analyst
    ) -> TaskContract:
        """Build the pin-point contract for one stale-figure fix.

        Narrower than a revision contract by design: the canonical record is
        final and the section's analysis already stands under the rulings —
        the seat's only job is to replace the listed superseded values with
        the current canonical values where they are stated as if current.
        Re-running models, re-arguing conclusions, or restructuring the
        section is out of bounds, and so are tool calls — a pure text
        correction needs no research, so the contract grants none.
        """
        objective = (
            f"Apply a pin-point correction to your \"{analyst.section}\" "
            f"section for the {engagement.depth} engagement on "
            f"{engagement.industry} in {engagement.region}. The stale-figure "
            "sweep below lists superseded values your section still states "
            "as if current. Update each listed old value to the current "
            "canonical value and leave everything else unchanged — same "
            "structure, same prose, same tables, same conclusions. Where a "
            "listed value sits inside a sentence or table cell, change only "
            "what the correction touches. Do not re-run models, re-argue "
            "conclusions, or restate the canonical record beyond the listed "
            f"corrections. Write in {engagement.language}."
        )
        output_format = (
            f"The complete \"{analyst.section}\" section with the listed "
            "values corrected — a full replacement identical to the current "
            "text except for the corrections, not a delta or an errata note. "
            "Preserve every [DATA]/[INFERENCE] label and confidence score."
        )
        boundaries = (
            f"Write only the \"{analyst.section}\" section. Change only the "
            "values the stale-figure list names for this section (and the "
            "minimal surrounding wording a correction forces). Make no tool "
            "calls. Do not add, drop, or reorder content; do not revisit the "
            "analysis."
        )
        return TaskContract(
            objective=objective,
            output_format=output_format,
            tools=[],
            boundaries=boundaries,
        )

    async def _run_stale_fixes(
        self,
        engagement: Engagement,
        crew: list[Analyst],
        titled: dict[str, str],
        entries: list[dict[str, str]],
        house: str,
        engagement_dir: Path,
        gates_dir: Path,
        scope_lock: str,
    ) -> dict[str, str]:
        """Execute one round of pin-point stale-figure fixes; return the map.

        Mirrors :meth:`_run_revisions` mechanically — map each named section
        title back to its analyst seat, re-dispatch the named seats in
        parallel, fact-check each fix, swap it in — but under the narrow
        stale-fix contract, with the original archived as
        ``gates/<key>.pre-stale-fix.md``. An entry naming a section no
        staffed seat owns is recorded under ``gates/`` alongside the listing
        and skipped. Exactly one round runs, by design: a value the fix misses
        is recorded as a limitation, not chased — the Canonical figures
        table prevails over the body either way.
        """
        by_title = {a.section.strip().lower(): a for a in crew}
        per_seat: dict[str, list[dict[str, str]]] = {}
        skipped: list[str] = []
        for entry in entries:
            analyst = by_title.get(entry["section"].strip().lower())
            if analyst is None or analyst.section not in titled:
                skipped.append(entry["section"])
                continue
            per_seat.setdefault(analyst.key, []).append(entry)
        if skipped:
            lines = "\n".join(
                f"- \"{title}\": no staffed seat owns this section at depth "
                f"{engagement.depth}; the stale entry was recorded and skipped."
                for title in sorted(set(skipped))
            )
            (gates_dir / "stale_figures.skipped.md").write_text(
                "Stale-figure entries that could not be dispatched:\n" + lines + "\n",
                encoding="utf-8",
            )
        if not per_seat:
            return titled

        seats = {a.key: a for a in crew}
        for key in per_seat:
            analyst = seats[key]
            (gates_dir / f"{key}.pre-stale-fix.md").write_text(
                titled[analyst.section], encoding="utf-8"
            )

        async def fix(analyst: Analyst, own: list[dict[str, str]]) -> tuple[str, str, str]:
            contract = self._stale_fix_contract(engagement, analyst)
            rows = "\n".join(
                f"- old: {e['old']} -> current: {e['current']}"
                + (f" (where: {e['location']})" if e["location"] else "")
                for e in own
            )
            context = (
                "## Your current section text (the text under correction)\n"
                f"{titled[analyst.section]}\n\n"
                "## Stale figures to correct in this section\n"
                f"{rows}\n\n"
                "## The canonical House View (the authoritative record)\n"
                f"{house}"
            )
            draft = await asyncio.to_thread(analyst.run, contract, context, self.worker)
            findings = await asyncio.to_thread(
                quality.fact_check, draft, self.worker, scope_lock
            )
            return analyst.key, draft, findings

        results = await asyncio.gather(
            *(fix(seats[key], own) for key, own in per_seat.items())
        )
        fixed = dict(titled)
        for key, draft, findings in results:
            analyst = seats[key]
            (engagement_dir / f"{key}.md").write_text(draft, encoding="utf-8")
            (gates_dir / f"{key}.stale-fix.factcheck.md").write_text(
                findings, encoding="utf-8"
            )
            fixed[analyst.section] = draft
        return fixed

    async def run(self, engagement: Engagement, out: str | Path = "report.md") -> Path:
        """Run the full engagement and return the path to the final report.

        v0.6.1 pipeline: scope (with Scope Lock) -> phases in ascending
        order, each one running its analysts in parallel and fact-checking
        them before the next phase starts, with the checked earlier-phase
        sections in the later contracts' context -> deterministic arithmetic
        gate over the valuation section (extract the stated figures,
        recompute the DCF, the SOM chain, and the economic-sanity checks in
        pure Python, dispatch one pin-point correction when the prose
        contradicts the recomputation, verify the correction once more; the
        verified-figures table lands under gates/ and binds the rest of the
        run, and the gate's final status — not any intermediate artifact —
        is what the limitations appendix states) -> synthesis loop
        (conflict scan ->
        adjudication draft with revision orders -> parallel revision round,
        each ordered seat rewriting its section under the rulings, the
        original archived and the revision fact-checked and swapped in; a
        rewritten valuation section is arithmetic-verified again -> final
        House View against the revised body, with the Canonical figures
        table, the verified figures authoritative over prose) -> red team,
        attacking the revised sections *and* the final ruling -> one
        bounded amendment pass over the House View's canonical record when
        the memo proves a canonical-grade error (the pre-amendment text
        archived under gates/) -> one stale-figure sweep over the final
        canonical record when anything was replaced upstream, turning
        leftover superseded values into a single round of pin-point fixes
        (pre-fix texts archived under gates/, anything the round misses
        recorded as a limitation) -> the editor writes only the editorial
        blocks, bound to the selected play, the Canonical figures of the
        House View as it now stands, and the verified figures -> the report
        is assembled in code as three parts, embedding the revised
        sections, the (possibly amended) House View, and the red-team memo
        verbatim.
        """
        tier = EFFORT.get(engagement.depth, EFFORT["standard"])

        # Resolve the engagement directory: workdir/<timestamp>-<slug>.
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M")
        engagement_dir = self.workdir / f"{stamp}-{engagement.slug}"
        engagement_dir.mkdir(parents=True, exist_ok=True)

        # Resolve the country source pack via the data engineer's interface,
        # degrading to a null pack if the data layer or this region is absent.
        # The orchestration core stays runnable regardless.
        self._pack = self._load_pack(engagement.region)

        # Staff the crew for this depth tier (roster and headcount cap applied),
        # then group it by dispatch phase, ascending. The headcount cap trims
        # the roster tail *before* the grouping: if every seat of a later phase
        # falls past the cap (possible at scan if the budget is tightened),
        # that phase simply does not run — expected behaviour, not an error.
        crew = self.load_crew(engagement.depth)
        phases: dict[int, list[Analyst]] = {}
        for analyst in crew:
            phases.setdefault(analyst.phase, []).append(analyst)

        # Recall a prior report on this market and inline a truncated excerpt.
        prior = self.memory.recall("reports", engagement.slug)
        prior_note = ""
        if prior:
            prior_note = (
                "\n\n## Prior engagement (for continuity, not to be copied)\n"
                f"{prior[:_MEMORY_RECALL_LIMIT]}"
            )

        # The plan opens with the Scope Lock; it is injected into every
        # contract's context in full — only the prior-engagement excerpt above
        # is ever truncated, so the Scope Lock always survives intact.
        plan = self.scope(engagement, crew)
        scope_lock = _scope_lock_block(plan)
        pack_context = self._pack_context()
        base_context = f"## Research plan\n{plan}\n\n## Data pack\n{pack_context}{prior_note}"

        gates_dir = engagement_dir / "gates"
        gates_dir.mkdir(exist_ok=True)

        # Dispatch one phase of analysts concurrently. Each runs in a worker
        # thread because the provider SDKs are synchronous; the contract bounds
        # each one. Working papers keep analyst keys as filenames (internal
        # artifacts); the deliverable uses section titles only. Drafts whose
        # last line looks cut mid-sentence get a truncation warning under
        # gates/ — the heuristic runs at landing, where the full draft exists.
        async def run_phase(
            analysts: list[Analyst], phase_context: str, has_entry_plays: bool
        ) -> dict[str, str]:
            async def run_analyst(analyst: Analyst) -> tuple[str, str]:
                contract = self._contract(engagement, analyst, tier, has_entry_plays)
                draft = await asyncio.to_thread(analyst.run, contract, phase_context, self.worker)
                (engagement_dir / f"{analyst.key}.md").write_text(draft, encoding="utf-8")
                if _looks_truncated(draft):
                    (gates_dir / f"{analyst.key}.truncation-warning.md").write_text(
                        "The working paper for the "
                        f"\"{analyst.section}\" section appears to end "
                        "mid-sentence — its final line does not close like "
                        "prose, a table row, a list item, or a heading. The "
                        "draft likely hit the worker output ceiling "
                        "(QUORUM_WORKER_MAX_TOKENS). The section is embedded "
                        "as written; treat its tail as incomplete.\n",
                        encoding="utf-8",
                    )
                return analyst.key, draft

            return dict(await asyncio.gather(*(run_analyst(a) for a in analysts)))

        # Fact-check one phase's sections in parallel, against the Scope Lock.
        # A draft flagged as truncated carries an inline note so the checker
        # audits it as an incomplete artifact rather than a finished one.
        async def run_checks(drafts: dict[str, str]) -> None:
            async def check(key: str, text: str) -> tuple[str, str]:
                to_check = text
                if (gates_dir / f"{key}.truncation-warning.md").exists():
                    to_check = (
                        "NOTE TO CHECKER: this draft appears to be truncated "
                        "mid-sentence (it likely hit the worker output "
                        "ceiling). Audit what is present and flag the "
                        "truncation itself as a finding.\n\n" + text
                    )
                findings = await asyncio.to_thread(
                    quality.fact_check, to_check, self.worker, scope_lock
                )
                return key, findings

            results = dict(await asyncio.gather(*(check(k, v) for k, v in drafts.items())))
            for key, text in results.items():
                (gates_dir / f"{key}.factcheck.md").write_text(text, encoding="utf-8")

        # Run the phases in ascending order: parallel dispatch, then the
        # fact-check gate, then the next phase with the checked sections so
        # far in its context. Whether a play-producing strategy seat ran in
        # an *earlier* phase governs each phase's valuation mandate: price
        # named plays when they exist, state a market-level valuation when
        # they cannot (the scan roster staffs no strategy seat).
        sections: dict[str, str] = {}
        dispatched: list[Analyst] = []
        for index, phase in enumerate(sorted(phases)):
            analysts = phases[phase]
            if index == 0:
                phase_context = base_context
            else:
                digest = _checked_sections_digest(dispatched, sections, phase)
                phase_context = (
                    f"{base_context}\n\n"
                    "## Fact-checked sections from earlier phases\n"
                    "The sections below are complete and fact-checked. Anchor "
                    "your analysis to them; do not re-derive them.\n\n"
                    f"{digest}"
                )
            has_entry_plays = any(a.key in _ENTRY_PLAY_KEYS for a in dispatched)
            phase_sections = await run_phase(analysts, phase_context, has_entry_plays)
            await run_checks(phase_sections)
            sections.update(phase_sections)
            dispatched.extend(analysts)

        # From here on, sections are addressed by their human-readable titles
        # (in roster order); analyst keys never reach the synthesis gate, the
        # red team, the editor, or the deliverable.
        titled = {a.section: sections[a.key] for a in crew if a.key in sections}

        # Deterministic arithmetic gate over the fact-checked valuation
        # section, before the synthesis loop reads it: extract the stated
        # figures, recompute the DCF and the SOM chain in pure Python, and
        # when the prose contradicts the recomputation, dispatch one
        # pin-point correction and verify the corrected text once more. A
        # numeric conflict is settled by re-running the arithmetic, never by
        # a downstream ruling's assertion. The verified-figures table
        # (gates/arithmetic.md) is mandatory input to the final House View
        # and the editor; a section with no recomputable build skips the
        # gate with a one-line record under gates/.
        titled, arithmetic_md, arithmetic_ok = await self._run_arithmetic_gate(
            engagement, crew, titled, engagement_dir, gates_dir, scope_lock
        )

        # Synthesis loop, step 1+2: scan the checked sections for
        # cross-section conflicts, then have the supervising partner write the
        # adjudication draft — a single selected play, rulings on every
        # conflict, the adjudication table, the volume bridge, and a closing
        # REVISION ORDERS block naming every section the rulings overturned.
        # Both artifacts land under gates/; the adjudication draft is the
        # input to the revision round, never the deliverable's House View.
        conflicts = await asyncio.to_thread(quality.find_conflicts, titled, self.lead)
        (gates_dir / "conflicts.md").write_text(conflicts, encoding="utf-8")
        adjudication = await self._synthesis_with_retry(
            lambda note: quality.adjudicate(titled, conflicts, self.lead, retry_note=note),
            "adjudication",
            gates_dir,
        )
        (gates_dir / "adjudication.md").write_text(adjudication, encoding="utf-8")

        # Step 3: the revision round. Parse the orders, map each ordered
        # title back to its analyst seat, and re-dispatch the ordered seats in
        # parallel under revision contracts — rewrite the section under the
        # rulings and the corrected assumptions, no re-arguing the verdict.
        # Each revision is fact-checked and replaces the original section;
        # the pre-revision draft is archived under gates/ for the audit trail.
        orders = quality.parse_revision_orders(adjudication)
        if orders:
            pre_revision = titled
            titled = await self._run_revisions(
                engagement,
                crew,
                titled,
                orders,
                adjudication,
                conflicts,
                tier,
                engagement_dir,
                gates_dir,
                scope_lock,
            )
            # If the revision round rewrote the valuation section the gate
            # verified, its figures moved: re-run the arithmetic gate over
            # the revision (one extract/verify pass, one correction round if
            # needed) so the verified-figures table the House View and the
            # editor receive describes the text that actually ships.
            # Distinctly tagged artifacts keep the first run's audit trail
            # intact. The section watched is the one the gate verifies: the
            # first staffed valuation-analyst seat's.
            gate_section = next(
                (
                    a.section
                    for a in crew
                    if a.skill == "valuation-analyst" and a.section in titled
                ),
                None,
            )
            if gate_section is not None and titled.get(gate_section) != pre_revision.get(
                gate_section
            ):
                # The re-run's table replaces the first run's downstream —
                # even when the re-run skipped (the revised text yielded no
                # recomputable build): a table describing superseded text
                # must never be injected as authoritative. The same goes for
                # the final status the limitations appendix states.
                titled, arithmetic_md, arithmetic_ok = await self._run_arithmetic_gate(
                    engagement,
                    crew,
                    titled,
                    engagement_dir,
                    gates_dir,
                    scope_lock,
                    tag="post-revision",
                )

        # Step 4: the final House View, written against the REVISED body.
        # It opens with the Canonical figures table the rest of the report
        # must follow, and lands under gates/ as the deliverable's ruling.
        house = await self._synthesis_with_retry(
            lambda note: quality.final_house_view(
                titled,
                adjudication,
                self.lead,
                retry_note=note,
                arithmetic=arithmetic_md,
            ),
            "house-view",
            gates_dir,
        )
        (gates_dir / "house_view.md").write_text(house, encoding="utf-8")

        # Red team over the revised sections and the final House View — the
        # ruling is attacked alongside the analysis it rules on. The memo
        # (including the Decision gates part, now checked for gate-set
        # coherence and required to apply that check to its own gate list)
        # is embedded verbatim in the deliverable.
        dissent = await asyncio.to_thread(quality.challenge, titled, self.lead, house)
        (gates_dir / "red_team.md").write_text(dissent, encoding="utf-8")

        # Post-red-team amendment of the canonical record. The revision loop
        # runs before the red team, so a canonical-grade error the memo
        # catches (pricing basis, a derivation that does not recompute, a
        # gate table ignoring its own coherence check) would otherwise have
        # no write-back channel — flagged in Part III, never fixed in Part I.
        # amend_canonical asks that one narrow question; on a NO-AMENDMENT
        # answer the House View passes through byte-identical. Exactly ONE
        # round runs, by design: the red team is not re-run against the
        # amended text, so amendment cannot oscillate with the challenge —
        # the memo and the amendment note both stay on the record, and the
        # editor's reconciliation points the affected ACCEPT entries at the
        # amendments.
        amended = await self._synthesis_with_retry(
            lambda note: quality.amend_canonical(house, dissent, self.lead, retry_note=note),
            "amendment",
            gates_dir,
        )
        if amended != house:
            (gates_dir / "house_view.pre-amendment.md").write_text(house, encoding="utf-8")
            house = amended
            (gates_dir / "house_view.md").write_text(house, encoding="utf-8")

        # Stale-figure sweep over the final canonical record. A real v0.4.1
        # deliverable carried a volume bridge still computing on a target the
        # adjudication had superseded — the Canonical table was right, the
        # body was not. The sweep runs only when something was actually
        # replaced (a revision round ran, or the red team forced an
        # amendment); a run where nothing changed has nothing to be stale
        # against, so the scan tier and the clean path pay nothing extra.
        # The sweep is not wrapped in the truncation-retry guard on purpose:
        # its clean answer is the bare NO STALE FIGURES sentinel, which the
        # mid-sentence heuristic would misread as a cut-off draft, and a
        # truncated *list* degrades gracefully — every parsed entry is
        # independently actionable.
        stale_fixed_count = 0
        stale_resolved: bool | None = None
        if orders or (gates_dir / "house_view.pre-amendment.md").exists():
            sweep = await asyncio.to_thread(quality.stale_figures, titled, house, self.lead)
            entries = quality.resolve_stale(sweep)
            if entries:
                (gates_dir / "stale_figures.md").write_text(sweep, encoding="utf-8")
                titled = await self._run_stale_fixes(
                    engagement,
                    crew,
                    titled,
                    entries,
                    house,
                    engagement_dir,
                    gates_dir,
                    scope_lock,
                )
                stale_fixed_count = len(
                    list(gates_dir.glob("*.pre-stale-fix.md"))
                )
                # Exactly one fix round runs; verify the listed old values
                # are gone with a deterministic literal check (no second
                # model pass). Anything still present — or any entry whose
                # section no staffed seat owns — is recorded as a limitation:
                # the Canonical figures table prevails over the body.
                leftovers = _stale_leftovers(entries, titled)
                stale_resolved = not leftovers
                if leftovers:
                    (gates_dir / "stale_figures.unresolved.md").write_text(
                        "Stale figures identified by the sweep that remain "
                        "after the one pin-point fix round (the Canonical "
                        "figures table prevails over these passages):\n"
                        + "\n".join(
                            f"- {e['old']} (superseded by {e['current']}) in "
                            f"\"{e['section']}\""
                            for e in leftovers
                        )
                        + "\n",
                        encoding="utf-8",
                    )

        # The editor authors only the executive summary, the reconciliation of
        # the red team's arguments, and the scenario analysis — with the House
        # View (as amended, when the red team forced a canonical correction)
        # binding the summary to the selected play and the conflict scan
        # informing the baseline ruling in the reconciliation.
        blocks = await asyncio.to_thread(
            quality.compile_report,
            engagement,
            titled,
            dissent,
            self.lead,
            house,
            conflicts,
            arithmetic_md,
        )

        # Assemble the deliverable in code: revised sections, the final House
        # View, and the red-team memo are embedded verbatim, so no model
        # output ceiling can truncate the body and no rewrite can drop the
        # dissent. Limitations gain a line when the ruling itself records an
        # unresolved conflict — the record stays in the bundle either way.
        report = report_output.assemble_report(
            meta=report_output.ReportMeta(
                region=engagement.region,
                industry=engagement.industry,
                depth=engagement.depth,
                engagement_id=engagement_dir.name,
            ),
            title=(
                f"{engagement.industry.title()} in "
                f"{report_output.display_region(engagement.region)} — Market Report"
            ),
            scope_summary=report_output.scope_summary_line(plan),
            executive_summary=blocks.executive_summary,
            house_view=house,
            sections=[
                report_output.ReportSection(heading=title, body=text)
                for title, text in titled.items()
            ],
            scenarios=blocks.scenarios,
            reconciliation=blocks.reconciliation,
            dissent=dissent,
            limitations=_limitations_note(
                gates_dir,
                rulings=f"{adjudication}\n{house}",
                final_arithmetic_ok=arithmetic_ok,
                stale_resolved=stale_resolved,
                stale_fixed_count=stale_fixed_count,
            ),
        )

        report_path = engagement_dir / "report.md"
        report_path.write_text(report, encoding="utf-8")

        # Persist the report to memory and copy it to the requested output path.
        self.memory.remember("reports", engagement.slug, report)
        out_path = Path(out)
        out_path.write_text(report, encoding="utf-8")
        return out_path


def _checked_sections_digest(
    earlier: list[Analyst], sections: dict[str, str], phase: int
) -> str:
    """Render the checked earlier-phase sections for a later contract's context.

    The sections that the entering ``phase`` must anchor to (per
    :data:`_FULL_TEXT_KEYS_BY_PHASE` — entering phase 2 that is the fact base:
    sizing, structure, demand; entering phase 3 it is the strategy sections
    plus sizing) are included in full. Every other earlier section contributes
    its title and a one-line gist, keeping the context proportional without
    hiding what was covered. A phase with no declared selection inherits the
    deepest one declared at or below it.
    """
    full_keys = _FULL_TEXT_KEYS_BY_PHASE.get(phase)
    if full_keys is None:
        declared = [p for p in sorted(_FULL_TEXT_KEYS_BY_PHASE) if p <= phase]
        full_keys = _FULL_TEXT_KEYS_BY_PHASE[declared[-1]] if declared else ()
    parts: list[str] = []
    for analyst in earlier:
        text = sections.get(analyst.key)
        if text is None:
            continue
        if analyst.key in full_keys:
            parts.append(f"### {analyst.section}\n{text}")
        else:
            parts.append(f"### {analyst.section}\n{_first_line(text)}")
    return "\n\n".join(parts)


def _looks_truncated(draft: str) -> bool:
    """Heuristically decide whether a worker draft was cut mid-sentence.

    A draft that ran out of output budget typically stops inside a sentence.
    The check looks at the last non-blank line: if it neither ends in a
    sentence-final character (:data:`_SENTENCE_ENDINGS`, covering Latin and
    CJK punctuation plus closing quotes and brackets) nor is structural
    markdown that legitimately ends without one — a table row, a horizontal
    rule, a list item, a heading, or a fence — the draft is flagged. The
    heuristic prefers false negatives: a missed truncation costs a warning,
    a false alarm costs reader trust in the warnings.
    """
    lines = [line.rstrip() for line in draft.splitlines() if line.strip()]
    if not lines:
        return False
    last = lines[-1].strip()
    # Structural markdown lines legitimately end without sentence punctuation.
    if last.startswith(("#", "|", "---", "***", "___", "```", "===")):
        return False
    if last.endswith("|"):
        return False
    # A line ending on closed emphasis ("...**", "...`") was deliberately
    # closed by the author; a hard token cut almost never lands exactly after
    # a closing marker. Strip the markers to judge the character beneath, and
    # accept either ending.
    if last.endswith(("**", "__", "`", "~~")):
        return False
    trimmed = last.rstrip("*_~` ")
    if not trimmed or trimmed.endswith(_SENTENCE_ENDINGS):
        return False
    # A confidence-score trailer ("[DATA] 0.9") closes a labeled claim.
    if _CONFIDENCE_TRAILER_RE.search(trimmed):
        return False
    # A short list item ("- CNY 12bn") is a complete thought without a period;
    # only flag list items long enough to plausibly be a cut sentence.
    if last.startswith(("-", "*", "+")) and len(last) <= 60:
        return False
    if last[0].isdigit() and "." in last[:4] and len(last) <= 60:
        return False
    return True


def _first_line(text: str) -> str:
    """Return the first substantive (non-heading) line of a section."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped
    return "(section drafted; see working papers)"


def _stale_leftovers(
    entries: list[dict[str, str]], sections: dict[str, str]
) -> list[dict[str, str]]:
    """Return the sweep entries whose old value still survives after the fix.

    Deterministic, model-free verification of the one-round stale fix: an
    entry counts as a leftover when its named section is absent from the
    fixed map (the seat was not staffed, so the fix never ran) or when the
    old value, compared with whitespace collapsed, still appears in the
    section's post-fix text. Best-effort by design — a sweep that quoted the
    old value loosely can slip past the literal check — and the cost of a
    miss is one absent limitation line, never a wrong figure prevailing: the
    Canonical figures table outranks the body by rule either way.
    """
    by_title = {title.strip().lower(): text for title, text in sections.items()}

    def _squash(text: str) -> str:
        return " ".join(text.split()).lower()

    leftovers: list[dict[str, str]] = []
    for entry in entries:
        body = by_title.get(entry["section"].strip().lower())
        if body is None or _squash(entry["old"]) in _squash(body):
            leftovers.append(entry)
    return leftovers


def _scope_lock_block(plan: str) -> str:
    """Extract the Scope Lock block from the research plan, verbatim.

    The block runs from the "Scope Lock" heading to the next heading. If the
    plan carries no such block (e.g. a fallback scoping prompt was used), the
    head of the plan is returned so the fact-checker still has a scope baseline
    to audit against.
    """
    lines = plan.splitlines()
    start = None
    for i, line in enumerate(lines):
        if "scope lock" in line.strip().lstrip("#*- ").lower():
            start = i
            break
    if start is None:
        return plan[:2000]
    collected = [lines[start]]
    for line in lines[start + 1 :]:
        if line.strip().startswith("#"):
            break
        collected.append(line)
    return "\n".join(collected).strip()


def _limitations_note(
    gates_dir: Path,
    rulings: str = "",
    final_arithmetic_ok: bool | None = None,
    stale_resolved: bool | None = None,
    stale_fixed_count: int = 0,
) -> str:
    """Compose the limitations appendix in client language.

    Assembled deterministically: it points the reader at the quality record
    rather than asking a model to summarize its own caveats. Two disciplines
    govern the wording. First, the deliverable's own no-internal-identifiers
    rule applies to this code as much as to any model output: the appendix
    names no engine directory, no file name, and no working-paper naming
    pattern — review artifacts are referred to collectively as the
    engagement bundle's working-paper archive. Second, status statements
    describe the *final* state of the engagement, supplied by the caller —
    ``final_arithmetic_ok`` is the last verification pass's result (``True``
    clean, ``False`` discrepancies remain, ``None`` when no recomputable
    build existed to verify) and ``stale_resolved`` is whether the one
    stale-figure fix round cleared every listed value (``None`` when no
    stale value was found) — never inferred from the existence of an
    intermediate archive file, which records that an event *happened*, not
    how it *ended*. The archive globs below are used only to count events
    (sections revised, corrections issued, outputs truncated); every
    "still"/"remains" statement comes from the explicit final-state
    parameters. ``rulings`` is the combined adjudication and final House
    View text: when it records an unresolved conflict (the word
    "unresolved" appears), a line says so.
    """
    findings = sorted(p.name for p in gates_dir.glob("*.factcheck.md"))
    revisions = sorted(p.name for p in gates_dir.glob("*.pre-revision.md"))
    lines = [
        "Per-section fact-check findings are preserved in the engagement "
        "bundle's working-paper archive and were not silently resolved: "
        f"{len(findings)} set(s) of findings accompany this report.",
        "The cross-section conflict scan, the supervising partner's "
        "adjudication (with its revision orders), and the final House View "
        "are preserved in the same archive; conflicts the rulings did not "
        "resolve remain on the record there.",
        "The red team's full memo is reproduced in the Dissenting View; the "
        "Reconciliation section records, argument by argument, what was "
        "accepted (and how the conclusion moved) and what was rebutted.",
        "Scenario probabilities, where stated, are subjective judgments, not "
        "measured frequencies.",
    ]
    if revisions:
        lines.append(
            f"{len(revisions)} section(s) were revised under the supervising "
            "partner's rulings after the conflict scan; each pre-revision "
            "draft is preserved in the working-paper archive alongside the "
            "revision's own fact-check findings."
        )
    if (gates_dir / "house_view.pre-amendment.md").exists():
        lines.append(
            "The House View's canonical record was amended once after the "
            "red-team review (see its \"Amendments after red-team review\" "
            "section); the pre-amendment text is preserved in the "
            "working-paper archive."
        )
    arithmetic_fixes = sorted(p.name for p in gates_dir.glob("*.pre-arithmetic-fix*.md"))
    if arithmetic_fixes:
        correction_line = (
            "The valuation's stated figures were checked against a "
            "deterministic recomputation of the section's own inputs and "
            f"received {len(arithmetic_fixes)} pin-point correction(s); "
            "each pre-correction text is preserved in the working-paper "
            "archive alongside the verification record."
        )
        if final_arithmetic_ok is True:
            correction_line += (
                " The final verification of the section as published found "
                "no remaining discrepancy."
            )
        elif final_arithmetic_ok is None:
            correction_line += (
                " The section as finally published stated no recomputable "
                "build, so the published text carries no verification "
                "verdict."
            )
        lines.append(correction_line)
    if final_arithmetic_ok is False:
        lines.append(
            "The valuation section as published still carries findings "
            "against the deterministic recomputation after the one "
            "correction round; the recomputed figures in the verification "
            "record prevail over any prose claim, and the remaining "
            "findings are itemised there."
        )
    if stale_fixed_count:
        stale_line = (
            f"{stale_fixed_count} section(s) received a pin-point "
            "stale-figure fix after the canonical record was finalised "
            "(superseded values updated to the Canonical figures, nothing "
            "else changed); each pre-fix text is preserved in the "
            "working-paper archive alongside the sweep listing."
        )
        if stale_resolved is True:
            stale_line += " The fix round cleared every listed value."
        lines.append(stale_line)
    if stale_resolved is False:
        lines.append(
            "Some identified superseded values remain in the body after "
            "the one pin-point fix round; the Canonical figures table "
            "prevails over those passages, and the remaining entries are "
            "itemised in the working-paper archive."
        )
    if "unresolved" in rulings.lower():
        lines.append(
            "Unresolved conflicts are retained on the record in the "
            "engagement bundle's conflict scan."
        )
    truncated = sorted(p.name for p in gates_dir.glob("*.truncation-warning.md"))
    if truncated:
        lines.append(
            f"{len(truncated)} working text(s) appear to end mid-sentence "
            "(an output-length limit was likely reached); each carries a "
            "warning in the working-paper archive. Treat the affected "
            "texts' closing passages as incomplete."
        )
    return "\n\n".join(lines)
