# ADR 260504: Decoupling Asset Manifest from System Prompts and Tool Logic

## Status
Accepted

## Context
In the Mentor system, the AI model interacts with a specialized retrieval tool to access critical assets (e.g., `syllabus.md`, `user_profile.md`). A recurring failure mode was observed where the Mentor LLM requested "phantom files"—assets it assumed existed based on probabilistic patterns or prior training—despite explicit negative constraints in the system prompt (e.g., "Do not request prerequisites.md").

The initial hardening plan proposed duplicating an `asset_manifest` (a mapping of `file` $\rightarrow$ `purpose`) in both the `system_prompt.json` and as a constant `AUTHORIZED_FILES` within the Python retrieval tool.

This approach introduced two primary risks:
1. **Synchronization Tax:** Any change to the critical asset list required simultaneous updates to a JSON configuration and Python source code.
2. **Divergence Bugs:** If the prompt and tool diverged, the LLM would request files it believed were authorized, only to be rejected by the tool, leading to confusing error loops.

## Decision
We will move the Asset Manifest from hardcoded configurations into a standalone, discoverable file: `manifest.json`.

### Implementation Details
1. **The Manifest:** A standalone JSON file acting as the single source of truth for all authorized critical assets.
2. **The Tool (The Enforcer):** The `mentor_critical_retrieval.py` tool will load `manifest.json` at runtime. It will validate all requests against this file.
3. **The System Prompt (The Protocol):** The system prompt will be stripped of the static asset list. Instead, it will define a **Communication Protocol**:
    - "Request critical assets via the retrieval tool."
    - "If a request is rejected, the tool will provide the current authorized manifest. Use this to re-align your request."
4. **Loop-Back Mechanism:** If a requested file is not in the manifest, the tool will return the full list of authorized assets as a "Protocol Directive," forcing the LLM to correct its internal state based on current reality rather than probabilistic patterns.

## Alternatives Considered

### Alternative 1: Hardcoded Manifest in Prompt and Tool
- **Description:** The original plan of mirroring the list in `system_prompt.json` and `mentor_critical_retrieval.py`.
- **Pros:** No extra file reads.
- **Cons:** Violates DRY (Don't Repeat Yourself) principle; high risk of divergence; increases system prompt pollution.

### Alternative 2: Dynamic Filesystem Scanning
- **Description:** Allowing the tool to return any file found in the designated directory.
- **Pros:** No manifest to maintain.
- **Cons:** Too permissive. Allows the LLM to discover internal files not meant for its consumption, breaking the curated pedagogical experience and increasing the risk of hallucinated dependencies.

## Consequences

### Positive
- **Maintainability:** Changes to the asset list now happen in one place (`manifest.json`).
- **Determinism:** The "Law" (Protocol) and "Reality" (Manifest) are decoupled but synchronized.
- **Prompt Efficiency:** Reduces the size of the system prompt by removing static lists.
- **Robustness:** The Loop-Back mechanism transforms tool errors into corrective training signals for the LLM.

### Negative/Risks
- **Runtime Dependency:** The tool now depends on the existence and validity of `manifest.json`.
- **Mitigation:** Implement a minimal hardcoded "Emergency Fallback" list in the Python tool to prevent total system failure if the manifest is corrupted or missing.

## Verification
Verification is achieved when:
1. The Mentor requests a "phantom file."
2. The tool rejects the request and returns the contents of `manifest.json`.
3. The Mentor acknowledges the correction and requests a valid file from the returned list.
