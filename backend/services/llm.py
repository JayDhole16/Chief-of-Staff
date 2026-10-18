"""
Bring-your-own-key LLM gateway.

Each founder stores their own provider key in Settings → API Keys; the server never
uses a shared key from the environment. Every call returns token usage so the
dashboard can show exactly what each founder is spending.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import anthropic
import httpx

REQUEST_TIMEOUT_SECONDS = 90.0

# provider id -> display metadata and defaults
PROVIDERS: dict[str, dict[str, Any]] = {
    "anthropic": {
        "label": "Anthropic (Claude)",
        "default_model": "claude-opus-5-5",
        "base_url": None,
        "key_hint": "sk-ant-...",
        "docs_url": "https://console.anthropic.com/settings/keys",
    },
    "openai": {
        "label": "OpenAI",
        "default_model": "gpt-4o-mini",
        "base_url": "https://api.openai.com/v1",
        "key_hint": "sk-...",
        "docs_url": "https://platform.openai.com/api-keys",
    },
    "gemini": {
        "label": "Google Gemini",
        "default_model": "gemini-2.0-flash",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "key_hint": "AIza...",
        "docs_url": "https://aistudio.google.com/app/apikey",
    },
    "groq": {
        "label": "Groq",
        "default_model": "llama-3.3-70b-versatile",
        "base_url": "https://api.groq.com/openai/v1",
        "key_hint": "gsk_...",
        "docs_url": "https://console.groq.com/keys",
    },
    "openrouter": {
        "label": "OpenRouter",
        "default_model": "openai/gpt-4o-mini",
        "base_url": "https://openrouter.ai/api/v1",
        "key_hint": "sk-or-...",
        "docs_url": "https://openrouter.ai/keys",
    },
    "custom": {
        "label": "Custom (OpenAI-compatible)",
        "default_model": "",
        "base_url": "",
        "key_hint": "optional for local servers",
        "docs_url": None,
    },
}

# Claude models that accept the server-side refusal fallback parameter.
_ANTHROPIC_FALLBACK_MODELS = {"claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"}


class LLMError(Exception):
    """Provider call failed; message is safe to show to the founder."""


class LLMNotConfiguredError(LLMError):
    pass


@dataclass
class LLMConfig:
    provider: str
    api_key: str | None
    model: str
    base_url: str | None


@dataclass
class LLMResult:
    text: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int


def resolve_config(provider: str, stored: dict[str, Any] | None) -> LLMConfig:
    if provider not in PROVIDERS:
        raise LLMNotConfiguredError(f"Unknown provider '{provider}'")
    meta = PROVIDERS[provider]
    stored = stored or {}
    model = (stored.get("model") or meta["default_model"] or "").strip()
    base_url = (stored.get("base_url") or meta["base_url"] or "").strip() or None
    api_key = stored.get("api_key")
    if provider != "custom" and not api_key:
        raise LLMNotConfiguredError(f"No API key saved for {meta['label']}")
    if provider == "custom" and not base_url:
        raise LLMNotConfiguredError("Custom provider needs a base URL")
    if not model:
        raise LLMNotConfiguredError(f"No model set for {meta['label']}")
    return LLMConfig(provider=provider, api_key=api_key, model=model, base_url=base_url)


def complete(
    config: LLMConfig,
    *,
    system: str,
    messages: list[dict[str, str]],
    max_tokens: int = 4000,
) -> LLMResult:
    """Send a chat completion. ``messages`` are ``{"role": "user"|"assistant", "content": str}``."""
    if config.provider == "anthropic":
        return _complete_anthropic(config, system, messages, max_tokens)
    if config.provider == "gemini":
        return _complete_gemini(config, system, messages, max_tokens)
    return _complete_openai_compatible(config, system, messages, max_tokens)


def test_connection(config: LLMConfig) -> tuple[bool, str]:
    try:
        result = complete(
            config,
            system="You are a connectivity check. Reply with the single word OK.",
            messages=[{"role": "user", "content": "Reply with OK."}],
            max_tokens=1000,
        )
    except LLMError as exc:
        return False, str(exc)
    return True, f"Connected to {config.model} ({result.input_tokens + result.output_tokens} tokens used)"


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------
def _complete_anthropic(
    config: LLMConfig, system: str, messages: list[dict[str, str]], max_tokens: int
) -> LLMResult:
    client = anthropic.Anthropic(
        api_key=config.api_key,
        base_url=config.base_url or None,
        timeout=REQUEST_TIMEOUT_SECONDS,
        max_retries=2,
    )
    try:
        if config.model in _ANTHROPIC_FALLBACK_MODELS:
            response = client.beta.messages.create(
                model=config.model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,  # type: ignore[arg-type]
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        else:
            response = client.messages.create(
                model=config.model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,  # type: ignore[arg-type]
            )
    except anthropic.AuthenticationError as exc:
        raise LLMError("Anthropic rejected the API key (401). Check the key in Settings → API Keys.") from exc
    except anthropic.PermissionDeniedError as exc:
        raise LLMError("Anthropic API key lacks permission for this model (403).") from exc
    except anthropic.NotFoundError as exc:
        raise LLMError(f"Anthropic model '{config.model}' was not found (404).") from exc
    except anthropic.RateLimitError as exc:
        raise LLMError("Anthropic rate limit or credit limit reached (429). Try again shortly.") from exc
    except anthropic.APIStatusError as exc:
        raise LLMError(f"Anthropic API error {exc.status_code}: {exc.message}") from exc
    except anthropic.APIConnectionError as exc:
        raise LLMError("Could not reach the Anthropic API. Check the server's network access.") from exc

    if response.stop_reason == "refusal":
        raise LLMError("The model declined to answer this request.")
    text = "".join(block.text for block in response.content if block.type == "text").strip()
    return LLMResult(
        text=text,
        provider=config.provider,
        model=response.model or config.model,
        input_tokens=response.usage.input_tokens or 0,
        output_tokens=response.usage.output_tokens or 0,
    )


def _http_error_message(provider_label: str, response: httpx.Response) -> str:
    detail = ""
    try:
        body = response.json()
        err = body.get("error") if isinstance(body, dict) else None
        if isinstance(err, dict):
            detail = err.get("message") or ""
        elif isinstance(err, str):
            detail = err
    except ValueError:
        detail = response.text[:200]
    hints = {
        401: "the API key was rejected",
        403: "the API key lacks permission",
        404: "the model or endpoint was not found",
        429: "rate limit or quota reached",
    }
    hint = hints.get(response.status_code, "request failed")
    return f"{provider_label} error {response.status_code}: {hint}. {detail}".strip()


def _complete_openai_compatible(
    config: LLMConfig, system: str, messages: list[dict[str, str]], max_tokens: int
) -> LLMResult:
    label = PROVIDERS[config.provider]["label"]
    headers = {"Content-Type": "application/json"}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    payload = {
        "model": config.model,
        "messages": [{"role": "system", "content": system}, *messages],
        "max_tokens": max_tokens,
    }
    url = f"{(config.base_url or '').rstrip('/')}/chat/completions"
    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
    except httpx.HTTPError as exc:
        raise LLMError(f"Could not reach {label} at {config.base_url}: {exc}") from exc
    if response.status_code >= 400:
        raise LLMError(_http_error_message(label, response))
    try:
        body = response.json()
        text = (body["choices"][0]["message"].get("content") or "").strip()
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"{label} returned an unexpected response") from exc
    usage = body.get("usage") or {}
    return LLMResult(
        text=text,
        provider=config.provider,
        model=body.get("model") or config.model,
        input_tokens=int(usage.get("prompt_tokens") or 0),
        output_tokens=int(usage.get("completion_tokens") or 0),
    )


def _complete_gemini(
    config: LLMConfig, system: str, messages: list[dict[str, str]], max_tokens: int
) -> LLMResult:
    label = PROVIDERS["gemini"]["label"]
    url = f"{(config.base_url or '').rstrip('/')}/models/{config.model}:generateContent"
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [
            {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
            for m in messages
        ],
        "generationConfig": {"maxOutputTokens": max_tokens},
    }
    try:
        response = httpx.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json", "x-goog-api-key": config.api_key or ""},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        raise LLMError(f"Could not reach {label}: {exc}") from exc
    if response.status_code >= 400:
        raise LLMError(_http_error_message(label, response))
    try:
        body = response.json()
        parts = body["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts).strip()
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"{label} returned no content (it may have been blocked by safety filters)") from exc
    usage = body.get("usageMetadata") or {}
    return LLMResult(
        text=text,
        provider=config.provider,
        model=config.model,
        input_tokens=int(usage.get("promptTokenCount") or 0),
        output_tokens=int(usage.get("candidatesTokenCount") or 0),
    )
