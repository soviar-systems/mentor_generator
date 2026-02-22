# Plan: Mentor Generator Agent — v1.0 Architecture

## Context

The problem catalog (v0.41) proves that free web chat LLMs cannot reliably act as "compilers" — they leak instructions (P1), compress output (P2), make format conversion errors (P3), and can't validate their own output (P14). 11 versions of evidence confirm this is a fundamental platform mismatch, not a prompt engineering gap.

**Decision**: Build a Python CLI agent that separates LLM judgment (persona mapping, curriculum design) from mechanical work (template filling, validation, YAML conversion). The LLM does what it's good at; code does the rest. This eliminates P1-P5, P13, and P14 by design.

**API budget**: Google Gemini free tier (20 RPD for Flash models). The agent uses **1 API call per generation** — all creative work in a single structured prompt. Leaves 19 RPD for retries or multiple generations per day.

---

## Architecture: Two-Engine Design

```
User answers (CLI)  +  Template (from mentor_generator.json)
        |                           |
        v                           |
  Creative Engine                   |
  (1 Gemini API call)               |
  → persona, curriculum,            |
    mission, validation             |
        |                           |
        +------ Compiler -----------+
                (pure Python)
                → fill placeholders
                → validate structure
                → convert to YAML
                    |
                    v
          mentor_system_prompt.yml
```

---

## File Structure

```
mentor_generator/
├── agent/                        # NEW — the generation agent
│   ├── __init__.py
│   ├── main.py                   # Entry point, orchestrates pipeline
│   ├── collector.py              # CLI questionnaire (0 API calls)
│   ├── creative_engine.py        # Builds prompt, calls LLM, parses JSON response
│   ├── template_engine.py        # Reads template, injects values, preserves _fields
│   ├── validator.py              # Structural validation (real, not theater)
│   ├── yaml_writer.py            # Deterministic JSON→YAML conversion
│   └── provider.py               # LLM provider abstraction (Gemini first)
├── config.yml                    # NEW — user config (model, output dir, env var name)
├── requirements.txt              # NEW — pyyaml, google-generativeai
├── mentor_generator.json         # EXISTING — source of truth (template + questions)
└── ...
```

---

## Implementation Steps

### Step 1: Project scaffolding
- Create `agent/` directory with `__init__.py`
- Create `requirements.txt` (pyyaml, google-generativeai)
- Create `config.yml` with defaults (provider, model, api_key_env var name, output_dir)

### Step 2: `provider.py` — LLM provider abstraction
- Abstract base: `LLMProvider` with single method `generate(prompt, system_prompt) -> str`
- `GeminiProvider` implementation using `google-generativeai` SDK
- API key loaded from environment variable (name configurable in config.yml)

### Step 3: `collector.py` — CLI data collection
- Read question texts from `mentor_generator.json` → `meta_prompt_logic.interactive_input_sequence`
- Present 9 questions via `input()` prompts with context explanations
- Q7 (strategy): validate DEPTH-FIRST vs TIME-BOXED selection + time input
- Return `UserAnswers` dataclass with all collected data
- Support `--answers-file` flag to load from YAML (for testing)

### Step 4: `creative_engine.py` — Single API call for all creative work
- Build one structured prompt with all 9 user answers
- Ask LLM to return JSON with: persona_name, tone, role_specifics, persona_adaptation, greetings, core_mission, curriculum_phases, tags, pedagogical_validation
- Parse response as JSON (with fallback regex extraction if wrapped in markdown)
- Validate all required keys present in response
- Return `CreativePayload` dataclass

### Step 5: `template_engine.py` — Deterministic template filling (CRITICAL)
- Deep-copy template from `mentor_generator.json` → `templates.mentor_system_prompt`
- Replace ONLY placeholder values (`<...>`) with user answers (literal) + creative payload (LLM-generated)
- **Preservation guarantee**: All human/pedagogical traits recovered in v0.29→v0.41 are preserved verbatim:
  - `pedagogical_principles` (partnership, honesty, respect, patience, curiosity)
  - `mentor_self_control` (self-correction, peer review, anti-praise examples)
  - `emergency_brake_rules` (recovery_protocol, explicit_check — only persona_adaptation is filled)
  - `learning_framework` (zero-level protocol, one-small-step, mastery-gated progression, strict turn-taking)
  - `interaction_flow` (response architecture, ask-and-wait rules)
  - All `_notes`, `_template_notes`, `_example_*` guidance fields
  - `session_output_protocol` with embedded `session_record_template`
