# Plan: Merge Generated Output into Single File (v0.41.0)

## Context

### The Problem Chain

1. **v0.40.0 Qwen3-Max test** revealed that web chat LLMs treat attached template files as context, not source code to copy. 10 sections dropped, immutable fields rewritten. (Full evidence in `docs/ARCHITECTURE_POSTMORTEM_v0.40.md`)

2. **Initial fix (embed templates in meta-prompt)** solved the generation phase — templates are now in the same document as the compiler instructions.

3. **But the same problem applies to learning sessions.** The mentor needs the session_template to output session records at session end. If session_template is a separate attached file, the mentor faces the same drift risk — treating it as context, not as an exact schema to follow.

4. **This means the 3-file generated output also has an architectural mismatch.** The mentor_system_prompt references session_template as an external file (`session_output_protocol.template_reference: "Use the structure from templates/session.template"`). In a web chat, the mentor might generate its own session record format.

### The Deeper Insight

The v0.31.0 refactor split the generated output into 3 files to separate concerns. But from the mentor's perspective in a web chat, it doesn't matter WHERE the data lives — it all becomes context. Splitting into 3 files only matters for:
- **Shareability**: same mentor_system_prompt for multiple users (each with own user_profile)
- **Editability**: user can edit a small user_profile file instead of a large combined file

Neither of these benefits outweigh the cost of:
- More files to attach (3-4 per session)
- Session template drift risk (mentor treats it as context)
- Cross-file references that the mentor must resolve

### Proposal: Return to Single Generated File

Merge all generated output into ONE file: `mentor_system_prompt` contains mentor rules + user profile + curriculum + session template.

**This is NOT reverting to v0.29.1.** The v0.29.1 problems were:

| v0.29.1 Problem | Returns? | Why Not |
|---|---|---|
| Meta-prompt + mentor in same file → role confusion | No | Meta-prompt stays in `mentor_generator.json`, separate from the generated file |
| LLM regenerates 450-line state file | No | LLM only outputs ~30-line session records to course_history. Never touches the main file. |
| Complex trigger logic (token counting, milestone detection) | No | Single trigger: session end |
| Dual-mode overhead (teaching vs state update) | No | No modes. Teach → output session record → done. |
| Lossy compression of session history | No | course_history is append-only. No compression. |

**What v0.29.1 had RIGHT (that v0.31.0 lost):**
- Everything the mentor needs was in one context
- The user managed one file, not three
- No cross-file references to resolve

### User Profile as Living Document

v0.29.1 had `learning_style_observed` and `problem_patterns` in `additional_context`. These were dynamic fields the LLM tried to update, which caused corruption.

The fix: **the user maintains these fields manually**, not the LLM.

After each session, the mentor's session record contains `observations.learning_patterns` and `observations.user_problems`. The user reads these and optionally updates their profile section in mentor_system_prompt. This gives the user a curated summary of their learning patterns without LLM corruption risk.

**Graceful degradation**: If the user never updates their profile, the mentor still synthesizes patterns from course_history session records — same as v0.40.0. The user-maintained fields are an optimization, not a requirement.

## Decision

### Generated Output: 1 File

The meta-prompt generates ONE file (`mentor_system_prompt`) containing:
1. Mentor profile (persona, tone, teaching style)
2. All rules (pedagogical principles, self-control, interaction flow, learning framework)
3. User profile (language, assessment, skills, goals, environment, curriculum)
4. User-maintained fields (learning_style_observed, known_difficulties — start empty)
5. Session output protocol with embedded session record template
6. Session protocols, context management

### Learning Session Workflow

**First session:**
1. Open new chat, attach `mentor_system_prompt`
2. Say "Let's start"

**Subsequent sessions:**
1. Open new chat, attach `mentor_system_prompt` + `course_history`
2. Say "Let's continue"

**Session end:**
1. Mentor outputs session record (following embedded template)
2. User appends record to `course_history`
3. User optionally updates `user_profile` section (learning style, known difficulties) based on session observations

### File Count Comparison

| Action | v0.40.0 | v0.41.0 |
|---|---|---|
| Meta-prompt phase: paste | 1 file + 3 attachments | 1 file |
| Generated output | 3 files | 1 file |
| First session | 3 attachments | 1 attachment |
| Subsequent sessions | 4 attachments | 2 attachments |
| Files user manages | 4 (mentor + profile + session_template + history) | 2 (mentor + history) |

### Size Estimate

Combined generated file:
- Mentor rules: ~200 lines
- User profile + curriculum: ~60 lines (with data filled)
- Session template (in session_output_protocol): ~40 lines
- Total: ~300 lines

This is SMALLER than v0.29.1's ~460 lines and well within all model context limits.

## Files to Modify

1. `mentor_generator.json` — single merged template, updated file_generation, updated guidance_for_user, version bump
2. `docs/adr/adr_26005_embed_templates_for_web_chat.md` — update to reflect single-file output (already created, needs revision)
3. `CLAUDE.md` — update file structure, workflow, core files
4. `CHANGELOG.md` — v0.41.0 entry
5. DELETE `templates/mentor_system_prompt.template.md`
6. DELETE `templates/user_profile.template.md`
7. DELETE `templates/session.template.md`

## Changes

### 1. `mentor_generator.json`

#### 1A. Create single merged template

Replace the three separate templates with ONE template under `templates.mentor_system_prompt`. This template merges:

