# Architecture Post-Mortem: Mentor Generator v0.35.0 → v0.41.0

**Date:** February 14, 2026
**Author:** vrudakov + Claude Opus 4.6
**Document Type:** Lessons Learned / Decision Record

---

## Executive Summary

The v0.31.0 refactor correctly separated the generated output into three files (mentor rules, user profile, session records). But it introduced a hidden assumption: **the template delivery mechanism requires agentic file transformation that web chat LLMs cannot perform.**

When Qwen3-Max was tested with v0.40.0, it catastrophically dropped 10 entire sections from mentor_system_prompt despite having the template file attached. The LLM treated the attached template as reference material and generated from its own understanding — not as source code to copy.

This document captures the full arc from v0.35.0 through v0.41.0: the instruction-scaling failures, the over-engineering trap, the compiler metaphor, and the discovery that web chats and agentic tools are fundamentally different environments.

---

## Part 1: The Architecture at v0.35.0

### File Structure

```
mentor_generator/
├── mentor_generator.json                  # Meta-prompt (questionnaire logic)
├── templates/
│   ├── mentor_system_prompt.template.md   # Mentor behavior rules (~230 lines)
│   ├── user_profile.template.md           # User profile + curriculum (~70 lines)
│   └── session.template.md               # Session record format (~47 lines)
```

### What Worked

1. **Three-file output**: User gets mentor_system_prompt + user_profile + session_template (from v0.31.0)
2. **Single course_history**: All session records in one file (ADR-26001, v0.35.0)
3. **Append-only sessions**: Never modify existing records
4. **Human-like mentor behavior**: Pedagogical warmth, anti-sycophancy, emergency brakes (v0.32.0)
5. **Template-first design**: Mentor fills exact template, doesn't decide structure

### The Implicit Assumption

The architecture assumed the generator LLM would:
1. Read each `.template.md` file as source code
2. Walk through it, preserving every character
3. Replace only `<placeholder>` tokens with user data
4. Output a structurally identical copy

This is **file transformation** — the same operation that tools like `sed`, `envsubst`, or Claude Code's Edit tool perform. The generator was conceived as a **compiler**, not an author.

---

## Part 2: The Instruction-Scaling Failure (v0.36.0 → v0.39.0)

### The Bug Cascade

Between v0.36.0 and v0.38.0, we tried to fix questionnaire execution bugs by adding more structural control:

| Version | Fix Attempted | Result |
|---------|--------------|--------|
| v0.36.0 | Added `_then` fields to questions, validation reasoning, session-end scenarios | LLMs printed "STOP. Wait for user response." as visible output |
| v0.37.0 | Removed `_then`, added question count, merged validation + generation gates | LLMs skipped Q9, skipped validation, generated files prematurely |
| v0.38.0 | 4-phase FSM with heartbeat tags, state tracker, HTML comments | Qwen and Gemini **described the file** instead of executing it |

v0.38.0 was the peak of over-engineering. The meta-prompt had become so structurally complex that LLMs couldn't parse it as instructions anymore — they treated it as a document to analyze.

### v0.39.0: The Simplification

v0.39.0 stripped everything back:
- Removed state tracker and HTML heartbeat comments
- Restored single linear sequence
- Added `ACTIVATION` command to force execution mode
- Flattened collection back to bare strings for Q2–Q9

**Result:** Immediate improvement. All tested models (Gemini, Claude, DeepSeek) correctly executed the questionnaire again.

### The Lesson

This is where ADR-26003 (Instruction Budget) was born:

> Every instruction added to a prompt competes for LLM attention. Redundant guardrails cause more harm than good. Adding too much structural noise causes LLMs to **describe files instead of executing them**.

The v0.38.0 → v0.39.0 regression proved that instructions don't scale linearly — they have a **tipping point** where the LLM shifts from "follow these instructions" to "analyze this document."

---

## Part 3: The Compiler Metaphor (v0.40.0)

### ADR-26002: Strict Placeholder Injection

