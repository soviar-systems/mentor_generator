---
id: 26006
title: "Post-Mortems as Validated Knowledge Chains"
date: 2026-02-14
status: accepted
superseded_by: null
tags: [governance, documentation]
---

# ADR-26006: Post-Mortems as Validated Knowledge Chains

## Date

2026-02-14

## Status

accepted

## Context

This project has three architecture post-mortems written over 18 days:

| Document | Period | Core Discovery |
|---|---|---|
| `ARCHITECTURE_POSTMORTEM_v0.30.md` | v0.30.x → v0.31.0 | Predictability comes from constraints, not instructions |
| `ARCHITECTURE_POSTMORTEM_v0.32.md` | v0.31.0 → v0.34.0 | Session files are the only dynamic data |
| `ARCHITECTURE_POSTMORTEM_v0.40.md` | v0.35.0 → v0.41.0 | Web chat LLMs treat attached files as context, not source code |

These documents were written independently — no template, no style guide. Yet they converged on the same structure:

1. **Problem statement** — what went wrong, with concrete symptoms
2. **Evidence** — exact output, line-by-line comparison, reproduction steps
3. **Failed fixes** — what we tried and why it didn't work
4. **Breakthrough insight** — the root cause that explains all the symptoms
5. **Solution** — the architectural change derived from the insight
6. **Principles extracted** — reusable lessons numbered and formatted as rules

This is the scientific method applied to architecture decisions: hypothesis → experiment → observation → revised hypothesis. Each postmortem tests assumptions from the previous one.

### The chain property

The postmortems are not isolated documents. They form a **knowledge chain** where each one:

- **Validates** principles from earlier postmortems (e.g., v0.40 confirms v0.30's "instructions don't scale" when Qwen drops 10 template sections despite explicit preservation rules)
- **Extends** the principle set (v0.30 produced principles 1-8, v0.32 refined the data flow model, v0.40 added principles 9-13)
- **References** earlier principles by number when they apply to new evidence

This chain creates **validated knowledge** — principles that have been tested against multiple failure scenarios across different model families, different architectural approaches, and different time periods. A principle that survives three postmortems is more trustworthy than one stated once.

### What prompted this ADR

When writing `ARCHITECTURE_POSTMORTEM_v0.40.md`, we noticed the pattern had emerged organically and recognized it as the project's primary learning mechanism. The postmortems are where architectural knowledge actually lives — ADRs record decisions, but postmortems record the *reasoning process* that produced those decisions. Without formalizing the structure, future postmortems might omit critical sections (like failed fixes — the most instructive part).

## Decision

Architecture post-mortems follow a fixed structure. Each postmortem is a link in a validated knowledge chain.

### Required Sections

| Section | Purpose | Key Question |
|---|---|---|
| **Executive Summary** | One-paragraph orientation | What was the core discovery? |
| **The Architecture at Version X** | Snapshot of the system before the problem | What did we have? |
| **What Went Wrong** | Concrete symptoms with evidence | What broke, and how do we know? |
| **Failed Fixes** | Attempted solutions and why they failed | What did we try that didn't work? |
| **Root Cause Analysis** | The deeper explanation behind the symptoms | Why did it really fail? |
| **The Solution** | Architectural change derived from root cause | What did we change? |
| **Principles Extracted** | Numbered, reusable lessons in rule format | What do we now know that we didn't before? |
| **Relationship to Previous Postmortems** | Validate/extend/contradict earlier principles | Does this confirm or revise what we thought we knew? |

### Rules

1. **Evidence over narrative.** Show the actual output, the actual diff, the actual failure. "The template was dropped" is a claim; a table showing 10 dropped sections with before/after is evidence.

2. **Failed fixes are mandatory.** The most instructive part of a postmortem is what didn't work and why. Omitting failed fixes makes it look like the solution was obvious — it never is. Failed fixes prevent future contributors from re-attempting the same approaches.

3. **Number the principles.** Principles accumulate across postmortems. Numbering allows later documents to reference earlier principles by number (e.g., "confirms Principle 3 from v0.30 postmortem"). The numbering is continuous across all postmortems, not restarted per document.

4. **Validate the chain.** Every new postmortem must include a section that maps its findings against principles from previous postmortems. Three outcomes are possible:
   - **Confirmed**: New evidence supports the principle
   - **Extended**: The principle applies to a broader context than originally stated
   - **Revised**: New evidence contradicts or refines the principle

5. **One postmortem per architectural shift.** Don't write a postmortem for every version bump. Write one when the architecture changes direction — when a new root cause is discovered that existing principles didn't predict.

6. **Name by the version where the problem was discovered**, not where it was fixed. `ARCHITECTURE_POSTMORTEM_v0.40.md` documents the failure discovered at v0.40.0, even though the fix is v0.41.0. The version number says "this is what we learned by reaching this point."

### File Convention

- Location: `architecture/postmortem/ARCHITECTURE_POSTMORTEM_v{VERSION}.md` (updated by ADR-26008)
- Version in filename: the version where the problem was discovered/investigated
- Author line includes both human and AI participants

## Consequences

### Positive

- Future postmortems have a clear structure to follow — no reinventing the format each time
- The "failed fixes" requirement preserves the learning process, not just the outcome
- The chain validation requirement forces authors to check whether new findings are actually new or just re-discoveries of existing principles
- Numbered principles create a shared vocabulary for architectural discussions ("this violates Principle 10")
- New contributors can read the chain chronologically to understand not just what the architecture is, but *why* every decision was made

### Negative / Risks

- The fixed structure might feel rigid when a postmortem doesn't fit neatly (e.g., a postmortem about a process problem rather than an architecture problem). **Mitigation**: The sections are required topics, not rigid templates. Adapt the content, keep the structure.
- Forcing chain validation could lead to post-hoc rationalization — finding connections that aren't really there. **Mitigation**: The three outcomes (confirmed, extended, revised) include "revised," which explicitly allows contradicting previous principles. The chain is a scientific record, not a marketing document.

## Alternatives

- **No formalized structure (status quo)**: Let postmortems evolve organically. **Rejection reason**: The structure already converged organically — formalizing it costs nothing and protects against future documents that omit critical sections.
- **ADR-only documentation**: Record all architectural knowledge as ADRs, skip postmortems. **Rejection reason**: ADRs record decisions; postmortems record the reasoning process. "We decided to embed templates" (ADR) is less instructive than "We tried separate files, Qwen dropped 10 sections, we discovered web chats can't do file transformation, so we embedded templates" (postmortem). The journey matters as much as the destination.
- **Lightweight incident reports**: Short documents with just "what happened" and "what we did." **Rejection reason**: Omits the most valuable parts — failed fixes and principle extraction. Incident reports answer "what happened?"; postmortems answer "what did we learn?"

## References

- `architecture/postmortem/ARCHITECTURE_POSTMORTEM_v0.30.md` — Principles 1-8 (constraints over instructions, append-only, minimal output, etc.)
- `architecture/postmortem/ARCHITECTURE_POSTMORTEM_v0.32.md` — Data flow model (session files as only dynamic data, synthesis over storage)
- `architecture/postmortem/ARCHITECTURE_POSTMORTEM_v0.40.md` — Principles 9-13 (execution environments, generation as default, instruction decay)

## Participants

1. vrudakov
2. Claude Opus 4.6
