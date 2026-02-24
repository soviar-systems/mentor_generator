# Architecture Restructuring: Data-Logic Separation & Sub-Packages

## Context

The `agent/` package has grown organically through v0.42–v0.44. While the 3-stage pipeline is sound, the codebase has accumulated architectural debt:

1. **Data embedded in logic** — `collector.py` has 18+ hardcoded string constants (questions, menus, error messages). `creative_engine.py` has hardcoded LLM prompts and section labels. Changing a question or prompt requires editing Python code.
2. **Flat structure** — all 11 modules sit at the `agent/` root. As new tools (researcher) are planned, the flat layout won't scale.
3. **Per-text translation** — `interviewer.py` makes N separate LLM calls (up to 13) for translation. Should be 1 batch call.

This plan restructures `agent/` into sub-packages with externalized data files, and redesigns translation for efficiency. Three independent plans, executed in separate sessions.

---

## Decision: Pure JSON for All Data Files

All extracted data files use JSON. Multi-line content (LLM prompts, question text) is stored as JSON arrays where each line is a list item — joined with `"\n".join()` at load time. No `.txt` or `.md` data files.

**Uniform array type**: ALL text values are arrays, even single-line ones (e.g., `["Enter 1 or 2: "]`). No mixed string|array types. The loader always uses `"\n".join(value)` — no type-checking branches.

**Rationale**: machine-readable, validatable, parseable by any tool, consistent with ADR-26007 (JSON = compiler input). Uniform arrays eliminate type-branching bugs ("parse, don't validate" principle). Git diffs are clean (one line per array item). Grounded in the two-audience principle from `ai_engineering_book/ai_system/3_prompts/format_as_architecture_signal_noise_in_prompt_delivery.md` — these files are compiler input (consumed by Python), not LLM input.

---

## Target Directory Structure

```
agent/
├── __init__.py
├── __main__.py                    # delegates to mentor.main
├── settings.py                    # shared: layered config + inject_api_keys()
├── provider.py                    # shared: LLM abstraction
├── artifacts.py                   # shared: save/load pipeline state
├── interview/                     # sub-package: reusable interview tool
│   ├── __init__.py                # re-exports: UserAnswers, collect_interactive, interview_source_hash
│   ├── collector.py               # collection logic (loads data/)
│   ├── translator.py              # translation logic (renamed from interviewer.py)
│   └── data/
│       ├── questions.json         # all questions, menus, prompts, locale map
│       └── translator_prompt.json # system prompt + batch prompt template
├── mentor/                        # sub-package: mentor generator tool
│   ├── __init__.py                # re-exports: main
│   ├── main.py                    # pipeline orchestrator
│   ├── creative_engine.py         # LLM call + labeled text parser
│   ├── template_engine.py         # deterministic placeholder injection
│   ├── validator.py               # structural validation
│   ├── yaml_writer.py             # YAML output
│   ├── USAGE.md                   # post-generation user guide
│   └── data/
│       ├── creative_prompts.json  # system_prompt + prompt_template + section_labels
│       └── templates/
│           └── mentor_system_prompt.template.json
└── tests/                         # flat test dir (unchanged runner: uv run pytest agent/tests/ -v)
    ├── test_pipeline.py           # updated imports
    ├── test_provider.py           # updated imports
    ├── test_interviewer.py        # updated imports + batch assertion
    ├── test_data_loading.py       # NEW: validates data files load correctly
    └── fixtures/
        ├── mock_answers.yml
        └── mock_creative_response.txt
```

---

## Plan A: Extract Data to JSON Files (No Structural Moves)

**Goal**: Separate data from logic. All files stay in current locations. Only the data source changes (hardcoded constants → JSON files loaded at runtime).

### A1. Create `agent/interview/data/questions.json`

Extract from `collector.py` lines 44–96. ALL text values are arrays (uniform type, no string|list branching).

