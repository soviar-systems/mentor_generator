# Plan: Provider-Specific Named API Keys (Config-to-Env Bridge)

## Context

Currently the config uses a generic `api_key` field that must be manually swapped when switching between LLM providers (Gemini → Anthropic → OpenAI). The user wants aider-like behavior: store provider-specific keys (`GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`) in the config file, and the agent auto-resolves the correct key based on the model prefix. This is a clean break — `api_key` and `interview_api_key` are removed entirely.

**Before:**
```yaml
model: gemini/gemini-2.5-flash
api_key: "AIza..."              # generic, must swap when changing providers
interview_model: anthropic/...
interview_api_key: "sk-ant-..."  # separate generic key
```

**After:**
```yaml
GEMINI_API_KEY: "AIza..."
ANTHROPIC_API_KEY: "sk-ant-..."
model: gemini/gemini-2.5-flash        # → auto-picks GEMINI_API_KEY
interview_model: anthropic/...         # → auto-picks ANTHROPIC_API_KEY
```

## Design: Config-to-Env Bridge

litellm already maps model prefixes to env vars (`gemini/` → `GEMINI_API_KEY`). We don't duplicate that mapping. Instead:

1. Early in `main.py`: scan config for keys matching `^[A-Z][A-Z0-9_]*_API_KEY$`, set as `os.environ[key]`
2. Remove `api_key` from `LiteLLMProvider` — litellm reads env vars automatically
3. No fallback, no deprecation — clean break

## Changes

### 1. `agent/settings.py` — Remove old keys from DEFAULTS

Remove two lines:
```python
"api_key": "",                           # line 30
"interview_api_key": "",                 # line 35
```

### 2. `agent/provider.py` — Remove api_key from provider

- Remove `api_key: str = ""` field from `LiteLLMProvider` dataclass (line 27)
- Remove `if self.api_key: kwargs["api_key"] = ...` from `generate()` (lines 39-40)
- Remove `api_key = config.get(...)` from `create_provider()` (line 82)
- Remove `api_key=api_key` from the return `LiteLLMProvider(...)` call (line 87)

### 3. `agent/main.py` — Add env bridge, simplify interview config

Add `_inject_api_keys()` function (before `main()`):
```python
import re
_API_KEY_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*_API_KEY$")

def _inject_api_keys(cfg: dict) -> None:
    for key, value in cfg.items():
        if _API_KEY_PATTERN.match(key) and isinstance(value, str) and value:
            os.environ[key] = value
            logger.debug("Injected API key from config: %s", key)
```

Call it in `main()` right before the HTTPS proxy block (line 37):
```python
_inject_api_keys(settings)
```

Simplify interview config (line 48-51) — remove `api_key` line:
```python
interview_config = {
    "model": settings["interview_model"],
    "api_base": settings.get("interview_api_base") or settings.get("api_base", ""),
}
```

### 4. `agent/tests/test_provider.py` — Update tests

- `test_create_provider_defaults`: remove `assert provider.api_key == ""` (line 20)
- **Delete** `test_create_provider_with_api_key` (lines 24-29)
- **Delete** `test_create_provider_empty_api_key_falls_back` (lines 40-45)
- Keep `test_create_provider_with_api_base` unchanged
- Add new test: `test_inject_api_keys_sets_env` — verify env bridge copies matching keys
- Add new test: `test_inject_api_keys_skips_non_matching` — verify lowercase/empty/non-matching keys are skipped

### 5. `docs/configuration.md` — Rewrite API key sections

Replace `api_key: ""` with provider-specific keys section. Replace `interview_api_key: ""` with a note that named keys handle everything. Update all quick-start examples.

### 6. `README.md` — Update quick start (line 33-34)

```yaml
model: gemini/gemini-2.5-flash
GEMINI_API_KEY: "your-api-key-here"
```

### 7. `CLAUDE.md` — Minor setting description updates

Remove mentions of `api_key` / `interview_api_key` from architecture description.

### 8. `CHANGELOG.md` — Version entry

Add breaking change entry for v0.44.0.

## Edge Cases

- **Config overrides OS env var**: `os.environ[key] = value` overwrites — config wins (consistent with layered config philosophy)
- **Old config with `api_key:`**: Loaded but nothing reads it → litellm auth error with clear message
- **Local models (Ollama)**: No `*_API_KEY` in config → bridge does nothing → works as before
- **Multi-provider** (different providers for model + interview_model): Both keys in config, both injected, litellm resolves each correctly

## Verification

1. `uv run pytest agent/tests/ -v` — all tests pass (0 API calls)
2. Manual: set `GEMINI_API_KEY` in config, run `uv run python -m agent.main` — full pipeline works
3. Manual: set two provider keys, use different providers for model/interview_model — both resolve correctly
