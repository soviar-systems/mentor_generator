# Plan: Fix 5 Behavioral Bugs in mentor_generator.json (v0.37.1 → v0.38.0)

## Context

The user tested the meta-prompt (v0.37.1) and the AI exhibited 4 bugs traceable to 5 root causes in the questionnaire flow. The file has been through 4 rounds of fixes (v0.35.0 → v0.37.1) with a history of regressions from over-engineering. This plan applies **minimal, targeted structural fixes** following the project principle: "Predictability comes from constraints, not instructions."

### Observed Bugs (from user's test trace)

| Bug | What happened | Expected |
|-----|--------------|----------|
| B1 | After greeting, AI said "How can I help you today, master?" | Should proceed to Q1 |
| B2 | Q2 asked with Q3's content ("What is your current level...") | Should ask "What topic or subject..." |
| B3 | After file upload, Q2 asked again (step didn't advance) | Should accept file as answer, advance |
| B4 | Q3 re-asked verbosely when user said "I showed you my experience" | Should acknowledge file, ask specific clarification |

### Root Causes

| RC | Description |
|----|-------------|
| RC1 | `greeting_step` is a bare string with no post-response instruction — AI has no structural guidance to proceed to Q1 |
| RC2 | Mixed question formats (bare strings vs objects) cause content confusion when AI indexes the array |
| RC3 | No instruction about treating file uploads as answers |
| RC4 | Top-level `_notes` says "10 steps" but actual count is 11 — contradicts state_tracker and inner notes |
| RC5 | `procedure_control_flow` assigns persona_mapping_confirmation (Step 10) to Phase 1, but Phase 2 (PERSONA_MAPPING) requires Step 11 — logical contradiction |

---

## Changes

### Change 1: Fix step count in top-level `_notes` [RC4]

**File:** `mentor_generator.json`, line 12

**Before:**
```
"There are exactly 10 interaction steps (greeting + 9 questions). Complete ALL of them."
```

**After:**
```
"There are exactly 11 interaction steps (greeting + 9 questions + 1 mapping confirmation). Complete ALL of them."
```

### Change 2: Realign phase-step boundaries in `procedure_control_flow` [RC5]

**File:** `mentor_generator.json`, lines 56-68

**Before:**
```json
"PHASE_1_COLLECTION": {
  "requires": "Steps 0-10",
  "status": "IN_PROGRESS"
},
"PHASE_2_PERSONA_MAPPING": {
  "requires": "Step 11",
  "status": "LOCKED"
},
```

**After:**
```json
"PHASE_1_COLLECTION": {
  "requires": "Steps 0-9 (greeting + questions 1-9)",
  "status": "IN_PROGRESS"
},
"PHASE_2_PERSONA_MAPPING": {
  "requires": "PHASE_1_COLLECTION complete (Step 10: apply persona_mapping_protocol, present confirmation, get user approval)",
  "status": "LOCKED"
},
```

State tracker constraint (`Step < 11`) and denominator (`N/11`) remain unchanged — they're correct.

### Change 3: Normalize Q2-Q8 from bare strings to `{ "ask": "..." }` objects [RC2]

**File:** `mentor_generator.json`, lines 88-94

Wrap each bare string in `{ "ask": "..." }`. Example:

**Before:** `{ "question_2": "What topic or subject..." }`
**After:** `{ "question_2": { "ask": "What topic or subject..." } }`

Apply to questions 2, 3, 4, 5, 6, 7, 8 (7 questions total).

**Why safe:** The v0.36.0 "STOP printing" bug was caused by `_then` fields with printable text. This adds only `ask` fields — no `_then`, no printable stop text. The structural uniformity (every question is `{ "question_N": { "ask": "..." } }`) eliminates the format-switching that caused content confusion.

### Change 4: Add `on_response` to `greeting_step` [RC1]

**File:** `mentor_generator.json`, lines 79-81

**Before:**
```json
{
  "greeting_step": "Greet and ask the user in Russian and English..."
}
```

**After:**
```json
{
  "greeting_step": {
    "ask": "Greet and ask the user in Russian and English what language they prefer to speak. Example: 'Здравствуйте! Какой язык вам удобнее для дальнейшего взаимодействия со мной?\n\nHello! Please, choose the language you want to talk to me.'",
    "on_response": "Record the user's language choice. Switch to that language for ALL future dialogue. Then proceed directly to question_1 — do NOT output any other response."
  }
}
```

### Change 5: Add file attachment handling to `_notes` [RC3]

**File:** `mentor_generator.json`, lines 40-51 (the `_notes` object inside `interactive_input_sequence`)

Add new entry:
```json
"FILE_AS_ANSWER": "If the user uploads or attaches a file instead of typing text, treat the file content as their answer to the current question. Acknowledge the file, extract relevant information, and advance to the next step. Do NOT re-ask the same question."
```

### Change 6: Version bump + changelog

- `metadata.version`: `"0.37.1"` → `"0.38.0"`
- `metadata.modified`: update to `"2026-02-13"`
- Prepend `CHANGELOG.md` with v0.38.0 entry

---

## Files Modified

| File | Changes |
|------|---------|
| `mentor_generator.json` | All 5 structural fixes + version bump |
| `CHANGELOG.md` | New v0.38.0 entry |

---

## Verification

1. `python3 -m json.tool mentor_generator.json` — validate JSON syntax
2. Verify `questions` array still has 11 items
3. Verify all questions have `{ "ask": "..." }` pattern
4. Verify step counts agree: top-level `_notes` = 11, `CRITICAL_TURN_TAKING` = 11, state_tracker = `/11`
5. Verify phase boundaries: Phase 1 = Steps 0-9, Phase 2 = Step 10
6. End-to-end: paste into LLM chat and test greeting → Q1 transition, file uploads, Q2/Q3 content accuracy

---

## Implementation Order

1. Change 1 (step count fix) — pure data correction
2. Change 2 (phase alignment) — FSM logic correction
3. Change 3 (normalize Q2-Q8) — structural fix, biggest change
4. Change 4 (greeting bridge) — depends on object pattern from Change 3
5. Change 5 (file handling note) — additive only
6. Change 6 (version + changelog) — last
