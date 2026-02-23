v0.44.0 – 2026-02-23

BREAKING CHANGE: Provider-specific named API keys (config-to-env bridge)

Replaces the generic `api_key` / `interview_api_key` config fields with
provider-specific named keys (`GEMINI_API_KEY`, `ANTHROPIC_API_KEY`,
`OPENAI_API_KEY`, etc.). The agent promotes matching keys from config to
environment variables at startup, and litellm auto-resolves the correct key
based on the model prefix. This enables zero-friction provider switching —
store all your keys once, change only `model:`.

Migration: replace `api_key: "AIza..."` with `GEMINI_API_KEY: "AIza..."` (or
the appropriate provider key). Remove `interview_api_key:` — the named keys
handle both stages automatically.

Code changes:
- Removed: `agent/settings.py` — `api_key` and `interview_api_key` from DEFAULTS
- Removed: `agent/provider.py` — `api_key` field from LiteLLMProvider dataclass and create_provider()
- Added: `agent/main.py` — `_inject_api_keys()` config-to-env bridge (regex: `^[A-Z][A-Z0-9_]*_API_KEY$`)
- Updated: `agent/main.py` — simplified interview_config (no more api_key fallback chain)
- Updated: `agent/tests/test_provider.py` — replaced api_key tests with env bridge tests
- Updated: `docs/configuration.md` — provider-specific keys section, updated quick-start examples
- Updated: `README.md` — quick start config example uses GEMINI_API_KEY
- Updated: `CLAUDE.md` — architecture description reflects named keys

---

v0.41.0 – 2026-02-14

ARCHITECTURE: Merge generated output into single YAML file (ADR-26005)

Problem: v0.40.0 testing revealed that web chat LLMs treat attached files as
context, not source code. The 3-file generated output (mentor_system_prompt,
user_profile, session_template) suffered from session template drift — the
mentor generated its own session record format instead of following the
attached template. Users also had to manage 4 files and attach 3-4 per session.

Solution: Merge all generated output into ONE file. Embed all templates in the
meta-prompt. Output as YAML to reduce token noise vs JSON.

Generated output: 1 YAML file (mentor_system_prompt) containing behavior rules,
user profile, curriculum, and session record template. User manages 2 files
total (mentor_system_prompt + course_history).

Meta-prompt:
- Embedded all three templates into templates.mentor_system_prompt (single
  merged template combining mentor rules, user profile, curriculum, and
  session record template)
- Added user-maintained fields: learning_style_observed, known_difficulties
  (start empty, user updates from session observations)
- Rewrote file_generation.steps for single YAML output
- Rewrote guidance_for_user for 1-file + course_history workflow
- Rewrote template_references for single template
- Updated course_history_protocol.on_start for 2-file workflow
- Updated context_management.file_structure for 2 files
- Updated session_output_protocol.template_reference to embedded template
- Added course_id to metadata (from former user_profile template)

Deleted files:
- templates/mentor_system_prompt.template.md (content merged into meta-prompt)
- templates/user_profile.template.md (content merged into meta-prompt)
- templates/session.template.md (content embedded in session_output_protocol)

ADR:
- Revised ADR-26005: expanded from "embed templates" to "single-file output
  with embedded templates" covering both generation and learning session phases

File count comparison:
| Action             | v0.40.0         | v0.41.0       |
|--------------------|-----------------|---------------|
| Generated output   | 3 files         | 1 file        |
| First session      | 3 attachments   | 1 attachment  |
| Subsequent session | 4 attachments   | 2 attachments |
| Files managed      | 4               | 2             |

Bugfixes (post-test):
- Fixed duplicate step numbering in guidance_for_user (two "2." steps for
  subsequent sessions — caused Qwen to merge steps, losing paste-vs-attach
  distinction)
- Strengthened verification step 3 wording: "exact top-level keys (do not
  rename or abbreviate)" to catch key renames like metadata→meta

Testing (Qwen3-Max, 2026-02-15):
- Questionnaire: all 9 questions asked correctly, persona mapping and
  validation gate executed properly, guidance printed (with minor rewrites)
- Compiler fidelity: ~95%. All 15 top-level sections present, literal values
  preserved verbatim, placeholder substitution correct, curriculum generated
  with proper structure (5 phases)
