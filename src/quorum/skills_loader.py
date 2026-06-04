"""Loader for the methodology ``SKILL.md`` files.

Each analyst is a directory under ``analyst-skills/`` holding a single
``SKILL.md`` with a YAML frontmatter block followed by the skill body. This
module locates that directory, parses a skill, and exposes progressive
disclosure: callers read ``name``/``description`` at planning time and only
pull the full ``body`` (or a ``reference/...`` file) when a skill is actually
dispatched.

The frontmatter is split with a single regular expression and parsed with
``yaml.safe_load``. A naive line-by-line ``split(":")`` would choke on the
multi-line ``description`` blocks and on bodies that themselves contain ``---``
rules, so it is deliberately avoided.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

# Captures the YAML frontmatter (group 1) and the body (group 2). re.S lets the
# body span lines and contain its own '---' rules without terminating the match.
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.S)


def _skills_dir() -> Path:
    """Resolve the skills root.

    ``QUORUM_SKILLS_DIR`` wins if set; otherwise the bundled ``analyst-skills``
    directory at the repository root is used. From ``src/quorum/<module>.py``
    that root is ``parents[2]``.
    """
    override = os.getenv("QUORUM_SKILLS_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parents[2] / "analyst-skills"


SKILLS_DIR = _skills_dir()


@dataclass
class Skill:
    """A parsed ``SKILL.md``: frontmatter metadata plus the methodology body."""

    name: str
    description: str
    body: str
    base_dir: Path

    def reference(self, rel: str) -> str:
        """Read a progressive-disclosure file relative to the skill directory.

        Skills keep supporting material (worked examples, source notes) under a
        ``reference/`` subfolder and link to it from the body. The body is
        loaded up front; these files are pulled only when the analyst follows
        the link.
        """
        path = (self.base_dir / rel).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Reference file not found for skill {self.name!r}: {path}")
        return path.read_text(encoding="utf-8")


def _parse_skill(text: str, base_dir: Path) -> Skill:
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        raise ValueError(f"SKILL.md in {base_dir} is missing a YAML frontmatter block.")

    front = yaml.safe_load(match.group(1)) or {}
    if not isinstance(front, dict):
        raise ValueError(f"SKILL.md frontmatter in {base_dir} did not parse to a mapping.")

    body = match.group(2).strip()
    name = str(front.get("name", base_dir.name)).strip()
    description = str(front.get("description", "")).strip()
    return Skill(name=name, description=description, body=body, base_dir=base_dir)


def load_skill(name: str) -> Skill:
    """Load a single skill by its directory name (e.g. ``five-forces-analyst``)."""
    path = SKILLS_DIR / name / "SKILL.md"
    if not path.is_file():
        raise FileNotFoundError(
            f"No SKILL.md for {name!r} under {SKILLS_DIR}. "
            "Set QUORUM_SKILLS_DIR or install the analyst-skills library."
        )
    return _parse_skill(path.read_text(encoding="utf-8"), path.parent)


def list_skills() -> list[str]:
    """Return the names of available skills, sorted.

    A skill is any immediate subdirectory of :data:`SKILLS_DIR` that contains a
    ``SKILL.md``.
    """
    if not SKILLS_DIR.is_dir():
        raise FileNotFoundError(
            f"Skills directory not found: {SKILLS_DIR}. "
            "Set QUORUM_SKILLS_DIR or install the analyst-skills library."
        )
    names = [
        child.name
        for child in SKILLS_DIR.iterdir()
        if child.is_dir() and (child / "SKILL.md").is_file()
    ]
    return sorted(names)


def skill_descriptions() -> dict[str, str]:
    """Return ``{name: description}`` for every available skill.

    This reads only the frontmatter of each ``SKILL.md`` -- never the body --
    so the orchestrator can route work across the whole library for a few
    hundred tokens. The full body is pulled lazily, per skill, at dispatch time
    via :func:`load_skill`.
    """
    descriptions: dict[str, str] = {}
    for name in list_skills():
        try:
            descriptions[name] = load_skill(name).description
        except (FileNotFoundError, ValueError):
            # A malformed or half-written skill should not sink routing for the
            # rest of the library; skip it and let the dispatch path surface the
            # concrete error if that skill is actually selected.
            continue
    return descriptions
