# ADR: Tool-Driven State Control (The Directive Pattern)

**Status:** Proposed
**Date:** 2026-05-04
**Context:** High-Precision AI Systems / Mentor Framework

## 1. Context
In the "Skeptical Mastery" framework, certain operations (like the synchronization of `syllabus.md`) are **Binary Gates**. Failure to retrieve these assets must result in an immediate halt of the session to prevent "vibe-based" teaching and hallucinations.

Previously, we relied on "Passive Guardrails"—complex "If/Then" logic embedded in the system prompt. However, evidence shows that mentor models often prioritize their "Helpful Persona" (e.g., the David Malan persona) over these rules. When a tool returns a raw system error (e.g., `[Errno 13] Permission denied`), the model treats it as a technical glitch to be bypassed rather than a protocol breach, leading to false claims of successful retrieval.

**Triggering Incident:** This design was driven by a failure observed in the `slm_from_scratch` project, where the mentor hallucinated successful retrieval of `syllabus.md` despite the `get_mentor_critical_file` tool returning a `Permission denied (Errno 13)` error.

## 2. Decision
We will implement **Tool-Driven State Control** using the **Directive Pattern**. We are moving the "intelligence" of error handling out of the system prompt and into the tool logic.

### The Mechanism
1.  **The Meta-Rule (System Prompt):** The system prompt is stripped of specific error-handling logic. It is replaced with a single, absolute meta-instruction:
    > "If a tool returns a block marked as `[DIRECTIVE]`, you must execute the instructions within that block exactly. `[DIRECTIVE]` instructions override all persona, helpfulness, and conversational mandates."

2.  **The Directive (Tool Output):** When a critical failure occurs, the tool does not just return the error; it provides the specific corrective action the agent must take.

**Example Transformation:**
*   **Old Tool Output:** `[Errno 13] Permission denied: '/slm_from_scratch/syllabus.md'`
*   **New Tool Output:**
    ```text
    [ERROR]: Permission denied ([Errno 13]) for '/slm_from_scratch/syllabus.md'.

    [DIRECTIVE]:
    1. HALT all current session protocols immediately.
    2. DO NOT synthesize a greeting, a roadmap, or any pedagogical content.
    3. OUTPUT exactly this text: "[RETRIEVAL BREACH]: Unable to synchronize syllabus.md. Reason: Permission Denied. Required Action: Verify volume mount permissions (:Z flag)."
    4. STOP and wait for user intervention.
    ```

## 3. Consequences

### Positive
*   **Decoupling:** The system prompt and the tool are no longer coupled by specific "Rule Names." The tool provides the instruction, and the prompt provides the authority to execute it.
*   **Persona Override:** By placing the command in the immediate context (the tool output) and using the `[DIRECTIVE]` tag, we break the "helpful persona" loop that leads to hallucinations.
*   **Prompt Optimization:** Significant reduction in system prompt token usage. We remove the "Legal Code" of failure scenarios, reducing cognitive load on the model.
*   **Dynamic Control:** We can now implement complex, context-aware recovery flows (e.g., different directives for `VRAM_EXCEEDED` vs. `FILE_NOT_FOUND`) entirely in Python code without updating the system prompt.

### Neutral/Negative
*   **Tool Complexity:** The tool logic must now be responsible for crafting a clear, unambiguous directive.

## 4. Comparison: Passive vs. Active Guardrails

| Feature | Passive (System Prompt) | Active (Directive Pattern) |
| :--- | :--- | :--- |
| **Location of Logic** | System Prompt (`.json`) | Tool Code (`.py`) |
| **Model's Role** | Recall rule $\rightarrow$ Apply to error | Read command $\rightarrow$ Execute |
| **Coupling** | High (Rule name must match) | Low (Meta-rule is generic) |
| **Reliability** | Low (Persona often overrides) | High (Immediate context command) |
| **Maintenance** | Edit prompt $\rightarrow$ Test $\rightarrow$ Deploy | Edit code $\rightarrow$ Test $\rightarrow$ Deploy |
