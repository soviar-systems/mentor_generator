# Research: Comprehensive Problem Catalog for Free Web Chat Deployment

## Context

The Mentor Generator (v0.41.0) produces personalized AI learning mentors via a meta-prompt that runs in **free web chat interfaces** (Gemini, Qwen, ChatGPT, Claude.ai, DeepSeek). This research synthesizes all test results, post-mortems (v0.30→v0.41), and ADRs to establish a complete picture of constraints and failure modes. This document is the foundation for all future architectural decisions.

---

## Part 1: Problem Catalog — Generation Phase (Compiler Role)

These problems occur when the meta-prompt asks a web chat LLM to generate the `mentor_system_prompt` file.

### P1. Instruction Leakage / Shadow Instructions
- **Source**: Gemini v0.41.0 self-diagnosis, post-mortem v0.35→v0.41
- **Symptom**: Template content embedded inside `mentor_generator.json` is "consumed" as behavioral directives rather than treated as inert payload. The LLM reads `session_output_protocol` rules and integrates them into its own behavior instead of copying them to output.
- **Root cause**: LLMs cannot distinguish between "instructions for me" and "data to copy" when both live in the same JSON structure. Nested instructional keys (`_notes`, protocol steps) trigger the instruction-following pathway.
- **Evidence**: Gemini dropped `session_output_protocol`, `_template_notes`, and all `_example_*` fields. Qwen3-Max (v0.40) dropped 10 entire sections.
- **Severity**: Critical — destroys pedagogical guardrails silently.

### P2. Compressive Heuristic / Token Economy Bias
- **Source**: Gemini v0.41.0 self-diagnosis, ADR-26003
- **Symptom**: LLM prioritizes "new" information (filled placeholders) over "old" information (boilerplate rules, `_notes`, examples). Output is semantically correct but structurally truncated.
- **Root cause**: Training data rewards brevity. When faced with 300+ lines of structured config, the model's efficiency bias activates and drops content perceived as redundant.
- **Evidence**: Gemini output was ~170 lines instead of ~300+. All `_notes` and `_example_*` fields were omitted.
- **Severity**: Critical — the dropped content IS the pedagogical architecture.

### P3. JSON→YAML Format Conversion Errors
- **Source**: Qwen v0.41.0 test results, Gemini v0.41.0 test results
- **Symptom**: Keys are renamed, truncated, or malformed during format conversion.
- **Evidence**:
  - Gemini: `metadata` → `meta` (invalid key name)
  - Qwen: `structure_data` → `structure_` (truncated key, line 957 of output)
  - Both: inconsistent quoting of YAML strings
- **Root cause**: JSON-to-YAML conversion is a "re-coding" step that forces the LLM to think/translate rather than copy. Each translation decision is an error opportunity.
- **Severity**: Medium — causes invalid YAML or broken field references.

### P4. Structural Parity Check is Semantic, Not Syntactic
- **Source**: Gemini v0.41.0 self-diagnosis
- **Symptom**: The LLM performs a semantic check ("is all user data present?") but not a syntactic check ("does the output have the same keys and depth as the template?").
- **Root cause**: LLMs cannot count lines, compare structures, or verify completeness. Self-validation is theater (Principle 7 from v0.30 post-mortem).
- **Evidence**: Gemini declared all validation checks [PASSED] then produced an output missing half the template.
- **Severity**: High — false confidence; user trusts the output.

### P5. Instruction Distance Decay
- **Source**: ADR-26003, post-mortem v0.35→v0.41
- **Symptom**: `preservation_first` and `structural_parity` rules are at the top of `mentor_generator.json`. By the time the LLM reaches `file_generation` (thousands of tokens later), these rules have decayed in attention.
- **Root cause**: LLM attention is position-sensitive. Instructions far from the point of action lose influence.
- **Evidence**: v0.40 Qwen dropped 10 sections despite explicit preservation instructions at the top.
- **Severity**: High — fundamental LLM limitation.