v0.40.0 formalized the compiler metaphor (ADR-26002):
- The generator AI is a **text-substitution engine**, not an author
- Templates are **immutable infrastructure**
- The compiler replaces `<placeholder>` tokens with user data and touches nothing else
- `preservation_first` and `structural_parity` rules enforce this

### What v0.40.0 Changed

1. Added `<greeting_text>` placeholders to session protocol welcome messages
2. Added `<persona_adaptation>` placeholder to emergency brake
3. Renamed `example_*` → `_example_*` (ADR-26004: field taxonomy)
4. Updated `persona_mapping_protocol` to point at new placeholder fields
5. Strengthened `preservation_first` to cover all `_`-prefixed fields

### The Testing Setup

User tested with Qwen3-Max:
- Pasted `mentor_generator.json` content
- Attached all three `.template.md` files
- Completed the 9-question questionnaire
- Triggered file generation

### The Test Was Fair

The compiler had its source code. All three template files were in context. All `preservation_first`, `structural_parity`, and compiler instructions were active.

---

## Part 4: The Qwen3-Max Catastrophe

### mentor_system_prompt — 10 Entire Sections DROPPED

| Template Section | Status | Impact |
|---|---|---|
| `_template_notes` | DROPPED | Meta-guidance for mentor AI gone |
| `pedagogical_principles` | DROPPED | 5 core teaching principles gone |
| `mentor_self_control` | DROPPED | Self-correction, peer review, anti-praise examples ALL gone |
| `course_history_protocol` | DROPPED | Mentor doesn't know how to read attached files |
| `session_protocols` wrapper | DROPPED | Protocols extracted to top level |
| `interaction_flow.primary_mode` | DROPPED | Teaching mode definition gone |
| `response_architecture` | DROPPED | Ask-and-wait pattern gone |
| `learning_framework` | DROPPED | one_small_step, mastery_gated, strict_turn_taking ALL gone |
| `context_management` | DROPPED | File attachment awareness gone |
| `session_output_protocol` | REPLACED | Rich protocol → 6-field flat object |

### Immutable Fields REWRITTEN

- `recovery_protocol`: template says "Step back to simpler explanation. Try different analogies..." → Qwen wrote "Immediately halt progression. Revert to minimal working example."
- `explicit_check`: template says "Check in with the student..." → Qwen wrote "require user to demonstrate correct application"
- Both session protocol `steps` arrays: completely rewritten with different content

### user_profile — Structure MANGLED

- `_template_notes` dropped
- Keys renamed: `user_language` → `language`, `initial_assessment` → `assessment`, `professional_skills` → `skills`
- `pacing` object simplified (lost `choice`, `user_time_input`, `policy`)
- `curriculum.phases` restructured (lost `phase_number`, `hands_on`, `estimated_sessions`)

### session_template — REPLACED ENTIRELY

- Template has structured schema: `position`, `content`, `mastery`, `observations`, `mentor_notes`
- Qwen output: flat `session_record` with 6 generic fields

### What DID Work

- `greeting_text` placeholders were filled correctly (v0.40.0 change worked)
- `persona_adaptation` was filled correctly (v0.40.0 change worked)
- Curriculum content quality was good
- User profile data extraction was accurate

The placeholder injection itself worked — when Qwen saw `<angle_brackets>`, it replaced them. But it generated its own structure around those replacements instead of preserving the template's structure.

---

## Part 5: Root Cause Analysis

### The LLM Didn't Copy — It Generated

Qwen3-Max was provided all three template files alongside `mentor_generator.json`. It had the source code. And it still generated from scratch.

**The LLM treats attached template files as reference material, not source code to copy.** When `file_generation.steps[0]` says "Take the raw text of the template files," Qwen reads them as context, synthesizes its understanding, and generates its own version. It never does character-level copying.

### Contributing Factors

**1. Loose coupling.** The template files are separate documents with no explicit link to `file_generation.steps`. The step says "template files" generically — it doesn't say "the attached file named `mentor_system_prompt.template.md` is your source; copy it character by character, replacing only `<...>` values." The LLM must infer the connection.

