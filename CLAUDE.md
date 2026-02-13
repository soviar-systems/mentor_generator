# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mentor Generator is a **meta-prompt engineering project** that creates personalized AI learning mentors. The system generates three configuration files that define a customized learning experience.

This is **not a traditional software project** - there is no build system, no package manager, no automated tests. The JSON/template files are the product.

## Architecture

### File Structure

```
mentor_generator/
├── mentor_generator.json              # Meta-prompt (questionnaire only)
├── templates/
│   ├── mentor_system_prompt.template  # Template for mentor behavior rules
│   ├── user_profile.template          # Template for user profile/curriculum
│   └── session.template               # Template for session records
├── architecture/
│   └── adr/                           # Architecture Decision Records
├── misc/
│   └── plan/                          # Implementation plans (saved for history)
├── README.md
├── CLAUDE.md
└── changelog
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

#### `templates/mentor_system_prompt.template`

Defines mentor behavior (filled once during generation):
- **mentor_profile** - Persona, tone, teaching style
- **mentor_self_control** - Self-correction, peer review checks, anti-praise examples
- **course_history_protocol** - How to read course_history and select session protocol
- **session_protocols** - First session vs subsequent session behavior
- **interaction_flow** - Turn-taking, emergency brakes
- **learning_framework** - Mastery-gated progression rules
- **context_management** - Single-file course_history approach (see ADR-26001)
- **session_output_protocol** - How to output session records for course_history

#### `templates/user_profile.template`

Defines user-specific data (filled once during generation, can be updated by user):
- **user_profile** - Language, assessment, skills, goals
- **constraints_and_strategy** - Hardware, pacing choice
- **curriculum** - Phased learning progression

#### `templates/session.template`

Defines session record structure (mentor fills at end of each session):
- **position** - Current phase, topic covered, next topic, progress
- **content** - Summary, tasks completed, projects, resources suggested
- **mastery** - Concepts validated/struggling, validation method
- **observations** - Learning patterns, user problems, mentor failures
- **mentor_notes** - Notes for future sessions

### Key Design Patterns

1. **Separation of Concerns**: Meta-prompt and mentor are different roles in different files
2. **Template-First Output**: Mentor fills exact templates, never "decides" what to include
3. **Append-Only Session History**: Session records are appended to a single course_history file, never modified (ADR-26001)
4. **Predictability Through Constraints**: Output format is constrained, not instructed
5. **Reusable Mentor Templates**: Same mentor_system_prompt works for multiple users
6. **Format-Agnostic**: JSON shown, but YAML/Markdown/text equally valid

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

- `_notes` and `_template_notes` fields contain instructions for AI, never overwritten
- Placeholders marked with `<...>` are filled during generation
- Top-level fields are human-readable and machine-usable
- Version tracked in `metadata.version`

## Critical Conventions

When you create a plan in /plan mode, save it to misc/plan/plan_<YYYYMMDD>_<descriptive_slug>.md, ONLY then start implementation. After the plan is fully implemented, move it to misc/plan/implemented/. This is needed to save the history of the decisions made between context switches.

## When Editing

- Preserve all `_notes` fields exactly as-is
- Maintain JSON validity (files must parse correctly)
- Follow existing naming conventions (snake_case for keys)
- Version bumps: `metadata.version` and `metadata.modified`
- Update `changelog` for significant changes
- Update `RELEASE_NOTES.md` for releases
- Keep `guidance_for_user.message_paragraphs` as exact text to print
