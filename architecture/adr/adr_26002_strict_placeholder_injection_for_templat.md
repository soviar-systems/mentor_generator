---
id: 26002
title: "Strict Placeholder Injection for Template Fidelity"
date: 2026-02-13
status: accepted
superseded_by: null
tags: [architecture, governance, workflow]
---

# ADR-26002: Strict Placeholder Injection for Template Fidelity

## Date

2026-02-13

## Status

accepted

## Context

In previous iterations of the meta-prompt generator, the AI was given the autonomy to "fill" templates by regenerating the entire content based on its interpretation of the user's requirements. This led to a critical failure known as **Instructional Drift via Summarization**.

When the generator agent attempted to be "efficient," it stripped away essential pedagogical guardrails—such as the `one_small_step` rule, `strict_turn_taking` protocols, and anti-praise constraints—contained within the `mentor_system_prompt.template.md`. The resulting mentor was verbose, ignored pedagogical limits, and discouraged the user.

The `old_file.json` (v0.29.1) approach demonstrated that keeping instructions within immutable `_notes` fields and treating the prompt as a "State Object" successfully preserved mentor behavior. We need a mechanism that ensures the generated output is a 1:1 structural mirror of the source template.

## Decision

We will transition from a **Generative Approach** to a **Strict Placeholder Injection** architecture.

1. **Templates as Immutable Infrastructure**: The template files (`mentor_system_prompt.template.md` and `user_profile.template.md`) are to be treated as boilerplate code. The generator is forbidden from modifying any text outside of defined variable boundaries.
2. **Variable Syntax**: Variables within templates are identified by bracketed placeholders (e.g., `<USER_TOPIC>`, `<concrete persona name>`).
3. **The "Compiler" Role**: The meta-prompt assistant will act as a text-substitution engine (a "compiler") rather than a creative writer. Its sole responsibility during the file generation phase is to map collected user data to these specific placeholders.
4. **Preservation of Internal Instructions**: All `_notes`, `_template_notes`, and logic blocks (like `mentor_self_control`) must be preserved verbatim in the final output. This ensures the Mentor AI reads its own operational constraints every time the file is loaded.

## Consequences

### Positive

* **Logic Fidelity**: Ensures 100% of the pedagogical guardrails survive the generation process.
* **Behavioral Consistency**: The mentor will follow the "Small Step" and "Stop After Question" rules regardless of the chosen persona.
* **Simplified Debugging**: If the mentor misbehaves, we can verify the system prompt against the template to ensure no rules were dropped during generation.
* **Context-Aware Mentoring**: By preserving `_notes`, the Mentor AI understands its own role and limitations as defined by the system designer.

### Negative / Risks

* **Token Overhead**: The generated files will be larger because they contain all original instructions and notes. **Mitigation**: Modern LLM context windows (Gemini, Claude) are more than sufficient to handle the ~2-3k tokens of a full system prompt.
* **Persona Integration**: The persona's "voice" must be strong enough to shine through a rigid structure. **Mitigation**: Use the `mentor_profile` and specific greeting placeholders to inject persona-specific terminology while keeping the rules static.

## Alternatives

* **Generative Summarization (Status Quo)**: Allow the AI to rewrite the prompt. **Rejection Reason**: Empirically failed; causes "complete disaster" in teaching workflow by removing mastery-gated constraints.
* **Modular File Injection**: Creating multiple small rule files. **Rejection Reason**: Hits the file attachment limits of web UIs (as addressed in ADR-26001).
* **Hard-Coded Prompts**: Maintaining a single prompt and only providing a small JSON user profile. **Rejection Reason**: Limits the ability to deeply customize the mentor's expertise and "Architect" persona for specialized topics like AI Code Generation.

## References

* **Pedagogical Guardrails**: `mentor_system_prompt.template`
* **File Management Policy**: {term}`ADR-26001`

## Participants

1. vrudakov
2. Gemini (Senior Prompt Engineer Persona)