```json
{
  "_notes": "Interview questions and UI strings. Field names map to UserAnswers dataclass. All text values are arrays — join with newline at load time.",
  "greeting": ["What language would you prefer to communicate in?"],
  "questions": [
    {
      "field": "mentor_language",
      "prompt": ["Which language should the learning mentor use when teaching you?"]
    },
    {
      "field": "topic",
      "prompt": [
        "What topic or subject do you want to learn?",
        "(e.g., Quantum Physics, Oil Painting, Python Programming, Ancient History)"
      ]
    },
    {
      "field": "experience_level",
      "prompt": [
        "What is your current experience or starting level?",
        "(e.g., absolute beginner, self-taught enthusiast, professional looking to specialize)"
      ]
    },
    {
      "field": "learning_goals",
      "prompt": [
        "What is your target depth and primary learning goal?",
        "(e.g., broad theoretical overview, practical how-to skills, deep expert-level mastery)"
      ]
    },
    {
      "field": "environment",
      "prompt": [
        "What environment, tools, or constraints do you have?",
        "(e.g., access to a laboratory, specific software, a musical instrument, a library)"
      ]
    },
    {
      "field": "subtopics",
      "prompt": [
        "Are there specific subtopics or focus areas you want covered?",
        "(e.g., 'focus on landscape techniques' or 'skip the introductory math')"
      ]
    }
  ],
  "strategy_menu": [
    "Which learning strategy is your priority?",
    "",
    "  [1] DEPTH-FIRST (Mastery-Gated)",
    "      Progression based solely on verified mastery.",
    "      No deadlines — understanding comes first.",
    "",
    "  [2] TIME-BOXED (Speed-First)",
    "      Course must finish by a specific deadline.",
    "      Content depth may be reduced to meet the timeline."
  ],
  "strategy_enter_prompt": ["Enter 1 or 2: "],
  "strategy_retry_message": ["Please enter 1 or 2."],
  "session_info_template": [
    "Recommended session length: {recommended} minutes.",
    "  This gives enough time for explanation, practice, and mastery checks",
    "  without fatigue."
  ],
  "accept_prompt_template": ["Press Enter to accept {recommended} min, or type your preferred session length in minutes: "],
  "deadline_prompt": ["Enter your deadline date."],
  "deadline_invalid_format": ["Invalid date format. Use YYYY-MM-DD (e.g., 2026-06-01)."],
  "deadline_in_past": ["Deadline must be in the future."],
  "questions_after_strategy": [
    {
      "field": "mastery_method",
      "prompt": [
        "How should the mentor verify your progress and mastery?",
        "(e.g., practical assignments, quizzes, Socratic questioning, code review)"
      ]
    },
    {
      "field": "persona",
      "prompt": [
        "What tone or persona should the mentor adopt?",
        "(e.g., 'a supportive coach', 'a strict professor', 'Pyotr Tchaikovsky', 'a friendly peer')"
      ]
    }
  ],
  "locale_map": {
    "en": "English", "ru": "Russian", "de": "German", "fr": "French",
    "es": "Spanish", "it": "Italian", "pt": "Portuguese", "zh": "Chinese",
    "ja": "Japanese", "ko": "Korean", "ar": "Arabic", "hi": "Hindi",
    "tr": "Turkish", "pl": "Polish", "nl": "Dutch", "sv": "Swedish",
    "uk": "Ukrainian", "cs": "Czech"
  }
}
```

**Loader** — uniform, no type branching:

```python
def _text(value: list[str]) -> str:
    """Join array of lines into a single string."""
    return "\n".join(value)
```

### A2. Create `agent/interview/data/translator_prompt.json`

Extract from `interviewer.py` line 24–29:

```json
{
  "_notes": "System prompt for the translation LLM. Used in both per-text and batch modes.",
  "system_prompt": [
    "You are a translation assistant.",
    "You translate text accurately and concisely.",
    "Keep any examples in parentheses.",
    "Keep [1]/[2] markers and English terms DEPTH-FIRST/TIME-BOXED as-is.",
    "Output ONLY the translation, no commentary."
  ]
}
```

### A3. Create `agent/mentor/data/creative_prompts.json`

Extract from `creative_engine.py` lines 48–116, 222–226:

