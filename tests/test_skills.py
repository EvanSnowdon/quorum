"""Tests for the analyst-skills library and its loader.

These assert the library's *structural* contract — every canonical skill exists,
each ``SKILL.md`` has a well-formed frontmatter whose ``name`` matches its
directory and carries a ``description`` and a ``license``, and each ships a
``reference/`` folder — and that :func:`quorum.skills_loader.list_skills` agrees
with what is on disk. No model is involved; this is pure filesystem and YAML.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from .conftest import CANONICAL_SKILLS

# Same frontmatter split the loader uses: frontmatter in group 1, body in group
# 2, with re.S so a body containing '---' rules does not end the match early.
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.S)


def _read_frontmatter(skill_md: Path) -> dict:
    """Parse and return the YAML frontmatter mapping of a SKILL.md."""
    text = skill_md.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    assert match is not None, f"{skill_md} has no '---' frontmatter block"
    front = yaml.safe_load(match.group(1))
    assert isinstance(front, dict), f"{skill_md} frontmatter is not a mapping"
    return front


def test_all_canonical_skills_have_a_directory(skills_dir: Path) -> None:
    """Each of the fifteen canonical skills is a directory under the library."""
    for name in sorted(CANONICAL_SKILLS):
        assert (skills_dir / name).is_dir(), f"missing skill directory: {name}"


def test_canonical_skill_count_is_fifteen() -> None:
    """The canonical set is exactly fifteen skills (guards the constant itself)."""
    assert len(CANONICAL_SKILLS) == 15


@pytest.mark.parametrize("name", sorted(CANONICAL_SKILLS))
def test_skill_has_well_formed_frontmatter(skills_dir: Path, name: str) -> None:
    """SKILL.md frontmatter: name matches the directory, has description + license."""
    skill_md = skills_dir / name / "SKILL.md"
    assert skill_md.is_file(), f"missing SKILL.md for {name}"

    front = _read_frontmatter(skill_md)

    assert str(front.get("name", "")).strip() == name, (
        f"{name}: frontmatter name {front.get('name')!r} does not match directory"
    )

    description = str(front.get("description", "")).strip()
    assert description, f"{name}: frontmatter has no non-empty description"

    license_value = str(front.get("license", "")).strip()
    assert license_value, f"{name}: frontmatter has no license"


@pytest.mark.parametrize("name", sorted(CANONICAL_SKILLS))
def test_skill_has_reference_directory(skills_dir: Path, name: str) -> None:
    """Each skill ships a non-empty ``reference/`` directory."""
    reference = skills_dir / name / "reference"
    assert reference.is_dir(), f"{name}: missing reference/ directory"
    assert any(reference.iterdir()), f"{name}: reference/ directory is empty"


def test_list_skills_returns_the_fifteen_canonical(skills_dir: Path) -> None:
    """``list_skills()`` enumerates exactly the fifteen canonical skills.

    The loader resolves its skills root from the bundled library by default;
    these structural tests run against the in-repo library either way, so we
    assert against the canonical set directly.
    """
    from quorum.skills_loader import list_skills

    found = set(list_skills())
    assert found == set(CANONICAL_SKILLS), (
        f"list_skills() mismatch: missing={CANONICAL_SKILLS - found}, "
        f"extra={found - CANONICAL_SKILLS}"
    )


@pytest.mark.parametrize("name", sorted(CANONICAL_SKILLS))
def test_load_skill_round_trips(name: str) -> None:
    """``load_skill`` returns a Skill with the expected name and a non-empty body."""
    from quorum.skills_loader import load_skill

    skill = load_skill(name)
    assert skill.name == name
    assert skill.description.strip(), f"{name}: loaded description is empty"
    assert skill.body.strip(), f"{name}: loaded body is empty"


def test_skill_descriptions_covers_every_skill() -> None:
    """``skill_descriptions()`` returns a non-empty description for all fifteen."""
    from quorum.skills_loader import skill_descriptions

    descriptions = skill_descriptions()
    assert set(descriptions) == set(CANONICAL_SKILLS)
    assert all(text.strip() for text in descriptions.values())
