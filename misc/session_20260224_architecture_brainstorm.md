# Session Context: Architecture Restructuring Brainstorm (2026-02-24)

## Session Purpose

Brainstorming session to design the architecture restructuring of the `agent/` package. No code changes — only plan and context files produced.

## Outputs

- **Plan**: `misc/plan/plan_20260224_architecture_restructure_data_logic_separation.md`
  - 3 independent sub-plans: A (data extraction), B (sub-packages), C (one-shot translation)
  - Execute in separate sessions, in order: A → B → C

## Key Decisions Made (User-Approved)

1. **Flat sub-packages**: `agent/interview/`, `agent/mentor/` — no `tools/` nesting level. Shared infra (`settings.py`, `provider.py`, `artifacts.py`) stays at `agent/` root.

2. **Pure JSON for all data files**: No `.txt` or `.md` data files. Multi-line content stored as JSON arrays where each line is a list item. ALL text values are arrays — even single-line ones (`["Enter 1 or 2: "]`). Loader is always `"\n".join(value)`, no type-branching.

3. **`inject_api_keys()` → `settings.py`**: Moved from `main.py` to shared infrastructure. Not mentor-specific — future tools (researcher) will also need it.

4. **3 independent plans**: A (data extraction, no moves) → B (sub-package restructuring) → C (one-shot translation + ADRs). Each plan is independently testable with `uv run pytest agent/tests/ -v`.

## Codebase Analysis (Save Future Agents from Re-Reading)

### Current File Inventory (agent/)

| File | Lines | Purpose | Data-Logic Coupling |
|------|-------|---------|---------------------|
| `collector.py` | 309 | CLI questionnaire | 18+ hardcoded string constants (questions, menus, error messages, locale map). Lines 44-96 are pure data. |
| `interviewer.py` | 145 | Translation + cache | `SYSTEM_PROMPT` constant (line 24-29). Per-text translation loop at line 123. |
| `creative_engine.py` | 321 | LLM call + parser | `SYSTEM_PROMPT` (48-51), `PROMPT_TEMPLATE` (53-116), `_SECTION_LABELS` (222-226). |
| `template_engine.py` | ~200 | Placeholder injection | `RUNTIME_TEMPLATE_KEYS` (single source of truth). Helper heuristics `_assess_level`, `_infer_depth`, `_split_items`. |
| `validator.py` | ~100 | Structural validation | `REQUIRED_TOP_LEVEL_KEYS` list. 5 check functions. |
| `main.py` | 185 | Pipeline orchestrator | `_inject_api_keys()` (lines 30-43) — shared, moves to settings.py. |
| `settings.py` | ~100 | Layered config | `DEFAULTS` dict, `load_settings()`, `setup_logging()`. |
| `provider.py` | ~60 | LLM abstraction | `LLMProvider` ABC, `LiteLLMProvider` dataclass, `create_provider()` factory. |
| `artifacts.py` | ~80 | Save/load state | `save_answers()`, `load_answers()`, `save_creative_response()`, `load_creative_response()`. |
| `yaml_writer.py` | ~40 | YAML output | `write_mentor_file()`. |

### Import Graph (Current)

```
main.py
├── collector.py ← settings.py
│   └── interviewer.py ← provider.py
├── creative_engine.py ← collector.py (UserAnswers), provider.py, settings.py
├── template_engine.py ← collector.py (UserAnswers), creative_engine.py (CreativePayload)
├── validator.py ← template_engine.py (RUNTIME_TEMPLATE_KEYS)
├── yaml_writer.py ← settings.py
├── artifacts.py ← collector.py (UserAnswers)
├── provider.py (standalone)
└── settings.py (standalone)
```

### Import Graph (After Restructuring)

```
mentor/main.py
├── interview/collector.py ← settings.py
│   └── interview/translator.py ← provider.py
├── mentor/creative_engine.py ← interview/collector.py (UserAnswers), provider.py, settings.py
├── mentor/template_engine.py ← interview/collector.py (UserAnswers), mentor/creative_engine.py
├── mentor/validator.py ← mentor/template_engine.py (RUNTIME_TEMPLATE_KEYS)
├── mentor/yaml_writer.py ← settings.py
├── artifacts.py ← interview/collector.py (UserAnswers)
├── provider.py (standalone)
└── settings.py (standalone, + inject_api_keys)
```

### Translation Flow (Current Problem)

`interviewer.py:123` — translates texts one-by-one:
```python
for text in to_translate:
    translated = _translate_one(provider, language, text)  # 1 LLM call per text
```

For a fresh Russian questionnaire: ~13 separate LLM calls. After cache: 0 calls.

The greeting (Q0) is translated separately before the user picks their language. After that, all remaining texts are translated. Two distinct translation moments:
1. Greeting → detected locale language (1 text, before language choice)
2. All remaining texts → user's chosen dialogue_language (12 texts, after Q0)

### Test Patterns to Follow

- All tests offline (0 API calls)
- Use `DEFAULTS["key"]` from settings.py, not hardcoded values
- Use `monkeypatch` sentinels for env var testing
- Golden fixtures in `agent/tests/fixtures/`
- MockProvider pattern: configurable responses, call tracking (see `test_interviewer.py`)

### ADR Numbering

Existing spoke ADRs: 26001-26009. New ADRs start at **26010**:
- ADR-26010: Data file formats (Plan A)
- ADR-26011: Sub-package architecture (Plan B)
- ADR-26012: One-shot batch translation (Plan C)

ADR format: see `docs/architecture/adr/` for examples. Required sections: Date, Status, Context, Decision, Consequences (Positive + Negative with Mitigations), Alternatives, References, Participants.

### Format Decision Context

The pure-JSON choice is grounded in the two-audience principle from:
`ai_engineering_book/ai_system/3_prompts/format_as_architecture_signal_noise_in_prompt_delivery.md`

Key insight: agent data files are **compiler input** (consumed by Python's `json.load()`), not LLM input. The 20-30% structural noise of JSON is irrelevant for Python parsing. The generated `mentor_system_prompt.yml` output remains YAML (runtime format for LLMs).

### Risk Areas

1. **`interview_source_hash()` stability**: After extracting to JSON, hash computation should switch to hashing the JSON file content directly (not reconstructing the text list). This is simpler and guarantees consistency.

2. **`settings["template_path"]` default change**: `./agent/templates/...` → `./agent/mentor/data/templates/...`. Users with explicit config are unaffected. Document in CHANGELOG.

3. **`creative_prompt.txt` placeholder markers**: The `PROMPT_TEMPLATE` uses Python `{placeholder}` syntax inside JSON strings. This works fine — JSON strings can contain `{` and `}` characters, and `"\n".join()` + `.format()` processes them correctly.

4. **Batch translation reliability**: LLMs may not reliably produce `[N]` markers. Mitigation: parser falls back to original English for missing items.
