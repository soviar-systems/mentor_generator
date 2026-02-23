# Architecture Post-Mortem: Mentor Generator v0.31.0 → v0.34.0

**Date:** January 28, 2026
**Author:** vrudakov + Claude Opus 4.5
**Document Type:** Lessons Learned / Decision Record

---

## Executive Summary

The v0.31.0 architecture correctly separated meta-prompt from mentor behavior, but introduced a new problem: **dynamic data (mentor failures, learning patterns) was placed in static files**.

This document captures the issue, why it matters, and the reasoning behind the v0.34.0 three-template architecture.

---

## Part 1: The v0.31.0 Architecture

### File Structure

```
mentor_generator/
├── mentor_generator.json              # Meta-prompt (questionnaire)
├── templates/
│   ├── mentor_system_prompt.template  # Mentor behavior rules ("static")
│   └── course_config.template         # User profile + curriculum + failure log
```

### What It Got Right

1. **Role Separation**: Meta-prompt and mentor in different files
2. **Immutable Sessions**: Each session creates new file, never modifies old
3. **Minimal Output**: Session file ~30 lines vs 450 lines of old architecture
4. **Template-First**: Mentor fills exact template, doesn't decide structure

### What It Got Wrong

The `course_config.template` contained `mentor_failure_log`:

```json
"mentor_failure_log": {
  "_notes": "Logs mentor errors for self-correction...",
  "log_entries": [
    {"error": "", "context": "", "lesson": ""}
  ]
}
```

And `mentor_system_prompt.template` instructed:

```json
"self_correction": "Before explaining a concept, check course_config.mentor_failure_log..."
```

**The Problem:** `course_config` was described as "rarely changes" and "static per user." But `mentor_failure_log` is inherently dynamic—it should grow over time as the mentor makes mistakes.

---

## Part 2: Why This Matters

### Scenario: Mentor Makes a Mistake

**Session 5:** Mentor gives a confusing analogy for recursion. User is frustrated.

**Expected behavior:** Mentor logs the failure, avoids that analogy in future sessions.

**Actual behavior with v0.31.0:**
1. Mentor might say "I'll remember that" but has nowhere to write it
2. The session file template has no `mentor_failures` field
3. The `course_config.mentor_failure_log` exists but:
   - User would need to manually edit it
   - It's described as "rarely changes" so users don't think to update it
   - There's no workflow for updating it

**Result:** The mentor never learns. Same mistakes repeat. User frustration accumulates.

### The Deeper Issue: Mixed Concerns

`course_config.template` contained:
- **Static data**: user profile, skills, goals, hardware constraints, curriculum
- **Dynamic data**: mentor_failure_log

This violates the principle established in the v0.30 postmortem:
> "Make operations append-only... Create new state files, don't modify existing ones."

If failure logs are in `course_config`, they can only be updated by modifying that file—which contradicts the append-only principle.

---

## Part 3: What Was Missing from Sessions

The v0.31.0 session file template:

```json
{
  "session_number": 5,
  "timestamp": "...",
  "duration_approx": "...",
  "position": {
    "phase": "...",
    "topic_covered": "...",
    "next_topic": "...",
    "phase_progress": "..."
  },
  "mastery": {
    "concepts_validated": [...],
    "concepts_struggling": [...],
    "validation_method": "..."
  },
  "session_summary": "...",
  "learning_observations": [...],
  "resources_suggested": [...],
  "mentor_notes": "..."
}
```

**What was missing from old_file.json (v0.29.1):**

| Old Field | v0.31.0 Location | Problem |
|-----------|------------------|---------|
| `mentor_failure_log` | course_config | Can't update dynamically |
| `tasks_completed` / `implementation_progress` | Missing | Lost session detail |
| `projects_worked_on` | Missing | Lost project tracking |
| `user_problems` / `problem_patterns` | Missing | Lost difficulty tracking |
| `external_resources_log` | Partial (resources_suggested exists) | OK |
| `learning_style_observed` | Partial (learning_observations exists) | OK |

The session template captured position and mastery but lost the "what actually happened" detail.

---

## Part 4: The Solution - Three-Template Architecture

### New File Structure