### P6. Model-Dependent Behavior Variance
- **Source**: Post-mortem v0.35→v0.41, all test results
- **Symptom**: Same meta-prompt produces dramatically different output quality across models.
- **Evidence**:
  - Qwen v0.41.0: ~95% structural fidelity, minor key truncation
  - Gemini v0.41.0: ~60% structural fidelity, major section drops, required user confrontation to even acknowledge the problem
  - Qwen3-Max v0.40: Catastrophic drift (10 sections dropped, immutable fields rewritten)
- **Root cause**: Different models have different instruction-following vs generative-default balances. Architecture that works on one model by coincidence is not architecture (Principle 11).
- **Severity**: Critical — product must work across models.

---

## Part 2: Problem Catalog — Runtime Phase (Mentor Role)

These problems occur during actual learning sessions, when the generated mentor operates.

### P7. Premature Session Save
- **Source**: Qwen3-Max real session v0.41.0
- **Symptom**: Mentor outputs "Saving session N..." and terminates the learning flow without user consent. Happened THREE times in one session (lines 708, 801, 879).
- **Root cause**: The word "session" or "finish" in user messages triggers the `session_output_protocol` pathway. The LLM interprets intent rather than waiting for explicit signal.
- **Evidence**: User said "we can finish the current session" (conditional/hypothetical) → mentor immediately saved. User said "I still do not understand it" → mentor saved anyway.
- **Severity**: High — breaks learning flow, frustrates user, violates turn-taking.

### P8. Turn-Taking Violations
- **Source**: Qwen3-Max real session v0.41.0
- **Symptom**: Mentor asks a question, user asks for clarification, mentor answers the clarification AND asks a NEW question — skipping the original unanswered question.
- **Evidence**: User explicitly called this out: "Record your failure - I have not provided the answer to Question 2 yet but you assume that I have."
- **Root cause**: Despite multiple redundant turn-taking rules (`CRITICAL_TURN_TAKING`, `strict_turn_taking`, `ask_and_wait`), the LLM's conversational momentum overrides them. The rules exist but don't have enough behavioral weight.
- **Severity**: High — undermines mastery-gated progression.

### P9. Factual Errors in Teaching Content
- **Source**: Qwen3-Max real session v0.41.0
- **Symptom**: Mentor provided incorrect code example for `libcst` `ScopeProvider` API. User had to debug and correct it.
- **Evidence**: Lines 674-693 (mentor's code) vs lines 738-777 (user's corrected version). The mentor passed a node object instead of a string key to scope lookup.
- **Root cause**: LLMs generate plausible-looking code that may not match actual library APIs. The `pre_response_peer_review` self-check didn't catch it (self-validation is theater).
- **Severity**: Medium — the mentor did acknowledge the error and log it in the session record. The self-correction mechanism worked at the *recording* level, just not at the *prevention* level.