- Remaining fidelity issues (5):
  1. metadata key renamed to "meta" (also missing YAML colon — invalid YAML)
  2. pre_response_peer_review.action field dropped entirely
  3. anti_praise_examples[0]._notes field dropped (preservation_first violation)
  4. structure_data key truncated to "structure_" (invalid YAML)
  5. guidance_for_user rewritten instead of verbatim (caused by our numbering bug)
- Improvement vs v0.40.0: catastrophic drift eliminated (v0.40.0 dropped 10
  sections, rewrote immutable fields). Single-file architecture works.

New ADR:
- ADR-26007: Format is Architecture — YAML for runtime instructions, JSON for
  compiler input and data records. Full analysis in ai_engineering_book article.

---

v0.40.0 – 2026-02-14

COMPLETE: Strict placeholder injection across templates (ADR-26002)

Completes the work started in 4d622de which updated mentor_generator.json
but did not touch the templates.

New ADRs:
- ADR-26003: Instruction Budget — LLM context limits vs redundant guardrails
- ADR-26004: Templates are output schemas, not examples

Templates:
- Added greeting_text placeholders to welcome_message and continuation_greeting
- Added persona_adaptation placeholder to emergency_brake_rules
- Renamed example_* → _example_* in greeting sections (ADR-26004: schema field taxonomy)
- Fixed session.template _template_notes to match course_history architecture (was
  still describing per-file sessions from before v0.35.0)

Meta-prompt:
- Updated persona_mapping_protocol rules to reference new placeholder fields
- Removed rule 6 (jargon in learning_framework.rules) — conflicts with immutability
- Updated template_references.placeholders_to_fill with complete field manifest
- Fixed preservation_first to cover all underscore-prefixed fields (_notes, _template_notes, _example_*)
- Fixed metadata.modified date (was 2025, should be 2026)

---

v0.39.0 – 2025-02-14

STRUCTURAL SIMPLIFICATION: Restore execution reliability

Root cause: v0.38.0 was over-engineered into a 4-phase FSM with heartbeat
tags, causing Qwen and Gemini to describe the file instead of executing it.

- Restored single linear sequence in interactive_input_sequence
- Added ACTIVATION command to description field to force execution mode
- Removed state_tracker and HTML heartbeat comments
- Simplified procedure_control_flow to a required_sequence checklist
- Flattened collection: removed {questions: [...]} nesting and restored bare strings for Q2-Q9
- Merged persona confirmation into persona_mapping_protocol
- Moved validation, guidance, and generation back into the primary linear sequence
- Flattened guidance structure to reduce nesting levels

---

v0.38.0 – 2026-02-13

FIX: 5 questionnaire bugs causing inconsistent step execution

Root cause: mixed question formats (bare strings vs objects), missing
greeting-to-Q1 transition, no file attachment handling, step count
contradiction, and phase-step misalignment in procedure_control_flow.

- Fixed step count: top-level _notes said "10 steps" but actual count is 11
  (greeting + 9 questions + 1 mapping confirmation) — now consistent with
  state_tracker and CRITICAL_TURN_TAKING
- Realigned procedure_control_flow phases: Phase 1 = Steps 0-9 (collection),
  Phase 2 = Step 10 (persona mapping + confirmation) — fixes logical
  contradiction where confirmation preceded the mapping it was confirming
- Normalized Q2-Q8 from bare strings to { "ask": "..." } objects — eliminates
  format-switching that caused the AI to grab Q3's content when asked for Q2
  (no _then fields added, safe from v0.36.0 regression)
- Added on_response field to greeting_step — provides structural bridge from
  greeting to Q1, preventing AI from reverting to generic assistant behavior
- Added FILE_AS_ANSWER rule to _notes — instructs AI to treat file uploads
  as answers, extract relevant info, and advance (not re-ask)

---

v0.37.0 – 2026-02-13

FIX: 4 structural regressions causing degraded LLM behavior

Root cause: v0.31.1–v0.36.0 restructured questions as {ask, _then} objects
with per-question "STOP" text, and separated validation/generation into
independent sibling objects. These structural changes caused LLMs to:
print "STOP. Wait for user response.", skip Q9, skip validation, and
generate files prematurely.

Fix restores v0.29.1's robust structural patterns while keeping v0.36.0
improvements (3-file output, externalized templates, rich guidance text):

- Removed all `_then` fields from questions — restored bare-string format (Q2–Q9)
  to eliminate printable "STOP" text entirely (v0.29.1 had no such text)
- Added explicit question count: `total_questions: 10` + triple reinforcement
  in collection._notes, _notes.CRITICAL_TURN_TAKING, and procedure_control_flow
