# Plan: Architecture Refactor - Proper Data Separation

**Version:** v0.32.0 → v0.34.0
**Date:** 2026-01-28

---

## Problem Analysis

The v0.31.0 refactor separated meta-prompt from mentor but introduced a data organization problem:

### Issue 1: mentor_failure_log is in the wrong place
- **Current:** In `course_config.template` (described as "rarely changes")
- **Problem:** If mentor makes a mistake in session 5, it can't be recorded without manually editing course_config
- **Result:** The mentor never learns from mistakes because there's no natural place to log them

### Issue 2: Session template is incomplete
Current session template is missing critical fields found in old_file.json:
- Solved tasks / exercises completed
- Projects worked on
- User problems encountered
- Mentor failures from this session

### Issue 3: Confusing naming
- `course_config` contains user profile + curriculum + failure log (mixed concerns)
- "Static" mentor_system_prompt actually instructs mentor to read dynamic data
- No standalone session template file (embedded in mentor_system_prompt)

### Issue 4: Context loss from old_file.json
The old single-file approach (v0.29.1) kept everything together. The split lost the continuity of:
- learning_changelog tracking
- external_resources cumulative log
- learning_style observations
- problem patterns

---

## Solution: Three-Template Architecture

```
templates/
├── mentor_system_prompt.template  # Mentor behavior rules (TRULY static)
├── user_profile.template          # User data + curriculum (static per user)
└── session.template               # Session record template (dynamic per session)
```

**Principle:** Session files are the ONLY dynamic data. Mentor synthesizes all context from them.

---

## Changes

### 1. Create `templates/session.template` (NEW FILE)

New standalone session template with comprehensive fields:

```json
{
  "_template_notes": {
    "purpose": "Session record template - mentor fills this at end of each session",
    "usage": "Save as session_N (session_1, session_2...). Attach ALL session files to each new chat.",
    "immutability": "Never modify old session files. Each session creates a new file."
  },

  "session_number": "<increment from last session, or 1>",
  "timestamp": "<ISO datetime>",
  "duration_approx": "<estimated session length>",

  "position": {
    "phase": "<current phase from curriculum>",
    "topic_covered": "<main topic(s) this session>",
    "next_topic": "<what comes next>",
    "phase_progress": "<X of Y topics in current phase>"
  },

  "content": {
    "session_summary": "<2-3 sentence summary>",
    "tasks_completed": ["<exercises, problems, or challenges the user solved>"],
    "projects_worked_on": ["<any project work done this session>"],
    "resources_suggested": [
      {"topic": "<topic>", "resource": "<title>", "type": "<book/video/article>"}
    ]
  },

  "mastery": {
    "concepts_validated": ["<concepts user demonstrated understanding of>"],
    "concepts_struggling": ["<concepts needing more work>"],
    "validation_method": "<how mastery was verified>"
  },

  "observations": {
    "learning_patterns": ["<observations about how this user learns best>"],
    "user_problems": ["<difficulties encountered, confusion points, frustrations>"],
    "mentor_failures": [
      {
        "error": "<what the mentor got wrong>",
        "context": "<when/where it occurred>",
        "lesson": "<what to avoid in future>"
      }
    ]
  },

  "mentor_notes": "<notes for future sessions>"
}
```

### 2. Rename and simplify `templates/course_config.template` → `templates/user_profile.template`

**Remove:** `mentor_failure_log` (moved to session files)

**Keep and organize:**
- `user_profile` (language, assessment, skills, goals)
- `constraints_and_strategy` (hardware, software, pacing)
- `curriculum` (phases with topics)

Updated structure:
```json
{
  "_template_notes": {
    "purpose": "User profile and curriculum - fill during meta-prompt generation",
    "usage": "Static user data. Attach to every session. Does not change after generation.",
    "sharing": "mentor_system_prompt can be shared; each user has own user_profile"
  },
  "metadata": {...},
  "user_profile": {...},
  "constraints_and_strategy": {...},
  "curriculum": {...}
}
```