### P10. Protocol Confusion Under Ambiguity
- **Source**: Qwen3-Max real session v0.41.0
- **Symptom**: When user said "If it is justified, we can finish the current session and start a new one," the mentor couldn't decide: continue teaching or save session? It oscillated between both actions across three messages.
- **Root cause**: Natural language ambiguity + multiple competing protocol rules (continue teaching vs respect user's suggestion vs session end trigger).
- **Severity**: Medium — makes the mentor appear indecisive and unreliable.

---

## Part 3: Problem Catalog — Architectural / Structural

### P11. Template Size vs Attention Budget
- **Source**: ADR-26003, ADR-26005, post-mortem v0.35→v0.41
- **Symptom**: The embedded template in `mentor_generator.json` is now ~350 lines of JSON. As a single document, it must fit in both:
  1. The generator's context (alongside questionnaire logic + user answers)
  2. The generated mentor's context (as the entire system prompt)
- **Trade-off**: Embedding solved the cross-file reference problem (P6) but increased per-document size, which amplifies P2 (compressive heuristic) and P5 (instruction distance).
- **Severity**: Structural tension — no clear solution yet.

### P12. Instruction Budget Threshold
- **Source**: ADR-26003, post-mortem v0.35→v0.41
- **Symptom**: There exists a model-specific threshold of instruction density beyond which LLMs switch from "execute mode" to "describe mode."
- **Evidence**: v0.38.0 (FSM + heartbeat tags) crossed the threshold → LLMs analyzed the file instead of following it. v0.39.0 stripped complexity → immediate recovery.
- **Pattern**:
  ```
  v0.36: More structure (_then fields) → LLMs printed internal instructions
  v0.37: Merge + flatten → LLMs skipped questions, validation
  v0.38: Maximum structure (FSM, heartbeat) → LLMs described file instead of executing
  v0.39: Strip to bare linear sequence → Immediate recovery
  ```
- **Severity**: Critical — this is the fundamental constraint of the product.

### P13. Web Chat ≠ Agentic Execution
- **Source**: ADR-26005, post-mortem v0.35→v0.41
- **Symptom**: Features that assume tool-use capabilities (file editing, precise text substitution, multi-file coordination) fail in web chat.
- **Key insight**: In web chat, attached files are **context that informs generation**, not source code to be transformed. The LLM reads, understands, and generates its own version — it does not copy-then-substitute.
- **Evidence**: v0.31-v0.40 architecture assumed file transformation capability that doesn't exist in target platform.
- **Severity**: Critical — fundamental platform constraint.

### P14. Self-Validation is Theater
- **Source**: Post-mortem v0.30, all test results
- **Symptom**: Validation gates, peer review checks, and structural parity checks are performed semantically (the LLM "thinks about" whether it's correct) but never syntactically (it cannot actually compare structures).
- **Evidence**: Every model declared [PASSED] on all validation checks, then produced output with missing sections, renamed keys, or truncated fields.
- **Severity**: High — creates false confidence in output quality.

---

## Part 4: Validated Principles (Cross-Referenced Across Post-Mortems)

These principles have been validated across multiple versions and post-mortems:

| # | Principle | First Found | Revalidated |
|---|-----------|-------------|-------------|
| 1 | Constrain output, don't instruct it | v0.30 | v0.38, v0.40, v0.41 |
| 2 | Separate roles into separate contexts | v0.30 | v0.31+ (stable) |
| 3 | Minimize LLM output size | v0.30 | v0.41 (still relevant) |
| 4 | Make operations append-only | v0.30 | v0.34+ (stable) |
| 5 | Eliminate judgment calls | v0.30 | v0.40, v0.41 |
| 6 | Don't ask LLMs to count or measure | v0.30 | v0.41 (validation theater) |
| 7 | Self-validation is theater | v0.30 | v0.41 (all models) |
| 8 | Explicit over implicit state | v0.30 | v0.34+ (stable) |
| 9 | Know your execution environment | v0.41 | NEW — web chat ≠ agentic |
| 10 | Attached files are context, not source | v0.41 | NEW — fundamental |
| 11 | Model-dependent behavior is not architecture | v0.41 | NEW — Gemini vs Qwen |
| 12 | Instructions decay over distance | v0.41 | NEW — preservation_first failure |
| 13 | Generation is default; copying is exception | v0.41 | NEW — LLM fundamental |

---

## Part 5: Constraint Map for Future Decisions

Any future change must be evaluated against these constraints:

### Hard Constraints (Cannot Be Changed)
1. **Platform**: Free web chat interfaces (no API, no tools, no file editing)
2. **Attachment limits**: 1-5 files depending on platform
3. **LLM attention budget**: Finite, position-sensitive, model-dependent
4. **LLM generative default**: Models generate, not copy
5. **Self-validation impossibility**: LLMs cannot verify their own structural output
6. **Format conversion errors**: Any format translation is an error opportunity

### Soft Constraints (Can Be Optimized)
1. **Template size**: Currently ~350 lines; can be reduced
2. **Instruction density**: Can be tuned (v0.38 too high, v0.39 too low)
3. **Instruction placement**: Critical rules can be moved closer to point of action
4. **Field taxonomy clarity**: `_` prefix convention can be made more explicit
5. **Session end trigger**: Can be made more explicit/less ambiguous

### Design Space (Open Questions for Future Versions)
1. Should the template source format match the output format (YAML→YAML) to eliminate P3?
2. Can we use delimiter hardening (`[[[PAYLOAD_START]]]`) to combat P1?
3. Should we split the meta-prompt into smaller sequential steps to stay under the instruction budget threshold (P12)?
4. Can we reduce the mentor system prompt size to improve runtime behavior (P7, P8)?
5. How do we handle session end ambiguity (P10) without adding more instructions (P12)?
6. What is the minimum viable mentor system prompt that preserves pedagogical quality?

---

## Part 6: Problem Priority Matrix

| Problem | Severity | Frequency | Fixability | Priority |
|---------|----------|-----------|------------|----------|
| P1 Instruction Leakage | Critical | Every generation (Gemini) | Hard — fundamental LLM behavior | 1 |
| P2 Compressive Heuristic | Critical | Every generation | Hard — training bias | 1 |
| P6 Model Variance | Critical | Cross-model | Medium — better constraints help | 1 |
| P12 Instruction Budget | Critical | Architecture-level | Medium — can tune density | 2 |
| P13 Web Chat ≠ Agentic | Critical | Architecture-level | Solved by v0.41 embedding | 2 |
| P7 Premature Session Save | High | Frequent (3x in 1 session) | Medium — trigger redesign | 3 |
| P8 Turn-Taking Violations | High | Frequent | Hard — LLM conversational momentum | 3 |
| P14 Self-Validation Theater | High | Every generation | Cannot fix — accept and design around | 3 |
| P5 Instruction Distance | High | Every generation | Medium — restructure placement | 4 |
| P3 Format Conversion Errors | Medium | Occasional | Medium — could match formats | 4 |
| P4 Parity Check Failure | High | Every generation | Subset of P14 | 4 |
| P9 Factual Errors | Medium | Occasional | Cannot fix — inherent LLM limitation | 5 |
| P10 Protocol Confusion | Medium | Occasional | Medium — clearer trigger rules | 5 |
| P11 Template Size Tension | Structural | Permanent | Trade-off — no clean solution | 5 |

---

## Part 7: Strategic Analysis — Free Web Chat vs Agentic Deployment

This is the central strategic question: **should the product continue targeting free web chats, or should it pivot to agentic/tool-based execution?**

### What the Evidence Shows

The 14 problems identified above split cleanly into two categories:

**Problems inherent to web chat (cannot be fixed by better prompting):**
- P1 (Instruction Leakage) — web chat LLMs cannot distinguish payload from instructions
- P2 (Compressive Heuristic) — web chat LLMs compress long structured output
- P3 (Format Conversion) — web chat LLMs make errors during format translation
- P4/P14 (Self-Validation Theater) — web chat LLMs cannot verify their own output
- P5 (Instruction Distance) — web chat has no mechanism to re-inject rules at point of action
- P13 (No Tool Use) — web chat cannot edit files, run validators, or diff structures

**Problems that exist in BOTH environments (not web-chat-specific):**
- P6 (Model Variance) — different models behave differently everywhere
- P7 (Premature Session Save) — conversational momentum issue, present in all chat
- P8 (Turn-Taking Violations) — LLM conversational default, all environments
- P9 (Factual Errors) — LLM hallucination, all environments
- P10 (Protocol Confusion) — ambiguity handling, all environments
- P11 (Template Size) — attention budget, all environments
- P12 (Instruction Budget Threshold) — fundamental LLM limit, all environments

### What Agentic Execution Would Solve

In an agentic environment (Claude Code, API with tools, MCP), we could:

| Problem | Agentic Solution |
|---------|-----------------|
| P1 Instruction Leakage | Tool reads template file, tool writes output file — separation is physical, not prompt-based |
| P2 Compressive Heuristic | Tool copies file sections verbatim; LLM only fills placeholders via targeted edits |
| P3 Format Conversion | `yq` or Python script handles JSON→YAML conversion deterministically |
| P4/P14 Self-Validation | `jq`/`yq` validates structure; `diff` compares against template; real validation, not theater |
| P5 Instruction Distance | Multi-step tool chain; each step has focused instructions adjacent to action |
| P13 No Tool Use | By definition solved |

**Agentic execution would eliminate 6 of 14 problems entirely and significantly reduce 2 more.**

### What Agentic Execution Would NOT Solve

- P7-P10 (runtime mentor problems) — the learning sessions still happen in conversational chat
- P6 (model variance) — still exists unless you lock to one model
- P11-P12 (instruction budget) — the mentor system prompt is still consumed by an LLM

**Critical insight: The generation phase and the runtime phase have fundamentally different platform requirements.**

### The Two-Phase Reality

| Phase | Current Platform | Ideal Platform | Why |
|-------|-----------------|----------------|-----|
| **Generation** (compiler) | Web chat | Agentic/tool-based | Needs file manipulation, validation, structural copying — all tool capabilities |
| **Runtime** (mentor sessions) | Web chat | Web chat | IS genuinely conversational; web chat is the natural fit; the user learns through dialogue |

The generation phase is **fighting the platform**. We're asking a conversational AI to behave as a text-substitution engine — the opposite of what it's designed to do. Every improvement since v0.30 has been a workaround for this mismatch.

The runtime phase is **aligned with the platform**. A learning mentor IS a conversational role. The remaining problems (P7-P10) are behavioral tuning issues, not platform mismatches.

### Three Strategic Options

**Option A: Stay on free web chat for everything**
- Pros: Maximum accessibility; zero cost to users; single workflow
- Cons: P1-P5 are unfixable; generation quality will always be model-dependent and imperfect; requires user to manually verify output
- Prognosis: Diminishing returns on optimization. v0.41 may be near the ceiling of what's achievable.

**Option B: Hybrid — agentic generation, web chat runtime**
- Pros: Solves generation problems cleanly; runtime stays accessible; user only needs agentic tool once (to generate the mentor file)
- Cons: Requires users to have access to Claude Code / API / similar tool for the one-time generation step; adds complexity to user workflow
- Prognosis: Best engineering outcome. Generation becomes deterministic. But narrows the user base.

**Option C: Full agentic (both phases)**
- Pros: Maximum control and quality
- Cons: Users must use paid tools for every session; defeats the original accessibility goal
- Prognosis: Different product entirely.

### Data Sufficiency Assessment

**Do we have enough data to decide?**

For the generation phase: **YES.** We have tested 3 models (Gemini, Qwen, Qwen3-Max) across 3 versions (v0.40, v0.41). The failure patterns are consistent and well-understood. The root causes are fundamental LLM behaviors, not prompt engineering gaps. More testing will confirm what we already know.

For the runtime phase: **PARTIALLY.** We have 1 real session example (Qwen3-Max). The problems found (P7-P10) are significant but potentially addressable through prompt tuning. More testing across models would strengthen confidence but isn't blocking for the strategic decision.

**Conclusion: We have sufficient data to state that free web chat generation will always produce imperfect output.** The question is whether "imperfect but usable with manual verification" is acceptable for the target audience, or whether we should separate the phases.

### Decision Framework

Each option trades off differently across the product's core values:

| Value | Option A (Web Chat) | Option B (Hybrid) | Option C (Full Agentic) |
|-------|--------------------|--------------------|------------------------|
| **Accessibility** | Maximum | Slightly reduced (one-time tool needed) | Significantly reduced |
| **Generation quality** | 60-95%, model-dependent | ~100%, deterministic | ~100%, deterministic |
| **User effort** | Manual verification of output | One-time setup, then simple | Tool required every session |
| **Model independence** | Architecture-dependent | Generation: independent; Runtime: still varies | Full control |
| **Development effort** | Continuing prompt optimization (diminishing returns) | Build generation tool + maintain meta-prompt | Different product |
| **Cost to user** | Free | Free (if using free-tier API) to minimal | Ongoing API costs |

**This is a product direction decision for the team.** The technical analysis shows the trade-offs clearly; the choice depends on which values the product prioritizes.

---

## Summary

The product operates under a **triple constraint**:
1. **Generation fidelity** — the compiler must reproduce templates accurately (P1-P6, P14)
2. **Runtime compliance** — the generated mentor must follow its own rules (P7-P10)
3. **Instruction budget** — adding rules to fix (1) and (2) risks crossing the threshold where LLMs stop executing and start describing (P12)

Every fix for one constraint risks violating another. The history of v0.30→v0.41 is the history of discovering this tension. Future solutions must acknowledge that **we cannot instruct our way out of these problems** — we can only constrain the output structure to make correct behavior the path of least resistance.
