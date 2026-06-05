"""Quorum: an open-source AI consulting firm.

The package ships two layers. Layer 1 is the methodology analyst skill library
under ``analyst-skills/``. Layer 2 is the engagement engine in this package: an
orchestrator-worker system that turns a ``region x industry x depth`` brief into
a sourced, fact-checked market report.

The two public entry points are :class:`Engagement` (the resolved brief) and
:class:`ManagingPartner` (the orchestrator that runs it). They are exported
lazily through ``__getattr__`` so that ``import quorum`` stays cheap and does
not eagerly pull in pydantic, the orchestrator, and the provider stack — code
that only needs ``__version__`` should not pay for the whole engine.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "0.2.0"

__all__ = ["Engagement", "ManagingPartner", "__version__"]

if TYPE_CHECKING:  # type checkers and IDEs resolve these without the runtime cost
    from .orchestrator import Engagement, ManagingPartner


def __getattr__(name: str) -> Any:
    if name in ("Engagement", "ManagingPartner"):
        from . import orchestrator

        return getattr(orchestrator, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
