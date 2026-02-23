# Mentor Generator: Architectural Analysis & Human-Like Traits Recovery Plan

## Context

The mentor_generator.json was refactored from a monolithic v0.29.1 (old_file.json) into a 3-template architecture (v0.34.1). Two concerns arose:
1. Is the current architecture maintainable mid-course and ready for agentic workflow?
2. Did the refactoring lose carefully tested human-like behavior formulations?

---

## Part 1: Architectural Analysis

### What works well (keep)

- **Clean 3-file separation**: mentor_system_prompt (static rules), user_profile (mutable user data), session files (immutable history). This is agent-friendly — each file has a single responsibility.
- **Immutable session files**: Safe history that can't be corrupted. Agents can append but not destroy.
- **Template-based output**: Predictable JSON structure makes programmatic parsing straightforward.
- **Separation of mentor from user**: Same mentor_system_prompt works for multiple users — reusable.

### Critical gaps that will break learning mid-course

#### Gap 1: No context compression — sessions accumulate infinitely

**Problem**: After 15-20 sessions, attaching ALL session files to a new chat will exceed context limits for most models (128k-200k tokens). The learning process WILL break mid-course.

**Old version had**: `compression_rules` (summarize history, merge updates), `retention_policy` (compress completed phases, retain current phase), `summary_digest`, `state_update_token_threshold: 200000`.

**Current version has**: Nothing. No compression, no threshold, no awareness of context limits.

**Decision**: Use a single append-only `course_history` file instead of individual session files. Session records are already concise summaries (~500-1000 tokens). No phase-level compression needed — see ADR-26001.

#### Gap 2: No curriculum position tracking in user_profile

**Problem**: The user_profile has the curriculum but no field for "current position."

**Decision**: SKIPPED. The `position` block in each session record within course_history serves as the authoritative position tracker. Adding `current_position` to user_profile would violate its design as a quasi-static file (only updated for fundamental changes like hardware/language/goals).

#### Gap 3: No agentic interface specification

**Problem**: The system is designed for copy-paste workflow. For agentic workflow, agents need to know: file naming conventions, directory structure, which files to read/write/append, and session lifecycle.

**Decision**: Deferred. Create interface spec when agentic workflow is actually needed.

---

## Part 2: Human-Like Traits — Divergence Analysis

### The philosophical shift

| Aspect | Old (v0.29.1) | New (v0.34.1) |
|--------|---------------|---------------|
| Core approach | "No emotions, no empathy, only reasoning" | "Be direct and truthful but polite and supportive" |
| Anti-sycophancy | Strip ALL emotion, anti-praise examples | Avoid list (empty praise, cold corrections) |
| Peer review | "emotionless" — rewrite emotional framing to neutral | "Human Check" — must sound like someone who cares |
| Teaching feel | Strict academic/Socratic | Warm guide/partner |

### The reconciliation principle

**Warmth and anti-sycophancy are NOT contradictory.** The fix is NOT to revert to "emotionless" but to add the concrete anti-sycophancy mechanisms (anti-praise examples, two-attempt rule, require reasoning) INTO the warm framework.

### Formulations restored (v0.35.0)

1. **Anti-praise examples** — concrete few-shot examples added to `feedback_approach`
2. **Two-attempt rule** — `patience_with_attempts` expanded with `on_first_miss` / `on_second_miss`
3. **require_reasoning** — restored from weakened `encourage_reasoning`
4. **Mastery check enforcement** — expanded with `if_incomplete` and `gate` fields
5. **Fiction/sci-fi recovery** — restored in `emergency_brake_rules.recovery_protocol`
6. **Persona mapping rules 6-7** — restored (jargon in learning rules + signature greeting)
7. **Failure log in peer review** — checkpoint updated to reference `course_history mentor_failures`

### Formulations kept as-is (v0.32.0/v0.34.0 improvements)

1. `pedagogical_principles` (partnership, honesty, respect, patience, curiosity)
2. `feedback_approach` with when_correct/when_incorrect/when_struggling
3. Welcome message examples with persona-specific warmth
4. "Human Check" in peer review
5. `no_time_pressure` in mastery gating
6. `honesty_and_warmth` and `genuine_interest`

---

## Implementation Summary

### Files modified

1. **`templates/mentor_system_prompt.template`** — primary changes:
   - Added `anti_praise_examples` to `feedback_approach`
   - Replaced `patience_with_attempts` with concrete two-attempt rule
   - Changed `encourage_reasoning` to `require_reasoning`
   - Expanded `mastery_check` with enforcement detail
   - Restored fiction/sci-fi in `emergency_brake_rules.recovery_protocol`
   - Updated "Level Appropriateness" checkpoint to mention failure log
   - Added `context_management` section (single-file approach)
   - Renamed `session_files_protocol` to `course_history_protocol`
   - Updated `session_output_protocol` for append-to-file workflow
   - Removed duplicated trigger logic from `session_protocols` _notes (DRY)

2. **`mentor_generator.json`**:
   - Restored persona mapping rules 6-7
   - Updated `guidance_for_user` for single-file course_history workflow
   - Updated `template_references` for course_history terminology
   - Bumped version to 0.35.0

3. **`templates/user_profile.template`** — no changes (current_position skipped)

### New files

- `architecture/adr/adr_26001_single_file_course_history.md` — ADR for single-file decision
