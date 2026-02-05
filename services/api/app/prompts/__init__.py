"""
Prompt library loader for the Life Story Chatbot.

Loads prompt templates from YAML files and supports variable interpolation.

Usage:
    from app.prompts import get_prompt, render_prompt, get_safety_response

    # Get a raw prompt string
    base = get_prompt("system", "base")

    # Get a prompt with variables filled in
    prompt = render_prompt("system", "with_summary", base=base, summary="...")

    # Get a safety response template
    response = get_safety_response("medical")
"""

from pathlib import Path
from typing import Dict

import yaml

_PROMPTS_DIR = Path(__file__).parent
_cache: Dict[str, dict] = {}


def _load(file: str) -> dict:
    """Load and cache a YAML prompt file."""
    if file not in _cache:
        path = _PROMPTS_DIR / f"{file}.yaml"
        with open(path) as f:
            _cache[file] = yaml.safe_load(f)
    return _cache[file]


def get_prompt(file: str, key: str) -> str:
    """Get a raw prompt string from a YAML file.

    Args:
        file: YAML filename without extension (e.g. "system", "summary")
        key: Top-level key within the YAML file
    """
    data = _load(file)
    return data[key].strip()


def render_prompt(file: str, key: str, **variables) -> str:
    """Get a prompt with {variables} interpolated.

    Args:
        file: YAML filename without extension
        key: Top-level key within the YAML file
        **variables: Values to substitute into {placeholders}
    """
    template = get_prompt(file, key)
    return template.format(**variables).strip()


def get_safety_response(category: str) -> str:
    """Get a safety response template by category name.

    Args:
        category: One of "medical", "legal", "crisis", "inappropriate"
    """
    return get_prompt("safety", category)


def reload():
    """Clear the prompt cache. Useful during development."""
    _cache.clear()
