from __future__ import annotations

import json
import re
from typing import Any

try:
    from llm_client import call_llm_json
except Exception:  # pragma: no cover - package import path fallback.
    from .llm_client import call_llm_json

PROMPT = """You are helping identify likely opponent assets for a public, unclassified training wargame.
Do not call this OSINT. Call it Opponent Asset Identification.
Use plain English. Avoid jargon. Give concise, useful results.
Every output must be specific to the scenario and Blue selected assets. Do not use canned examples.
Every string field must be non-empty.

Scenario: {scenario}
Adversary: {adversary}
Blue selected assets: {blue_assets}

Return JSON only:
{{
  "classification":"PUBLIC-SOURCE ESTIMATE",
  "scenario":"{scenario}",
  "adversary":"{adversary}",
  "threat_level":"HIGH",
  "confidence":75,
  "summary":"short plain English summary",
  "predicted_assets":[{{"name":"asset name","category":"category","quantity":"plain estimate","confidence":75,"threat_to_blue":"HIGH","capability":"why it matters in plain English","counter":"how Blue can reduce risk"}}],
  "key_warnings":["warning 1","warning 2","warning 3"],
  "recommended_blue_additions":["addition 1","addition 2","addition 3"],
  "historical_precedent":"brief real-world echo, not overclaiming exact match"
}}
"""

def _parse_json(raw: str) -> dict[str, Any]:
    text = re.sub(r"^```json\s*|^```\s*|\s*```$", "", raw.strip()).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            raise
        data = json.loads(match.group())
    if not isinstance(data, dict):
        raise ValueError("Intel response was not a JSON object.")
    return data


def _text(value: Any) -> str:
    return str(value or "").strip()


def _number(value: Any, field: str) -> int:
    try:
        number = int(round(float(value)))
    except Exception as exc:
        raise ValueError(f"Intel response missing numeric {field}.") from exc
    return max(0, min(100, number))


def _text_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"Intel response missing {field}.")
    rows = [_text(item) for item in value]
    rows = [item for item in rows if item]
    if not rows:
        raise ValueError(f"Intel response returned an empty {field}.")
    return rows


def _normalize_asset(item: Any, index: int) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError(f"Intel response asset {index + 1} was not an object.")
    asset = {
        "name": _text(item.get("name")),
        "category": _text(item.get("category")),
        "quantity": _text(item.get("quantity")),
        "confidence": _number(item.get("confidence"), f"predicted_assets[{index}].confidence"),
        "threat_to_blue": _text(item.get("threat_to_blue")),
        "capability": _text(item.get("capability")),
        "counter": _text(item.get("counter")),
    }
    missing = [key for key, value in asset.items() if key != "confidence" and not value]
    if missing:
        raise ValueError(f"Intel response asset {index + 1} missing {', '.join(missing)}.")
    return asset


def _normalize_briefing(data: dict[str, Any], scenario: str, adversary: str) -> dict[str, Any]:
    predicted_assets = data.get("predicted_assets")
    if not isinstance(predicted_assets, list) or not predicted_assets:
        raise ValueError("Intel response did not include predicted_assets.")

    briefing = {
        "classification": _text(data.get("classification")) or "PUBLIC-SOURCE ESTIMATE",
        "scenario": _text(data.get("scenario")) or scenario,
        "adversary": _text(data.get("adversary")) or adversary,
        "threat_level": _text(data.get("threat_level")),
        "confidence": _number(data.get("confidence"), "confidence"),
        "summary": _text(data.get("summary")),
        "predicted_assets": [_normalize_asset(item, index) for index, item in enumerate(predicted_assets)],
        "key_warnings": _text_list(data.get("key_warnings"), "key_warnings"),
        "recommended_blue_additions": _text_list(data.get("recommended_blue_additions"), "recommended_blue_additions"),
        "historical_precedent": _text(data.get("historical_precedent")),
    }
    missing = [key for key in ["threat_level", "summary", "historical_precedent"] if not briefing[key]]
    if missing:
        raise ValueError(f"Intel response missing {', '.join(missing)}.")
    return briefing

def generate_intel_briefing(scenario: str, adversary: str, blue_assets: list) -> dict:
    prompt = PROMPT.format(
        scenario=scenario,
        adversary=adversary,
        blue_assets=json.dumps(blue_assets),
    )
    raw = call_llm_json(
        prompt,
        max_tokens=2400,
        temperature=0.25,
    )
    try:
        return _normalize_briefing(_parse_json(raw), scenario, adversary)
    except Exception as first_error:
        repair_prompt = f"""{prompt}

The previous model output was invalid or incomplete.
Error: {type(first_error).__name__}: {first_error}
Previous output:
{raw[:4000]}

Return one complete JSON object that satisfies the schema. Do not omit any field."""
        repaired = call_llm_json(repair_prompt, max_tokens=2400, temperature=0)
        return _normalize_briefing(_parse_json(repaired), scenario, adversary)
