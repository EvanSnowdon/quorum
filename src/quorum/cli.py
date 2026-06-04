"""Command-line entry point: ``quorum --region ... --industry ...``."""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

from .orchestrator import Engagement, ManagingPartner


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="quorum",
        description="Run a Quorum engagement: a sourced, fact-checked market report.",
    )
    parser.add_argument("--region", required=True, help="Region or country (e.g. CN, US, EU).")
    parser.add_argument(
        "--industry", required=True, help="Industry to analyze (e.g. 'electric vehicles')."
    )
    parser.add_argument(
        "--depth",
        default="standard",
        choices=["scan", "standard", "due_diligence"],
        help="Compute tier; trades cost against rigor. Default: standard.",
    )
    parser.add_argument(
        "--language", default="en", help="Report output language (ISO 639-1). Default: en."
    )
    parser.add_argument(
        "--out", default="report.md", help="Path to write the final report. Default: report.md."
    )
    parser.add_argument(
        "--format",
        dest="fmt",
        default="markdown",
        choices=["markdown", "json"],
        help="Output format for the final report. Default: markdown.",
    )
    parser.add_argument(
        "--workdir",
        default="./engagements",
        help="Directory for engagement bundles. Default: ./engagements.",
    )

    models = parser.add_argument_group(
        "model selection",
        "Pick any provider/model per run. Flags override QUORUM_* environment "
        "variables and .env. The 'openai' provider drives any OpenAI-compatible "
        "endpoint (DeepSeek, Qwen, Kimi, vLLM, Ollama, ...) via --base-url.",
    )
    models.add_argument(
        "--provider",
        choices=["anthropic", "openai"],
        help="LLM provider. Default: anthropic (or QUORUM_PROVIDER).",
    )
    models.add_argument(
        "--model",
        help="Model for both roles (e.g. claude-sonnet-4-6, gpt-4o, deepseek-chat).",
    )
    models.add_argument(
        "--lead-model",
        help="Override the lead model only (engagement manager, red team, editor).",
    )
    models.add_argument(
        "--worker-model",
        help="Override the worker model only (the parallel analysts).",
    )
    models.add_argument(
        "--base-url",
        help="OpenAI-compatible base URL (e.g. https://api.deepseek.com or "
        "http://localhost:11434/v1 for Ollama).",
    )
    return parser.parse_args(argv)


def _apply_model_flags(args: argparse.Namespace) -> None:
    """Map model-selection flags onto the QUORUM_* environment variables.

    The engine reads model configuration exclusively from the environment
    (see :mod:`quorum.llm`), so the CLI translates flags into the same
    variables. Set after ``load_dotenv`` so a flag always beats a .env entry.
    """
    mapping = {
        "QUORUM_PROVIDER": args.provider,
        "QUORUM_MODEL": args.model,
        "QUORUM_LEAD_MODEL": args.lead_model,
        "QUORUM_WORKER_MODEL": args.worker_model,
        "QUORUM_BASE_URL": args.base_url,
    }
    for key, value in mapping.items():
        if value:
            os.environ[key] = value


def main(argv: list[str] | None = None) -> None:
    """Parse arguments, run the engagement, and report where the output landed."""
    # Load .env if present; the provider SDKs read API keys from the environment.
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    args = _parse_args(argv)
    _apply_model_flags(args)
    engagement = Engagement(
        region=args.region,
        industry=args.industry,
        depth=args.depth,
        language=args.language,
    )
    partner = ManagingPartner(workdir=args.workdir)
    out_path = asyncio.run(partner.run(engagement, out=args.out))

    report = Path(out_path).read_text(encoding="utf-8")
    final_path = _export(report, args.fmt, str(out_path))
    print(f"Report written to {final_path} ({len(report.split())} words).")


def _export(report_md: str, fmt: str, path: str) -> str:
    """Apply the requested output format to the rendered report.

    The exporter lives in the data/output layer (``output.export_report``),
    which the engine engineer does not own. The orchestrator already wrote a
    markdown file to ``path``; for plain markdown that file is the deliverable.
    For other formats we hand off to ``export_report`` if it is installed,
    degrading to the markdown file (and a warning) rather than failing the run
    if the output layer is absent. The import is kept off the core path so a
    missing output module never breaks ``import quorum`` or the engine.
    """
    if fmt == "markdown":
        return path
    try:
        from .output import export_report
    except ImportError:
        print(f"Warning: output layer unavailable; wrote markdown to {path} instead of {fmt}.")
        return path
    try:
        return export_report(report_md, fmt, path)
    except Exception as exc:  # pragma: no cover - depends on the output layer
        print(f"Warning: export to {fmt} failed ({exc}); markdown remains at {path}.")
        return path


if __name__ == "__main__":
    main()
