---
id: 26005
title: "Single-File Output with Embedded Templates"
date: 2026-02-14
status: accepted
superseded_by: null
tags: [architecture]
---

# ADR-26005: Single-File Output with Embedded Templates

## Date

2026-02-14

## Status

accepted

## Context

LLM applications operate in two fundamentally different execution environments:

**Agentic environment** (Claude Code, Copilot Workspace, Cursor): The LLM orchestrates tools that read, edit, and write files. Files are structured data to manipulate. Character-level precision is achievable.

**Web chat environment** (ChatGPT, Gemini, Claude.ai, DeepSeek, Qwen): The user pastes or attaches context, and the LLM generates a response. Attached files are context that informs generation, not source code to transform.

An architecture that relies on the LLM reading external files and producing structurally identical copies with targeted substitutions is implicitly an **agentic architecture**. When deployed in a web chat, the LLM treats those files as reference material and generates from understanding rather than copying from source.

### Generation phase problem

The separate template files introduced in v0.31.0 assumed the generator could perform file transformation — an agentic capability that web chat LLMs do not reliably have. Testing confirmed this: some models approximate the behavior, others catastrophically diverge (see `docs/ARCHITECTURE_POSTMORTEM_v0.40.md` for evidence).

### Learning session problem

The same issue applies to the generated output. v0.31.0–v0.40.0 split the output into 3 files (mentor_system_prompt, user_profile, session_template). The mentor_system_prompt referenced session_template as an external file. In web chat, the mentor treats attached files as context, not as exact schemas — leading to session record format drift.

### Multi-file attachment cost

The 3-file output required users to manage 4 files (3 generated + course_history) and attach 3-4 per session. Most web chat UIs limit attachments. Each additional file is a point of failure for non-technical users.

The target users are ordinary people working in free web chats without API access. The architecture must work within web chat constraints.

## Decision

### 1. Embed templates in meta-prompt

Embed all templates directly into `mentor_generator.json` under a `templates` key. Delete the separate `.template.md` files.

### 2. Merge generated output into single file

The meta-prompt generates ONE file (`mentor_system_prompt`) containing:
- Mentor behavior rules (persona, self-control, interaction flow, learning framework)
- User profile (language, assessment, skills, goals)
- User-maintained fields (learning_style_observed, known_difficulties — start empty)
- Environment and strategy (resources, constraints, pacing)
- Curriculum (phased learning progression)
- Session output protocol with embedded session record template
- Context management

### 3. Output as YAML

The template is stored as JSON in the meta-prompt (for validation with `jq`/Python). The compiler converts to YAML on output. YAML has ~60% less structural noise than JSON (no braces, no mandatory quotes, no commas), reducing token competition with instructional content.

### Rules

1. **Everything the compiler needs lives in one document.** In a web chat, the only reliable context is what's in the conversation. Templates must be in the same document as the compilation instructions.

2. **Reference templates by path, not by description.** `file_generation.steps` must say "Copy the ENTIRE object at `templates.mentor_system_prompt`" — not "Take the raw text of the template files."

3. **One source of truth.** No separate `.template.md` copies. Two copies create a sync burden and the risk of silent divergence.

4. **Single generated file.** Everything the mentor needs is in one document. No cross-file references to resolve. The user manages 2 files total (mentor_system_prompt + course_history).

5. **User workflow must be minimal.** One file to paste for generation, 1-2 files to attach per session. The simpler the workflow, the fewer failure points for non-technical users.

## Consequences

### Positive

- Works across all models — no dependency on model-specific instruction-following strength
- Simplest possible web chat workflow: paste one file, answer questions, save output
- Templates are adjacent to compilation instructions, reducing instruction-distance decay (ADR-26003)
- Single source of truth for template content
- Session record template is embedded in the mentor's rules, eliminating format drift
- User manages 2 files instead of 4
- First session requires 1 attachment instead of 3; subsequent sessions 2 instead of 4
- YAML output reduces token noise vs JSON (~60% less structural overhead)

### Negative / Risks

- `mentor_generator.json` grows from ~220 to ~550 lines. **Mitigation**: Well within all model context limits. The pre-v0.31.0 monolith was ~460 lines and worked.
- Template edits happen inside `mentor_generator.json`, not in standalone files. **Mitigation**: Development convenience is secondary to user workflow reliability.
- Mentor_system_prompt contains user-specific data, so it can't be shared across users. **Mitigation**: Shareability was a theoretical benefit that didn't outweigh the multi-file cost.
- JSON→YAML conversion adds a step for the compiler. **Mitigation**: JSON→YAML is a mechanical transformation that all LLMs handle reliably.

## Alternatives

- **Keep separate files, strengthen instructions**: More procedural copy instructions. **Rejection reason**: Instruction scaling trap (ADR-26003). More instructions about external files won't override the generative default.
- **3-file output, embed templates only**: Solves generation phase but not session template drift. **Rejection reason**: Half-measure that leaves the learning session problem unsolved.
- **Mapping table**: Output only placeholder values, merge externally. **Rejection reason**: Requires tooling the target users don't have.
- **Document as model limitation**: "Works on Gemini, not guaranteed elsewhere." **Rejection reason**: Architecture should work across models.

## References

- Evidence and root cause analysis: `docs/ARCHITECTURE_POSTMORTEM_v0.40.md`
- Instruction budget: ADR-26003
- Compiler role: ADR-26002
- v0.30 postmortem Principle 10: "Attached files are context, not source code"

## Participants

1. vrudakov
2. Claude Opus 4.6