```json
{
  "_notes": "LLM prompts and parsing config for the creative engine.",
  "system_prompt": [
    "You are a curriculum designer and persona mapper.",
    "You receive a user profile and produce labeled creative content blocks.",
    "Output ONLY the labeled sections described in the prompt.",
    "No commentary outside the sections."
  ],
  "prompt_template": [
    "Based on the following user profile, produce creative content for a learning mentor.",
    "",
    "## User Profile",
    "- Dialogue language: {dialogue_language}",
    "- Mentor teaching language: {mentor_language}",
    "- Topic: {topic}",
    "- Experience level: {experience_level}",
    "- Learning goals: {learning_goals}",
    "- Environment/tools: {environment}",
    "- Subtopics requested: {subtopics}",
    "- Strategy: {strategy}",
    "- Time input: {time_input}",
    "- Mastery verification method: {mastery_method}",
    "- Desired persona: {persona}",
    "",
    "## Output format",
    "",
    "Write EXACTLY these sections, each starting with the label on its own line.",
    "Do not add any other sections. Write content in {mentor_language}.",
    "...remaining lines from PROMPT_TEMPLATE in creative_engine.py lines 74-116..."
  ],
  "section_labels": [
    "PERSONA_NAME", "EXPERTISE", "TONE", "ROLE_SPECIFICS",
    "PERSONA_ADAPTATION", "GREETING_FIRST", "GREETING_CONTINUATION",
    "CORE_MISSION", "TAGS", "CURRICULUM"
  ],
  "strategy_instructions": {
    "_notes": "Strategy-specific text appended to prompt_template. {time_input} and {recommended} are placeholders.",
    "TIME-BOXED": [
      "IMPORTANT: The user has a TIME-BOXED strategy. {time_input}.",
      "Design the curriculum to fit within this timeline.",
      "Each session is ~{recommended} min."
    ],
    "DEPTH-FIRST": [
      "The user chose DEPTH-FIRST strategy ({time_input}).",
      "Design for thorough mastery — session counts are estimates."
    ]
  }
}
```

### A4. Modify `collector.py` — Load from JSON

- Remove all `_GREETING_TEXT`, `_QUESTIONS`, `_STRATEGY_MENU_TEXT`, `_QUESTIONS_AFTER_STRATEGY`, `_LOCALE_MAP` constants
- Add `_load_questions()` function that reads `data/questions.json` (path relative to `__file__`)
- Add `_text()` helper: `"\n".join(value)` (uniform array type, no branching)
- `_all_localizable_texts()` now reads from JSON instead of referencing module constants
- `collect_interactive()` uses loaded data
- `interview_source_hash()` hashes the JSON file content (simpler and more reliable than reconstructing string list)

### A5. Modify `interviewer.py` — Load from JSON

- Remove `SYSTEM_PROMPT` constant
- Add `_load_translator_prompt()` that reads `data/translator_prompt.json`
- `_translate_one()` uses loaded system prompt

### A6. Modify `creative_engine.py` — Load from JSON

- Remove `SYSTEM_PROMPT`, `PROMPT_TEMPLATE`, `_SECTION_LABELS` constants
- Remove `_strategy_instruction()` function (logic moves to data)
- Add `_load_creative_prompts()` that reads `data/creative_prompts.json`
- `generate_creative()` loads prompt template, joins lines, formats with user data
- `_split_sections()` uses loaded section labels
- Strategy instruction is loaded from `strategy_instructions[answers.strategy]` and formatted

### A7. Update tests

