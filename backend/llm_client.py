from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv(Path(__file__).with_name(".env"))
load_dotenv()


@dataclass(frozen=True)
class LLMProvider:
    name: str
    model: str
    client: OpenAI
    extra_headers: dict[str, str] | None = None


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def _valid_key(value: str) -> bool:
    return bool(value and not value.lower().startswith("your_"))


def _provider_order() -> list[str]:
    raw = _env("LLM_PROVIDER_ORDER", "openrouter,gemini,openai")
    order = [item.strip().lower() for item in raw.split(",") if item.strip()]
    return order or ["openrouter", "gemini", "openai"]


def _build_provider(name: str) -> LLMProvider | None:
    if name == "openrouter":
        key = _env("OPENROUTER_API_KEY")
        if not _valid_key(key):
            return None
        return LLMProvider(
            name="openrouter",
            model=_env("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
            client=OpenAI(
                base_url=_env("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
                api_key=key,
            ),
            extra_headers={
                "HTTP-Referer": _env("OPENROUTER_SITE_URL", "http://localhost:3000"),
                "X-Title": _env("OPENROUTER_APP_NAME", "WARBREAK"),
            },
        )

    if name == "gemini":
        key = _env("GEMINI_API_KEY")
        if not _valid_key(key):
            return None
        return LLMProvider(
            name="gemini",
            model=_env("GEMINI_MODEL", "gemini-2.5-flash"),
            client=OpenAI(
                base_url=_env("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"),
                api_key=key,
            ),
        )

    if name == "openai":
        key = _env("OPENAI_API_KEY") or _env("OPENAI_API")
        if not _valid_key(key):
            return None
        return LLMProvider(
            name="openai",
            model=_env("OPENAI_MODEL", "gpt-4o-mini"),
            client=OpenAI(
                base_url=_env("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                api_key=key,
            ),
        )

    return None


PROVIDERS = [provider for name in _provider_order() if (provider := _build_provider(name))]
PROVIDER = "fallback-chain" if PROVIDERS else "none"
MODEL = " -> ".join(f"{provider.name}:{provider.model}" for provider in PROVIDERS) or "none"
provider_status: dict[str, str] = {
    name: "configured" if any(provider.name == name for provider in PROVIDERS) else "missing"
    for name in ["openrouter", "gemini", "openai"]
}
provider_status["active"] = "none"
provider_status["last_error"] = ""


def _completion_kwargs(
    provider: LLMProvider,
    prompt: str,
    temperature: float,
    max_tokens: int,
    json_mode: bool,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model": provider.model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    if provider.extra_headers:
        kwargs["extra_headers"] = provider.extra_headers
    return kwargs


def _error_summary(exc: Exception) -> str:
    message = str(exc).replace("\n", " ").strip()
    if len(message) > 180:
        message = f"{message[:177]}..."
    return f"{type(exc).__name__}: {message or 'request failed'}"


def call_llm(prompt: str, temperature: float = 0.3, max_tokens: int = 800, json_mode: bool = False) -> str:
    if not PROVIDERS:
        raise RuntimeError("No LLM providers configured. Set OPENROUTER_API_KEY, GEMINI_API_KEY, or OPENAI_API_KEY.")

    errors: list[str] = []
    for provider in PROVIDERS:
        try:
            response = provider.client.chat.completions.create(
                **_completion_kwargs(provider, prompt, temperature, max_tokens, json_mode)
            )
            content = response.choices[0].message.content if response.choices else ""
            text = (content or "").strip()
            if not text:
                raise RuntimeError("provider returned an empty response")
            provider_status[provider.name] = "ok"
            provider_status["active"] = provider.name
            provider_status["last_error"] = ""
            return text
        except Exception as exc:
            summary = _error_summary(exc)
            provider_status[provider.name] = f"failed: {summary}"
            provider_status["last_error"] = summary
            errors.append(f"{provider.name} failed ({summary})")

    provider_status["active"] = "none"
    raise RuntimeError(f"All LLM providers failed: {'; '.join(errors)}")


def call_llm_json(prompt: str, temperature: float = 0.2, max_tokens: int = 800) -> str:
    suffix = "\n\nCRITICAL: Return ONLY raw JSON. No markdown. No backticks. No explanation. Start with { and end with }."
    return call_llm(prompt + suffix, temperature=temperature, max_tokens=max_tokens, json_mode=True)
