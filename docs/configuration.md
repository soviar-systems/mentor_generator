# Configuration Reference

All settings are configured via YAML files. The agent loads them in layers — later files override earlier ones:

```
1. Code defaults   (agent/settings.py DEFAULTS)
2. Global config   (~/.mentor.generator.config.yml)    ← user preferences, API keys
3. Local config    (./.mentor.generator.config.yml)     ← project overrides
```

**Where to put API keys**: use the global config (`~/.mentor.generator.config.yml`) in your
home directory. The local config (`./.mentor.generator.config.yml`) lives inside the project
and risks being committed to version control — even though this repo's `.gitignore` excludes
it, forks and copies may not. Never put secrets in a file that sits inside a git repository.

Any key below can be set in either config file. Copy this entire block into
`~/.mentor.generator.config.yml` and uncomment what you need.

---

## All Settings

```yaml
# =============================================================================
# LLM — Creative Stage
# =============================================================================
# The main LLM that generates persona, curriculum, and creative content.
# One API call per pipeline run.

# Model in litellm format: provider/model-name.
# Examples:
#   gemini/gemini-2.5-flash          — Google Gemini (default)
#   gemini/gemini-2.5-pro            — Google Gemini, higher quality
#   ollama_chat/gemma3:27b           — local Ollama, no API key needed
#   anthropic/claude-sonnet-4-5-20250514  — Anthropic
#   openai/gpt-4o                    — OpenAI
# Full list: https://docs.litellm.ai/docs/providers
model: gemini/gemini-2.5-flash

# API key passed directly to the provider.
# When empty, litellm falls back to standard env vars
# (GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.).
# Not needed for local models (Ollama).
api_key: ""

# Custom API endpoint URL. Only needed for self-hosted or proxy setups.
# Example: http://my-gateway:8080/v1
api_base: ""


# =============================================================================
# LLM — Interview Stage
# =============================================================================
# Optional LLM that translates questionnaire questions to the user's language.
# When interview_model is empty, the questionnaire runs in English (0 API calls).
# A small/local model works well here (~18 short calls per run).
# Translations are cached — subsequent runs for the same language cost 0 calls.

# Model for translating interview questions.
# Leave empty to skip translation and use English.
# Example: ollama_chat/gemma3:12b
interview_model: ""

# API key for the interview model.
# Falls back to api_key above if empty.
interview_api_key: ""

# API endpoint for the interview model.
# Falls back to api_base above if empty.
# Example: http://localhost:11434  (Ollama on non-default port)
interview_api_base: ""


# =============================================================================
# Network
# =============================================================================

# HTTPS proxy URL for cloud API calls (corporate environments).
# Only affects HTTPS connections — local traffic (e.g., Ollama) is not proxied.
# Example: http://corporate-proxy:8080
https_proxy: ""


# =============================================================================
# Paths
# =============================================================================

# Path to the output schema template.
template_path: ./agent/templates/mentor_system_prompt.template.json

# Directory for generated mentor files (mentor_system_prompt.yml + course_history).
output_dir: ./output

# Directory for pipeline artifacts:
# saved answers, cached LLM responses, interview translation cache, logs.
artifacts_dir: .mentor.generator.artifacts


# =============================================================================
# Collection
# =============================================================================

# Session length suggestion shown during DEPTH-FIRST strategy selection.
recommended_session_minutes: 45

# Allowed range for custom session length input.
session_minutes_min: 15
session_minutes_max: 180


# =============================================================================
# Pipeline
# =============================================================================

# Number of retry attempts after a failed creative LLM call.
api_retries: 2

# Delay in seconds between retries.
api_retry_delay_sec: 5.0


# =============================================================================
# Logging
# =============================================================================

# Console log level: debug, info, warning, error.
# The log file always captures debug level regardless of this setting.
log_level: info

# Directory and filename for the log file.
log_file_dir: .mentor.generator.artifacts
log_file_name: agent.log
```

---

## Quick-Start Examples

**Minimal** — Gemini cloud, English interview:
```yaml
model: gemini/gemini-2.5-flash
api_key: "AIza..."
```

**Cloud + localized interview:**
```yaml
model: gemini/gemini-2.5-flash
api_key: "AIza..."
interview_model: ollama_chat/gemma3:12b
```

**Fully local** — no cloud, no API key:
```yaml
model: ollama_chat/gemma3:27b
interview_model: ollama_chat/gemma3:12b
```

**Corporate environment** — cloud + proxy:
```yaml
model: gemini/gemini-2.5-flash
api_key: "AIza..."
https_proxy: "http://corporate-proxy:8080"
interview_model: ollama_chat/gemma3:12b
```
