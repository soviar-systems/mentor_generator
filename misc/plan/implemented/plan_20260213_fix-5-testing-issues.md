# Plan: Fix 5 issues found during mentor_generator.json testing

## Context

User tested `mentor_generator.json` end-to-end and discovered 5 problems: a "STOP" instruction leaking into visible output, a regression in validation detail, incomplete session-ending guidance, a missing note about extra attachments, and a false claim about AI file validation.

---

## Issue 1: "STOP. Wait for user response." printed visibly after each question

**File:** `mentor_generator.json`, lines 63–119

**Root cause:** The `"then": "STOP. Wait for user response."` field sits outside `_notes`, so LLMs may treat it as content to print rather than a behavioral directive. The `_notes.CRITICAL_TURN_TAKING` block (lines 34–41) already contains proper turn-taking instructions.

**Fix:** Convert `"then"` to `"_then"` in all 10 occurrences (greeting_step + Q1–Q9). The `_` prefix follows the project convention for AI-internal fields. Keep the values as-is — they serve as procedural hints for weaker models, but won't be printed because `_`-prefixed fields are treated as notes.

Changes (10 occurrences):
- Line 63: `"then"` → `"_then"` (greeting_step)
- Line 70: `"then"` → `"_then"` (Q1)
- Line 76: `"then"` → `"_then"` (Q2)
- Line 82: `"then"` → `"_then"` (Q3)
- Line 88: `"then"` → `"_then"` (Q4)
- Line 94: `"then"` → `"_then"` (Q5)
- Line 100: `"then"` → `"_then"` (Q6)
- Line 106: `"then"` → `"_then"` (Q7)
- Line 112: `"then"` → `"_then"` (Q8)
- Line 118: `"then"` → `"_then"` (Q9)

---

## Issue 2: Validation report is abrupt compared to old_file.json

**File:** `mentor_generator.json`, lines 138–157

**Root cause:** The refactoring from monolithic to template-based architecture correctly removed checks about dual-role clarity and state management (no longer relevant). But the current version has only 4 checks, and the `verbal_validation_report` instruction is vague — it just says "detailed VERBAL report" without guiding what "detailed" means.

**Fix:**
1. Add a 5th check: `"template_completeness"` — verify all `<placeholder>` fields in templates are filled with user data, no placeholders remain
2. Enhance the `verbal_validation_report.action` with explicit structure guidance
3. Keep the self_check_loop as-is (it's fine)

New validation section:
```json
"deep_pedagogical_self_validation": {
  "_notes": "VERBALLY confirm EACH check has passed before outputting files.",
  "user_level_appropriateness": "Match learning flow to user's starting level. Include zero-level fallback if beginner.",
  "stepwise_flow_integrity": "Ensure micro-validation points exist and emergency brakes allow reverting to simpler explanations.",
  "rule_consistency": "Check staged progression and depth levels are coherent with user profile.",
  "curriculum_completeness": "Verify curriculum phases cover the topic adequately for stated goals.",
  "template_completeness": "Verify all template placeholders will be filled with user data. No <placeholder> fields should remain unfilled."
}
```

New verbal_validation_report:
```json
"verbal_validation_report": {
  "_notes": "MANDATORY step. Present this report BEFORE guidance_for_user.",
  "action": "Generate a VERBAL report for the user. For EACH of the five validation checks: state the check name, confirm pass/flag concern, and briefly explain your reasoning. If any check fails, engage self_check_loop before proceeding."
}
```

---

## Issue 3: "When you end a learning session" only covers user-initiated end

**File:** `mentor_generator.json`, lines 192–196

**Root cause:** Only describes "tell the mentor you want to end." Misses natural conclusion and context-limit scenarios.

**Fix:** Rewrite lines 192–196 to cover all three cases:

```json
"**When a session ends:**",
"A session can end in several ways:",
"- **You decide to stop** — tell the mentor (e.g., 'Let's wrap up for today')",
"- **A topic or phase is completed** — the mentor may suggest a natural stopping point",
"- **The conversation gets very long** — if you notice the AI struggling or repeating itself, wrap up the session to preserve your progress. Web chats have context limits that are not always visible to you.",
"",
"In all cases:",
"1. The mentor will output a new session record",
"2. Append this record to your **course_history** file — it contains your progress, learning observations, and any mentor mistakes to avoid",
"3. Never delete old records from course_history — each session appends a new record",
```

---

## Issue 4: Add note about additional files in "Why One course_history File?"

**File:** `mentor_generator.json`, lines 202–204

**Fix:** Add a sentence after the existing paragraph:

```json
"### Why One course_history File?",

"Most web AI chats limit how many files you can attach. By keeping all session records in one file, you only ever need to attach 3-4 files total, no matter how many sessions you've had.",

"You can always attach additional files alongside the core ones — for example, a workbook with exercises you completed, reference materials, or code samples you want the mentor to review during the session.",
```

---

## Issue 5: False claim about AI detecting file errors

**File:** `mentor_generator.json`, line 228

**Root cause:** The claim "the AI will tell you the file has an error" is unreliable. Most LLMs silently work with malformed JSON or hallucinate corrections. The mentor has no file-validation protocol.

**Fix:** Replace line 228 with honest, still reassuring guidance:

```json
"**You won't break anything** as long as you only change the values (the parts after the colons). To be safe, keep a backup copy before editing. If your mentor starts behaving unexpectedly after an edit, check the file for JSON syntax errors (mismatched quotes, missing commas). You can paste the file into any free online JSON validator to verify it.",
```

---

## Verification

1. Validate JSON syntax of `mentor_generator.json` after all edits (paste into `python3 -m json.tool`)
2. Re-run the meta-prompt end-to-end in a test chat to verify:
   - Questions are asked one at a time without printing "STOP"
   - Validation report is detailed and structured
   - User guidance covers all three session-ending scenarios
   - "Why One course_history File?" mentions additional files
   - Editing advice is honest (no false AI validation claim)

## Files modified

- `mentor_generator.json` — all 5 fixes
