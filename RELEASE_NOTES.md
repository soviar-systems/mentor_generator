# Release Notes

## Version 0.31.0 - January 28, 2026

### BREAKING CHANGE: 3-File Architecture

This release completely overhauls the architecture to improve reliability and predictability.

### Why This Change Was Necessary

The previous monolithic design had fundamental reliability problems:

1. **Role Confusion**: One file contained both meta-prompt logic AND mentor template. LLMs would get confused about which role they were playing - sometimes acting as the questionnaire assistant when they should be teaching, or vice versa.

2. **Unreliable State Updates**: The mentor had to regenerate 450+ lines of JSON at every milestone. This was error-prone - LLMs would forget fields, corrupt structure, or introduce subtle changes to static rules that should never change.

3. **Cognitive Overload**: Complex triggers (token counting, internal flags, dual-mode management) added mental load. The more rules we added to make it reliable, the more confused the LLM became.

4. **Unpredictable Output**: Instructions like "save the important context" left the LLM to decide what was important. Different runs produced different results.

**Core insight: Predictability comes from constraints, not instructions.**

Instead of telling the mentor "output the updated JSON with these rules," we now say "fill this exact 30-line template." The template IS the constraint. No decisions means no confusion.

### What Changed

**Before (v0.30.x):**
- One monolithic JSON file containing both meta-prompt and mentor template
- Mentor had to regenerate 450+ lines of JSON at every state update
- Complex triggers for context management (token counting, flags)
- Dual-mode confusion (teaching vs state update)

**After (v0.31.0):**
- Meta-prompt separated from mentor templates
- Mentor generates TWO output files: `mentor_system_prompt` + `course_config`
- Each learning session creates a small `session_N` file (~30 lines)
- No complex triggers - just session end
- Template-first output - mentor fills exact templates, no decisions

### New File Structure

```
mentor_generator/
├── mentor_generator.json              # Meta-prompt only
├── templates/
│   ├── mentor_system_prompt.template  # Mentor behavior rules
│   └── course_config.template         # User profile/curriculum
```

### New Features

- **Session Files**: Each session creates immutable `session_1`, `session_2`, etc.
- **Reusable Mentors**: Share `mentor_system_prompt` with others learning same topic
- **Format-Agnostic**: JSON, YAML, Markdown, or plain text all valid
- **Hardcoded User Instructions**: No more LLM interpretation of guidance

### Migration

Users with existing v0.30.x JSON files should start fresh with the new system. Manual migration is possible but not recommended.

### Removed

- `additional_context` block (moved to `course_config` and session files)
- `context_limit_approaching` trigger
- `CONTEXT_SAVE_REQUIRED` flag
- `pre_content_save_check` rule
- Dual-mode management complexity

---

## Version 0.29.1 - November 25, 2025

### Enhancements and New Features

- **Version Update**: Bumped version from 0.28.0 to 0.29.1.

- **Question Updates**:
  - Updated question_8 to include learning strategy options (DEPTH-FIRST and TIME-BOXED) along with detailed descriptions.
  - Removed the previous question_8 about time constraints.

- **Additional Context Changes**:
  - Moved `user_profile` from a separate section into `additional_context`.
  - Added `constraints_and_strategy` within `additional_context`, including details like hardware limits, software stack, efficiency principles, study constraints, and system constraints.
  - Updated the structure of `learning_changelog` to include `next_focus`.

- **Interaction Flow Enhancements**:
  - Added a new rule `pre_content_save_check` under `strict_turn_taking`. This rule ensures that before starting any new concept explanation, the mentor checks if a state update is required due to context depth. If so, it announces the need for a state update, requests user confirmation, and handles both confirmation and rejection scenarios.

- **JSON Update Protocol Enhancements**:
  - Added `context_limit_approaching` as a trigger condition under `json_update_protocol`. This sets an internal flag when the current token count exceeds the system constraints threshold.
  - Updated the rules to include specific instructions for handling context limit approaching, ensuring that state updates occur only at the next available pedagogical break point.

- **Learning Framework Adjustments**:
  - Clarified and expanded the `pacing_policy` under `constraints_and_strategy`.

### Bug Fixes

- None identified in this release.

### Documentation Updates

- Updated README.md to include projects examples.
- Added a real example section in README_ru.md for Deep Learning with PyTorch.
- Expanded warnings and best practices in both READMEs.