```
templates/
├── mentor_system_prompt.template  # Mentor behavior rules (TRULY static)
├── user_profile.template          # User data + curriculum (static per user)
└── session.template               # Session record (dynamic per session)
```

### What Goes Where

| Data Type | File | Update Frequency |
|-----------|------|------------------|
| Mentor behavior rules | mentor_system_prompt.template | Never |
| User profile, skills, goals | user_profile.template | Never (after generation) |
| Hardware/software constraints | user_profile.template | Never |
| Curriculum phases/topics | user_profile.template | Never |
| Session progress | session_N files | Each session (new file) |
| Tasks completed | session_N files | Each session |
| Projects worked on | session_N files | Each session |
| User problems | session_N files | Each session |
| Mentor failures | session_N files | Each session |
| Learning observations | session_N files | Each session |
| Resources suggested | session_N files | Each session |

### The Key Insight

**Session files are the ONLY dynamic data.**

The mentor doesn't need a separate "failure log file" because:
1. Each session can record failures from that session
2. Mentor scans ALL session files at start
3. Cumulative failure history is the union of all session files
4. Append-only: new sessions add data, old sessions unchanged

### Updated Session Template

```json
{
  "session_number": 5,
  "timestamp": "...",
  "duration_approx": "...",

  "position": {...},

  "content": {
    "session_summary": "...",
    "tasks_completed": ["<exercises solved>"],
    "projects_worked_on": ["<project work>"],
    "resources_suggested": [...]
  },

  "mastery": {...},

  "observations": {
    "learning_patterns": ["<how user learns>"],
    "user_problems": ["<difficulties encountered>"],
    "mentor_failures": [
      {"error": "...", "context": "...", "lesson": "..."}
    ]
  },

  "mentor_notes": "..."
}
```

### How the Mentor Uses This

At session start, the mentor:

