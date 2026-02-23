---
id: 26004
title: "Templates Are Output Schemas, Not Examples"
date: 2026-02-14
status: accepted
superseded_by: null
tags: [architecture, governance]
---

# ADR-26004: Templates Are Output Schemas, Not Examples

## Date

2026-02-14

## Status

accepted

## Context

The three template files (`mentor_system_prompt.template.md`, `user_profile.template.md`, `session.template.md`) serve a specific role in the architecture: the generator AI (compiler) reads them and outputs files that are structurally identical, with `<placeholder>` tokens replaced by user data.

This makes them **output schemas** — they define the exact structure and content of the generated files. Every character in the template that is not a `<placeholder>` appears verbatim in the output.

This was implicit in ADR-26002 ("Templates as Immutable Infrastructure," "1:1 structural mirror") but never stated explicitly. Without a clear definition, two problems emerge:

### Problem 1: Unprefixed guidance fields

The `welcome_message` and `continuation_greeting` objects currently contain fields like `example_generic`, `example_with_persona`, `example_professional`. These are guidance for the generator — style examples to inform how it fills a greeting. But they have no `_` prefix, so they look like literal output fields.

This creates ambiguity:
- Should the compiler preserve them in the output? (They're not `_`-prefixed, so yes per current rules)
- But they're not real data — they're examples. Having "If persona is 'Gandalf':..." appear in a non-Gandalf mentor's system prompt is confusing.
- They also lack an actual data field — there's no `greeting_text` for the compiler to inject the real greeting into.

### Problem 2: No field taxonomy

Without a clear definition of what each type of field means, contributors add fields ad hoc — sometimes as literal content, sometimes as guidance, sometimes as examples — with no consistent convention for distinguishing them.

## Decision

Templates are **output schemas**. Every field in a template falls into exactly one of four categories:

| Category | Convention | Compiler behavior | Example |
|---|---|---|---|
| **Literal value** | No prefix, no `<brackets>` | Copy verbatim to output | `"patience": "Learning takes time..."` |
| **Placeholder** | Value contains `<...>` | Replace `<...>` with user data | `"persona_name": "<concrete persona name>"` |
| **Internal guidance** | Key starts with `_` | Copy verbatim to output (guidance for the mentor AI during sessions) | `"_notes": "Core principles that..."` |
| **Generator-only guidance** | Key starts with `_example_` | Copy verbatim to output (style reference for both generator and mentor) | `"_example_generic": "Welcome! I'm..."` |

### Rules

1. **Every non-`_` field is output.** If a field doesn't start with `_`, it defines literal content or a placeholder that becomes literal content after injection. There is no "example" or "illustrative" category without the `_` prefix.

2. **`_`-prefixed fields are guidance.** They are preserved in the output (the mentor AI reads them during sessions), but they are clearly marked as non-data. The `_notes`, `_template_notes`, and `_example_*` prefixes all follow this convention.

3. **Every injectable point has a placeholder field.** If the generator needs to inject persona-specific content somewhere, there must be a field with a `<...>` value at that location. The generator cannot "update" a literal value — it can only replace placeholders.

4. **Existing `example_*` fields must be renamed to `_example_*`.** This fixes the current violation where style guidance masquerades as output data.

## Consequences

### Positive

- Clear contract: contributors know exactly what each field type means and how to add new ones
- The compiler has an unambiguous rule: replace `<...>`, preserve everything else character-for-character
- Eliminates the "should I keep or replace this example?" ambiguity
- `_example_*` fields survive into the generated output, where they serve as style reference for the mentor AI too (e.g., if the mentor needs to adapt greetings across sessions)

### Negative / Risks

- Renaming `example_*` → `_example_*` is a breaking change for any generated files that reference these fields by name. **Mitigation**: No consuming code references these field names; they're read by the AI as contextual guidance, not accessed programmatically.

## Alternatives

- **Remove examples entirely, put them in `mentor_generator.json`**: Per ADR-26003, generator guidance belongs in the compiler manual. **Rejection reason**: These examples also serve the mentor AI during sessions — if the mentor needs to generate a greeting variant (e.g., for a returning student after a long break), the `_example_*` fields provide style reference. They have a legitimate audience in the generated output.
- **Keep `example_*` without prefix**: Status quo. **Rejection reason**: Violates the schema contract — unprefixed fields are output data, but examples are not data.
- **Use a separate `guidance` object**: Group all guidance into a dedicated sub-object. **Rejection reason**: Over-engineering per ADR-26003. The `_` prefix convention already exists and works.

## References

- Compiler role and placeholder injection: ADR-26002
- Instruction budget and template audience: ADR-26003
- Existing `_notes` convention: used throughout all templates since v0.31.0

## Participants

1. vrudakov
2. Claude Opus 4.6
