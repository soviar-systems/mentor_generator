# Plan: Complete Strict Placeholder Injection in Templates

## Context

Commit `4d622de` fixed `mentor_generator.json` to adopt the "compiler" role with strict placeholder injection (ADR-26002). But it did not touch the templates. The templates had functional gaps that broke the compiler contract:

1. **Persona mapping has no injection points**: `persona_mapping_protocol` rules 5/7 say to update greetings and emergency brake, but those fields have no `<placeholder>` tokens
2. **session.template._template_notes contradict architecture**: say "Save as session_N" but system uses single course_history file (ADR-26001)
3. **mentor_generator.json references are incomplete**: `placeholders_to_fill` doesn't list persona injection points
4. **`example_*` fields violate schema convention**: not `_`-prefixed despite being guidance, not output data
5. **Persona mapping rule 6 conflicts with immutability**: says "embed jargon into learning_framework.rules" but rules should be immutable

## Revision: Over-Engineering Stripped

The original plan (from plan mode) included 6 additional changes that were rejected before implementation as over-engineering per ADR-26003:

- ~~`placeholder_convention` and `immutability_scope` in template `_template_notes`~~ — redundant with `preservation_first` in mentor_generator.json
- ~~`_immutable` markers on 3 sections~~ — redundant, adds structural noise
- ~~`session_length_awareness` in context_management~~ — scope creep, unrelated to placeholder injection
- ~~`placeholder_convention` in user_profile template~~ — redundant with mentor_generator.json

This revision prompted two new ADRs:
- **ADR-26003**: Instruction Budget — LLM context limits vs redundant guardrails
- **ADR-26004**: Templates are output schemas, not examples

## Files Modified

1. `templates/mentor_system_prompt.template.md`
2. `templates/session.template.md`
3. `mentor_generator.json`
4. `CHANGELOG.md`

## Changes Implemented

### 1. `templates/mentor_system_prompt.template.md`

**1B. Added `greeting_text` placeholder to `first_session_protocol.welcome_message`**
- Renamed `example_*` → `_example_*` (ADR-26004: schema field taxonomy)
- Added `greeting_text` field with `<placeholder>` for persona-appropriate welcome

**1C. Added `greeting_text` placeholder to `subsequent_session_protocol.continuation_greeting`**
- Same pattern: renamed `example_*` → `_example_*`, added `greeting_text` placeholder

**1D. Added `persona_adaptation` placeholder to `emergency_brake_rules`**
- New field for persona-specific encouragement
- `recovery_protocol` and `explicit_check` left unchanged (immutable)

### 2. `templates/session.template.md`

**2A. Fixed `_template_notes` to match course_history architecture**
- Replaced "Save as session_N" / "Attach ALL session files" with course_history workflow
- Now correctly describes append-to-course_history usage

### 3. `mentor_generator.json`

**4A. Updated `persona_mapping_protocol.mapping_rules`**
- Rule 5 now targets `emergency_brake_rules.persona_adaptation` (not immutable `recovery_protocol`)
- Removed old rule 6 (jargon in learning_framework.rules — conflicts with immutability)
- Old rule 7 split into rule 6 (first session greeting) and rule 7 (continuation greeting)
- All rules now explicitly reference placeholder fields

**4B. Updated `placeholders_to_fill` with complete manifest**
- 9 entries, each mapping to an actual `<...>` placeholder in the template

**4C. Fixed `preservation_first` to cover all `_`-prefixed fields**
- Now explicitly lists `_notes`, `_template_notes`, `_example_*`

**Version bump**: 0.39.0 → 0.40.0, modified date fixed to 2026-02-14

## Verification Results

All checks passed:
1. All 4 JSON files parse correctly
2. Every `mapping_rules` rule references a field with a `<...>` placeholder
3. Every `placeholders_to_fill` entry maps to an actual placeholder
4. `session.template._template_notes` no longer mentions "session_N" or "separate files"
5. `recovery_protocol` and `explicit_check` have no placeholders (immutable)
6. All greeting example fields have `_example_*` prefix
