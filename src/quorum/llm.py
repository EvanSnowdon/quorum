"""Model-agnostic completion client.

A single :class:`LLM` wraps whichever provider the environment selects so the
rest of the engine never imports a provider SDK directly. Two roles are in
play across the firm — a *lead* model for the engagement manager and the chief
editor, and a *worker* model for the methodology experts and the first two
quality gates — exposed as the :meth:`LLM.lead` and :meth:`LLM.worker`
factories.

Configuration is entirely environment-driven:

``QUORUM_PROVIDER``
    ``anthropic`` (default) or ``openai``. The ``openai`` provider also drives
    any OpenAI-compatible endpoint (vLLM, Ollama's compat server, etc.) via
    ``QUORUM_BASE_URL``.
``QUORUM_MODEL``
    Single override applied to both roles. Takes precedence over the per-role
    defaults but not over the per-role overrides below.
``QUORUM_LEAD_MODEL`` / ``QUORUM_WORKER_MODEL``
    Per-role overrides; the most specific setting wins.
``QUORUM_BASE_URL``
    OpenAI-compatible base URL. Ignored by the Anthropic provider.

Provider SDKs are imported lazily inside :meth:`complete` so that ``import
quorum`` and the test suite work without ``anthropic`` or ``openai`` installed.
"""

from __future__ import annotations

import os

_ANTHROPIC_LEAD_DEFAULT = "claude-opus-4-6"
_ANTHROPIC_WORKER_DEFAULT = "claude-sonnet-4-6"
_OPENAI_LEAD_DEFAULT = "gpt-4o"
_OPENAI_WORKER_DEFAULT = "gpt-4o-mini"


def _provider() -> str:
    provider = os.getenv("QUORUM_PROVIDER", "anthropic").strip().lower()
    if provider not in ("anthropic", "openai"):
        raise RuntimeError(
            f"Unknown QUORUM_PROVIDER {provider!r}; expected 'anthropic' or 'openai'."
        )
    return provider


class LLM:
    """A configured handle to one provider/model pair.

    Construct directly when you already know the model name, or use the
    :meth:`lead` / :meth:`worker` factories to resolve the role default and the
    environment overrides in one step.
    """

    def __init__(self, model: str, provider: str | None = None) -> None:
        self.provider = (provider or _provider()).strip().lower()
        self.model = model

    @classmethod
    def lead(cls) -> "LLM":
        """Return the lead model (engagement manager, chief editor)."""
        provider = _provider()
        default = _ANTHROPIC_LEAD_DEFAULT if provider == "anthropic" else _OPENAI_LEAD_DEFAULT
        model = os.getenv("QUORUM_LEAD_MODEL") or os.getenv("QUORUM_MODEL") or default
        return cls(model=model, provider=provider)

    @classmethod
    def worker(cls) -> "LLM":
        """Return the worker model (experts, fact-check and red-team gates)."""
        provider = _provider()
        default = _ANTHROPIC_WORKER_DEFAULT if provider == "anthropic" else _OPENAI_WORKER_DEFAULT
        model = os.getenv("QUORUM_WORKER_MODEL") or os.getenv("QUORUM_MODEL") or default
        return cls(model=model, provider=provider)

    def complete(
        self,
        system: str,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> str:
        """Run a single-turn completion and return the assistant text.

        Raises :class:`RuntimeError` with a readable message on a missing SDK,
        a missing API key, or a transport failure.
        """
        if self.provider == "anthropic":
            return self._complete_anthropic(system, prompt, max_tokens, temperature)
        return self._complete_openai(system, prompt, max_tokens, temperature)

    def _complete_anthropic(
        self, system: str, prompt: str, max_tokens: int, temperature: float
    ) -> str:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - exercised only without the SDK
            raise RuntimeError(
                "The 'anthropic' package is required for QUORUM_PROVIDER=anthropic. "
                "Install it with `pip install anthropic`."
            ) from exc

        client = anthropic.Anthropic()
        try:
            message = client.messages.create(
                model=self.model,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as exc:
            raise RuntimeError(f"Anthropic request failed ({self.model}): {exc}") from exc

        return "".join(
            block.text for block in message.content if getattr(block, "type", None) == "text"
        )

    def _complete_openai(
        self, system: str, prompt: str, max_tokens: int, temperature: float
    ) -> str:
        try:
            import openai
        except ImportError as exc:  # pragma: no cover - exercised only without the SDK
            raise RuntimeError(
                "The 'openai' package is required for QUORUM_PROVIDER=openai. "
                "Install it with `pip install openai`."
            ) from exc

        base_url = os.getenv("QUORUM_BASE_URL")
        client = openai.OpenAI(base_url=base_url) if base_url else openai.OpenAI()
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as exc:
            raise RuntimeError(f"OpenAI request failed ({self.model}): {exc}") from exc

        return response.choices[0].message.content or ""
