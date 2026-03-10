"""
Centralized string resolution for multi-language support.

Loads string tables from fixtures/strings/{lang}.yaml and resolves
keys like "atc.cleared_takeoff_hdg_alt" with variable substitution.

Audio files are optional — the resolver returns the path but the
frontend checks existence before playing.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml

from django.conf import settings

STRINGS_DIR = Path(settings.BASE_DIR) / "fixtures" / "strings"
AUDIO_BASE_URL = settings.STATIC_URL + "audio"

SUPPORTED_LANGUAGES = {
    "en": "English",
    "es": "Español",
}

DEFAULT_LANGUAGE = "en"


@lru_cache(maxsize=8)
def _load_string_table(lang: str) -> dict:
    """Load and cache a language's string table."""
    path = STRINGS_DIR / f"{lang}.yaml"
    if not path.exists():
        if lang != DEFAULT_LANGUAGE:
            return _load_string_table(DEFAULT_LANGUAGE)
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _resolve_key(table: dict, key: str) -> dict | None:
    """Resolve a dotted key like 'atc.cleared_takeoff_hdg_alt' from nested dict."""
    parts = key.split(".", 1)
    if len(parts) == 1:
        val = table.get(parts[0])
        return val if isinstance(val, dict) else None
    category = parts[0]
    entry_key = parts[1]
    category_dict = table.get(category, {})
    if isinstance(category_dict, dict):
        val = category_dict.get(entry_key)
        return val if isinstance(val, dict) else None
    return None


def resolve(key: str, variables: dict | None = None, lang: str = DEFAULT_LANGUAGE) -> dict:
    """Resolve a string key to text and audio URL.

    Args:
        key: Dotted string key, e.g. "atc.cleared_takeoff_hdg_alt"
        variables: Dict of {variable_name: value} for template substitution
        lang: Language code, e.g. "en", "es"

    Returns:
        {
            "text": "Resolved text with variables substituted",
            "audio_url": "/static/audio/en/atc/cleared_takeoff_hdg_alt.mp3",
            "key": "atc.cleared_takeoff_hdg_alt",
        }
    """
    variables = variables or {}
    table = _load_string_table(lang)
    entry = _resolve_key(table, key)

    if entry is None and lang != DEFAULT_LANGUAGE:
        # Fall back to default language
        table = _load_string_table(DEFAULT_LANGUAGE)
        entry = _resolve_key(table, key)

    if entry is None:
        # Key not found — return the key itself as text
        return {"text": key, "audio_url": None, "key": key}

    text = entry.get("text", key)

    # Substitute {variables}
    for var_name, var_value in variables.items():
        text = text.replace(f"{{{var_name}}}", str(var_value))

    # Build audio URL: atc.cleared_takeoff → /static/audio/en/atc/cleared_takeoff.mp3
    audio_path = key.replace(".", "/")
    audio_url = f"{AUDIO_BASE_URL}/{lang}/{audio_path}.mp3"

    return {"text": text, "audio_url": audio_url, "key": key}


def resolve_payload(payload: dict, lang: str = DEFAULT_LANGUAGE) -> dict:
    """Resolve all string keys in an event payload.

    Looks for keys ending in _key (atc_text_key, narration_key, coaching_key)
    and resolves them, adding resolved text and audio URLs to the payload.

    The original payload is not modified — returns a new dict.
    """
    resolved = dict(payload)
    variables = payload.get("variables", {})

    # ATC text
    if "atc_text_key" in payload:
        r = resolve(payload["atc_text_key"], variables, lang)
        resolved["atc_text"] = r["text"]
        resolved["atc_audio_url"] = r["audio_url"]

    # Narration
    if "narration_key" in payload:
        r = resolve(payload["narration_key"], variables, lang)
        resolved["narration"] = r["text"]
        resolved["narration_audio_url"] = r["audio_url"]

    # Coaching
    if "coaching_key" in payload:
        r = resolve(payload["coaching_key"], variables, lang)
        resolved["coaching_if_wrong"] = r["text"]

    # Decision point option text (for i18n of option labels)
    if "decision_points" in payload:
        resolved_dps = []
        for dp in payload["decision_points"]:
            resolved_dp = dict(dp)
            if "prompt_key" in dp:
                r = resolve(dp["prompt_key"], variables, lang)
                resolved_dp["prompt"] = r["text"]
            if "options" in dp:
                resolved_opts = []
                for opt in dp["options"]:
                    resolved_opt = dict(opt)
                    if "text_key" in opt:
                        r = resolve(opt["text_key"], variables, lang)
                        resolved_opt["text"] = r["text"]
                    resolved_opts.append(resolved_opt)
                resolved_dp["options"] = resolved_opts
            resolved_dps.append(resolved_dp)
        resolved["decision_points"] = resolved_dps

    return resolved


def clear_cache():
    """Clear the string table cache (useful after loading new fixtures)."""
    _load_string_table.cache_clear()
