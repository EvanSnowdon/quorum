"""The engagement manager: scope, dispatch, assemble.

:class:`ManagingPartner` is the lead agent. It reads the crew roster, scopes a
MECE research plan, dispatches a parallel team of analysts under task
contracts, routes the drafts through the quality gates, and writes the final
report. Analysts run concurrently and never talk to each other; all
coordination flows through this class and the engagement directory.
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

        The plan names the sections the staffed crew will cover and how they
        divide the brief without overlap. It is stored under ``plans`` so a
        later run on the same market can be compared against it.
        """
        roster = "\n".join(f"- {a.section} ({a.role}, skill: {a.skill})" for a in crew)
        system = self._scope_system()
        prompt = (
            f"Engagement: {engagement.industry} in {engagement.region}, "
            f"depth {engagement.depth}.\n\n"
            f"Staffed sections:\n{roster}\n\n"
            "Write the research plan."
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
            "Produce a MECE research plan: state the central question, then show "
            "how the staffed sections divide it with no gaps and no overlap. Be "
            "concise; this is a plan, not the report."
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

    def _contract(self, engagement: Engagement, analyst: Analyst, tier: dict[str, int]) -> TaskContract:
        """Build the four-element contract for one analyst.

        The contract's tool allowlist is the analyst's default tools intersected
        with what the active source pack can actually serve, plus the universal
        spine endpoints; ``web_search`` and ``memory_read`` are never gated by a
        pack. This keeps a contract from authorising a local source the region
        has no pack for.
        """
        pack_quality = getattr(self._pack, "data_quality_score", "unknown")
        objective = (
            f"Produce the \"{analyst.section}\" section for a {engagement.depth} "
            f"engagement on {engagement.industry} in {engagement.region}. "
            f"Available data pack quality score: {pack_quality}. Write in "
            f"{engagement.language}."
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
        """Run the full engagement and return the path to the final report."""
        tier = EFFORT.get(engagement.depth, EFFORT["standard"])

        # Resolve the engagement directory: workdir/<timestamp>-<slug>.
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M")
        engagement_dir = self.workdir / f"{stamp}-{engagement.slug}"
        engagement_dir.mkdir(parents=True, exist_ok=True)

        # Resolve the country source pack via the data engineer's interface,
        # degrading to a null pack if the data layer or this region is absent.
        # The orchestration core stays runnable regardless.
        self._pack = self._load_pack(engagement.region)

        # Staff the crew for this depth tier (roster and headcount cap applied).
        crew = self.load_crew(engagement.depth)

        # Recall a prior report on this market and inline a truncated excerpt.
        prior = self.memory.recall("reports", engagement.slug)
        prior_note = ""
        if prior:
            prior_note = (
                "\n\n## Prior engagement (for continuity, not to be copied)\n"
                f"{prior[:_MEMORY_RECALL_LIMIT]}"
            )

        plan = self.scope(engagement, crew)
        pack_context = self._pack_context()
        context = f"## Research plan\n{plan}\n\n## Data pack\n{pack_context}{prior_note}"

        # Dispatch analysts concurrently. Each runs in a worker thread because
        # the provider SDKs are synchronous; the contract bounds each one.
        async def run_analyst(analyst: Analyst) -> tuple[str, str]:
            contract = self._contract(engagement, analyst, tier)
            draft = await asyncio.to_thread(analyst.run, contract, context, self.worker)
            (engagement_dir / f"{analyst.key}.md").write_text(draft, encoding="utf-8")
            return analyst.key, draft

        results = await asyncio.gather(*(run_analyst(a) for a in crew))
        sections = dict(results)

        # Fact-check each section, also in parallel.
        async def check(key: str, text: str) -> tuple[str, str]:
            findings = await asyncio.to_thread(quality.fact_check, text, self.worker)
            return key, findings

        findings = dict(await asyncio.gather(*(check(k, v) for k, v in sections.items())))
        gates_dir = engagement_dir / "gates"
        gates_dir.mkdir(exist_ok=True)
        for key, text in findings.items():
            (gates_dir / f"{key}.factcheck.md").write_text(text, encoding="utf-8")

        # Red team over the combined sections, then editorial compilation —
        # both on the lead model.
        dissent = await asyncio.to_thread(quality.challenge, sections, self.lead)
        (gates_dir / "red_team.md").write_text(dissent, encoding="utf-8")

        report = await asyncio.to_thread(
            quality.compile_report, engagement, sections, dissent, self.lead
        )

        report_path = engagement_dir / "report.md"
        report_path.write_text(report, encoding="utf-8")

        # Persist the report to memory and copy it to the requested output path.
        self.memory.remember("reports", engagement.slug, report)
        out_path = Path(out)
        out_path.write_text(report, encoding="utf-8")
        return out_path
