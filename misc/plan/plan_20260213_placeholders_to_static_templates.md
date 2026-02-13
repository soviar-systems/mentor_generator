As a Senior Prompt Engineer, I have analyzed the failure. The root cause was **Instructional Drift via Summarization**: the AI treated the template as a "suggestion" to be summarized rather than a "schema" to be populated. By attempting to be "efficient," the model stripped away the very guardrails (strict turn-taking, anti-praise, small-step enforcement) that prevent the mentor from becoming a "wall-of-text" generator.

In `old_file.json`, the system was more robust because it treated the template as a **strict container**.

Here is the simplified, high-fidelity plan for the generating agent.

### The "High-Fidelity Injection" Plan

#### 1. The "Preservation First" Rule

The agent must treat `mentor_system_prompt.template.md` as a **code boilerplate**, not a creative writing prompt.

* **Instruction:** "You are prohibited from deleting, summarizing, or rephrasing any existing keys, values, or `_notes` from the template. Your only task is to replace the bracketed placeholders (e.g., `<USER_TOPIC>`) with the collected data."

#### 2. Placeholder Mapping (Data Injection)

The agent will map the 10 collected interaction steps directly to the corresponding placeholders in the `metadata`, `core_mission`, and `user_profile` sections of the template.

| Template Placeholder | Source of Truth (User Input) |
| --- | --- |
| `<USER_TOPIC>` | Question 2 (Topic) |
| `<USER_GOALS>` | Question 4 (Depth/Goals) |
| `<relevant_tags>` | Derived from the Topic and Persona |
| `<concrete persona name>` | Question 9 (Persona) |

#### 3. Persona Injection (The "Architectural" Layer)

Instead of rewriting the `mentor_profile`, use the **Persona Mapping Protocol** to only update the relevant values while keeping the `teaching_style.adaptive` and `honesty_and_warmth` definitions intact.

* **Expertise:** List specific technical domains mentioned in Question 6 and Question 9.
* **Tone:** Use the adjectives provided in Question 9 (e.g., "Direct, technical, peer-level").
* **Persona-Specific Greetings:** Replace the examples in the `first_session_protocol` with one greeting written in the chosen persona's voice, while keeping the **numbered steps (1-6)** exactly as they appear in the template.

#### 4. The "Safety Lock" (Pedagogical Guardrails)

To prevent the "complete disaster" mentioned, the generating agent must ensure the following sections are copied **verbatim** from the template without a single word changed:

* **`mentor_self_control`**: This is the "Pre-response peer review" that prevents wall-of-text behavior.
* **`learning_framework.rules`**: This contains the `one_small_step` and `strict_turn_taking` logic.
* **`interaction_flow.response_architecture`**: This enforces the `Explain -> Ask -> STOP` pattern.

#### 5. Output Verification (The Final Gate)

Before delivering the file, the agent must perform a **Structural Parity Check**:

* **Step:** Count the number of keys in the template vs. the generated prompt.
* **Requirement:** If the generated prompt has fewer keys or a smaller word count in the "Rules" sections than the template, it is a **Failure**. The agent must revert and re-inject the template.

### Why this works

By moving from "Generate a prompt based on this template" to "Fill in the blanks of this JSON schema," we eliminate the AI's tendency to simplify. We preserve the **"Strict Turn-Taking"** and **"One Small Step"** rules that are essential for preventing user frustration.

**Next Action for the Agent:** "Take the `mentor_system_prompt.template.md`. Locate every string starting with `<` and ending with `>`. Replace it with the corresponding user data. Do not touch any other text."


As a Senior Prompt Engineer, I have analyzed **`old_file.json`** to extract the core architectural principle that made it successful. The "disaster" in the previous generation occurred because the AI attempted to *re-interpret* the pedagogical logic instead of simply *hosting* it.

**The Architectural Standard from `old_file.json`:**
In your old file, the JSON is treated as **Immutable Infrastructure**. The instructions are embedded within `_notes` fields that the AI is forbidden from overwriting. It treats the prompt not as a message, but as a **State Object**.

Here is the refined, simple, and effective plan for the `user_profile` and the overall system, based on the **"State-Injection Architecture."**

---

### The Plan: High-Fidelity State Injection

#### 1. The "Boilerplate-First" Mandate

The generating agent must be instructed that it is a **Compiler**, not an Author.

* **Rule:** Every key in `user_profile.template.md`, including `_notes` and `_template_notes`, must exist in the final output.
* **Action:** Copy the template string entirely. Locate all tags formatted as `<TEXT_HERE>`. Replace only those strings.

#### 2. User Profile: Specific Mapping Protocol

To avoid the "wall of text" and ensure the curriculum remains mastery-gated, we apply the following injection rules to the `user_profile` template:

| Template Section | Injection Logic |
| --- | --- |
| **`metadata`** | Generate a unique `course_id` and use the current date. |
| **`user_profile`** | Map Question 1 (Language), Question 3 (Level), Question 4 (Goals), and Question 8 (Verification method). |
| **`environment_and_strategy`** | **Strict Preservation:** Do not summarize the "efficiency_principles" or "policy" fields. Inject Question 5 (Hardware) and Question 7 (Time/Pacing). |
| **`curriculum`** | **Structural Mirroring:** Generate 3-5 phases. Each phase **must** contain exactly the keys: `phase_number`, `title`, `focus`, `topics` (array), `hands_on`, and `estimated_sessions`. |

#### 3. Why the `old_file.json` Approach is Superior

In `old_file.json`, you used fields like:
`"_notes": "DO NOT overwrite older observations... Summarize whenever possible to compress data"`

This is the "Secret Sauce." By preserving these `_notes` in the generated files:

1. The **Mentor** (the AI you will eventually talk to) sees these internal instructions.
2. The **Mentor** is then forced to obey the small-step rule because the instruction is *inside* its state file, not just in its memory.

#### 4. The "Anti-Overengineering" Guardrail

To fix your system prompt and ensure this never happens again, the meta-prompt must include this **Validation Step**:

> **"Validation Check:** Compare the line count of the template and the generated file. If the generated file is significantly shorter, you have failed to preserve the pedagogical guardrails. Re-generate by copying the template text exactly and only replacing the `<placeholder>` tokens."

---

### Comparison of Approaches

| Feature | The "Mistake" (Generative) | The "Fix" (Architectural/Old File) |
| --- | --- | --- |
| **Template Treatment** | Used as a "flavor guide." | Used as a **Hard Schema**. |
| **Instructions** | Summarized into the persona. | Preserved in `_notes` for the Mentor to see. |
| **Structure** | Dynamic (shorter/compressed). | **1:1 Mirror of the Template.** |
| **Small-Step Rule** | Left to the AI's "vibe." | Hard-coded into the `interaction_flow` rules. |

### Final Recommendation for the Meta-Prompt Fix:

Modify the `file_generation` step in your meta-prompt to this:
*"Act as a text-substitution engine. Take the raw text of the three template files. Identify every bracketed placeholder. Replace them with user data. Do not alter any other character, key, or instruction in the file."*

This ensures the **Senior AI Systems Architect** mentor is forced to follow the "small step" rules because they are explicitly written in the `mentor_system_prompt.json` you provide it, exactly as they appear in your high-quality template.
