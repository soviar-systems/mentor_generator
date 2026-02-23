---
id: 26009
title: "Agent Architecture: Template Extraction and Self-Contained Package"
date: 2026-02-23
status: accepted
supersedes: 26005
tags: [architecture, agent, template]
---

# ADR-26009: Agent Architecture: Template Extraction and Self-Contained Package

## Date

2026-02-23

## Status

accepted (supersedes ADR-26005)

## Context

ADR-26005 decided to embed the mentor system prompt template inside `mentor_generator.json` because the web-chat deployment could only see files loaded into context. This was the correct decision for that platform.

The project is now building an agentic CLI tool (`agent/`) that reads files from disk, calls an LLM API for creative work, and fills templates deterministically with Python code. The web-chat constraint no longer applies. Keeping the template embedded creates unnecessary coupling — the agent must parse a 545-line meta-prompt just to extract a nested object.

The problem catalog (v0.41) proved that 6 of 14 identified problems (P1-P5, P14) are structural consequences of asking an LLM to act as a text-substitution compiler. The agent eliminates these by separating LLM judgment (persona mapping, curriculum design) from mechanical work (template filling, validation, YAML conversion).

## Decision

1. **Extract the template** from `mentor_generator.json` → `agent/templates/mentor_system_prompt.template.json`. The template is the output schema — a standalone, versionable file.

2. **Make `agent/` a self-contained package** with its own template, tests, and usage docs:
   ```
   agent/
   ├── templates/
   │   └── mentor_system_prompt.template.json
   ├── tests/
   │   └── fixtures/
   ├── USAGE.md
   ├── main.py
   └── ... (modules)
   ```

3. **Preserve the web-chat workflow** in `web_version/` for backward compatibility. `mentor_generator.json` (with embedded template) moves there unchanged.

4. **Template path is configurable** via `template_path` in `.mentor.generator.config.yml`, defaulting to `./agent/templates/mentor_system_prompt.template.json`.

## Consequences

### Positive

- Template is independently versionable and editable without touching the meta-prompt
- Agent reads only what it needs — no parsing a 545-line file for a nested object
- `agent/` is an atomic distributable unit — copy the directory and it works
- Web-chat workflow preserved for users who prefer it
- Future templates (e.g., different mentor styles) can be added to `agent/templates/`

### Negative / Risks

- Two copies of the template exist (agent/templates/ and web_version/mentor_generator.json). **Mitigation**: web_version/ is frozen legacy; only agent/templates/ is the active source of truth.
- ADR-26005's embedding rationale no longer applies to the agent, but still applies to web_version/. **Mitigation**: ADR-26005 is superseded for the agent only; its reasoning remains valid documentation of the web-chat design.

## Alternatives

1. **Keep template embedded, have agent extract it at runtime**: Rejected — unnecessary coupling; the agent would depend on the web-chat file format.
2. **Delete mentor_generator.json entirely**: Rejected — it's a working product for web-chat users. Preserve in web_version/.
3. **Template as YAML instead of JSON**: Considered — would eliminate the JSON→YAML conversion step. Deferred because the template uses JSON for validation (ADR-26007) and the agent's `yaml.dump()` handles conversion deterministically.

## References

- ADR-26005: Embed templates for web chat (superseded for agent)
- ADR-26007: Format is architecture (JSON for input, YAML for output)
- Problem catalog: `docs/architecture/research/problem_catalog_v0.41.md`
- Agent plan: `misc/plan/plan_20260223_agent_v2_architecture_rethink.md`

## Participants

1. vrudakov
2. Claude Opus 4.6