- All content from current `mentor_system_prompt.template.md` (rules, protocols, etc.)
- `user_profile` section from `user_profile.template.md` (with placeholders for user data)
- `curriculum` section from `user_profile.template.md`
- User-maintained fields: `learning_style_observed` (starts as empty array), `known_difficulties` (starts as empty array)
- Session record template embedded in `session_output_protocol` (from `session.template.md`)

Structure of the merged template:

```
templates.mentor_system_prompt:
├── _template_notes (updated for single-file workflow)
├── metadata
├── core_mission
├── pedagogical_principles
├── mentor_profile
├── mentor_self_control
├── user_profile
│   ├── user_language: <placeholder>
│   ├── initial_assessment: <placeholder>
│   ├── professional_skills: <placeholder>
│   ├── learning_goals: <placeholder>
│   ├── depth_preference: <placeholder>
│   ├── learning_style_observed: [] (user-maintained)
│   └── known_difficulties: [] (user-maintained)
├── environment_and_strategy: <placeholders>
├── curriculum
│   ├── _notes
│   ├── phases: [<generated>]
│   └── subtopics_requested: <placeholder>
├── course_history_protocol (updated for 2-file workflow)
├── session_protocols
├── interaction_flow
├── learning_framework
├── context_management (updated — 2 files, not 4)
├── session_output_protocol
│   ├── (existing fields)
│   └── session_record_template: {entire session.template content}
```

#### 1B. Rewrite `file_generation.steps`

```json
"steps": [
    "1. Copy the ENTIRE object at templates.mentor_system_prompt. For each value containing <angle_brackets>, replace the <...> portion with collected user data. Leave ALL other values exactly as they appear.",
    "2. For curriculum.phases, generate 3-5 phases following the EXACT field structure from the template (same keys: phase_number, title, focus, topics, hands_on, estimated_sessions).",
    "3. Verify: the output must contain ALL of these top-level keys: _template_notes, metadata, core_mission, pedagogical_principles, mentor_profile, mentor_self_control, user_profile, environment_and_strategy, curriculum, course_history_protocol, session_protocols, interaction_flow, learning_framework, context_management, session_output_protocol. If any is missing, you dropped template content — re-copy.",
    "4. Output as a single JSON code block. Label it 'mentor_system_prompt'. Remind user to save this file and create an empty course_history file."
]
```

#### 1C. Update `template_references`

Replace three references with one:

```json
"template_references": {
    "_notes": "Single template that produces the complete mentor file. Session record template is embedded within session_output_protocol.",
    "mentor_system_prompt_template": {
        "source": "templates.mentor_system_prompt",
        "output_filename": "mentor_system_prompt",
        "purpose": "Complete mentor file: behavior rules, user profile, curriculum, session record format"
    }
}
```

#### 1D. Update `guidance_for_user`

Rewrite for single-file workflow:
- "I will generate **one file** for you: **mentor_system_prompt**"
- First session: attach mentor_system_prompt
- Subsequent: attach mentor_system_prompt + course_history
- Session end: append record to course_history
- User can update their profile section (learning_style_observed, known_difficulties)
- Remove session_template explanation

#### 1E. Update `_notes`, `description`, version bump

- `_notes`: "generates one file" not "three files"
- `description`: remove "generates three files"
- Version: 0.41.0

#### 1F. Update internal template references

- `course_history_protocol.on_start`: reads one file (this file) + course_history
- `context_management.file_structure`: "mentor_system_prompt + course_history"
- `session_output_protocol.template_reference`: "Use the session_record_template structure below" (not external file)
- `_template_notes.usage`: updated for 2-file workflow

#### 1G. Update `persona_mapping_protocol` placeholders_to_fill

Remove references to user_profile_template and session_template. Single output file.

### 2. ADR-26005 (revision)

Update the already-created ADR to reflect single-file output:
- The fix applies to BOTH generation phase (templates in meta-prompt) AND learning sessions (session template in mentor rules)
- Generated output: 1 file, not 3
- User workflow: 1-2 attachments per session

### 3. CLAUDE.md

- Remove `templates/` from file structure
- Generated Output section: 1 file + course_history
- Core Files: single merged template
- Usage Workflow: simplified attachment instructions
- ADR-26005 in architectural principles

### 4. CHANGELOG.md

v0.41.0 entry documenting the merge.

### 5-7. Delete template files

Remove all three `.template.md` files.

## Implementation Order

1. Build the merged template (1A) — the critical step
2. Update mentor_generator.json (1B-1G)
3. Revise ADR-26005 (2)
4. Delete template files (5-7)
5. Update CLAUDE.md (3)
6. Update CHANGELOG.md (4)
7. Validate JSON, verify all references
8. Save plan to misc/plan/implemented/

## Verification

1. `mentor_generator.json` parses as valid JSON
2. Merged template contains ALL sections from all three former templates
3. `file_generation.steps` produce 1 file, not 3
4. `guidance_for_user` describes 1-file + course_history workflow
5. `course_history_protocol` references "this file" + course_history (not 4 files)
6. `session_output_protocol` contains the session record template inline
7. `context_management` says 2 files (mentor_system_prompt + course_history)
8. No references to external `.template.md` files, `user_profile` as separate file, or `session_template` as separate file remain
9. CLAUDE.md reflects single-file architecture
10. User-maintained fields (`learning_style_observed`, `known_difficulties`) present with empty defaults