**2. Instruction distance.** By the time file generation happens (after greeting + 9 questions + persona mapping + validation + user guidance), the `preservation_first` and `structural_parity` rules from the top of `interactive_input_sequence` are thousands of tokens behind. The LLM's attention to these rules has decayed.

**3. Generative default.** LLMs default to generating, not copying. Telling an LLM "copy this but change X" requires stronger signals than telling it "generate Y." The current instructions weren't strong enough to override Qwen's generative default.

### The Architectural Mismatch

The 3-file template architecture implicitly assumes the generator LLM can perform **file transformation**: read a template file as source code, walk through it character by character, replace specific tokens, output a structurally identical copy.

This is an **agentic capability**. It's what tools like Claude Code do with Read/Edit/Write — tools that operate on files as structured data, not as context to understand.

But the target users work in **web chats** (Gemini, ChatGPT, Claude free tier, DeepSeek, Qwen). In web chats:
- Attached files are **context** that informs generation
- The LLM reads them, builds understanding, and generates output from that understanding
- There is no "edit this file" operation — only "generate a response"

Gemini 3 Flash approximates the copy-then-substitute behavior through strong instruction-following. But Qwen3-Max does what web chat LLMs naturally do: **generate from understanding, not copy from source.**

### Why Gemini Worked but Qwen Didn't

This is model-dependent instruction adherence, not a reliable architectural property:

| Behavior | Gemini 3 Flash | Qwen3-Max |
|----------|---------------|-----------|
| Read template as source code | Yes (approximation) | No |
| Preserve immutable fields | Mostly | No |
| Fill placeholders | Yes | Yes |
| Maintain structural parity | Close | Not at all |

The architecture was working on Gemini **by coincidence of model capability**, not by architectural guarantee. Any model update, different model choice, or even different prompt length could break it.

---

## Part 6: The Broader Lesson — Two Execution Environments

### Agentic Environment

```
LLM + Tools → Read file → Edit specific tokens → Write file
```

- Files are **data structures** to manipulate
- The LLM orchestrates tools that do the actual file operations
- Character-level precision is achievable
- Examples: Claude Code, GitHub Copilot Workspace, Cursor

### Web Chat Environment

```
User → Paste/attach context → LLM generates response
```

- Files are **context** that informs generation
- The LLM generates output from understanding, not from editing
- Character-level preservation is not reliable
- Examples: ChatGPT, Gemini, Claude.ai, DeepSeek, Qwen

**The v0.31.0 architecture was designed for the agentic environment but deployed in the web chat environment.**

The separate `.template.md` files were a development convenience that assumed agentic capabilities the target platform doesn't have.

### The Target User

The target is ordinary users who work in (mostly free) web chats and do not have API access to the models. They:
1. Paste or type the meta-prompt content into a chat
2. Answer questions
3. Copy the generated files
4. Use them in new chats

No file system access. No tool use. No code execution. Just text in, text out.

---

## Part 7: The Solution — Embed Templates (v0.41.0)

### Decision

Embed all three templates directly into `mentor_generator.json`. Delete the separate `.template.md` files.

### Why This is NOT v0.29.1

The v0.29.1 monolith had specific problems. None of them return with embedding:

| v0.29.1 Problem | Returns? | Why Not |
|---|---|---|
| Meta-prompt + mentor in same file → role confusion | No | Templates are source code for the compiler, not mentor instructions. Generated output is still 3 separate files. |
| State management complexity | No | Removed in v0.31.0, stays removed. |
| Mutable state mixed with static rules | No | Templates are immutable source code. Generated output separates static from dynamic. |
| Full JSON regeneration (450 lines) | No | Session records are still ~30 lines. |

What v0.31.0 actually fixed was the **generated output** architecture: separating mentor rules from user profile from session records. That separation is preserved. The user still gets 3 files. The templates being inside `mentor_generator.json` changes the **delivery mechanism**, not the output architecture.

### Why Embedding Works

