---
id: 26003
title: "Instruction Budget: LLM Context Limits vs. Redundant Guardrails"
date: 2026-02-14
status: accepted
superseded_by: null
tags: [architecture, governance]
---

# ADR-26003: Instruction Budget: LLM Context Limits vs. Redundant Guardrails

## Date

2026-02-14

## Status

accepted

## Context

This project has two competing failure modes, both empirically observed:

**Failure Mode A — Too few guardrails (pre-v0.39.0 generator output):**
The generator AI "fills" templates by rewriting them, stripping pedagogical guardrails like `one_small_step`, `strict_turn_taking`, and anti-praise rules. ADR-26002 addresses this with the "compiler" role and strict placeholder injection.

**Failure Mode B — Too many guardrails (v0.38.0):**
v0.38.0 added a 4-phase FSM, heartbeat tags, and dense structural metadata. The result: Qwen and Gemini switched from "execute mode" to "describe mode" — they analyzed the file instead of following it. v0.39.0 fixed this by simplifying back to a linear sequence.

These are not independent problems. They share a root cause: **LLMs have a finite attention budget, and every instruction competes for it.**

### How humans and LLMs differ

A human engineer reads a spec, internalizes the rules, and applies them from memory. You can write "do not modify rules sections" once in a 50-page document and the engineer remembers it at every decision point. The instruction cost is O(1) — write it once, applied everywhere.

An LLM processes tokens with attention. Instructions far from the point of action receive less attention weight. An instruction in `mentor_generator.json` saying "preserve all `_notes` fields" has less influence when the LLM is 3000 tokens deep into generating `mentor_system_prompt`, compared to a co-located `_immutable` marker right next to the field.

This creates a temptation: **put a guardrail at every point of action.** Add `_immutable` markers to every critical section. Add `placeholder_convention` to every template's `_template_notes`. Add inline warnings everywhere.

But this is the v0.38.0 trap. Each added marker:
- Consumes tokens from the finite context window
- Increases the instruction density, making the file look like a "specification to analyze" rather than "instructions to follow"
- Creates redundancy that the LLM must reconcile (is `_immutable` the same as `preservation_first`? Are there differences?)
- Adds maintenance burden — every new guardrail is another thing to keep in sync

### The specific case that prompted this ADR

When implementing ADR-26002's placeholder injection across templates, the initial plan included:
- `placeholder_convention` field in all 3 templates' `_template_notes`
- `immutability_scope` field listing protected sections
- `_immutable` markers as first field in 3 critical sections
- `session_length_awareness` (unrelated feature)

All of these duplicate instructions already present in `mentor_generator.json`:
- `preservation_first` already tells the compiler to preserve everything
- `structural_parity` already checks for dropped content
- `file_generation.steps` already says "DO NOT alter any other character"

The redundant markers would have added ~200 tokens of structural noise to the template with zero new information for the compiler — it already has these rules in its primary instruction source (`mentor_generator.json`).

## Decision

We adopt an **instruction budget** principle: every instruction added to a template or meta-prompt must pass a cost-benefit test.

### Rules

1. **Single source of truth for compiler behavior.** Instructions for the generator AI live in `mentor_generator.json` (the compiler's manual), not scattered across templates (the source code). The compiler reads its manual before processing source code — that's where its rules belong.

2. **Templates contain structure, not meta-instructions.** Templates define what the output looks like. They contain `_notes` that guide the *mentor AI* during learning sessions, not the *generator AI* during file creation. Adding generator-facing meta-instructions to templates conflates two audiences.

3. **Add placeholders at functional gaps only.** If `persona_mapping_protocol` says "fill the greeting with persona voice" but the greeting field has no `<placeholder>`, that's a functional gap — the compiler literally cannot do what it's told. Fix by adding a placeholder. But if the compiler is already told to "preserve all `_notes`" in its manual, don't also add `_immutable` markers to every `_notes` field.

4. **Prefer one clear instruction over many scattered hints.** One well-placed rule in `preservation_first` is better than five `_immutable` markers in templates. The markers feel like "defense in depth" but actually create noise that dilutes attention.

5. **Scope creep is over-engineering.** If a change doesn't solve the problem stated in the ticket/plan, it doesn't belong in the implementation. `session_length_awareness` is a valid feature — but it's not a placeholder injection problem and shouldn't be bundled with one.

### How to evaluate a proposed guardrail

Ask three questions:
1. **Is there an existing instruction that already covers this?** If yes, the new one is redundant.
2. **Is there a functional gap?** (e.g., a rule references a field that doesn't exist, a placeholder is missing). If yes, fix the gap with minimal structure.
3. **Does this instruction target the right audience?** Generator instructions → `mentor_generator.json`. Mentor instructions → templates. Don't cross the streams.

## Consequences

### Positive

- Templates stay lean — less structural noise means LLMs are more likely to execute than describe
- Clear separation: `mentor_generator.json` = compiler manual, templates = source code, generated files = compiled output
- Prevents the v0.38.0 pattern of accumulating meta-instructions until the file collapses under its own weight
- Easier maintenance — rules live in one place, not scattered across 4 files

### Negative / Risks

- Co-located signals *do* help LLM attention. By not adding `_immutable` markers, we rely on the compiler following its manual instructions from a distance. **Mitigation**: The `structural_parity` check catches drift after the fact — if the generated file is shorter than the template, the compiler must re-inject.
- Future contributors may add "just one more marker" without understanding the budget constraint. **Mitigation**: This ADR documents the principle and the v0.38.0 cautionary tale.

## Alternatives

- **Redundant markers everywhere (defense in depth)**: Add `_immutable`, `placeholder_convention`, and inline warnings to every template section. **Rejection reason**: This is the v0.38.0 pattern. Empirically increases the chance of LLMs switching to describe mode. Also creates sync burden — if `preservation_first` changes, 5 template markers must also change.
- **No guardrails (trust the LLM)**: Remove `preservation_first` and `structural_parity`, rely on the LLM being smart enough. **Rejection reason**: Empirically fails. LLMs summarize content when not explicitly told not to (ADR-26002).
- **Separate instruction file for the compiler**: Create a `compiler_rules.md` that the generator reads alongside templates. **Rejection reason**: Adds another file to manage. `mentor_generator.json` already serves this role.

## References

- v0.38.0 over-engineering failure → v0.39.0 simplification (CHANGELOG.md)
- Instructional drift problem: ADR-26002
- File attachment limits: ADR-26001

## Participants

1. vrudakov
2. Claude Opus 4.6
