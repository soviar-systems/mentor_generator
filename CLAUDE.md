# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mentor Generator is a **meta-prompt engineering project** that creates personalized AI learning mentors. The system generates three configuration files that define a customized learning experience.

This is **not a traditional software project** - there is no build system, no package manager, no automated tests. The JSON/template files are the product.

## Architecture

### File Structure

```
mentor_generator/
├── mentor_generator.json                  # Meta-prompt (questionnaire only)
├── templates/
│   ├── mentor_system_prompt.template.md   # Template for mentor behavior rules
│   ├── user_profile.template.md           # Template for user profile/curriculum
│   └── session.template.md                # Template for session records
├── docs/
│   └── adr/                               # Architecture Decision Records
├── misc/
│   └── plan/                              # Implementation plans (saved for history)
│       └── implemented/                   # Plans moved here after completion
├── CHANGELOG.md
├── CLAUDE.md
└── README.md
```

### Generated Output (Per User)

```
user_course/
├── mentor_system_prompt    # Static mentor rules (attach every session)
├── user_profile            # User profile + curriculum (attach every session)
├── session_template        # Session record format (attach every session)
└── course_history          # Append-only file with all session records
```

### Core Files

#### `mentor_generator.json` (Meta-Prompt)

Contains ONLY the questionnaire logic:
- **meta_prompt_logic** - Instructions for conducting 9-question collection
- **interactive_input_sequence** - The questions and flow control
- **validation** - Pedagogical validation checks
- **persona_mapping_protocol** - Translates persona preferences into instructions
- **guidance_for_user** - Hardcoded user instructions (printed verbatim)
- **file_generation_protocol** - How to fill and output templates
- **template_references** - Points to template files

#### `templates/mentor_system_prompt.template.md`

Defines mentor behavior (filled once during generation):
- **mentor_profile** - Persona, tone, teaching style
- **mentor_self_control** - Self-correction, peer review checks, anti-praise examples
- **course_history_protocol** - How to read course_history and select session protocol
- **session_protocols** - First session vs subsequent session behavior
- **interaction_flow** - Turn-taking, emergency brakes
- **learning_framework** - Mastery-gated progression rules
- **context_management** - Single-file course_history approach (see ADR-26001)
- **session_output_protocol** - How to output session records for course_history

#### `templates/user_profile.template.md`

Defines user-specific data (filled once during generation, can be updated by user):
- **user_profile** - Language, assessment, skills, goals
- **constraints_and_strategy** - Hardware, pacing choice
- **curriculum** - Phased learning progression

#### `templates/session.template.md`

Defines session record structure (mentor fills at end of each session):
- **position** - Current phase, topic covered, next topic, progress
- **content** - Summary, tasks completed, projects, resources suggested
- **mastery** - Concepts validated/struggling, validation method
- **observations** - Learning patterns, user problems, mentor failures
- **mentor_notes** - Notes for future sessions

### Architectural Principles (from ADRs)

These principles are derived from accepted ADRs in `docs/adr/`. When a new ADR is accepted, update this section to reflect its key decisions.

**ADR-26001: Single-file course_history** — All session records live in one append-only `course_history` file. Users attach 3-4 files per session, not N. Never modify existing records, only append.

**ADR-26002: Strict placeholder injection** — The generator AI is a compiler, not an author. Templates are immutable infrastructure. The compiler replaces `<placeholder>` tokens with user data and touches nothing else. `preservation_first` and `structural_parity` in `mentor_generator.json` enforce this.