### 3. Update `templates/mentor_system_prompt.template`

**3a. Update `_template_notes` to clarify "static" meaning:**
```json
"_template_notes": {
  "purpose": "Mentor behavior rules - defines how the mentor teaches and interacts",
  "static_clarification": "This file's RULES are static. The mentor reads DYNAMIC data from session files.",
  ...
}
```

**3b. Update `mentor_self_control.self_correction`:**
```json
"self_correction": "Before explaining a concept, scan all attached session files for mentor_failures entries related to this topic. If found, explicitly avoid the noted error."
```

**3c. Update `session_files_protocol`:**
```json
"session_files_protocol": {
  "_notes": "How the mentor reads attached files",
  "on_start": [
    "Read mentor_system_prompt (this file) for behavior rules",
    "Read user_profile for user data, constraints, and curriculum",
    "Read ALL session_N files for: progress, learning patterns, user problems, mentor failures"
  ],
  "synthesis": "Combine all session files to build: current position in curriculum, cumulative learning observations, list of mentor failures to avoid, suggested resources to follow up on"
}
```

**3d. Update `session_output_protocol`:**
- Reference external template file
- Emphasize completeness of all fields

**3e. Add guidance for learning_observations:**
```json
"learning_observations": {
  "_filling_note": "Note patterns about how this student learns. Build on previous sessions - don't repeat, extend."
}
```

### 4. Update `mentor_generator.json`

**4a. Update `template_references`:**
```json
"template_references": {
  "mentor_system_prompt_template": {
    "location": "templates/mentor_system_prompt.template",
    ...
  },
  "user_profile_template": {
    "location": "templates/user_profile.template",
    "purpose": "User profile, constraints, curriculum (static)",
    ...
  },
  "session_template": {
    "location": "templates/session.template",
    "purpose": "Session record structure - mentor uses this to output session files",
    "note": "This template is for mentor reference, not filled by meta-prompt"
  }
}
```

**4b. Update `guidance_for_user.message_paragraphs`:**
- Change "course_config" → "user_profile"
- Mention session template purpose
- Explain that mentor failures are tracked per-session

**4c. Version bump to 0.34.0**

### 5. Update `CLAUDE.md`

- Update file structure diagram
- Update file descriptions
- Document session.template purpose
- Update "Generated Output" section

---

## Files to Modify

| File | Action |
|------|--------|
| `templates/session.template` | **CREATE** - New standalone template |
| `templates/course_config.template` | **RENAME** → `user_profile.template`, remove mentor_failure_log |
| `templates/mentor_system_prompt.template` | Update references, self_correction, session_files_protocol |
| `mentor_generator.json` | Update template_references, guidance_for_user, version |
| `CLAUDE.md` | Update architecture documentation |

---

## What This Fixes

1. **Mentor learns from mistakes**: Failures logged per-session, mentor scans all sessions
2. **Complete session records**: Tasks, projects, problems, failures all captured
3. **Clear separation**: Static config vs dynamic session data
4. **Consistent naming**: user_profile = user data, session = session data
5. **Context preservation**: All old_file.json tracking is now in session files

---

## What We Are NOT Doing

Per the postmortem principles:
- No token counting or context management (LLMs can't count)
- No state compression (lossy and unpredictable)
- No dual-mode management (teaching mode only)
- No complex triggers (session end only)

---

## Verification

1. **JSON validity**: All template files must parse as valid JSON
2. **Template completeness**: Session template covers all old_file.json dynamic fields
3. **Cross-reference check**: mentor_system_prompt correctly references user_profile
4. **Manual walkthrough**: Simulate session end → verify template can capture all needed data

---

## Commit Message

```
refactor: 3-template architecture with proper data separation (v0.34.0)

- Create templates/session.template for comprehensive session records
- Rename course_config.template → user_profile.template (static user data only)
- Move mentor_failure_log to session files (per-session tracking)
- Add tasks_completed, projects_worked_on, user_problems to session template
- Update mentor_system_prompt to scan session files for failures
- Update guidance_for_user with new file names
```
