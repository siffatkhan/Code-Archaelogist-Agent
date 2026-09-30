# services/llm/ — Phase 3 (M3)

Groq LLM client wrapper and the project's central prompt templates. Every
agent built in later phases (Historian, Guidance, Knowledge Gap) calls
through this module rather than talking to the `groq` SDK or writing
prompt strings directly.

## Files

- `groq_client.py` — wraps the official `groq` Python SDK. Public
  functions: `ask(prompt: str, **kwargs) -> str` and
  `chat(messages: list[dict], **kwargs) -> str`. Every SDK exception is
  mapped to one of four clear, specific exceptions —
  `LLMConfigurationError`, `LLMRateLimitError`, `LLMTimeoutError`,
  `LLMRequestError` — so calling code never has to catch a raw `groq.*`
  exception or parse a stack trace to know what went wrong.
- `prompt_templates.py` — one named builder function per agent use case:
  `build_historian_messages()`, `build_guidance_messages()`,
  `build_gap_check_messages()`. Each returns a ready-to-send `messages`
  list. Repository content (evidence, file context) is always wrapped in
  tagged blocks (`<evidence>`, `<file_context>`) clearly marked as
  untrusted data in the system prompt — never concatenated in a way that
  could be mistaken for an instruction.

## Setup

```
pip install groq
export GROQ_API_KEY=your_key_here   # never hard-code this
export GROQ_MODEL=llama-3.3-70b-versatile   # optional, this is the default
```

`GROQ_API_KEY` is read lazily — importing this module never fails just
because the key isn't set yet; the error only surfaces on the first
actual LLM call, as an `LLMConfigurationError` with a clear message.

## Guardrail wording

`prompt_templates.REFUSAL_MESSAGE` holds the exact refusal sentence from
the Technical Build Spec's example: `"this assistant only answers
questions related to the analyzed repository."` Both the Historian and
Guidance system prompts reference this same constant, so the wording
can't drift between templates. Per the Phase 6 plan, the *primary*
off-topic guardrail should be a deterministic branch in the LangGraph
workflow, not solely this module's system-prompt instruction — a
`build_gap_check_messages()` template is included here as one signal an
agent can combine with a deterministic check, not as the sole gate.

## Running the tests

```
cd <repo-root>
python3 -m pytest backend/app/services/llm/tests/ -v
```

23 tests, all mocked — no real network call to Groq is made (there's no
live API key in most dev/CI environments, and testable error-handling
shouldn't require one). SDK exceptions are constructed for real using
`httpx` request/response objects the same way the SDK itself builds them,
so the tests exercise real exception-mapping logic, not a stand-in.
Covers: missing API key, every mapped SDK exception
(`AuthenticationError`, `RateLimitError`, `APITimeoutError`,
`APIConnectionError`, `APIStatusError`), model env-var override, empty
response handling, and — for the templates — that injected "ignore your
instructions"-style text inside evidence stays literally inside the
delimited block rather than escaping it.

## Manual live check (do this once before a demo)

```
export GROQ_API_KEY=your_real_key
python3 -c "from backend.app.services.llm.groq_client import ask; print(ask('say hello in 3 words'))"
```

This isn't part of the automated suite since it needs real network access
and a real key, but it's worth running once to confirm actual
connectivity works end to end, not just the mocked error paths.

## Known limitations (by design)

- `DEFAULT_MODEL` is a reasonable current Groq model choice, overridable
  via `GROQ_MODEL` without a code change — Groq's model lineup can change
  faster than this file does.
- `build_gap_check_messages()` produces a classifier prompt but does not
  parse or act on the response itself — that's Phase 6/7's job. This
  phase only builds the prompt.
