"""The engagement manager: scope, dispatch, assemble.

:class:`ManagingPartner` is the lead agent. It reads the crew roster, scopes a
MECE research plan (opening with a binding Scope Lock), dispatches analysts in
two phases under task contracts — the strategic picture first, then valuation
and critique against the fact-checked phase-1 sections — routes the drafts
through the quality gates, and assembles the final report in code, embedding
the checked sections and the red-team memo verbatim. Analysts run concurrently
within a phase and never talk to each other; all coordination flows through
this class and the engagement directory.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

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

# Phase-1 sections whose full text is carried into phase-2 contracts. These are
# the strategy, structure, and sizing seats — the inputs valuation and critique
# must anchor to. Other phase-1 sections enter as title plus a one-line gist.
_PHASE_TWO_FULL_TEXT_KEYS = ("strategy_choice", "industry_structure", "market_sizing")

# Phase-1 seats whose remit includes proposing named entry plays. If none of
# them is staffed (e.g. a trimmed roster), phase-2 valuation runs at market
# level instead of pricing plays that were never written.
_ENTRY_PLAY_KEYS = ("strategy_choice", "firm_power")


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
        objective. Phase-2 seats running the valuation skill additionally carry
        the named-plays mandate when a play-producing strategy seat ran in
        phase 1 (``has_entry_plays``): they price the entry plays actually
        proposed, never a generic entrant. At depths where no strategy seat is
        staffed, the mandate degrades to market-level valuation, stated as such.
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
        if analyst.phase == 2 and analyst.skill == "valuation-analyst":
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

    async def run(self, engagement: Engagement, out: str | Path = "report.md") -> Path:
        """Run the full engagement and return the path to the final report.

        v0.2 pipeline: scope (with Scope Lock) -> phase-1 analysts in parallel
        -> fact-check phase 1 -> phase-2 analysts in parallel, with the checked
        phase-1 sections in context -> fact-check phase 2 -> red team -> the
        editor writes only the editorial blocks -> the report is assembled in
        code, embedding the checked sections and the red-team memo verbatim.
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
        # then split it by dispatch phase. The headcount cap trims the roster
        # tail *before* the split: if every phase-2 seat falls past the cap
        # (possible at scan if the budget is tightened), phase 2 simply does not
        # run — expected behaviour, not an error.
        crew = self.load_crew(engagement.depth)
        phase_one = [a for a in crew if a.phase != 2]
        phase_two = [a for a in crew if a.phase == 2]

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
        context = f"## Research plan\n{plan}\n\n## Data pack\n{pack_context}{prior_note}"

        gates_dir = engagement_dir / "gates"
        gates_dir.mkdir(exist_ok=True)

        # Whether a play-producing strategy seat is staffed in phase 1 governs
        # the phase-2 valuation mandate: price named plays when they exist,
        # state a market-level valuation when they cannot.
        has_entry_plays = any(a.key in _ENTRY_PLAY_KEYS for a in phase_one)

        # Dispatch one phase of analysts concurrently. Each runs in a worker
        # thread because the provider SDKs are synchronous; the contract bounds
        # each one. Working papers keep analyst keys as filenames (internal
        # artifacts); the deliverable uses section titles only.
        async def run_phase(analysts: list[Analyst], phase_context: str) -> dict[str, str]:
            async def run_analyst(analyst: Analyst) -> tuple[str, str]:
                contract = self._contract(engagement, analyst, tier, has_entry_plays)
                draft = await asyncio.to_thread(analyst.run, contract, phase_context, self.worker)
                (engagement_dir / f"{analyst.key}.md").write_text(draft, encoding="utf-8")
                return analyst.key, draft

            return dict(await asyncio.gather(*(run_analyst(a) for a in analysts)))

        # Fact-check one phase's sections in parallel, against the Scope Lock.
        async def run_checks(drafts: dict[str, str]) -> None:
            async def check(key: str, text: str) -> tuple[str, str]:
                findings = await asyncio.to_thread(
                    quality.fact_check, text, self.worker, scope_lock
                )
                return key, findings

            results = dict(await asyncio.gather(*(check(k, v) for k, v in drafts.items())))
            for key, text in results.items():
                (gates_dir / f"{key}.factcheck.md").write_text(text, encoding="utf-8")

        # Phase 1: the strategic picture — sizing, structure, named entry plays.
        sections = await run_phase(phase_one, context)
        await run_checks(sections)

        # Phase 2: valuation and critique, dispatched only after phase 1 is
        # checked, with the checked phase-1 sections in context so they price
        # and critique the *specific* strategies on the table.
        if phase_two:
            digest = _phase_one_digest(phase_one, sections)
            phase_two_context = (
                f"{context}\n\n"
                "## Fact-checked phase-1 sections\n"
                "The sections below are complete and fact-checked. Anchor your "
                "analysis to them; do not re-derive them.\n\n"
                f"{digest}"
            )
            phase_two_sections = await run_phase(phase_two, phase_two_context)
            await run_checks(phase_two_sections)
            sections.update(phase_two_sections)

        # From here on, sections are addressed by their human-readable titles
        # (in roster order); analyst keys never reach the red team, the editor,
        # or the deliverable.
        titled = {a.section: sections[a.key] for a in crew if a.key in sections}

        # Red team over the combined sections; its memo (including the Decision
        # gates part) is embedded verbatim in the deliverable.
        dissent = await asyncio.to_thread(quality.challenge, titled, self.lead)
        (gates_dir / "red_team.md").write_text(dissent, encoding="utf-8")

        # The editor authors only the executive summary, the reconciliation of
        # the red team's arguments, and the scenario analysis.
        blocks = await asyncio.to_thread(
            quality.compile_report, engagement, titled, dissent, self.lead
        )

        # Assemble the deliverable in code: checked sections and the red-team
        # memo are embedded verbatim, so no model output ceiling can truncate
        # the body and no rewrite can drop the dissent.
        report = report_output.assemble_report(
            meta=report_output.ReportMeta(
                region=engagement.region,
                industry=engagement.industry,
                depth=engagement.depth,
                engagement_id=engagement_dir.name,
            ),
            title=f"{engagement.industry.title()} in {engagement.region} — Market Report",
            scope_summary=report_output.scope_summary_line(plan),
            executive_summary=blocks.executive_summary,
            sections=[
                report_output.ReportSection(heading=title, body=text)
                for title, text in titled.items()
            ],
            scenarios=blocks.scenarios,
            reconciliation=blocks.reconciliation,
            dissent=dissent,
            limitations=_limitations_note(gates_dir),
        )

        report_path = engagement_dir / "report.md"
        report_path.write_text(report, encoding="utf-8")

        # Persist the report to memory and copy it to the requested output path.
        self.memory.remember("reports", engagement.slug, report)
        out_path = Path(out)
        out_path.write_text(report, encoding="utf-8")
        return out_path