1. Reads `mentor_system_prompt` for behavior rules
2. Reads `user_profile` for static user data and curriculum
3. Reads ALL `session_N` files and synthesizes:
   - Current position (from latest session's `next_topic`)
   - Cumulative learning patterns (union of all `learning_patterns`)
   - All mentor failures to avoid (union of all `mentor_failures`)
   - All suggested resources (for follow-up questions)
   - All user problems (to watch for recurring difficulties)

This synthesis happens naturally from reading files—no special "state management" needed.

---

## Part 5: Why This Approach Works

### Principle 1: Append-Only is Natural

Sessions are inherently append-only. You don't "update" session 3 after session 5—you create session 6. The data model matches the reality.

### Principle 2: Synthesis Over Storage

Instead of maintaining a "master failure log" that must be updated, the mentor synthesizes a failure list from session history each time. This is:
- More reliable (can't corrupt a master file)
- More complete (full history preserved)
- More natural (matches how humans review notes)

### Principle 3: Clear File Roles

- `mentor_system_prompt.template`: How to teach (behavior)
- `user_profile.template`: Who you're teaching (user data)
- `session.template`: What happened (session record)

No file has mixed concerns. No file needs updating after creation.

### Principle 4: "Static" Actually Means Static

The v0.31.0 `mentor_system_prompt.template` said it was "static" but instructed checking `course_config.mentor_failure_log`. This was confusing:
- The rules are static, but they reference dynamic data
- "Static file checks dynamic file" is a code smell

The v0.34.0 approach:
- `mentor_system_prompt.template` contains rules (static)
- Rules say "scan session files for failures" (session files are dynamic)
- The static file references dynamic files correctly

---

## Part 6: Naming Decisions

### Why Rename `course_config` → `user_profile`?

1. **Accuracy**: The file contains user profile and curriculum, not "course configuration"
2. **Clarity**: "Profile" suggests static user data; "config" suggests something you might change
3. **Parallel naming**: `user_profile` pairs well with `mentor_system_prompt` (both are about WHO)

### Why a Separate `session.template`?

In v0.31.0, the session template was embedded inside `mentor_system_prompt.template` under `session_output_protocol.session_file_template`.

Problems:
1. Not visible as a first-class template
2. Harder to review and modify
3. Mixed concerns (behavior rules + output format)

Solution: Extract to standalone file. The template IS the constraint—make it visible.

---

## Part 7: Migration Notes

### For Existing Users

Users who already generated files with v0.31.0 terminology:
- `course_config` files still work (content is the same)
- Can optionally rename to `user_profile` for consistency
- No data loss—just naming change

### For New Users

The v0.34.0 `guidance_for_user` explains the three-file structure clearly.

---

## Part 8: Lessons Learned

### Lesson 1: Test the Update Workflow

We tested session creation but not "what happens when the mentor fails and needs to remember it." The failure logging workflow was broken because we didn't trace through it.

**Practice:** For each data type, ask: "How does this get created? How does it get read later?"

### Lesson 2: "Static" Should Mean Static

If you call something static, ensure nothing dynamic depends on it being updated. The `mentor_failure_log` in `course_config` was a violation of our own principle.

**Practice:** Label files by their actual update frequency: Static (never), Per-User (once), Per-Session (each time).

### Lesson 3: Old Architecture Had Wisdom

The old monolithic `old_file.json` had problems (regeneration, role confusion), but it also had comprehensive tracking:
- `implementation_progress`
- `problem_patterns`
- `learning_style_observed`

When splitting, we lost some of this detail. The session template should be comprehensive enough to capture everything the old approach captured—just organized correctly.

**Practice:** When refactoring, audit: "What does the old version track that we might lose?"

---

## Part 9: What Could Go Wrong

### Risk 1: Session Files Grow Large

If users have 50+ sessions, attaching all files might hit context limits.

**Mitigation:** This is acceptable. The postmortem established that LLMs can't count tokens reliably, so we shouldn't try to manage context. Let the LLM's context window be the natural limit. Users can start fresh course if needed.

### Risk 2: Mentor Fails to Synthesize

The mentor must combine data from multiple session files. This could fail.

**Mitigation:** The synthesis is read-only and cumulative (union of arrays). No judgment calls like "summarize" or "compress." The mentor just collects all `mentor_failures` entries, doesn't decide which to keep.

### Risk 3: Users Forget to Attach Files

If user forgets session files, mentor loses context.

**Mitigation:** The `guidance_for_user` clearly states "attach ALL session_N files." This is a user workflow issue, not an architecture issue.

---

## Appendix A: Data Flow Diagram

```
Meta-Prompt Phase:
┌─────────────────────┐
│ mentor_generator.json │ → Questionnaire → User Answers
└─────────────────────┘
           │
           ▼
    ┌──────────────────────────────────┐
    │ Generate two files:               │
    │   • mentor_system_prompt          │
    │   • user_profile                  │
    └──────────────────────────────────┘

Learning Session Phase:
┌────────────────────────────────────────────────────┐
│ User attaches:                                      │
│   • mentor_system_prompt (behavior rules)           │
│   • user_profile (static user data)                 │
│   • session_1, session_2, ... (previous sessions)   │
└────────────────────────────────────────────────────┘
           │
           ▼
    ┌──────────────────────────────────┐
    │ Mentor synthesizes context:       │
    │   • Current position              │
    │   • All past failures             │
    │   • Learning patterns             │
    │   • Suggested resources           │
    └──────────────────────────────────┘
           │
           ▼
    [Teaching Session]
           │
           ▼
    ┌──────────────────────────────────┐
    │ Session ends → Output session_N   │
    │   • New file (append-only)        │
    │   • Contains session record       │
    │   • Includes any failures         │
    └──────────────────────────────────┘
```

---

## Appendix B: Field Mapping

| v0.29.1 (old_file.json) | v0.31.0 | v0.34.0 |
|-------------------------|---------|---------|
| `mentor_failure_log` | course_config | session.observations.mentor_failures |
| `learning_changelog.session_logs[].concepts_covered` | session.mastery.concepts_validated | session.mastery.concepts_validated |
| `learning_changelog.session_logs[].implementation_progress` | Missing | session.content.tasks_completed |
| `learning_changelog.problems` | Missing | session.observations.user_problems |
| `learning_changelog.learning_style_observed` | session.learning_observations | session.observations.learning_patterns |
| `learning_changelog.external_resources_log` | session.resources_suggested | session.content.resources_suggested |

---

## Document History

- 2026-01-28: Initial version created during v0.34.0 planning
