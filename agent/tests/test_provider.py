"""LiteLLMProvider factory tests — 0 API calls.

Tests create_provider() and LiteLLMProvider construction only.
No actual LLM calls are made.
"""

from __future__ import annotations

from agent.provider import LiteLLMProvider, create_provider
from agent.settings import DEFAULTS


def test_create_provider_defaults():
    """Factory with minimal config returns provider with default model."""
    config = {"model": DEFAULTS["model"]}
    provider = create_provider(config)

    assert isinstance(provider, LiteLLMProvider)
    assert provider.model == DEFAULTS["model"]
    assert provider.api_key == ""
    assert provider.api_base == ""


def test_create_provider_with_api_key():
    """api_key from config is passed through to provider."""
    config = {"model": DEFAULTS["model"], "api_key": "test-key-123"}
    provider = create_provider(config)

    assert provider.api_key == "test-key-123"


def test_create_provider_with_api_base():
    """api_base from config is passed through to provider."""
    config = {"model": DEFAULTS["model"], "api_base": "http://localhost:11434"}
    provider = create_provider(config)

    assert provider.api_base == "http://localhost:11434"


def test_create_provider_empty_api_key_falls_back():
    """Empty api_key means litellm will use env vars (tested at factory level)."""
    config = {"model": DEFAULTS["model"], "api_key": ""}
    provider = create_provider(config)

    assert provider.api_key == ""
