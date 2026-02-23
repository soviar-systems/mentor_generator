# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mentor Generator is a **meta-prompt engineering project** that creates personalized AI learning mentors. The system generates a single YAML configuration file that defines a customized learning experience.

The project has two workflows: **agent/** (Python CLI, the primary product) and **web_version/** (legacy web-chat workflow, preserved for backward compatibility).

## Architecture

### File Structure

```
mentor_generator/
├── agent/                                 # THE PRODUCT — self-contained Python CLI
│   ├── settings.py                        # Layered config (global → local → defaults)
│   ├── provider.py                        # LLM provider abstraction (Gemini)
│   ├── collector.py                       # CLI questionnaire (0 API calls)
│   ├── creative_engine.py                 # Single LLM call + labeled text parser
│   ├── template_engine.py                 # Deterministic placeholder injection
│   ├── validator.py                       # Structural validation
│   ├── yaml_writer.py                     # YAML output
│   ├── artifacts.py                       # Save/load pipeline artifacts
│   ├── main.py                            # Pipeline orchestrator (--skip-collect, --skip-api)
│   ├── templates/
│   │   └── mentor_system_prompt.template.json  # Output schema (15 top-level keys)
│   ├── USAGE.md                           # Post-generation user guide
│   └── tests/                             # Golden-file tests (0 API calls)
│       ├── test_pipeline.py
│       ├── README.md                      # Developer guide
│       └── fixtures/
├── web_version/                           # Legacy web-chat workflow
│   └── mentor_generator.json              # Original meta-prompt
├── architecture/
│   ├── adr/                               # Architecture Decision Records
│   ├── postmortem/                         # Version retrospectives (historical records)
│   └── research/                           # Cross-cutting analysis and synthesis
├── misc/
│   └── plan/                              # Implementation plans (saved for history)
│       └── implemented/                   # Plans moved here after completion
├── pyproject.toml                         # uv project config
├── uv.lock
├── CHANGELOG.md
├── CLAUDE.md
└── README.md
```

### Generated Output (Per User)

```
user_course/
├── mentor_system_prompt    # Complete mentor file: rules, profile, curriculum, session record template (YAML)
└── course_history          # Append-only file with all session records (JSON)
```

### Agent Architecture

Three-stage pipeline: **Collect** (0 API) → **Create** (1 API) → **Compile** (0 API).

- LLM returns labeled text blocks (PERSONA_NAME:, EXPERTISE:, etc.), code builds JSON structure
- Template has two kinds of `<...>` markers: compile-time (filled by agent) and runtime (filled by mentor AI in `session_record_template`)
- `RUNTIME_TEMPLATE_KEYS` in template_engine.py is the single source of truth for runtime template skip list
- Settings are layered: code DEFAULTS → global config → local config (aider-style)

### Core Files (Web Version — Legacy)

#### web_version/mentor_generator.json (Meta-Prompt)

Contains the questionnaire logic AND the embedded template:
- **meta_prompt_logic** - Instructions for conducting 9-question collection
- **interactive_input_sequence** - The questions and flow control
- **validation** - Pedagogical validation checks
- **persona_mapping_protocol** - Translates persona preferences into instructions
- **guidance_for_user** - Hardcoded user instructions (printed verbatim)
- **file_generation_protocol** - How to fill template and output as YAML
- **templates.mentor_system_prompt** - The single merged template (JSON object, output as YAML)
- **template_references** - Documents the template and its placeholders

#### Output Schema (15 top-level keys)

The template (`agent/templates/mentor_system_prompt.template.json`) produces:
- **mentor_profile** - Persona, tone, teaching style
- **mentor_self_control** - Self-correction, peer review checks, anti-praise examples
- **user_profile** - Language, assessment, skills, goals, user-maintained fields
- **environment_and_strategy** - Resources, constraints, pacing
- **curriculum** - Phased learning progression
- **course_history_protocol** - How to read course_history and select session protocol
- **session_protocols** - First session vs subsequent session behavior
- **interaction_flow** - Turn-taking, emergency brakes
- **learning_framework** - Mastery-gated progression rules
- **context_management** - Single-file course_history approach (see ADR-26001)
- **session_output_protocol** - How to output session records, with embedded session record template

### Architectural Principles (from ADRs)

These principles are derived from accepted ADRs in architecture/adr/. When a new ADR is accepted, update this section to reflect its key decisions.

**ADR-26001: Single-file course_history** — All session records live in one append-only course_history file. Users attach 1-2 files per session, not N. Never modify existing records, only append.

**ADR-26002: Strict placeholder injection** — The generator AI is a compiler, not an author. Templates are immutable infrastructure. The compiler replaces <placeholder> tokens with user data and touches nothing else. preservation_first and structural_parity in mentor_generator.json enforce this.

**ADR-26003: Instruction budget** — Every instruction added to a template must pass a cost-benefit test. Compiler instructions live in mentor_generator.json (the compiler's manual), not scattered across templates. Don't duplicate guardrails — one clear rule in the meta-prompt beats five scattered markers in templates. Adding too much structural noise causes LLMs to describe files instead of executing them (v0.38.0 → v0.39.0 lesson).

**ADR-26004: Templates are output schemas** — Every field in a template is one of four types: literal value (no prefix, no brackets — copied verbatim), placeholder (<...> — replaced by compiler), internal guidance (_-prefixed keys like _notes, _template_notes, _example_* — preserved in output as guidance for the mentor AI), or generator-only guidance (currently none — all _-prefixed fields travel to output). No unprefixed "example" or "illustrative" fields allowed.

**ADR-26005: Single-file output with embedded templates** — (Web-chat workflow only, superseded by ADR-26009 for agent workflow.) Templates are embedded in the meta-prompt, not external files. Generated output is ONE file (mentor_system_prompt) containing all mentor rules, user profile, curriculum, and session record template. Output as YAML to reduce token noise. User manages 2 files total (mentor_system_prompt + course_history). Solves both the generation-phase drift (templates as context) and learning-session drift (session template as context).

**ADR-26007: Format is architecture** — Format affects LLM behavior: structural noise tokens consume attention budget, and training-data distribution biases processing mode (JSON → data parsing, YAML → instruction following). Meta-prompt stays JSON (compiler input, needs validation). Generated output is YAML (runtime instructions, lowest noise with key-value addressability). Session records are JSON (structured data for field scanning).

**ADR-26008: Architecture directory taxonomy** — All architectural documentation lives in architecture/ (not generic docs/), organized into three subdirectories by document type: adr/ (decisions), postmortem/ (version retrospectives), research/ (cross-cutting analysis). Each has its own naming convention and lifecycle. No files at the architecture/ root.

**ADR-26009: Agent architecture — template extraction** — Template extracted from mentor_generator.json to standalone `agent/templates/mentor_system_prompt.template.json`. The agent/ package is self-contained. Web-chat workflow preserved in `web_version/`. Supersedes ADR-26005 for the agent workflow (ADR-26005 remains valid for web_version/).

Additional patterns:
- **Separation of Concerns**: Meta-prompt and mentor are different roles in different files

### Learning Strategies

- **DEPTH-FIRST**: Mastery-gated, time is variable, knowledge quality guaranteed
- **TIME-BOXED**: Deadline-driven, content depth may be reduced to meet timeline

## Development

- Package manager: `uv` (not pip). Run `uv sync --dev` to install.
- Python: pinned to 3.13 in `.python-version` (3.14 freethreaded lacks prebuilt grpcio wheels)
- Run tests: `uv run pytest agent/tests/ -v` (0 API calls, offline)
- Run full pipeline: `uv run python -m agent.main`
- Recompile only: `uv run python -m agent.main --skip-collect --skip-api`
- Config: `~/.mentor.generator.config.yml` (global/secrets) → `.mentor.generator.config.yml` (local overrides)
- Artifacts: `.mentor.generator.artifacts/` (gitignored, reusable across runs)

## JSON/Template Conventions

Template field taxonomy (ADR-26004):
- **Literal values** — no prefix, no <brackets>. Copied verbatim to output.
- **Placeholders** — value contains <...>. Replaced with user data by the compiler.
- **_-prefixed fields** — _notes, _template_notes, _example_*. Internal guidance preserved in output for the mentor AI.
- No unprefixed "example" or "illustrative" fields. If it's guidance, it must have a _ prefix.

Other conventions:
- Version tracked in metadata.version
- Top-level fields are human-readable and machine-usable

## Usage Workflow

### Creating a Mentor (Agent — Primary)

1. Configure API key: set `GEMINI_API_KEY` env var (or set `api_key_env` in global config)
2. Run `uv run python -m agent.main`
3. Answer 9 CLI questions
4. Agent calls Gemini once, fills template, validates, outputs YAML
5. Output: `output/mentor_system_prompt.yml` + empty `output/course_history`

### Creating a Mentor (Web Chat — Legacy)

1. Copy web_version/mentor_generator.json content
2. Paste into powerful LLM chat
3. Answer 9 questions
4. AI validates and outputs ONE YAML file
5. Save file to course folder
6. Create an empty course_history file

### Learning Sessions

1. Open new chat, attach mentor_system_prompt (+ course_history for session 2+)
2. Say "Let's continue" (or "Let's start" for first session)
3. Learn with mastery-gated progression
4. At session end, mentor outputs a session record
5. Append record to course_history, repeat

## Critical Conventions

### Planning
When you create a plan in /plan mode, save it to misc/plan/plan_<YYYYMMDD>_<descriptive_slug>.md, ONLY then start implementation. After the plan is fully implemented, move it to misc/plan/implemented/. This is needed to save the history of the decisions made between context switches.

**Plan splitting**: Always divide large plans into smaller independent parts. Each part runs in a separate session with clean context, reducing token usage. Split at natural boundaries where the next part doesn't need the exploration context from the previous one.

### Commit Conventions

Follow the structured commit body format (from ADR-26024 in the ai_engineering_book repo).

Subject line: <type>[(<scope>)]: <subject>

Types: feat, fix, docs, refactor, style, test, chore

Body: one bullet per file changed, format:
```
- <Verb>: <file-path> — <what/why>
```

Verb prefixes: Created, Updated, Deleted, Renamed, Fixed, Moved, Added, Removed, Refactored, Configured. File path is relative to repo root, wrapped in backticks. One bullet = one line, no line length limit. Git trailers are excluded from changelog parsing.

Examples:
```
feat: add greeting placeholders to session protocols (v0.40.0)

- Added: templates/mentor_system_prompt.template.md — greeting_text placeholder in welcome_message for persona injection
- Fixed: templates/session.template.md — _template_notes still described per-file sessions from before v0.35.0
- Updated: mentor_generator.json — persona_mapping_protocol rules to reference new placeholder fields
- Created: architecture/adr/adr_26003_instruction_budget_llm_context_limits.md — instruction budget principle

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

## When Editing

- Preserve all _-prefixed fields exactly as-is (_notes, _template_notes, _example_*)
- Maintain JSON validity (files must parse correctly)
- Follow existing naming conventions (snake_case for keys)
- Version bumps: metadata.version and metadata.modified
- Update CHANGELOG.md for significant changes
- Update RELEASE_NOTES.md for releases
- Keep guidance_for_user.message_paragraphs as exact text to print
- When a new ADR is accepted, update the "Architectural Principles" section above
