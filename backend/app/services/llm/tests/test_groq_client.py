"""
Tests for groq_client.py.

These tests never make a real network call to Groq — there's no live API
key in this environment, and the point of good error-handling code is
that it's testable without one. The Groq SDK client is mocked at the
`chat.completions.create` boundary; SDK exceptions are constructed for
real (using httpx request/response objects, the same way the SDK itself
would build them) so we're testing our actual exception-mapping logic,
not a fake stand-in for it.

Before a real demo: run a manual check with a real GROQ_API_KEY set,
e.g. `python3 -c "from backend.app.services.llm.groq_client import ask;
print(ask('say hello in 3 words'))"`, to confirm live connectivity once.
That's a manual step, not part of this automated suite, since it needs a
real key and real network access to api.groq.com.
"""

from unittest.mock import MagicMock, patch

import groq
import httpx
import pytest

from backend.app.services.llm import groq_client


@pytest.fixture(autouse=True)
def reset_client_and_env(monkeypatch):
    """Every test starts with no cached client and a known env var state,
    so tests can't leak state into each other."""
    groq_client._reset_client_for_tests()
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    yield
    groq_client._reset_client_for_tests()


def _fake_request() -> httpx.Request:
    return httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")


def _fake_response(status_code: int) -> httpx.Response:
    return httpx.Response(status_code, request=_fake_request(), json={"error": {"message": "boom"}})


def _fake_success_response(text: str = "hello from groq"):
    message = MagicMock()
    message.content = text
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


# --- configuration / missing key ------------------------------------------


def test_missing_api_key_raises_configuration_error():
    with pytest.raises(groq_client.LLMConfigurationError, match="GROQ_API_KEY"):
        groq_client.ask("hello")


def test_present_api_key_does_not_raise_configuration_error(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key-for-test")
    with patch("backend.app.services.llm.groq_client.groq.Groq") as mock_groq_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _fake_success_response()
        mock_groq_cls.return_value = mock_client

        result = groq_client.ask("hello")
        assert result == "hello from groq"


# --- successful call shape -------------------------------------------------


def test_chat_passes_messages_through_and_returns_content(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    with patch("backend.app.services.llm.groq_client.groq.Groq") as mock_groq_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _fake_success_response("42")
        mock_groq_cls.return_value = mock_client

        messages = [{"role": "system", "content": "be terse"}, {"role": "user", "content": "2+2?"}]
        result = groq_client.chat(messages)

        assert result == "42"
        _, kwargs = mock_client.chat.completions.create.call_args
        assert kwargs["messages"] == messages
        assert kwargs["model"] == groq_client.DEFAULT_MODEL


def test_model_env_override_is_respected(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    monkeypatch.setenv("GROQ_MODEL", "some-other-model")
    with patch("backend.app.services.llm.groq_client.groq.Groq") as mock_groq_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _fake_success_response()
        mock_groq_cls.return_value = mock_client

        groq_client.ask("hello")
        _, kwargs = mock_client.chat.completions.create.call_args
        assert kwargs["model"] == "some-other-model"


def test_empty_choices_raises_request_error(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    with patch("backend.app.services.llm.groq_client.groq.Groq") as mock_groq_cls:
        mock_client = MagicMock()
        response = MagicMock()
        response.choices = []
        mock_client.chat.completions.create.return_value = response
        mock_groq_cls.return_value = mock_client

        with pytest.raises(groq_client.LLMRequestError, match="no completion choices"):
            groq_client.ask("hello")


# --- error mapping: every SDK exception becomes a clear, specific error ---


def test_authentication_error_maps_to_configuration_error(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    with patch("backend.app.services.llm.groq_client.groq.Groq") as mock_groq_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = groq.AuthenticationError(
            "invalid api key", response=_fake_response(401), body=None
        )
        mock_groq_cls.return_value = mock_client

        with pytest.raises(groq_client.LLMConfigurationError, match="authentication"):
            groq_client.ask("hello")


def test_rate_limit_error_maps_to_rate_limit_error(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    with patch("backend.app.services.llm.groq_client.groq.Groq") as mock_groq_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = groq.RateLimitError(
            "too many requests", response=_fake_response(429), body=None
        )
        mock_groq_cls.return_value = mock_client

        with pytest.raises(groq_client.LLMRateLimitError, match="rate limit"):
            groq_client.ask("hello")


def test_timeout_error_maps_to_timeout_error(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    with patch("backend.app.services.llm.groq_client.groq.Groq") as mock_groq_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = groq.APITimeoutError(
            request=_fake_request()
        )
        mock_groq_cls.return_value = mock_client

        with pytest.raises(groq_client.LLMTimeoutError, match="timed out"):
            groq_client.ask("hello")


def test_connection_error_maps_to_request_error(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    with patch("backend.app.services.llm.groq_client.groq.Groq") as mock_groq_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = groq.APIConnectionError(
            request=_fake_request()
        )
        mock_groq_cls.return_value = mock_client

        with pytest.raises(groq_client.LLMRequestError, match="Could not reach"):
            groq_client.ask("hello")


def test_generic_status_error_maps_to_request_error(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    with patch("backend.app.services.llm.groq_client.groq.Groq") as mock_groq_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = groq.APIStatusError(
            "server exploded", response=_fake_response(500), body=None
        )
        mock_groq_cls.return_value = mock_client

        with pytest.raises(groq_client.LLMRequestError, match="Groq API returned an error"):
            groq_client.ask("hello")


def test_no_raw_sdk_exception_ever_escapes(monkeypatch):
    """Every mapped exception above must be an LLMError subclass, never
    the raw groq.* exception leaking through to calling code."""
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    with patch("backend.app.services.llm.groq_client.groq.Groq") as mock_groq_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = groq.RateLimitError(
            "boom", response=_fake_response(429), body=None
        )
        mock_groq_cls.return_value = mock_client
        try:
            groq_client.ask("hello")
        except groq.GroqError:
            pytest.fail("a raw groq SDK exception escaped groq_client.ask()")
        except groq_client.LLMError:
            pass  # expected


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
