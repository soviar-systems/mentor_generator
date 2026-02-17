---
id: 26008
title: "Architecture Directory Taxonomy"
date: 2026-02-17
status: accepted
superseded_by: null
tags: [documentation, structure]
---

# ADR-26008: Architecture Directory Taxonomy

## Date

2026-02-17

## Status

accepted

## Context

The project's architectural documentation lived in `docs/` — a generic name that doesn't distinguish architectural records from potential future user-facing documentation (instructions, guides, specifications). Inside, ADRs had their own subdirectory (`docs/adr/`) but post-mortems sat loose at the root, and a new document type — cross-cutting research and analysis — had no home.

Three distinct architectural document types exist:

| Document type | Purpose | Lifecycle |
|---|---|---|
| Architecture Decision Records | Record a single decision with context and consequences | Immutable once accepted (may be superseded) |
| Post-mortems | Retrospective on what happened in a version range | Immutable once written |
| Research / Analysis | Cross-cutting synthesis across post-mortems and ADRs | May be superseded as new evidence arrives |

All three are architectural documentation. None are user-facing docs, API specs, or guides. Naming the parent directory `docs/` is imprecise and invites unrelated content.

## Decision

Rename `docs/` to `architecture/` and organize into three subdirectories:

```
architecture/
├── adr/           # Architecture Decision Records
├── postmortem/    # Version retrospectives (historical records)
└── research/      # Cross-cutting analysis and synthesis
```

Naming conventions per directory:

| Directory | File naming |
|---|---|
| `adr/` | `adr_<5-digit-id>_<slug>.md` |
| `postmortem/` | `ARCHITECTURE_POSTMORTEM_v<version>.md` |
| `research/` | `<descriptive_slug>_v<version>.md` |

Rules:
1. Every architectural document goes into exactly one of the three subdirectories
2. ADRs and post-mortems are write-once — corrections go in new documents, not edits
3. Research documents may be updated or superseded when new evidence changes conclusions
4. No documents at the `architecture/` root — everything lives in a subdirectory
5. If user-facing documentation is ever needed (instructions, guides), it goes in a separate `docs/` directory, not here

## Consequences

### Positive

- Directory name communicates purpose — no ambiguity about what belongs here
- Clear placement rule for each document type
- Leaves `docs/` available for user-facing documentation if ever needed
- Each subdirectory has its own naming convention and lifecycle

### Negative / Risks

- Breaks convention: most projects use `docs/`. **Mitigation**: this project has no user-facing docs, no doc generators, no tooling that depends on the `docs/` name.
- All existing references to `docs/` paths must be updated (CLAUDE.md, cross-references in ADRs/post-mortems). **Mitigation**: do this in the same commit as the rename.

## Alternatives

1. **Keep `docs/` with subdirectories (`docs/adr/`, `docs/postmortem/`, `docs/research/`)**: Rejected — `docs/` is a generic name that invites non-architectural content. The sibling project (`ai_engineering_book`) already uses `architecture/` for the same purpose, and consistency across projects reduces cognitive load.
2. **Flat `docs/` root with naming prefixes (e.g., `docs/PM_v0.40.md`, `docs/RES_problem_catalog.md`)**: Rejected — prefixes are a poor substitute for directories. No lifecycle separation, harder to glob by type.
3. **Separate top-level directories (`adr/`, `postmortem/`, `research/`)**: Rejected — scatters related content across the repo root. A single parent directory communicates that these are all part of the same architectural knowledge base.

## References

- Problem catalog that motivated the research/ subdirectory: `architecture/research/problem_catalog_v0.41.md`
- ADR-26006: Postmortem as validated knowledge chain
- Sibling project precedent: `ai_engineering_book/architecture/`

## Participants

1. vrudakov
2. Claude Opus 4.6
