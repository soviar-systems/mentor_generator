# Revised Plan: Mentor Generator Agent v2 — Architecture Rethink

## Context

The original plan (plan_20260218) assumed the template must stay embedded in `mentor_generator.json` for backward compatibility with web chat. Now that we're building an agentic architecture, that constraint is gone. The agent reads files from disk — the template should be standalone, and `agent/` should be a self-contained atomic product with its own template, tests, and docs.

This plan revises the file structure, creates ADR-26009 for the architectural shift, completes remaining implementation (Steps 5-9), and moves legacy web-chat files to `web_version/`.

---

## File Structure (Revised)

```
mentor_generator/
├── agent/                           # THE PRODUCT — self-contained
│   ├── __init__.py                  # EXISTS
│   ├── settings.py                  # EXISTS
│   ├── provider.py                  # EXISTS
│   ├── collector.py                 # EXISTS
│   ├── creative_engine.py           # EXISTS
│   ├── artifacts.py                 # EXISTS
│   ├── template_engine.py           # NEW (Step B)
│   ├── validator.py                 # NEW (Step C)
│   ├── yaml_writer.py              # NEW (Step D)
│   ├── main.py                      # NEW (Step E)
│   ├── template.json                # MOVED from root — the output schema
│   ├── USAGE.md                     # NEW — post-generation user guide
│   └── tests/                       # MOVED from root
│       ├── __init__.py
│       ├── test_pipeline.py         # NEW (Step F)
│       └── fixtures/
│           ├── mock_answers.yml
│           └── mock_creative_response.txt
├── web_version/                     # Legacy web-chat workflow
│   ├── mentor_generator.json        # MOVED from root
│   └── system_prompt.yml            # MOVED from root
├── .mentor.generator.config.yml     # EXISTS
├── .gitignore                       # EXISTS
├── requirements.txt                 # EXISTS
├── CLAUDE.md                        # EXISTS (update file structure section)
├── CHANGELOG.md                     # EXISTS
├── README.md                        # EXISTS
├── LICENSE                          # EXISTS
├── architecture/                    # EXISTS
│   └── adr/
│       └── adr_26009_*.md           # NEW — agent architecture ADR
└── misc/
    └── plan/
        ├── implemented/             # Old plan moved here
        └── plan_20260223_*.md       # This plan
```

---

## Settings Change

In `agent/settings.py` DEFAULTS:
- Rename `meta_prompt_path` → `template_path`
- Default value: `"./agent/template.json"` (relative to project root)

Update `.mentor.generator.config.yml` to match.

---

## Implementation Steps

### Step 0: Housekeeping
1. Create `web_version/` directory
2. Move `mentor_generator.json` → `web_version/` (plain file move, not git mv — already untracked)
3. Move `system_prompt.yml` → `web_version/` (untracked)
4. Move `template.json` → `agent/template.json`
5. Move `tests/` → `agent/tests/`
6. Create `agent/USAGE.md` from the `guidance_for_user.message_paragraphs` content in mentor_generator.json
7. Rename `meta_prompt_path` → `template_path` in settings.py DEFAULTS + .mentor.generator.config.yml
8. Move old plan to `misc/plan/implemented/`, save this plan to `misc/plan/`
9. Create ADR-26009

### Step B: template_engine.py
- **Reads**: `agent/template.json` (via `settings["template_path"]`)
- **Input**: `UserAnswers` + `CreativePayload`
- **Logic**: `copy.deepcopy(template)`, fill each placeholder explicitly:
  - `metadata`: course_id (UUID), created (today), topic, tags
  - `core_mission`: payload.core_mission
  - `mentor_profile`: persona_name, expertise, tone, role_specifics
  - `user_profile`: language, level, description, skills, goals, depth
  - `environment_and_strategy`: resources, constraints, pacing choice + time
  - `curriculum.phases`: full replacement from payload
  - `curriculum.subtopics_requested`: from answers
  - `session_protocols` greeting texts: from payload
  - `interaction_flow.emergency_brake_rules.persona_adaptation`: from payload
- **Post-fill**: walk output, find remaining `<...>`, log warnings
- **Guarantee**: everything not in the explicit map passes through via deep copy

### Step C: validator.py
- 15 required top-level keys check
- No `<placeholder>` markers remain (regex)
- All `_`-prefixed keys from original template preserved
- `curriculum.phases` has 1+ phases with required fields
- `pacing.choice` is DEPTH-FIRST or TIME-BOXED
- Returns `list[str]` of errors (empty = valid)

### Step D: yaml_writer.py
- `yaml.dump(sort_keys=False, allow_unicode=True, default_flow_style=False)`
- Write to `{output_dir}/mentor_system_prompt.yml`
- Create empty `{output_dir}/course_history` if not exists

### Step E: main.py — Pipeline orchestrator
```
python -m agent.main                    # full pipeline
python -m agent.main --skip-collect     # reuse saved answers
python -m agent.main --skip-api         # recompile only
```
Flow: setup_logging → collect → save answers → API call → save response → parse → fill template → validate → write YAML → print USAGE.md

### Step F: Golden-file test
- `agent/tests/fixtures/mock_answers.yml` + `mock_creative_response.txt`
- Test: load → parse → fill → validate → YAML output → compare golden file
- 0 API calls
- Run: `python -m pytest agent/tests/`

### Step G: ADR-26009 — Agent Architecture: Template Extraction
- **Decision**: Extract template from mentor_generator.json to standalone `agent/template.json`. The agent package is self-contained. Web-chat workflow preserved in `web_version/`.
- **Supersedes**: ADR-26005 (embed templates for web chat) — that decision was correct for web chat but no longer applies to the agent.
- **Consequences**: template is independently versionable, agent/ is an atomic distributable unit, web_version/ preserves backward compatibility.

---

## Valuable info extracted from old plan (plan_20260218)

### Key Design Decisions (still valid)
| Decision | Why |
|----------|-----|
| 1 API call, not 10 | 20 RPD limit; all creative fields are interdependent |
| CLI form, not conversational | 0 API calls for collection; questions are fixed |
| Code fills template, not LLM | Eliminates P1 (leakage), P2 (compression), P3 (format errors) |
| Code validates structure, not LLM | Eliminates P14 (validation theater) |
| `yaml.dump()` for conversion | Deterministic; eliminates P3 entirely |
| Minimal provider interface (1 method) | Easy to add new providers |

### Changed decisions
| Old | New | Why |
|-----|-----|-----|
| Template stays in mentor_generator.json | Template extracted to agent/template.json | Agent reads from disk; no embedding constraint |
| LLM returns JSON | LLM returns labeled text blocks, code builds structure | Keep LLM probabilistic output separate from deterministic structure |

### Open discussion (carried forward)
- Gherkin approach for user update requests — TODO for future session

### Phase 2 scope (carried forward, not in this plan)
- Terminal mentor agent, auto session management, context tracking, turn-taking enforcement

---

## Verification

1. `python -m agent.main` — full pipeline with real API
2. `python -m agent.main --skip-collect --skip-api` — recompile from artifacts
3. `python -m pytest agent/tests/` — golden-file test (0 API)
4. `python -c "import yaml; yaml.safe_load(open('output/mentor_system_prompt.yml'))"` — YAML valid
5. `grep '<' output/mentor_system_prompt.yml` — no remaining placeholders
6. All 15 top-level keys present, all `_notes`/`_example_*` fields preserved
