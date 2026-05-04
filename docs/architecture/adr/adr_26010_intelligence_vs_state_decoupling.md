---
id: 26010
title: "Intelligence vs. State Decoupling: The Map and the Mentor"
date: 2026-05-02
status: accepted
tags: [architecture, state-management, context-engineering]
---

# ADR-26010: Intelligence vs. State Decoupling: The Map and the Mentor

## Date

2026-05-02

## Status

accepted

## Context

This finding emerged during the deployment and stress-testing of a mentor instance in the `slm_from_scratch` project. 

A critical failure mode was identified: **The Conciseness Trap**. When using high-reasoning models—specifically **gemma-4-31b-it** and **gemini 3.1 Flash lite**—the models exhibited a strong tendency to summarize a detailed syllabus tree into high-level tables to be "helpful," even when explicitly instructed not to.

It is crucial to distinguish the architectural layers here:
- **The Meta-Agent (`mentor_generator`)**: The tool used to design the system prompts and pedagogical rules.
- **The Mentor Instance**: The deployed agent running the course (currently utilizing a web-based architecture).

The failure occurred at the **Mentor Instance** level. We discovered that we were using "intelligence" (LLM reasoning/transformation) to solve a "data" problem (representing a fixed list). Every transformation of data is a point of failure. By forcing the model to "do the work" of mapping the syllabus, the architecture invited the model to corrupt the data through summarization.

## Decision

We shift the architecture from **RAG-based Interpretation** to **State-based Execution**. 

1. **Decouple Data from Logic**: We decouple the **Control Plane** (The Map/State) from the **Execution Plane** (The Mentor/Logic). 
2. **Static Roadmap Artifacts**: Instead of asking the LLM to interpret a syllabus tree, the system will provide a pre-computed, static roadmap artifact (e.g., `roadmap_snapshot.md` or `course_state.json`).
3. **Role Shift**: The LLM's role is shifted from *interpreting* the map (fragile) to *following* the map (robust).
4. **Architect Ownership**: Context management moves from the model's reasoning to the Architect's design. If a requirement is binary and absolute, it is provided as a fixed asset, not a reasoning task.

**The Golden Rule of Roadmap Fidelity**: The Mentor must never act as a compiler for the syllabus; it must act as a mirror for the roadmap artifact.

**New Execution Flow:**
`syllabus.md` $\rightarrow$ [Architect/Pre-computation] $\rightarrow$ `roadmap_snapshot.md` $\rightarrow$ [LLM Reporting] $\rightarrow$ User.

## Consequences

### Positive

- **Eliminates the "Conciseness Trap"**: The LLM no longer needs to "summarize" the roadmap; it simply displays a perfected static artifact.
- **Reduces "Instruction Drift"**: Removes the need for repetitive, high-weight negative constraints (e.g., "Do not summarize!") in the system prompt, freeing up the instruction budget for pedagogical quality.
- **Deterministic State**: Enables "Save Game" functionality. Changes to the course structure are made once in the artifact and immediately reflected without the model needing to "re-learn" or "re-interpret" the syllabus.
- **Separation of Concerns**: 
    - **Architect**: Owns the Control Plane (What is learned, in what order, and what is the current state).
    - **Mentor**: Owns the Execution Plane (How to explain concepts and verify mastery).

### Negative / Risks

- **Manual Update Overhead**: Any change to the syllabus now requires an update to the roadmap artifact. **Mitigation**: The roadmap is intended to be stable; frequent changes to the core syllabus are discouraged.

## Guardrail Analysis: Soft vs. Hard Verification

A critical distinction is made regarding how fidelity is enforced.

**The Self-Verification Paradox**: Asking an LLM to "internally verify" that its output matches a source file in its context window is itself a reasoning task. Because the model is subject to the same RLHF biases (conciseness) it is trying to check, internal verification is a heuristic, not a proof.

1. **Soft Guardrails (Heuristic Validation)**: These are the checks embedded in the `system_prompt.json` (e.g., "Syllabus Audit Integrity"). They act as behavioral nudges that reduce error rates but cannot guarantee 100% fidelity because they rely on the model's own internal judgment.
2. **Hard Guardrails (Deterministic Verification)**: This requires an external orchestration layer to intercept the LLM's output and run a deterministic `diff` against the static artifact. Only an external, non-LLM tool can provide a "Proof of Fidelity."

**Current Implementation Status**: The system currently employs **Soft Guardrails**. While the shift to a static artifact drastically reduces the probability of corruption, absolute fidelity is managed via the Architect's review rather than a programmatic hard guardrail.

## Alternatives

1. **Heavier Prompting/Constraints**: Attempting to "out-prompt" the RLHF conciseness bias. **Rejected** — this leads to "Instruction-Scaling Tipping Point" and agentic friction without guaranteeing 100% fidelity.
2. **Custom Programmatic Parser**: Writing a script to extract the syllabus and feed it as a flat list. **Rejected** — a static Markdown/JSON artifact is simpler to maintain and more transparent for the user.

## References

- `ReadMe.md`: Section "Architectural Decoupling: Intelligence vs. State"
- `mentor/system_prompt.json`: Updated to v3.5.5 to enforce roadmap fidelity.

## Participants

1. User (Architect)
2. Qwen Code
