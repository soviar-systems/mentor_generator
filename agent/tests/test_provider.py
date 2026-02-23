"""LiteLLMProvider factory tests — 0 API calls.

Tests create_provider() and LiteLLMProvider construction only.
No actual LLM calls are made.
"""

from __future__ import annotations

import os

from agent.provider import LiteLLMProvider, create_provider
from agent.settings import DEFAULTS


def test_create_provider_defaults():
    """Factory with minimal config returns provider with default model."""
    config = {"model": DEFAULTS["model"]}
    provider = create_provider(config)

    assert isinstance(provider, LiteLLMProvider)
    assert provider.model == DEFAULTS["model"]
    assert provider.api_base == ""


def test_create_provider_with_api_base():
    """api_base from config is passed through to provider."""
    config = {"model": DEFAULTS["model"], "api_base": "http://localhost:11434"}
    provider = create_provider(config)

    assert provider.api_base == "http://localhost:11434"


def test_inject_api_keys_sets_env(monkeypatch):
    """Named API keys from config are promoted to environment variables."""
    from agent.main import _inject_api_keys

    # Guarantee clean env — monkeypatch restores originals at teardown,
    # even though _inject_api_keys writes to os.environ directly.
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    cfg = {
        "GEMINI_API_KEY": "AIza-test-key",
        "ANTHROPIC_API_KEY": "sk-ant-test-key",
    }
    _inject_api_keys(cfg)

    assert os.environ["GEMINI_API_KEY"] == "AIza-test-key"
    assert os.environ["ANTHROPIC_API_KEY"] == "sk-ant-test-key"


def test_inject_api_keys_skips_non_matching(monkeypatch):
    """Lowercase keys, empty values, and non-matching patterns are skipped."""
    from agent.main import _inject_api_keys

    # Use sentinel values so we test what the function *changes*,
    # not what the machine env happens to contain.
    _SENTINEL = "__test_sentinel__"
    for key in ("gemini_api_key", "GEMINI_API_KEY", "MY_SECRET"):
        monkeypatch.setenv(key, _SENTINEL)

    cfg = {
        "gemini_api_key": "should-skip-lowercase",  # lowercase — skip
        "GEMINI_API_KEY": "",                        # empty value — skip
        "MY_SECRET": "not-an-api-key",               # no _API_KEY suffix — skip
    }
    _inject_api_keys(cfg)

    # Sentinels must survive — function must not have touched these keys.
    assert os.environ["gemini_api_key"] == _SENTINEL
    assert os.environ["GEMINI_API_KEY"] == _SENTINEL
    assert os.environ["MY_SECRET"] == _SENTINEL