- Merged `validation` + `verbal_validation_report` → single `validation_gate`
  with GATE semantics and `proceed_condition` (structural prerequisite, not passive checklist)
- Merged `guidance_for_user` + `file_generation_protocol` → single
  `guidance_and_generation` with phase_1_guidance (verbatim text) and
  phase_2_generate_files (gated on user confirmation), recreating v0.29.1's
  embedded generation gate pattern
- Updated `procedure_control_flow.required_sequence` to reflect merged structure
- Updated top-level `_notes` field convention (removed `_then` reference)
- Sequence items reduced from 8 → 6 by merging related concerns

---

v0.36.0 – 2026-02-13

FIX: 5 issues found during end-to-end testing of mentor_generator.json

- Renamed "then" → "_then" in all 10 question steps to prevent LLMs from printing "STOP. Wait for user response." as visible output
- Added explicit FIELD CONVENTION rule in top-level _notes: underscore-prefixed fields are internal and must never be printed
- Added 5th validation check (template_completeness) to deep_pedagogical_self_validation
- Enhanced verbal_validation_report to require per-check reasoning (references deep_pedagogical_self_validation dynamically)
- Rewrote session-ending guidance to cover 3 scenarios: user-initiated, natural completion, context-limit degradation
- Added note about attaching additional files alongside core ones in "Why One course_history File?" section
- Replaced false claim about AI detecting file errors with honest guidance (backup copy + online JSON validator)

---

v0.35.0 – 2026-02-13

FEATURE: Restore human-like traits + single-file course_history architecture

Architectural change (ADR-26001):
- Replaced individual session_N files with single append-only course_history file
- Users append each session record to one file instead of managing N separate files
- Solves web UI attachment limits (most limit to 5-10 files)
- Renamed session_files_protocol → course_history_protocol
- Updated all references from "session files" to "course_history" throughout
- Added context_management section with awareness for very large histories
- Updated session_output_protocol for append-to-file workflow
- Updated guidance_for_user with course_history workflow instructions

Restored anti-sycophancy mechanisms from v0.29.1 (adapted to warm tone):
- Added anti_praise_examples to feedback_approach (concrete few-shot examples)
- Replaced vague patience_with_attempts with concrete two-attempt rule
- Changed encourage_reasoning back to require_reasoning (mastery gate)
- Expanded mastery_check with if_incomplete and gate enforcement detail
- Restored fiction/sci-fi references in emergency_brake_rules.recovery_protocol
- Updated Level Appropriateness peer review checkpoint to reference failure log

Persona mapping:
- Restored rules 6-7: persona jargon in learning rules + signature greeting

Removed DRY violations:
- session_protocols _notes no longer duplicate trigger logic from course_history_protocol

New files:
- architecture/adr/adr_26001_single_file_course_history.md
- misc/plan/plan_20260213_architectural_analysis_and_human_traits_recovery.md

Updated: CLAUDE.md, README.md references

v0.34.1 – 2026-01-29

FIX: Complete user workflow instructions and include session_template in output

Problem: Users were told to attach session_template but the meta-prompt never provided it.
The workflow instructions were also too brief, causing confusion for new users.

Changes to `mentor_generator.json`:
- Meta-prompt now outputs THREE files: mentor_system_prompt, user_profile, session_template
- session_template is output verbatim (no modifications needed)
- Split workflow into "FIRST session" and "SUBSEQUENT sessions" with detailed steps
- Added "Editing Your user_profile" section with reassuring guidance for non-technical users
- Updated all references from "two files" to "three files"
- Updated `file_generation_protocol` steps to include session_template
- Updated `template_references.session_template` to clarify two-stage process

v0.34.0 – 2026-01-28

REFACTOR: 3-template architecture with proper data separation

Problem: v0.31.0 introduced data organization issues:
- mentor_failure_log in course_config couldn't be updated without manual editing
- Session template was incomplete (missing tasks, projects, user problems)
- Confusing naming (course_config mixed static and dynamic concerns)

Solution: Three-template architecture where session files are the ONLY dynamic data.

File changes:
- CREATE `templates/session.template` - Comprehensive session record structure
- RENAME `course_config.template` → `user_profile.template` - Static user data only
- REMOVE `mentor_failure_log` from user_profile (now tracked per-session)