def _phase_one_digest(phase_one: list[Analyst], sections: dict[str, str]) -> str:
    """Render the checked phase-1 sections for a phase-2 contract's context.

    The strategy, structure, and sizing sections are included in full — phase-2
    seats price the named entry plays against them. Every other phase-1 section
    contributes its title and a one-line gist, keeping the context proportional
    without hiding what was covered.
    """
    parts: list[str] = []
    for analyst in phase_one:
        text = sections.get(analyst.key)
        if text is None:
            continue
        if analyst.key in _PHASE_TWO_FULL_TEXT_KEYS:
            parts.append(f"### {analyst.section}\n{text}")
        else:
            parts.append(f"### {analyst.section}\n{_first_line(text)}")
    return "\n\n".join(parts)


def _first_line(text: str) -> str:
    """Return the first substantive (non-heading) line of a section."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped
    return "(section drafted; see working papers)"


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


def _limitations_note(gates_dir: Path) -> str:
    """Compose the limitations appendix from the gate artifacts on disk.

    Assembled deterministically: it points the reader at the per-section
    fact-check findings and the reconciliation of the red team's arguments
    rather than asking a model to summarize its own caveats.
    """
    findings = sorted(p.name for p in gates_dir.glob("*.factcheck.md"))
    lines = [
        "Per-section fact-check findings are preserved in the engagement "
        "bundle under `gates/` and were not silently resolved: "
        f"{len(findings)} findings file(s) accompany this report.",
        "The red team's full memo is reproduced in the Dissenting View; the "
        "Reconciliation section records, argument by argument, what was "
        "accepted (and how the conclusion moved) and what was rebutted.",
        "Scenario probabilities, where stated, are subjective judgments, not "
        "measured frequencies.",
    ]
    return "\n\n".join(lines)
