---
id: 26007
title: "Format is Architecture: YAML Output, JSON Source"
date: 2026-02-15
status: accepted
superseded_by: null
tags: [architecture, format]
---

# ADR-26007: Format is Architecture: YAML Output, JSON Source

## Date

2026-02-15

## Status

accepted

## Context

The mentor generator has two file categories serving different LLM audiences:

1. `mentor_generator.json` — compiler input, read once during generation
2. `mentor_system_prompt` — runtime instructions, read by the mentor every session
3. Session records in `course_history` — structured data the mentor scans for fields

Format affects LLM behavior: structural noise tokens (`{}`, `""`, `,`, `**`, `##`) consume attention budget without carrying instructional content. Different formats also appear in different training-data contexts, which may bias processing patterns (JSON = data parsing, YAML = configuration/instructions).

For full analysis with token counts, training distribution evidence, and a decision framework, see the companion article: `ai_engineering_book/ai_system/3_prompts/format_as_architecture_signal_noise_in_prompt_delivery.md`

## Decision

| File | Format | Why |
|---|---|---|
| `mentor_generator.json` | **JSON** | Development artifact. Needs `jq`/Python validation. Compiler reads precise field paths. |
| `mentor_system_prompt` | **YAML** | Runtime instruction set. Lowest structural noise among formats that preserve key-value addressability. |
| Session records in `course_history` | **JSON** | Structured data for field scanning. JSON's strictness fits machine-parseable records. |

Rules:
1. Meta-prompt stays in JSON (compiler input, needs validation tooling)
2. Generated output is YAML (runtime instructions, minimal noise)
3. Session records stay in JSON (structured data, not instructions)
4. Never use Markdown for structured prompt files (destroys field addressability, its own formatting symbols are noise)

## Consequences

### Positive

- Lowest structural noise in the generated file while preserving field access
- Clear format boundary: JSON for development, YAML for runtime, JSON for data
- Consistent with web chat deployment (ADR-26005)

### Negative / Risks

- Two formats in one project. **Mitigation**: boundary is clear and intentional.
- YAML indentation sensitivity. **Mitigation**: simple nesting (2-3 levels), no anchors or block scalars.

## References

- Full analysis: `ai_engineering_book/ai_system/3_prompts/format_as_architecture_signal_noise_in_prompt_delivery.md`
- Web chat deployment: ADR-26005
- Instruction budget: ADR-26003
- Qwen3-Max v0.41.0 test: `misc/chat-Interactive Meta-Prompt Generation.txt`

## Participants

1. vrudakov
2. Claude Opus 4.6
