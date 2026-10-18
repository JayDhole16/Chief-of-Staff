"""
Bring-your-own-key LLM gateway.

Each founder stores their own provider key in Settings → API Keys; the server never
uses a shared key from the environment. Every call returns token usage so the
dashboard can show exactly what each founder is spending.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
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
        "default_model": "gemini-3.8-flash",
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


# Models the provider has shut down, mapped to their current replacement so saved
# settings keep working (https://ai.google.dev/gemini-api/docs/models).
RETIRED_MODELS = {
    "gemini-2.0-flash": "gemini-3.8-flash",
    "gemini-2.0-flash-lite": "gemini-3.5-flash-lite",
    "gemini-3-pro-preview": "gemini-3.1-pro-preview",
    "gemini-3.1-flash-lite-preview": "gemini-3.5-flash-lite",
}

# Gemini 3.x thinks by default and thinking tokens count toward maxOutputTokens,
# so leave headroom for the visible answer.
GEMINI_THINKING_HEADROOM = 8192
# Chat and drafting don't need deep reasoning: low thinking keeps Gemini 3.x fast and cheap.
GEMINI_THINKING_LEVEL = "low"


def _timeout_message(label: str) -> str:
    return (
        f"{label} took longer than {int(REQUEST_TIMEOUT_SECONDS)} seconds to answer. "
        "Try again, or pick a faster model in API Keys."
    )


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
    model = RETIRED_MODELS.get(model, model)
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
    response = _anthropic_create(config, system=system, messages=messages, max_tokens=max_tokens)
    text = "".join(block.text for block in response.content if block.type == "text").strip()
    return LLMResult(
        text=text,
        provider=config.provider,
        model=response.model or config.model,
        input_tokens=response.usage.input_tokens or 0,
        output_tokens=response.usage.output_tokens or 0,
    )


def _anthropic_create(config: LLMConfig, **params: Any) -> Any:
    """One Messages API call with readable errors; refusal fallback on supported models."""
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
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                **params,
            )
        else:
            response = client.messages.create(model=config.model, **params)
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
    except anthropic.APITimeoutError as exc:
        raise LLMError(_timeout_message("Anthropic")) from exc
    except anthropic.APIConnectionError as exc:
        raise LLMError("Could not reach the Anthropic API. Check the server's network access.") from exc
    if response.stop_reason == "refusal":
        raise LLMError("The model declined to answer this request.")
    return response


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
    except httpx.TimeoutException as exc:
        raise LLMError(_timeout_message(label)) from exc
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


def _gemini_generate(config: LLMConfig, payload: dict[str, Any], max_tokens: int) -> dict[str, Any]:
    """POST generateContent with Gemini-specific config; returns the parsed body."""
    label = PROVIDERS["gemini"]["label"]
    url = f"{(config.base_url or '').rstrip('/')}/models/{config.model}:generateContent"
    generation: dict[str, Any] = {"maxOutputTokens": max_tokens + GEMINI_THINKING_HEADROOM}
    if config.model.startswith("gemini-3"):
        generation["thinkingConfig"] = {"thinkingLevel": GEMINI_THINKING_LEVEL}
    headers = {"Content-Type": "application/json", "x-goog-api-key": config.api_key or ""}

    def post(body: dict[str, Any]) -> httpx.Response:
        try:
            return httpx.post(url, json=body, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
        except httpx.TimeoutException as exc:
            raise LLMError(_timeout_message(label)) from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"Could not reach {label}: {exc}") from exc

    response = post({**payload, "generationConfig": generation})
    if response.status_code == 400 and "thinkingConfig" in generation and "thinking" in response.text.lower():
        # This model/API version rejects the thinking setting: fall back to its default.
        logging.getLogger("cos.llm").warning("Gemini rejected thinkingConfig for %s; retrying without it", config.model)
        generation = {k: v for k, v in generation.items() if k != "thinkingConfig"}
        response = post({**payload, "generationConfig": generation})
    if response.status_code >= 400:
        raise LLMError(_http_error_message(label, response))
    try:
        body = response.json()
    except ValueError as exc:
        raise LLMError(f"{label} returned an unexpected response") from exc
    return body if isinstance(body, dict) else {}


def _gemini_output_tokens(usage: dict[str, Any]) -> int:
    # Thinking tokens are billed as output but reported separately.
    return int(usage.get("candidatesTokenCount") or 0) + int(usage.get("thoughtsTokenCount") or 0)


def _complete_gemini(
    config: LLMConfig, system: str, messages: list[dict[str, str]], max_tokens: int
) -> LLMResult:
    label = PROVIDERS["gemini"]["label"]
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [
            {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
            for m in messages
        ],
    }
    body = _gemini_generate(config, payload, max_tokens)
    try:
        parts = body["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"{label} returned no content (it may have been blocked by safety filters)") from exc
    usage = body.get("usageMetadata") or {}
    return LLMResult(
        text=text,
        provider=config.provider,
        model=config.model,
        input_tokens=int(usage.get("promptTokenCount") or 0),
        output_tokens=_gemini_output_tokens(usage),
    )


# ---------------------------------------------------------------------------
# Agent loop: native tool/function calling for every provider
# ---------------------------------------------------------------------------
logger = logging.getLogger("cos.agent")

# A tool handler receives (tool_name, arguments) and returns (result, is_error).
ToolHandler = Callable[[str, dict[str, Any]], "tuple[Any, bool]"]


@dataclass
class AgentResult:
    text: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    steps: int = 0
    tool_calls: list[dict[str, Any]] = field(default_factory=list)


def run_agent(
    config: LLMConfig,
    *,
    system: str,
    messages: list[dict[str, str]],
    tools: list[dict[str, Any]],
    handle_tool: ToolHandler,
    max_steps: int = 8,
    max_tokens: int = 8000,
) -> AgentResult:
    """Let the model call tools until it answers in text (or max_steps is reached).

    ``tools`` are ``{"name", "description", "parameters": <JSON schema>}``. Tool failures
    are returned to the model as error results so it can recover or explain; only
    provider failures raise LLMError.
    """
    result = AgentResult(text="", provider=config.provider, model=config.model)

    def call_tool(name: str, args: Any) -> tuple[Any, bool]:
        if not isinstance(args, dict):
            args = {}
        try:
            output, is_error = handle_tool(name, args)
        except Exception as exc:  # a tool bug must never break the conversation
            logger.exception("tool %s crashed", name)
            output, is_error = {"error": f"Tool '{name}' failed unexpectedly: {exc}"}, True
        result.tool_calls.append({"name": name, "arguments": args, "ok": not is_error, "output": output})
        if is_error:
            logger.info("tool %s returned an error: %s", name, output)
        return output, is_error

    if config.provider == "anthropic":
        _agent_anthropic(config, system, messages, tools, call_tool, max_steps, max_tokens, result)
    elif config.provider == "gemini":
        _agent_gemini(config, system, messages, tools, call_tool, max_steps, max_tokens, result)
    else:
        _agent_openai(config, system, messages, tools, call_tool, max_steps, max_tokens, result)
    if not result.text:
        result.text = (
            "I ran out of steps before finishing. Here is what I did so far: "
            + ", ".join(f"{c['name']} ({'ok' if c['ok'] else 'failed'})" for c in result.tool_calls)
            if result.tool_calls
            else "I don't have an answer for that."
        )
    return result


def _agent_anthropic(config, system, messages, tools, call_tool, max_steps, max_tokens, result) -> None:
    convo: list[dict[str, Any]] = [dict(m) for m in messages]
    tool_defs = [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]} for t in tools]
    for _ in range(max_steps):
        response = _anthropic_create(config, system=system, messages=convo, tools=tool_defs, max_tokens=max_tokens)
        result.steps += 1
        result.model = response.model or config.model
        result.input_tokens += response.usage.input_tokens or 0
        result.output_tokens += response.usage.output_tokens or 0
        if response.stop_reason != "tool_use":
            result.text = "".join(b.text for b in response.content if b.type == "text").strip()
            return
        # Pass the assistant turn back unchanged (including any thinking blocks).
        convo.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                output, is_error = call_tool(block.name, block.input)
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(output, default=str), "is_error": is_error}
                )
        convo.append({"role": "user", "content": tool_results})


def _agent_openai(config, system, messages, tools, call_tool, max_steps, max_tokens, result) -> None:
    label = PROVIDERS[config.provider]["label"]
    headers = {"Content-Type": "application/json"}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    url = f"{(config.base_url or '').rstrip('/')}/chat/completions"
    convo: list[dict[str, Any]] = [{"role": "system", "content": system}, *messages]
    tool_defs = [
        {"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}}
        for t in tools
    ]
    for _ in range(max_steps):
        payload = {"model": config.model, "messages": convo, "tools": tool_defs, "max_tokens": max_tokens}
        try:
            response = httpx.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
        except httpx.TimeoutException as exc:
            raise LLMError(_timeout_message(label)) from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"Could not reach {label}: {exc}") from exc
        if response.status_code >= 400:
            message = _http_error_message(label, response)
            if response.status_code == 400 and "tool" in message.lower():
                message += " (this model may not support tool calling; pick a model that does)"
            raise LLMError(message)
        try:
            body = response.json()
            msg = body["choices"][0]["message"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"{label} returned an unexpected response") from exc
        result.steps += 1
        result.model = body.get("model") or config.model
        usage = body.get("usage") or {}
        result.input_tokens += int(usage.get("prompt_tokens") or 0)
        result.output_tokens += int(usage.get("completion_tokens") or 0)
        calls = msg.get("tool_calls") or []
        if not calls:
            result.text = (msg.get("content") or "").strip()
            return
        convo.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": calls})
        for call in calls:
            fn = call.get("function") or {}
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except ValueError:
                output, is_error = {"error": "Arguments were not valid JSON; call the tool again."}, True
            else:
                output, is_error = call_tool(fn.get("name", ""), args)
            convo.append({"role": "tool", "tool_call_id": call.get("id", ""), "content": json.dumps(output, default=str)})


def _agent_gemini(config, system, messages, tools, call_tool, max_steps, max_tokens, result) -> None:
    label = PROVIDERS["gemini"]["label"]
    contents: list[dict[str, Any]] = [
        {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]} for m in messages
    ]
    declarations = [{"name": t["name"], "description": t["description"], "parameters": t["parameters"]} for t in tools]
    for _ in range(max_steps):
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": contents,
            "tools": [{"functionDeclarations": declarations}],
        }
        body = _gemini_generate(config, payload, max_tokens)
        try:
            content = body["candidates"][0]["content"]
            parts = content.get("parts") or []
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"{label} returned no content (it may have been blocked by safety filters)") from exc
        result.steps += 1
        usage = body.get("usageMetadata") or {}
        result.input_tokens += int(usage.get("promptTokenCount") or 0)
        result.output_tokens += _gemini_output_tokens(usage)
        calls = [p["functionCall"] for p in parts if "functionCall" in p]
        if not calls:
            result.text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
            return
        contents.append({"role": "model", "parts": parts})
        responses = []
        for call in calls:
            output, is_error = call_tool(call.get("name", ""), call.get("args") or {})
            function_response: dict[str, Any] = {"name": call.get("name", ""), "response": {"result": output, "is_error": is_error}}
            if call.get("id"):
                function_response["id"] = call["id"]
            responses.append({"functionResponse": function_response})
        contents.append({"role": "user", "parts": responses})
