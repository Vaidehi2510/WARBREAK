from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from dotenv import load_dotenv
from openai import APIStatusError, OpenAI, OpenAIError

load_dotenv(Path(__file__).with_name(".env"), override=True)


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    model: str
    key_names: tuple[str, ...]
    base_url: str | None = None
    default_headers: dict[str, str] | None = None
    extra_body: dict[str, str] | None = None

    @property
    def api_key(self) -> str:
        for key_name in self.key_names:
            value = os.getenv(key_name)
            if value:
                return value
        return ""

    @property
    def configured(self) -> bool:
        return bool(self.api_key)


def _openrouter_headers() -> dict[str, str]:
    headers = {}
    site_url = os.getenv("OPENROUTER_SITE_URL")
    app_name = os.getenv("OPENROUTER_APP_NAME")
    if site_url:
        headers["HTTP-Referer"] = site_url
    if app_name:
        headers["X-Title"] = app_name
    return headers


def _provider_map() -> dict[str, ProviderConfig]:
    gemini_reasoning = os.getenv("GEMINI_REASONING_EFFORT", "none")
    return {
        "openrouter": ProviderConfig(
            name="openrouter",
            model=os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
            key_names=("OPENROUTER_API_KEY",),
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            default_headers=_openrouter_headers(),
        ),
        "gemini": ProviderConfig(
            name="gemini",
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            key_names=("GEMINI_API_KEY",),
            base_url=os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"),
            extra_body={"reasoning_effort": gemini_reasoning} if gemini_reasoning else None,
        ),
        "openai": ProviderConfig(
            name="openai",
            model=os.getenv("OPENAI_MODEL", "gpt-5.4-mini"),
            key_names=("OPENAI_API_KEY", "OPENAI_API"),
            base_url=os.getenv("OPENAI_BASE_URL") or None,
        ),
    }


def _provider_names() -> list[str]:
    raw = os.getenv("LLM_PROVIDER_ORDER", "openrouter,gemini,openai")
    names = [name.strip().lower() for name in raw.split(",") if name.strip()]
    return names or ["openrouter", "gemini", "openai"]


def _provider_chain(include_unconfigured: bool = False) -> list[ProviderConfig]:
    providers = _provider_map()
    chain = []
    for name in _provider_names():
        provider = providers.get(name)
        if provider and (include_unconfigured or provider.configured):
            chain.append(provider)
    return chain


PROVIDER = " -> ".join(provider.name for provider in _provider_chain(include_unconfigured=True))
MODEL = " -> ".join(f"{provider.name}:{provider.model}" for provider in _provider_chain(include_unconfigured=True))

_clients: dict[str, OpenAI] = {}


def provider_status() -> list[dict[str, object]]:
    return [
        {
            "provider": provider.name,
            "model": provider.model,
            "configured": provider.configured,
        }
        for provider in _provider_chain(include_unconfigured=True)
    ]


def get_client(provider: ProviderConfig) -> OpenAI:
    client = _clients.get(provider.name)
    if client is not None:
        return client

    api_key = provider.api_key
    if not api_key:
        raise RuntimeError(f"{provider.name} API key is not configured.")

    kwargs = {"api_key": api_key}
    if provider.base_url:
        kwargs["base_url"] = provider.base_url
    if provider.default_headers:
        kwargs["default_headers"] = provider.default_headers

    client = OpenAI(**kwargs)
    _clients[provider.name] = client
    return client


def _provider_error(exc: Exception) -> str:
    message = str(exc)
    if isinstance(exc, APIStatusError):
        body = getattr(exc, "body", None)
        if isinstance(body, dict):
            error = body.get("error")
            if isinstance(error, dict) and error.get("message"):
                message = str(error["message"])
    return re.sub(r"\s+", " ", message).strip()[:500]


def _extract_json_object(raw: str) -> str:
    raw = re.sub(r"^```json\s*|^```\s*|\s*```$", "", raw.strip()).strip()
    try:
        json.loads(raw)
        return raw
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise
        candidate = match.group()
        json.loads(candidate)
        return candidate


def _completion(
    provider: ProviderConfig,
    prompt: str,
    temperature: float,
    max_tokens: int,
    response_format: dict | None,
) -> str:
    kwargs = {
        "model": provider.model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        kwargs["response_format"] = response_format
    if provider.extra_body:
        kwargs["extra_body"] = provider.extra_body

    response = get_client(provider).chat.completions.create(**kwargs)
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError(f"{provider.name} returned an empty response.")
    return content.strip()


def _call_with_fallback(
    prompt: str,
    temperature: float,
    max_tokens: int,
    response_format: dict | None = None,
    validator: Callable[[str], str] | None = None,
) -> str:
    providers = _provider_chain()
    if not providers:
        raise RuntimeError("No LLM providers configured. Set OPENROUTER_API_KEY, GEMINI_API_KEY, or OPENAI_API_KEY.")

    errors: list[str] = []
    for provider in providers:
        try:
            content = _completion(provider, prompt, temperature, max_tokens, response_format)
            return validator(content) if validator else content
        except (APIStatusError, OpenAIError, RuntimeError, json.JSONDecodeError) as exc:
            errors.append(f"{provider.name}: {_provider_error(exc)}")

    raise RuntimeError("All LLM providers failed: " + " | ".join(errors))


def call_llm(
    prompt: str,
    temperature: float = 0.3,
    max_tokens: int = 1500,
    response_format: dict | None = None,
) -> str:
    return _call_with_fallback(
        prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format=response_format,
    )


def call_llm_json(prompt: str, temperature: float = 0.2, max_tokens: int = 1500) -> str:
    suffix = "\n\nCRITICAL: Return only valid JSON with double-quoted keys and string values. No markdown, no backticks, no explanation."
    return _call_with_fallback(
        prompt + suffix,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
        validator=_extract_json_object,
    )