**ADR-26003: Instruction budget** — Every instruction added to a template must pass a cost-benefit test. Compiler instructions live in `mentor_generator.json` (the compiler's manual), not scattered across templates. Don't duplicate guardrails — one clear rule in the meta-prompt beats five scattered markers in templates. Adding too much structural noise causes LLMs to describe files instead of executing them (v0.38.0 → v0.39.0 lesson).

**ADR-26004: Templates are output schemas** — Every field in a template is one of four types: literal value (no prefix, no brackets — copied verbatim), placeholder (`<...>` — replaced by compiler), internal guidance (`_`-prefixed keys like `_notes`, `_example_*` — preserved in output as guidance for the mentor AI), or generator-only guidance (currently none — all `_`-prefixed fields travel to output). No unprefixed "example" or "illustrative" fields allowed.

Additional patterns:
- **Separation of Concerns**: Meta-prompt and mentor are different roles in different files
- **Reusable Mentor Templates**: Same mentor_system_prompt works for multiple users
- **Format-Agnostic**: JSON shown, but YAML/Markdown/text equally valid

### Learning Strategies

- **DEPTH-FIRST**: Mastery-gated, time is variable, knowledge quality guaranteed
- **TIME-BOXED**: Deadline-driven, content depth may be reduced to meet timeline

## Usage Workflow

### Creating a Mentor (Meta-Prompt Phase)

1. Copy `mentor_generator.json` content
2. Paste into powerful LLM chat
3. Answer 9 questions
4. AI validates and outputs THREE files
5. Save all files to course folder
6. Create an empty `course_history` file

### Learning Sessions

1. Open new chat, attach `mentor_system_prompt` + `user_profile` + `session_template` + `course_history`
2. Say "Let's continue" (or "Let's start" for first session)
3. Learn with mastery-gated progression
4. At session end, mentor outputs a session record
5. Append record to `course_history`, repeat

## JSON/Template Conventions

Template field taxonomy (ADR-26004):
- **Literal values** — no prefix, no `<brackets>`. Copied verbatim to output.
- **Placeholders** — value contains `<...>`. Replaced with user data by the compiler.
- **`_`-prefixed fields** — `_notes`, `_template_notes`, `_example_*`. Internal guidance preserved in output for the mentor AI.
- No unprefixed "example" or "illustrative" fields. If it's guidance, it must have a `_` prefix.

Other conventions:
- Version tracked in `metadata.version`
- Top-level fields are human-readable and machine-usable

## Commit Conventions

Follow the structured commit body format (from ADR-26024 in the ai_engineering_book repo).

Subject line: `<type>[(<scope>)]: <subject>`

Types: `feat`, `fix`, `docs`, `refactor`, `style`, `test`, `chore`

Body: one bullet per file changed, format:
```
- <Verb>: `<file-path>` — <what/why>
```

Verb prefixes: `Created`, `Updated`, `Deleted`, `Renamed`, `Fixed`, `Moved`, `Added`, `Removed`, `Refactored`, `Configured`. File path is relative to repo root, wrapped in backticks. One bullet = one line, no line length limit. Git trailers are excluded from changelog parsing.

Examples:
```
feat: add greeting placeholders to session protocols (v0.40.0)

- Added: `templates/mentor_system_prompt.template.md` — greeting_text placeholder in welcome_message for persona injection
- Fixed: `templates/session.template.md` — _template_notes still described per-file sessions from before v0.35.0
- Updated: `mentor_generator.json` — persona_mapping_protocol rules to reference new placeholder fields
- Created: `docs/adr/adr_26003_instruction_budget_llm_context_limits.md` — instruction budget principle

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

## Critical Conventions

When you create a plan in /plan mode, save it to misc/plan/plan_<YYYYMMDD>_<descriptive_slug>.md, ONLY then start implementation. After the plan is fully implemented, move it to misc/plan/implemented/. This is needed to save the history of the decisions made between context switches.

## When Editing

- Preserve all `_`-prefixed fields exactly as-is (`_notes`, `_template_notes`, `_example_*`)
- Maintain JSON validity (files must parse correctly)
- Follow existing naming conventions (snake_case for keys)
- Version bumps: `metadata.version` and `metadata.modified`
- Update `CHANGELOG.md` for significant changes
- Update `RELEASE_NOTES.md` for releases
- Keep `guidance_for_user.message_paragraphs` as exact text to print
- When a new ADR is accepted, update the "Architectural Principles" section above