New session template fields:
- `content.tasks_completed` - Exercises and problems solved
- `content.projects_worked_on` - Project work done
- `observations.learning_patterns` - How this user learns best
- `observations.user_problems` - Difficulties, confusion, frustrations
- `observations.mentor_failures` - Mentor errors to avoid in future

Changes to `mentor_system_prompt.template`:
- Added `static_clarification` to `_template_notes`
- Updated `self_correction` to scan session files for mentor_failures
- Updated `session_files_protocol` to reference user_profile and synthesize all sessions
- Simplified `session_output_protocol` to reference external template

Changes to `mentor_generator.json`:
- Updated `template_references` with `output_filename` instead of `location`
- Added `session_template` reference
- Updated `guidance_for_user` with new file names and session tracking explanation

Documentation:
- Added `docs/ARCHITECTURE_POSTMORTEM_v0.32.md` documenting design decisions
- Added `misc/plan.md` with implementation plan
- Updated CLAUDE.md with new architecture

v0.32.0 – 2026-01-28

FEATURE: Humanize mentor behavior with pedagogical warmth

Added `pedagogical_principles` block to mentor template:
- `partnership` - Guide, not drill sergeant
- `honesty` - Always tell the truth, acknowledge difficulty
- `respect` - Treat student as intelligent adult
- `patience` - Try different explanations when needed
- `curiosity` - Encourage questions

Enhanced `feedback_approach` in peer review:
- `when_correct` - Confirm clearly and build on it
- `when_incorrect` - Say so politely and guide toward understanding
- `when_struggling` - Acknowledge difficulty and help
- `avoid` - Empty praise, cold corrections, condescension, fake enthusiasm

Updated `teaching_style`:
- Added `honesty_and_warmth` - Direct and truthful but polite and supportive
- Added `genuine_interest` - Learning as shared exploration, not interrogation

Updated session protocols with warmer greetings:
- `first_session_protocol.welcome_message` with persona examples
- `subsequent_session_protocol.continuation_greeting` for returning students

v0.31.2 – 2026-01-28

FIX: Restore first session welcome behavior (regression from v0.31.0)

The mentor was skipping the introductory lecture and curriculum presentation on first session.
Root cause: v0.31.0 refactor made session protocol instructions too terse compared to v0.29.0.

Changes to `mentor_system_prompt.template`:
- Added `protocol_selection` block to `session_files_protocol` with explicit IF/THEN logic
- Added `_notes` to `session_protocols`: "Execute ALL steps in order - do not skip any step"
- `first_session_protocol._notes`: Added "Acts as the COURSE INTRODUCTION LECTURE. User has never seen the curriculum before."
- `subsequent_session_protocol._notes`: Added "Acts as RECAP AND CONTINUATION. User already knows the curriculum."
- Numbered all steps (1-6) and made them more explicit:
  - "Present the ENTIRE learning roadmap... as a formatted table with all phases, topics, and estimated progression"
  - "Explain the learning goals and practical skills they will gain upon completion"
  - "Address administrative matters: session duration expectations, study schedule, learning approach"
- Added explicit "STOP and wait for user response" as final step in both protocols

v0.31.1 – 2026-01-28

FIX: Strengthened turn-taking enforcement for Gemini 3 Flash compatibility

- Added CRITICAL_TURN_TAKING rule to top-level `_notes` in meta-prompt
- Restructured all questions in `collection` with explicit `"then": "STOP. Wait for user response."` fields
- Added `one_question_pattern` to sequence `_notes`: "Ask question → STOP → wait for answer → process answer → ask next question → STOP"
- Expanded `ask_and_wait` in mentor template to object with `rule`, `pattern`, and `violation` fields
- Strengthened `Turn-Taking` check point: "If question asked and more text follows = VIOLATION. Regenerate."
- Expanded `wait_for_answer` with explicit pattern: "[explanation] → [question] → [END OF MESSAGE]"
- Expanded `mandatory_break` with enforcement: "This is NON-NEGOTIABLE. Question asked = message ends immediately."

v0.31.0 – 2026-01-28

BREAKING CHANGE: Complete architecture overhaul - 3-file system

- Separated meta-prompt from mentor template into distinct files
- New file structure:
  - `mentor_generator.json` - Meta-prompt only (questionnaire logic)
  - `templates/mentor_system_prompt.template` - Mentor behavior rules
  - `templates/course_config.template` - User profile and curriculum
