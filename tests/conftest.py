"""Shared pytest fixtures and import-path setup.

Two jobs:

1. **Import path.** The package lives under ``src/`` (``src/quorum``). If the
   suite is run without an editable install (``pip install -e .``), that
   directory is not on ``sys.path``. We add it here so ``import quorum`` works
   either way — the tests are designed to run from a bare checkout in CI as well
   as from an installed environment.

2. **Placeholder environment.** The provider clients read API keys from the
   environment. None of these tests make a network call, but constructing an
   :class:`~quorum.llm.LLM` (or importing code that resolves provider defaults)
   should never fail merely because no key is set. We seed dummy keys and pin the
   provider so the suite is hermetic and order-independent.

No test in this suite requires network access or a real model.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"

# Prepend src/ so `import quorum` resolves to the in-tree package even without an
# editable install. Idempotent: guarded so repeated collection does not stack it.
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Also make the repo root importable so `import evals` and `import protocols`
# resolve when the suite runs from a bare checkout.
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


@pytest.fixture(autouse=True)
def _placeholder_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Seed dummy provider credentials so no test trips on a missing key.

    Autouse and function-scoped: every test gets a clean, predictable provider
    environment, and changes never leak between tests.
    """
    monkeypatch.setenv("QUORUM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-placeholder-not-a-real-key")
    monkeypatch.setenv("OPENAI_API_KEY", "test-placeholder-not-a-real-key")


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Absolute path to the repository root."""
    return _REPO_ROOT


@pytest.fixture(scope="session")
def skills_dir(repo_root: Path) -> Path:
    """Absolute path to the bundled ``analyst-skills`` library."""
    return repo_root / "analyst-skills"


# The fifteen canonical methodology skills. Shared across tests so the roster and
# the on-disk library are checked against the same authoritative list.
CANONICAL_SKILLS: frozenset[str] = frozenset(
    {
        "five-forces-analyst",
        "value-chain-analyst",
        "jtbd-disruption-analyst",
        "seven-powers-analyst",
        "good-strategy-critic",
        "playing-to-win-analyst",
        "blue-ocean-analyst",
        "crossing-the-chasm-analyst",
        "pestel-analyst",
        "tam-sam-som-analyst",
        "ansoff-analyst",
        "three-horizons-analyst",
        "pyramid-editor",
        "valuation-analyst",
        "mece-engagement-manager",
    }
)


@pytest.fixture(scope="session")
def canonical_skills() -> frozenset[str]:
    """The fifteen canonical skill names, as a frozenset."""
    return CANONICAL_SKILLS