- The LLM never sees this template — it cannot compress, rewrite, or drop any of these fields
- This structurally eliminates the entire class of problems from v0.30→v0.41 post-mortems

### Step 6: `validator.py` — Real structural validation
- Check all 15 required top-level keys present
- Check no `<placeholder>` markers remain in output
- Check structural depth matches template (compare key paths)
- Check all `_`-prefixed fields preserved
- Return list of errors (empty = valid)

### Step 7: `yaml_writer.py` — Deterministic output
- `yaml.dump()` with `sort_keys=False` (preserves template key order), `allow_unicode=True`
- Write to `{output_dir}/mentor_system_prompt` (or user-specified path)

### Step 8: `main.py` — Pipeline orchestrator
- Load config → load template → collect answers → call creative engine → inject into template → validate → write YAML
- Error handling: API failures get 2 retries with backoff; on final failure, save answers to file for `--resume`
- Print `guidance_for_user` message after successful generation
- Print validation results (pedagogical checks from LLM)

### Step 9: Golden-file integration test
- Create a fixed set of mock answers (`tests/fixtures/mock_answers.json`) and a mock creative payload (`tests/fixtures/mock_creative_payload.json`)
- Run the full pipeline: template_engine → validator → yaml_writer (0 API calls — creative engine is mocked)
- Save the output as a golden file (`tests/fixtures/golden_mentor_system_prompt.yml`)
- Test asserts: output matches golden file; validator returns 0 errors
- This single test catches regressions in template filling, field preservation, and YAML conversion

### Open discussion: Gherkin approach for user update requests
- **TODO**: Discuss using Gherkin-style specifications (Given/When/Then) for defining and validating user requests for updates to the mentor or agent. User to provide more context on this idea in a future session.

---

## Key Design Decisions

| Decision | Why |
|----------|-----|
| 1 API call, not 10 | 20 RPD limit; all creative fields are interdependent |
| CLI form, not conversational | 0 API calls for collection; questions are fixed and well-defined |
| Template stays in mentor_generator.json | Single source of truth; backward compatible with web chat |
| Code fills template, not LLM | Eliminates P1 (leakage), P2 (compression), P3 (format errors) |
| Code validates structure, not LLM | Eliminates P14 (validation theater) |
| `yaml.dump()` for conversion | Deterministic; eliminates P3 entirely |
| Minimal provider interface (1 method) | Easy to add new providers without over-engineering |

## Dependencies

- `pyyaml` — YAML output
- `google-generativeai` — Gemini API (MVP)
- Python 3.10+ (dataclasses, type hints)

## Verification

1. Run `python -m agent.main` with test answers
2. Check generated YAML parses correctly (`python -c "import yaml; yaml.safe_load(open(...))"`)
3. Compare output structure against template — all 15 top-level keys present
4. Verify all `_notes`, `_example_*` fields are in output (grep for `_notes:`)
5. Compare against Gemini web chat test results in `misc/test_results/` — agent output should contain all sections that Gemini dropped

## What This Does NOT Cover (future phases)

### Phase 2: Terminal Mentor Agent (after generation agent is validated)
The same agent architecture can extend to runtime learning sessions:
- **Terminal chat loop**: User runs `python -m agent.mentor` with their `mentor_system_prompt` file
- **Automatic session management**: Agent writes session records to `course_history` automatically (no copy-paste)
- **Context window tracking**: Agent counts tokens, warns when approaching limits
- **Auto-compaction**: Summarize older sessions to keep context within budget
- **Turn-taking enforcement**: Agent code controls when LLM speaks, preventing P7/P8/P10
- **Session end via command**: `/end` command instead of ambiguous natural language triggers
- **API budget**: Needs Gemma 27B (15k RPD) or paid tier — Flash 20 RPD is insufficient for multi-turn sessions
- **Prerequisite**: Test Gemma 27B quality for teaching/mentoring tasks before committing

### Other future work
- Conversational questionnaire mode (could use Gemma 27B's 15k RPD)
- Web UI wrapper
- Multiple provider testing
