# Plan: Fix 4 Structural Regressions (v0.36.0 → v0.37.0)

## Problem Statement

v0.36.0 introduced 4 regressions compared to v0.29.1 (`old_file.json`) during end-to-end testing:

1. LLMs print "STOP. Wait for user response." as visible output
2. Mentor tone/role question (Q9) is skipped
3. Self-validation not performed
4. Files generated immediately after Q8, skipping Q9/validation/guidance

## Root Cause Analysis

### Regression 1: "STOP. Wait for user response." printed

| Version | Approach | Outcome |
|---------|----------|---------|
| v0.29.1 | No stop text anywhere. Single `_notes.wait_user` instruction | Works — nothing to print |
| v0.31.1 | Added `"then": "STOP. Wait for user response."` per question | LLMs print it verbatim |
| v0.36.0 | Renamed to `"_then"` + added FIELD CONVENTION rule | Still printed — underscore convention not universally respected |

**Root cause**: The literal text "STOP. Wait for user response." exists 10 times in the JSON. Some LLMs (especially Gemini) treat any natural-language field value as dialogue content regardless of key naming conventions.

**v0.29.1 solution that worked**: No such text exists in the file at all. Turn-taking is a general instruction in `_notes`, not per-question text.

### Regression 2: Q9 (mentor tone) skipped

**v0.29.1**: Questions are a flat list of bare strings. Q9 is structurally identical to Q2-Q8 — just another string in an array. No structural signal to stop before Q9.

**v0.36.0**: Questions are nested objects with `ask`/`_then` fields. After Q8's long multi-paragraph strategy question + `"_then": "STOP"`, some LLMs interpret the collection as complete because:
- Q8 is the last "substantive" question (asks for a strategy choice with detailed explanations)
- The `_then` stop signal after Q8 creates a structural pause
- No explicit question count says "there are exactly 9 questions"
- Q9 is about tone/persona — feels optional compared to core learning questions

### Regression 3: Self-validation not performed

**v0.29.1**: `validation` and `verbal_validation_report` are items in the sequence, but file generation is embedded as step 8/8 inside `guidance_for_user.steps`. The LLM must pass through all prior steps to reach generation.

**v0.36.0**: `validation` and `verbal_validation_report` are separate sibling objects in `interactive_input_sequence`. They are "passive checklist items" — the LLM can skip them because they are not structurally linked to file generation.

### Regression 4: Premature file generation

**v0.29.1**: File generation is step 8 of 8 inside `guidance_for_user.steps`, after explicit user confirmation (step 7). The 300-line inline `mentor_system_prompt_template` provides "structural gravity" — the LLM can see how much work remains.

**v0.36.0**: `file_generation_protocol` is a separate top-level object, guarded only by `"_notes": "Execute ONLY after user confirms readiness."` This is a weak barrier because:
- It relies on `_notes` (internal instruction) to prevent a visible action
- Templates are external references, so the LLM sees a short path from "questions done" to "output files"
- The `guidance_for_user` verbatim message is ~80 lines that can be skipped

## Design Decisions

### Decision 1: Remove all `_then` fields, restore bare-string questions

**Rationale**: v0.29.1 proved that a single general `_notes` instruction is sufficient for turn-taking. Per-question stop text was added in v0.31.1 for Gemini compatibility, but it introduced the very text that LLMs print. The fix is to remove the source of the problem, not try to hide it with naming conventions.

**Trade-off**: Gemini Flash may not stop after each question without per-question signals. However, the current approach causes worse problems (printing stop text + skipping questions). The general `_notes` instruction works for Claude, ChatGPT, DeepSeek, and most Gemini models.

### Decision 2: Add explicit question count with triple reinforcement

**Rationale**: Neither v0.29.1 nor v0.36.0 explicitly states how many questions exist. Adding the count in three places creates redundancy that LLMs can't miss:
1. `collection._notes`: "There are exactly 9 questions plus a greeting step (10 interactions total)"
2. `collection.total_questions: 10` (machine-readable)
3. `_notes.CRITICAL_TURN_TAKING`: "...The collection has EXACTLY 10 steps"

### Decision 3: Merge validation + verbal_report → `validation_gate`

**Rationale**: Two separate objects = easy to skip. One object named "gate" with `proceed_condition` = structural prerequisite.

Key structural elements:
- Name includes "gate" — signals blocking behavior
- `_notes`: "MANDATORY GATE. You CANNOT proceed..."
- `proceed_condition`: "ALL checks passed. ONLY THEN proceed."
- `verbal_report` is inline, not a separate skippable object

### Decision 4: Merge guidance + file_generation → `guidance_and_generation`

**Rationale**: Recreates v0.29.1's embedded gate pattern. File generation is phase 2 inside the same object as guidance (phase 1). The LLM cannot "see" the file generation instructions without also having processed the guidance and confirmation request.

Key structural elements:
- `phase_1_guidance` ends with "Are you ready?" — natural confirmation gate
- `phase_2_generate_files._notes`: "Execute ONLY after user explicitly confirms"
- Both phases are in one JSON object — structural coupling, not just sequential ordering

## Changes Applied

### `mentor_generator.json`

**interactive_input_sequence structure change**:

Before (8 items):
```
[_notes, procedure_control_flow, collection[...], persona_mapping,
 validation, verbal_validation_report, guidance_for_user, file_generation_protocol]
```

After (6 items):
```
[_notes, procedure_control_flow, collection{...}, persona_mapping,
 validation_gate, guidance_and_generation]
```

**Question format change**: `{ask, _then}` objects → bare strings (Q2-Q9), minimal objects without `_then` (greeting, Q1).

**Collection format change**: Array → Object with `_notes`, `total_questions`, `questions` array.

### `CHANGELOG.md`

Prepended v0.37.0 entry documenting all changes.

## Verification

1. `python3 -m json.tool mentor_generator.json` — JSON syntax valid
2. End-to-end test with LLM — verify all 4 regressions are fixed