1. **The compiler gets its source code.** In a web chat, everything the LLM can access must be in the conversation context. Embedding guarantees the templates are in context.

2. **One file to paste.** Matches the simplest possible web chat workflow — no file attachments needed.

3. **Tighter coupling.** `file_generation.steps` can reference `templates.mentor_system_prompt` by path, not vaguely "template files."

4. **v0.29.1 worked** — not because monoliths are good, but because everything was in one context. Embedding preserves this while keeping the v0.31.0 output architecture.

### New file_generation.steps

The old steps said "Take the raw text of the template files" — vague, relies on the LLM inferring which files.

The new steps reference embedded templates by path:

```
1. FILE 1: Copy the ENTIRE object at templates.mentor_system_prompt. Replace only <...> values.
2. FILE 2: Copy the ENTIRE object at templates.user_profile. Replace only <...> values.
3. FILE 3: Copy the ENTIRE object at templates.session VERBATIM. Change NOTHING.
4. Verify: mentor_system_prompt must contain ALL these top-level keys: [explicit list]
5. Label each file. Remind user to save.
```

The key difference: "Copy the ENTIRE object at `templates.X`" is a concrete instruction referencing a specific location in the same document, not a vague instruction about external files.

---

## Part 8: Principles Extracted

### Principle 9: Know Your Execution Environment

❌ Bad: Design for agentic file transformation, deploy in web chat
✅ Good: Design for the actual capabilities of the target platform

If the target is web chat LLMs, everything the LLM needs must be in the conversation context. External file references work for agentic tools, not for web chat.

### Principle 10: Attached Files Are Context, Not Source Code

❌ Bad: "Read the attached template file and copy it exactly"
✅ Good: Template embedded in the prompt, referenced by path

In web chats, "attached file" means "additional context for generation." The LLM will read it, understand it, and generate its own version. It will not copy it character by character.

### Principle 11: Model-Dependent Behavior Is Not Architecture

❌ Bad: "It works on Gemini, so the architecture is correct"
✅ Good: "It works on Gemini AND Qwen AND DeepSeek because the architecture doesn't depend on model-specific capabilities"

If an architecture works on one model but fails on another, the architecture has a hidden assumption about model capabilities. That assumption should be made explicit and either guaranteed or removed.

### Principle 12: Instructions Decay Over Distance

❌ Bad: Set rules at the top, generate files 9000 tokens later
✅ Good: Place critical rules adjacent to where they're needed

The `preservation_first` rule was at the top of `interactive_input_sequence`. File generation happened after 9 questions, persona mapping, validation, and user guidance — thousands of tokens later. By then, the rule's influence had decayed.

### Principle 13: Generation Is the Default; Copying Is the Exception

❌ Bad: "Copy this template, only replacing placeholders"
✅ Good: Template is embedded, steps say "Copy the ENTIRE object at [path]"

LLMs generate text. Asking them to **not** generate — to copy instead — fights their fundamental operation. Embedding the template and using explicit path references creates a stronger signal than instructions about external files.

---

## Part 9: Timeline of the Instruction-Scaling Arc

| Version | Strategy | What Happened |
|---------|----------|---------------|
| v0.35.0 | Anti-sycophancy, course_history (ADR-26001) | Worked. Good architectural decision. |
| v0.36.0 | More structure (`_then` fields, validation reasoning) | LLMs printed internal instructions as output |
| v0.37.0 | Fix by merging related concerns | LLMs skipped questions and validation |
| v0.38.0 | Maximum structure (FSM, heartbeat, state tracker) | LLMs **described the file** instead of executing it |
| v0.39.0 | Strip back to simplicity | Immediate recovery. Lesson: instructions don't scale. |
| v0.40.0 | Compiler metaphor (ADR-26002), placeholder injection | Placeholders work. But template structure still dropped by Qwen. |
| v0.41.0 | Embed templates | Removes the hidden agentic assumption entirely. |

The arc shows a pattern: **adding instructions solves the immediate problem but creates new problems at scale.** The real fix is always structural — change what the LLM sees, not what you tell it to do.