- Meta-prompt now generates TWO output files instead of one monolithic JSON
- Session files: Each learning session creates immutable `session_N` file
- Removed complex state management:
  - Removed `additional_context` block from mentor
  - Removed `context_limit_approaching` trigger
  - Removed `CONTEXT_SAVE_REQUIRED` flag
  - Removed dual-mode complexity (teaching vs state update)
- Added `session_files_protocol` - how mentor reads attached files
- Added `session_output_protocol` - exact template for session output
- Hardcoded user instructions in `guidance_for_user.message_paragraphs`
- Format-agnostic design: JSON, YAML, Markdown, or plain text all valid
- Mentor templates now reusable across different users
- Updated README.md with new workflow
- Updated CLAUDE.md with new architecture

v0.30.0 – 2025-11-28

- Bumped version from 0.29.2 to 0.30.0.
- Updated the `modified` date to `2025-11-28`.
- Changed the license from "GPLv3" to "MIT".
- Modified the `session_resumption_protocol`:
  - Added a new `session_control` object with an initial state of `initial_session_protocol_completed: false`.
  - Updated the `_notes` for both `first_session_protocol` and `subsequent_session_protocol` to reflect the use of `session_control.initial_session_protocol_completed`.
- Updated the `content_requirements` rule in `json_update_protocol`:
  - Changed from updating only changed fields plus required metadata to always outputting the complete, updated JSON block.
- Removed the `context_window_model` and `pacing_choice` fields from `system_constraints`.
- Added new fields to `phase_in_progress`: `current_focus` and `next_focus`.
- Cleaned up some minor formatting issues for consistency.

v0.29.2 – 2025-11-26

- Bumped version from 0.29.1 to 0.29.2.
- Updated the `modified` date to `2025-11-26`.
- Modified the `triggers` condition for `state_update_mode` in `mentor_generator.json`. The new trigger condition is now:
  ```
  "Only when `state_update_protocols.json_update_protocol.json_generation_triggers` conditions are met"
  ```

v0.29.1 – 2025-11-25

- Bumped version from 0.28.0 to 0.29.1.
- Updated question_8 to include learning strategy options (DEPTH-FIRST and TIME-BOXED) along with detailed descriptions.
- Removed the previous question_8 about time constraints.
- Moved `user_profile` from a separate section into `additional_context`.
- Added `constraints_and_strategy` within `additional_context`, including details like hardware limits, software stack, efficiency principles, study constraints, and system constraints.
- Updated the structure of `learning_changelog` to include `next_focus`.
- Added a new rule `pre_content_save_check` under `strict_turn_taking`. This rule ensures that before starting any new concept explanation, the mentor checks if a state update is required due to context depth. If so, it announces the need for a state update, requests user confirmation, and handles both confirmation and rejection scenarios.
- Added `context_limit_approaching` as a trigger condition under `json_update_protocol`. This sets an internal flag when the current token count exceeds the system constraints threshold.
- Updated the rules to include specific instructions for handling context limit approaching, ensuring that state updates occur only at the next available pedagogical break point.
- Clarified and expanded the `pacing_policy` under `constraints_and_strategy`.
- Added projects examples in README.md.
- Expanded warnings and best practices in both READMEs.
- Updated README_ru.md with a real example section for Deep Learning with PyTorch.

v0.28.0 – 2025-11-16

- Bumped version; renamed metadata fields (`created` → `birth`, `last_updated` → `modified`).
- Improved naming: human-readable `name`, lowercase placeholders, clearer step labels (e.g., `` `collection` complete ``).
- Restructured state management: moved session protocols under `session_resumption_protocol`, added `user_profile` root section.
- Consolidated `interaction_flow`, `response_architecture`, and `emergency_brake_rules` into a unified flow.
- Replaced flat `additional_context` with phased changelog (`phase_in_progress`, `finished_phases_logs`) and explicit retention rules.
- Added `zero_level_protocol` rule; fixed `external_resources_log` path.
- Minor cleanup: removed bolding, fixed grammar, standardized key references, trimmed redundancy.

0.27.0
- teaching_style demands honesty from the mentor

0.26.0
- socratic style removed - too many questions without ground theory

0.25.0
- emotionless added in `mentor_self_control.peer_reviewer_style`
- socratic style added
- session-based way turned to concepts_mastered-based way (before the mentor hurried to finish the session but we need to get the understanding from the user)

0.24.2
- changelog moved to a dedicated file, finally

0.24.1
- emergency_brake moved to list_of_rules
- concepts_mastered got the predefined structure
- resources_suggested got the predefined structure
