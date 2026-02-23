# Plan: litellm Provider + LLM Interview + Proxy (v0.43.0)

## Context

Three problems converge into one architectural change:

1. **`google-generativeai` is deprecated** (support ended Nov 30 2025). Must migrate.
2. **Interview is English-only**. Users need questions in their chosen language. Small models (Gemma 12B/27B) can handle this cheaply.
3. **Config UX issues**: API key requires shell env var (`~/.bashrc`), no proxy support for corporate environments.

**Key insight**: Aider solves multi-provider routing via **litellm** — a universal LLM client that uses `provider/model-name` format (e.g., `gemini/gemini-2.5-flash`, `ollama_chat/gemma3:12b`). One package replaces provider-specific SDKs. The user wants the same capability with `model` / `interview_model` parameters (like aider's `--model` / `--editor-model`).

**litellm also supports passing `api_key` directly** to `completion()` — meaning users can set keys in our config file instead of `~/.bashrc`.

---

## Part 1: Provider — litellm replaces google-generativeai

### Architecture change

```
BEFORE:  google-generativeai SDK → Gemini cloud only, api_key from env var
AFTER:   litellm.completion()    → any provider, api_key from config file
```

Model format follows litellm/aider convention:
- `gemini/gemini-2.5-flash` → Google Gemini API
- `ollama_chat/gemma3:27b` → local Ollama
- `anthropic/claude-sonnet-4-5-20250514` → Anthropic (bonus, free)
- `openai/gpt-4o` → OpenAI (bonus, free)

### `pyproject.toml` — swap dependency

```toml
dependencies = [
    "pyyaml>=6.0",
    "litellm>=1.50",     # was: google-generativeai>=0.8.0
]
```

### `agent/provider.py` — rewrite provider

Replace `GeminiProvider` with `LiteLLMProvider`:

```python
@dataclass
class LiteLLMProvider(LLMProvider):
    """Universal LLM provider via litellm. Supports 100+ models."""
    model: str = "gemini/gemini-2.5-flash"
    api_key: str = ""       # passed directly to completion(), not env var
    api_base: str = ""      # for custom endpoints (optional)

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        from litellm import completion

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs = {"model": self.model, "messages": messages}
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.api_base:
            kwargs["api_base"] = self.api_base

        response = completion(**kwargs)
        return response.choices[0].message.content
```

Update `create_provider()` factory — simplified, no more provider switching:

```python
def create_provider(config: dict) -> LLMProvider:
    return LiteLLMProvider(
        model=config.get("model", "gemini/gemini-2.5-flash"),
        api_key=config.get("api_key", ""),
        api_base=config.get("api_base", ""),
    )
```

Keep: `LLMProvider` ABC (unchanged), `extract_json()` helper (unchanged).
Delete: `GeminiProvider` class.
Remove: `provider` setting (litellm determines provider from model prefix).

### `agent/settings.py` — new DEFAULTS

```python
DEFAULTS: dict = {
    # --- LLM (creative stage) ---
    "model": "gemini/gemini-2.5-flash",     # litellm format: provider/model
    "api_key": "",                           # NEW: direct API key (no more env var indirection)
    "api_base": "",                          # NEW: custom endpoint URL (optional)

    # --- LLM (interview stage) ---
    "interview_model": "",                   # NEW: empty = skip LLM interview, use English
    "interview_api_key": "",                 # NEW: separate key for interview provider (optional)
    "interview_api_base": "",               # NEW: separate endpoint (optional, e.g. Ollama host)

    # --- Network ---
    "https_proxy": "",                       # NEW: HTTPS proxy for cloud models (Part 3)

    # removed: "provider", "api_key_env"
    # ... rest unchanged (template_path, output_dir, etc.) ...
}
```

### API key resolution — solved

With litellm, `api_key` can be passed directly to `completion()`. The user's workflow becomes:

```yaml
# ~/.mentor.generator.config.yml
model: gemini/gemini-2.5-flash
api_key: "AIza..."   # ← right here, no ~/.bashrc needed
```

For Ollama local models, no `api_key` needed at all:

```yaml
model: ollama_chat/gemma3:27b
interview_model: ollama_chat/gemma3:12b
```

If `api_key` is empty in config, litellm falls back to standard env vars (`GEMINI_API_KEY`, `OPENAI_API_KEY`, etc.) — backward compatible for users who prefer env vars.

---

## Part 2: LLM-Powered Interview

Pipeline changes from `Collect (0 API) → Create (1 API) → Compile (0 API)` to:
```
Collect (N API via interview_model) → Create (1 API via model) → Compile (0 API)
```

### Design: LLM as translator, code keeps control

The LLM adapts each question to the user's language. The code maintains the structured 11-field collection flow (`UserAnswers`). The LLM does NOT conduct a free-form interview.

**Why not free-form?** The fields are consumed by `creative_engine.py` and `template_engine.py` with specific expectations. Free-form could miss fields or produce ambiguous data. The Q7 strategy selection has deterministic menu logic that must be preserved.

### Flow

1. **Q0 (language)**: detect system locale via `locale.getlocale()`:
   - If `ru_*` → show Russian greeting (current behavior)
   - If `en_*` or unknown → show English greeting
   - Other locales + interview LLM available → LLM translates greeting to detected locale + English fallback
   - User types their preferred language → stored as `dialogue_language`

2. **Q1–Q6, Q8–Q9**: for each question:
   - `interviewer.localize_question(question_text)` → translated question
   - User answers in their language
   - `interviewer.normalize_answer(user_input, field_name)` → English value for `UserAnswers`

3. **Q7 (strategy)**: deterministic menu stays "Enter 1 or 2":
   - `interviewer.localize_strategy_menu()` → translated menu text
   - Input logic unchanged (1 or 2, session minutes, deadline date)
   - Follow-up prompts also localized

### New file: `agent/interviewer.py`

```python
class Interviewer:
    """Adapts interview questions to user's language via LLM."""

    def __init__(self, provider: LLMProvider, language: str):
        self.provider = provider
        self.language = language

    def localize_question(self, question_text: str) -> str:
        """Translate question to user's language."""
        ...  # one short LLM call

    def normalize_answer(self, user_input: str, field_name: str) -> str:
        """Extract/normalize answer to English for UserAnswers."""
        ...  # one short LLM call

    def localize_strategy_menu(self) -> str:
        """Translate strategy selection menu."""
        ...  # one short LLM call

    def localize_text(self, text: str) -> str:
        """Generic text translation for follow-up prompts."""
        ...  # one short LLM call
```

### Modified: `agent/collector.py`

Signature gains optional parameter:

```python
def collect_interactive(interview_provider: LLMProvider | None = None) -> UserAnswers:
```

- `None` → current behavior (hardcoded English, 0 API calls)
- Provider → create `Interviewer(provider, dialogue_language)` after Q0

### Modified: `agent/main.py`

Before Stage 1, create interview provider if configured:

```python
interview_provider = None
if not args.skip_collect and settings.get("interview_model"):
    try:
        interview_config = {
            "model": settings["interview_model"],
            "api_key": settings.get("interview_api_key") or settings.get("api_key", ""),
            "api_base": settings.get("interview_api_base") or settings.get("api_base", ""),
        }
        interview_provider = create_provider(interview_config)
    except Exception as e:
        logger.warning("Interview LLM unavailable (%s), using English", e)
```

### Graceful degradation

If interview LLM is unavailable → logs warning, falls back to English-only interview. No crash.

### API call budget

~18 short calls to a small model (8 localizations + 8 normalizations + ~2 menu/follow-up). With Gemma 12B: ~2–5 sec, almost free.

---

## Part 3: HTTPS Proxy Support

### Why `https_proxy` only (not `http_proxy`)

Ollama runs on `http://localhost:11434`. A generic `http_proxy` would route local Ollama traffic through proxy, breaking it. `https_proxy` only affects HTTPS connections (cloud API calls).

### Implementation

In `agent/main.py`, at startup (before any provider calls):

```python
https_proxy = settings.get("https_proxy", "")
if https_proxy:
    os.environ["HTTPS_PROXY"] = https_proxy
    logger.info("HTTPS proxy set: %s", https_proxy)
```

litellm uses httpx/requests under the hood, which respect `HTTPS_PROXY` environment variable. Setting it at process level ensures all cloud API calls go through the proxy.

### Config example

```yaml
# ~/.mentor.generator.config.yml
model: gemini/gemini-2.5-flash
api_key: "AIza..."
https_proxy: "http://corporate-proxy:8080"
interview_model: ollama_chat/gemma3:12b
```

---

## Part 4: Tests

### New: `agent/tests/test_provider.py`

1. `test_create_provider_defaults` — returns LiteLLMProvider with correct model
2. `test_create_provider_with_api_key` — api_key passed through
3. `test_create_provider_with_api_base` — api_base passed through
4. `test_create_provider_empty_api_key` — empty string, litellm falls back to env vars

All offline, 0 API calls. Test factory logic only.

### New: `agent/tests/test_interviewer.py`

```python
class MockProvider(LLMProvider):
    def __init__(self, responses: list[str]):
        self.responses = list(responses)
        self.calls = []
    def generate(self, prompt, system_prompt=""):
        self.calls.append((prompt, system_prompt))
        return self.responses.pop(0)
```

1. `test_localize_question` — correct system prompt, returns translated text
2. `test_normalize_answer` — extracts English value from localized input
3. `test_localize_strategy_menu` — preserves [1]/[2] numbering

All offline, 0 API calls.

### Existing: `agent/tests/test_pipeline.py`

**Unchanged.** These tests never import `provider.py` or `collector.py`.

---

## Part 5: Manual Smoke Tests

1. **Local Ollama, English (no interview_model set)**:
   ```bash
   # Config: model: ollama_chat/gemma3:27b
   uv run python -m agent.main
   ```

2. **Cloud Gemini, localized interview**:
   ```bash
   # Config: model: gemini/gemini-2.5-flash, interview_model: ollama_chat/gemma3:12b
   uv run python -m agent.main
   ```

3. **Recompile (no provider needed)**:
   ```bash
   uv run python -m agent.main --skip-api
   ```

4. **Automated tests**:
   ```bash
   uv run pytest agent/tests/ -v
   ```

---

## Files Summary

| Action   | File                              | What changes                                    |
|----------|-----------------------------------|-------------------------------------------------|
| Modify   | `pyproject.toml`                  | `google-generativeai` → `litellm`               |
| Rewrite  | `agent/provider.py`               | GeminiProvider → LiteLLMProvider, new factory   |
| Modify   | `agent/settings.py`               | New keys, remove provider/api_key_env           |
| Modify   | `agent/collector.py`              | Accept optional `interview_provider` param      |
| Modify   | `agent/main.py`                   | Interview provider creation, proxy setup        |
| Create   | `agent/interviewer.py`            | Interviewer class (localize/normalize)          |
| Create   | `agent/tests/test_provider.py`    | LiteLLMProvider factory tests                   |
| Create   | `agent/tests/test_interviewer.py` | Interviewer unit tests with MockProvider        |
| Modify   | `CLAUDE.md`                       | Update architecture, settings, dev docs         |
| Modify   | `CHANGELOG.md`                    | v0.43.0 entry                                   |

## Config Examples

**Minimal (Gemini cloud, English interview)**:
```yaml
model: gemini/gemini-2.5-flash
api_key: "AIza..."
```

**Full (cloud + local interview + proxy)**:
```yaml
model: gemini/gemini-2.5-flash
api_key: "AIza..."
https_proxy: "http://proxy:8080"
interview_model: ollama_chat/gemma3:12b
```

**Fully local (no cloud, no API key)**:
```yaml
model: ollama_chat/gemma3:27b
interview_model: ollama_chat/gemma3:12b
```

## Version: v0.43.0