---

## Part 10: What Could Go Wrong with v0.41.0

### Risk 1: Larger meta-prompt file

`mentor_generator.json` grows from ~220 lines to ~570 lines with embedded templates.

**Mitigation:** 570 lines (~10-11k tokens) is well within all model context limits. The v0.29.1 monolith was ~460 lines and worked fine. The 3-file architecture was never necessary for size reasons — it was for separation of concerns, which is preserved in the output.

### Risk 2: Editing friction

Developers editing templates must now work inside `mentor_generator.json` instead of standalone files.

**Mitigation:** Templates are a section of the JSON, clearly labeled. The development workflow changes, but the development audience (us) has tools. The user workflow (the priority) gets simpler.

### Risk 3: Gemini regression

Gemini 3 Flash works with the current 3-file approach. Will embedding change its behavior?

**Mitigation:** Embedding gives Gemini MORE information in the same context, not less. The templates are now adjacent to the generation instructions, not in separate files the LLM must connect. This should be neutral or positive for Gemini.

### Risk 4: LLM still generates instead of copying

Even with embedded templates, the LLM might still generate from understanding rather than copy.

**Mitigation:** The new `file_generation.steps` use explicit path references ("Copy the ENTIRE object at `templates.mentor_system_prompt`") and include a verification step with an exhaustive key checklist. This is a stronger signal than "Take the raw text of the template files." But this risk is inherent to web chat — it can only be mitigated, not eliminated.

---

## Part 11: Relationship to Previous Postmortems

### v0.30 Postmortem Principles — Still Valid

| Principle | Status in v0.41.0 |
|-----------|-------------------|
| "Predictability comes from constraints, not instructions" | Reinforced. Embedded templates are stronger constraints than external file references. |
| "Instructions don't scale" | Confirmed again by v0.38.0 FSM failure and v0.40.0 Qwen failure. |
| "Self-validation is theater" | Still true. The v0.41.0 verification step is a checklist for the LLM, not a guarantee. |
| "Every token is a chance for error" | Still true. Session output is still ~30 lines. |
| "Separate roles into separate contexts" | Preserved. Generated output is still 3 files. |

### v0.32 Postmortem Principles — Still Valid

| Principle | Status in v0.41.0 |
|-----------|-------------------|
| "Session files are the ONLY dynamic data" | Preserved. course_history is still append-only. |
| "Synthesis over storage" | Preserved. Mentor still synthesizes from session records. |
| "Static actually means static" | Preserved. mentor_system_prompt and user_profile are still static after generation. |

### New Principles from This Postmortem

- "Know your execution environment" (Principle 9)
- "Attached files are context, not source code" (Principle 10)
- "Model-dependent behavior is not architecture" (Principle 11)
- "Instructions decay over distance" (Principle 12)
- "Generation is the default; copying is the exception" (Principle 13)

---

## Appendix A: Data Flow — Before and After

### v0.35.0–v0.40.0 (Separate Templates)

```
User Workflow:
1. Paste mentor_generator.json content
2. Attach 3 template files
3. Answer 9 questions
4. LLM reads templates as context → generates 3 files

Problem: Step 4 — "reads as context" ≠ "copies as source code"
```

### v0.41.0 (Embedded Templates)

```
User Workflow:
1. Paste mentor_generator.json content (templates included)
2. Answer 9 questions
3. LLM reads templates from same document → generates 3 files

Fix: Templates are part of the instruction set, not external context
```

## Appendix B: The Over-Engineering Arc

```
v0.36.0  _then fields per question          → LLM prints internal instructions
v0.37.0  merge + flatten                     → LLM skips steps
v0.38.0  4-phase FSM + heartbeat + tracker   → LLM describes instead of executes
v0.39.0  strip to bare linear sequence       → works again

Lesson: The simpler the structure, the more reliably the LLM follows it.
         There is a complexity budget. Exceed it and the LLM switches from
         "execute" to "analyze."
```

---

## Document History

- 2026-02-14: Initial version created during v0.41.0 planning
