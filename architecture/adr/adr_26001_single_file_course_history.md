---
id: 26001
title: "Single-file course_history replaces individual session files"
date: 2026-02-13
status: accepted
superseded_by: null
tags: [architecture]
---

# ADR-26001: Single-file course_history replaces individual session files

## Date
2026-02-13

## Status

accepted

## Context

The mentor generator system produces session records at the end of each learning session. In the original design (v0.34.1), each session record was saved as a separate file (`session_1`, `session_2`, etc.), and users were instructed to attach ALL session files to each new chat.

This creates two problems:

1. **File management burden**: After 10+ sessions, users must manage and attach 10+ individual files to each chat. This is cumbersome and error-prone (forgetting a file means lost context).

2. **Web UI attachment limits**: Most AI web interfaces (Gemini, Claude, ChatGPT) limit the number of files that can be attached to a chat (typically 5-10). With 3 core files (mentor_system_prompt, user_profile, session_template) plus N session files, users hit this limit around session 5-7, making the system unusable.

The old monolithic design (v0.29.1) avoided this by embedding all state in a single JSON file, but at the cost of complexity and fragility.

Session records are already concise structured summaries (~500-1000 tokens each). Even at 50 sessions, total course_history would be ~25-50k tokens — well within context limits of modern models (128k-200k).

## Decision

We will replace individual `session_N` files with a single append-only `course_history` file.

- After each session, the mentor outputs a session record and instructs the user to append it to their `course_history` file.
- The `course_history` file is the single source of truth for all session history.
- Users attach exactly 3-4 files per session: `mentor_system_prompt`, `user_profile`, `session_template`, and (from session 2+) `course_history`.
- Session records within `course_history` are never modified or deleted — only appended.
- No phase-level compression is needed because session records are already summaries. If the file eventually grows very large (60+ sessions), the mentor can suggest summarizing the oldest completed-phase records.

## Consequences

### Positive
- Constant attachment count (3-4 files) regardless of session count — stays within all web UI limits
- Simpler user workflow — one file to manage instead of N
- No information loss — individual session detail is preserved (unlike phase-level compression which would summarize summaries)
- Append-only semantics are easy to understand and hard to break

### Negative / Risks
- Single point of failure: if course_history is corrupted or lost, all history is gone. **Mitigation**: Users are advised to keep backups; the append-only nature means accidental edits only affect the latest entry.
- File grows indefinitely. **Mitigation**: At ~800 tokens per session, even 50 sessions is ~40k tokens — well within context limits. For extreme cases (60+ sessions), the mentor suggests compression of oldest records.

## Alternatives

- **Keep individual session_N files**: Status quo. **Rejection Reason**: Hits web UI attachment limits at ~7 sessions, making the system unusable for most users.
- **Phase-level compression into separate phase_summary files**: Compress sessions per phase into summary files. **Rejection Reason**: Adds complexity (phase-boundary trigger logic), creates "summary of summaries" information loss, and still requires multiple files.
- **Phase-level compression into single file**: Compress at phase boundaries but into one file. **Rejection Reason**: Unnecessary complexity — session records are already summaries and don't need further compression given current model context sizes.
- **Embed state in mentor_system_prompt (old v0.29.1 approach)**: Single monolithic file. **Rejection Reason**: Violates separation of concerns, makes the file fragile, mixes static rules with dynamic data.

## References

- Old monolithic design: `old_file.json` (v0.29.1) — `additional_context_protocol.learning_changelog_management`
- Session template: `templates/session.template`
## Participants

1. vrudakov
2. Claude Opus 4.6