- `test_pipeline.py` — no changes needed (tests consume functions, not constants)
- `test_interviewer.py` — no changes (mocks the provider, doesn't test prompt loading)
- Add `test_data_loading.py` — validates all 3 JSON files load correctly, have required keys

### A8. Write ADR-26010: Data File Formats

**Title**: "Agent Data Files: Pure JSON with List-Based Multi-Line Content"
**Decision**: All agent data files use JSON. Multi-line content stored as arrays (each line = list item), joined with `"\n"` at load time. All text values are arrays (uniform type). Extends ADR-26007 (JSON = compiler input) to internal agent data.
**References**: ADR-26007, `ai_engineering_book/ai_system/3_prompts/format_as_architecture_signal_noise_in_prompt_delivery.md` (Section 4: two-audience principle — compiler reads JSON, runtime LLM reads YAML).

### Verification (Plan A)

```bash
uv run pytest agent/tests/ -v                                    # all pass
uv run python -c "from agent.collector import collect_interactive"  # imports ok
uv run python -m agent.main --skip-collect --skip-api              # recompile works
```

---

## Plan B: Sub-Package Restructuring (File Moves + Import Rewiring)

**Goal**: Reorganize `agent/` into `interview/` and `mentor/` sub-packages. Pure mechanical refactoring — no behavior changes.

**Depends on**: Plan A completed (data files exist at correct relative paths).

### B1. Create sub-package directories

```
mkdir -p agent/interview/data
mkdir -p agent/mentor/data/templates
```

### B2. Move files

| Source | Destination |
|--------|-------------|
| `agent/collector.py` | `agent/interview/collector.py` |
| `agent/interviewer.py` | `agent/interview/translator.py` (rename) |
| `agent/interview/data/questions.json` | stays (created in Plan A) |
| `agent/interview/data/translator_prompt.json` | stays (created in Plan A) |
| `agent/creative_engine.py` | `agent/mentor/creative_engine.py` |
| `agent/template_engine.py` | `agent/mentor/template_engine.py` |
| `agent/validator.py` | `agent/mentor/validator.py` |
| `agent/yaml_writer.py` | `agent/mentor/yaml_writer.py` |
| `agent/main.py` | `agent/mentor/main.py` |
| `agent/USAGE.md` | `agent/mentor/USAGE.md` |
| `agent/templates/...` | `agent/mentor/data/templates/...` |
| `agent/mentor/data/creative_prompts.json` | stays (created in Plan A) |

### B3. Create `__init__.py` files with re-exports

`agent/interview/__init__.py`:
```python
from agent.interview.collector import UserAnswers, collect_interactive, interview_source_hash
from agent.interview.translator import InterviewCache, translate_interview
```

`agent/mentor/__init__.py`:
```python
from agent.mentor.main import main
```

### B4. Update all imports

Every import across the codebase changes. Key rewiring:

| Old import | New import | Files affected |
|------------|-----------|----------------|
| `from agent.collector import ...` | `from agent.interview.collector import ...` | creative_engine, template_engine, artifacts, tests |
| `from agent.interviewer import ...` | `from agent.interview.translator import ...` | collector, main |
| `from agent.creative_engine import ...` | `from agent.mentor.creative_engine import ...` | main, tests |
| `from agent.template_engine import ...` | `from agent.mentor.template_engine import ...` | main, validator, tests |
| `from agent.validator import ...` | `from agent.mentor.validator import ...` | main, tests |
| `from agent.yaml_writer import ...` | `from agent.mentor.yaml_writer import ...` | main |
| `from agent.main import _inject_api_keys` | `from agent.settings import inject_api_keys` | test_provider (B6: moves to settings.py) |

### B5. Update entry points

- `agent/__main__.py`: `from agent.mentor.main import main`
- `pyproject.toml` entry point (if defined): `agent.mentor.main:main`
- `settings.py` DEFAULTS: `"template_path": "./agent/mentor/data/templates/mentor_system_prompt.template.json"`

### B6. Move `_inject_api_keys` to `settings.py`

`_inject_api_keys()` is shared infrastructure (tested in `test_provider.py`), not mentor-specific. Move to `settings.py`:

```python
# agent/settings.py
_API_KEY_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*_API_KEY$")

def inject_api_keys(cfg: dict) -> None:
    """Promote named API keys from config to env vars."""
    for key, value in cfg.items():
        if _API_KEY_PATTERN.match(key) and isinstance(value, str) and value:
            os.environ[key] = value
            logger.debug("Injected API key from config: %s", key)
```

Callers (`mentor/main.py`, future `researcher/main.py`) import from `agent.settings`.
Test import in `test_provider.py` changes: `from agent.settings import inject_api_keys`.

### B7. Clean up old locations

Delete `agent/templates/` directory after move. Remove stale `.pyc` files.

### B8. Update tests

All test imports change per B4 table. No logic changes.

### B9. Write ADR-26011: Sub-Package Architecture

**Title**: "Sub-Package Architecture: Interview and Mentor Separation"
**Decision**: `agent/interview/` for reusable collection/translation, `agent/mentor/` for mentor generation. Shared infrastructure at `agent/` root. Future tools plug in as sibling sub-packages.

### B10. Update CLAUDE.md

Update file structure section, import examples, and architectural principles.

### Verification (Plan B)

```bash
uv run pytest agent/tests/ -v                      # all pass
uv run python -m agent.main --skip-collect --skip-api  # recompile works
python -c "from agent.interview import UserAnswers"    # re-exports work
python -c "from agent.mentor import main"              # re-exports work
```

---

## Plan C: One-Shot Translation + Final ADRs

**Goal**: Replace per-text translation (N LLM calls) with batch translation (1 call). Write remaining ADRs. Update CLAUDE.md and CHANGELOG.md.

**Depends on**: Plan B completed (translator.py is at `agent/interview/translator.py`).

### C1. Redesign `translate_interview()` for batch mode

Current flow (`translator.py:123`):
```python
for text in to_translate:
    translated = _translate_one(provider, language, text)
```

New flow:
```python
if to_translate:
    batch_result = _translate_batch(provider, language, to_translate)
    translations.update(batch_result)
    if cache:
        for text, translated in batch_result.items():
            cache.set(language, text, translated)
```

### C2. Implement `_translate_batch()`

**Prompt format**: numbered items → numbered translations.

```
Translate all the following texts to {language}.
Rules: [loaded from translator_prompt.json]

[1]
What language would you prefer to communicate in?

[2]
Which language should the learning mentor use when teaching you?
...
```

**Response parser**: regex `\[(\d+)\]` to find boundaries. Missing numbers fall back to original English.

### C3. Update `translator_prompt.json`

Add batch prompt template:
```json
{
  "system_prompt": ["...existing..."],
  "batch_prompt_template": [
    "Translate all the following texts to {language}.",
    "Rules:",
    "- Keep any examples in parentheses",
    "- Keep [1]/[2] markers and English terms DEPTH-FIRST/TIME-BOXED as-is",
    "- Output ONLY numbered translations in the same [N] format",
    "- Preserve the exact number of items"
  ]
}
```

### C4. Update cache interaction

Cache structure unchanged (per-text keys). The batch call fills all keys at once. `interview_source_hash()` still hashes all texts — any change invalidates entire cache.

### C5. Update tests

- `test_interviewer.py`: `test_translate_interview_calls_provider` assertion changes from `len(provider.calls) == N` to `len(provider.calls) == 1`
- Add batch-specific tests: partial response fallback, partial cache hit, empty to_translate list

### C6. Write ADR-26012: One-Shot Batch Translation

**Title**: "One-Shot Batch Translation for Interview Questions"
**Decision**: All interview texts translated in a single numbered-list LLM call. Reduces 13 calls → 1-2. Cache per-text keys preserved.

### C7. Final documentation

- Update CLAUDE.md architectural principles with ADR-26010, 26011, 26012 summaries
- Update CLAUDE.md file structure diagram
- Update `docs/configuration.md` for new template_path default
- Version bump to v0.45.0
- CHANGELOG.md entry

### Verification (Plan C)

```bash
uv run pytest agent/tests/ -v                          # all pass
uv run pytest agent/tests/ -v --cov=agent --cov-report=term-missing  # coverage check
# Manual: run with interview_model configured, verify 1 LLM call for translation
```

---

## Files Modified (All 3 Plans Combined)

**Created**:
- `agent/interview/__init__.py`
- `agent/interview/data/questions.json`
- `agent/interview/data/translator_prompt.json`
- `agent/mentor/__init__.py`
- `agent/mentor/data/creative_prompts.json`
- `agent/tests/test_data_loading.py`
- `docs/architecture/adr/adr_26010_agent_data_files_pure_json.md`
- `docs/architecture/adr/adr_26011_sub_package_architecture.md`
- `docs/architecture/adr/adr_26012_oneshot_batch_translation.md`

**Moved** (git mv):
- `agent/collector.py` → `agent/interview/collector.py`
- `agent/interviewer.py` → `agent/interview/translator.py`
- `agent/creative_engine.py` → `agent/mentor/creative_engine.py`
- `agent/template_engine.py` → `agent/mentor/template_engine.py`
- `agent/validator.py` → `agent/mentor/validator.py`
- `agent/yaml_writer.py` → `agent/mentor/yaml_writer.py`
- `agent/main.py` → `agent/mentor/main.py`
- `agent/USAGE.md` → `agent/mentor/USAGE.md`
- `agent/templates/` → `agent/mentor/data/templates/`

**Modified**:
- `agent/__main__.py` (import path)
- `agent/settings.py` (template_path default + `inject_api_keys()` moved from main.py)
- `agent/artifacts.py` (import paths)
- `agent/tests/test_pipeline.py` (import paths)
- `agent/tests/test_provider.py` (import paths)
- `agent/tests/test_interviewer.py` (import paths + batch assertions)
- `CLAUDE.md` (file structure, architectural principles)
- `CHANGELOG.md` (v0.45.0)
- `docs/configuration.md` (template_path)
