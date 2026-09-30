"""
groq_client.py

Thin wrapper around the Groq chat completion API (the project's fixed LLM
provider — see Technical Build Spec / tech stack). Every agent built in
later phases calls through this module rather than importing the `groq`
SDK directly, so there is exactly one place that: reads the API key,
picks the model, and turns SDK exceptions into clear, specific errors
instead of raw tracebacks (a non-functional requirement from the
Technical Build Spec: "errors are clear and actionable, not silent").

This module makes real network calls to Groq's API when used for real.
It does not execute anything from an analyzed repository — it only sends
text (prompts built by prompt_templates.py) and returns text back.
"""

from __future__ import annotations

import os
from typing import Optional

import groq

# A fast, capable default. Overridable via the GROQ_MODEL environment
# variable without touching code, since Groq's available models can
# change faster than this file does.
DEFAULT_MODEL = "llama-3.3-70b-versatile"
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MAX_TOKENS = 1024
DEFAULT_TEMPERATURE = 0.2


class LLMError(Exception):
    """Base class for every error this module raises. Callers (agents)
    can catch this one type if they just want to know "the LLM call
    didn't work," or catch a specific subclass below to react
    differently (e.g. treat a rate limit as retryable, a config error
    as not)."""


class LLMConfigurationError(LLMError):
    """Raised when the client can't even be set up — missing or invalid
    API key. This is a setup problem, not a transient one; retrying
    won't help."""


class LLMRateLimitError(LLMError):
    """Raised when Groq reports we've hit a rate limit. Retryable after
    a delay — callers should surface this as "rate limited, try again,"
    per the spec's error-handling requirement, not a generic failure."""


class LLMTimeoutError(LLMError):
    """Raised when the request didn't get a response in time. Retryable."""


class LLMRequestError(LLMError):
    """Raised for any other Groq API failure (bad request, server error,
    connection problem). The original error's message is preserved in
    this exception's message so it's still debuggable."""


_client: Optional[groq.Groq] = None


def _get_client() -> groq.Groq:
    """Lazily construct and cache a single Groq client. Lazy so importing
    this module never fails just because GROQ_API_KEY isn't set yet in
    the environment (e.g. during Phase 1/2 tests that never touch this
    file) — the error only surfaces when an LLM call is actually made."""
    global _client
    if _client is not None:
        return _client

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise LLMConfigurationError(
            "GROQ_API_KEY environment variable is not set. Set it before "
            "making any LLM call (e.g. in a local .env file, never "
            "hard-coded in source)."
        )

    _client = groq.Groq(api_key=api_key)
    return _client


def _reset_client_for_tests() -> None:
    """Test-only hook to clear the cached client so tests can exercise
    _get_client() under different mocked conditions (e.g. missing key,
    then present key) without leaking state between tests."""
    global _client
    _client = None


def chat(
    messages: list[dict[str, str]],
    model: Optional[str] = None,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> str:
    """
    Send a chat-style message list to Groq and return the model's text
    reply. `messages` follows the standard `[{"role": "user"|"system"|
    "assistant", "content": "..."}]` shape — Groq's API is OpenAI-chat
    compatible, and prompt_templates.py builds messages in exactly this
    shape.

    Raises one of the LLMError subclasses above on any failure, never a
    raw SDK exception or a bare traceback.
    """
    client = _get_client()
    model = model or os.environ.get("GROQ_MODEL", DEFAULT_MODEL)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
    except groq.AuthenticationError as exc:
        raise LLMConfigurationError(
            f"Groq rejected the API key (authentication error): {exc}"
        ) from exc
    except groq.RateLimitError as exc:
        raise LLMRateLimitError(
            f"Groq rate limit hit, try again shortly: {exc}"
        ) from exc
    except groq.APITimeoutError as exc:
        raise LLMTimeoutError(
            f"Groq request timed out after {timeout}s: {exc}"
        ) from exc
    except groq.APIConnectionError as exc:
        raise LLMRequestError(f"Could not reach Groq's API: {exc}") from exc
    except groq.APIStatusError as exc:
        raise LLMRequestError(
            f"Groq API returned an error (status {exc.status_code}): {exc.message}"
        ) from exc
    except groq.GroqError as exc:
        # Catch-all for any other SDK-raised error not covered above.
        raise LLMRequestError(f"Groq client error: {exc}") from exc

    if not response.choices:
        raise LLMRequestError("Groq returned no completion choices.")

    content = response.choices[0].message.content
    if content is None:
        raise LLMRequestError("Groq returned an empty message content.")

    return content


def ask(prompt: str, **kwargs) -> str:
    """Convenience wrapper for the common case: a single user-turn prompt,
    no separate system message. Equivalent to
    `chat([{"role": "user", "content": prompt}], **kwargs)`."""
    return chat([{"role": "user", "content": prompt}], **kwargs)
