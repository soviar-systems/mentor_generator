# Architecture Post-Mortem: Mentor Generator v0.30.x → v0.31.0

**Date:** January 28, 2026
**Author:** vrudakov + Claude Opus 4.5
**Document Type:** Lessons Learned / Decision Record

---

## Executive Summary

The v0.30.x architecture of Mentor Generator suffered from fundamental reliability problems stemming from a monolithic design that asked LLMs to do too much decision-making. After extensive debugging and failed fixes, we performed a complete architectural overhaul based on a core insight:

> **Predictability comes from constraints, not instructions.**

This document captures the full context of what went wrong, why our fixes failed, and the reasoning behind the new architecture.

---

## Part 1: The Old Architecture (v0.30.x)

### File Structure

```
mentor_generator/
└── mentor_generator.json    # ~460 lines, everything in one file
```

### Conceptual Model

One JSON file served **two distinct purposes**:

1. **Meta-Prompt Role**: Guide an LLM through a 9-question questionnaire to collect user information
2. **Mentor Template Role**: Define the behavior rules for the generated learning mentor

The file contained:
- `meta_prompt_logic` - Questionnaire instructions
- `mentor_system_prompt_template` - Embedded 300+ line template including:
  - `mentor_profile` - Persona, tone, teaching style
  - `interaction_flow` - Dual modes (teaching vs state update)
  - `learning_framework` - Mastery-gated progression rules
  - `state_update_protocols` - Complex triggers for JSON regeneration
  - `additional_context` - User profile, progress, session logs (~80 lines of mutable state)

### State Management Design

The mentor was responsible for:
1. Teaching the user (primary function)
2. Tracking when to save state (trigger detection)
3. Deciding what state to save (content selection)
4. Outputting the complete updated JSON (~450 lines)

**Triggers for state update:**
- Explicit session end (user says "let's stop")
- Major milestone achieved (concept mastery demonstrated)
- Context limit approaching (token count > threshold)

**State update protocol:**
1. Detect trigger condition
2. Announce mode transition: "Updating your learning progress..."
3. Switch from "teaching mode" to "state update mode"
4. Output complete JSON with updated `additional_context`
5. Return to teaching mode

---

## Part 2: What Went Wrong

### Problem 1: Role Confusion

**Symptom:** LLMs would sometimes act as the meta-prompt questionnaire assistant during learning sessions, or act as the mentor during the questionnaire phase.

**Root Cause:** Both roles existed in the same file. The LLM had to understand "right now I am role X, not role Y" based on context. This is a fragile mental model.

**Example failure:**
```
User: "Let's continue from where we left off"
Mentor: "Great! Let me ask you question 3: What is your current experience level?"
```
The mentor confused "continuing a session" with "continuing the questionnaire."

**Why instructions didn't help:** We added explicit notes like "You are now the MENTOR, not the meta-prompt assistant." But instructions compete with the structure of the file itself. The LLM sees `meta_prompt_logic` right there in context and can't fully ignore it.

### Problem 2: Full JSON Regeneration

**Symptom:** State updates would have missing fields, corrupted structure, or unwanted changes to static sections.

**Root Cause:** Asking an LLM to output 450+ lines of JSON accurately is asking for trouble. Even with explicit instructions "output the COMPLETE JSON," models would:
- Truncate output
- Forget nested fields
- Subtly modify static sections (changing `teaching_style` values, etc.)
- Lose `_notes` fields that were marked "never overwrite"

**Example failure:**
```json
// Before state update
"mentor_profile": {
  "tone": ["professional", "patient", "uses analogies"],
  "teaching_style": {
    "adaptive": "stepwise, with micro-validation",
    "honesty": "Honest and objective..."
  }
}

// After state update (corrupted)
"mentor_profile": {
  "tone": "professional and patient",  // Lost array structure
  "teaching_style": "adaptive"          // Lost entire object
}
```

**Why instructions didn't help:** We added validation rules: "Verify only `metadata` and `additional_context` fields are modified." But the LLM can't actually verify its own output reliably. It generates tokens sequentially and doesn't have a diff tool.

### Problem 3: Complex Trigger Logic

**Symptom:** State updates would happen at wrong times, or not happen when needed.

**Root Cause:** We had three different trigger types with different detection mechanisms:
- Explicit session end: Parse user intent from natural language
- Milestone achieved: Evaluate if "concept mastery demonstrated"
- Context limit: Count tokens (LLMs can't actually do this)

**Example failure - token counting:**
```
"context_limit_approaching": {
  "trigger_condition": "IF current token count > 60000 THEN set CONTEXT_SAVE_REQUIRED=TRUE"
}
```
LLMs cannot count tokens. They would either:
- Never trigger (thinking "I'm probably under 60k")
- Trigger too early (being overly cautious)
- Trigger randomly (just guessing)

**Example failure - milestone detection:**
```
User: "So basically, backprop is just chain rule applied backwards through the network"
Mentor: "Excellent! You've demonstrated mastery. Let me update your progress..."
```
Was that really mastery? The mentor couldn't reliably distinguish between:
- Genuine understanding
- Parroting back what was just explained
- Partial understanding with gaps

### Problem 4: Dual-Mode Cognitive Overhead

**Symptom:** Mode transitions were awkward, sometimes incomplete, or confusing to users.

**Root Cause:** The concept of "teaching mode" vs "state update mode" required the LLM to:
1. Track which mode it's in
2. Know when to transition
3. Announce transitions clearly
4. Actually behave differently in each mode
5. Return to the correct mode after state update

**Example failure:**
```
Mentor: "Let me update your progress..."
Mentor: [outputs JSON]
Mentor: "Now, where were we? Let's continue with backpropagation."
User: "We just finished backpropagation. You said we're moving to gradient descent."
Mentor: "Ah yes, of course. Let's discuss backpropagation gradients..."
```
The mode transition disrupted the LLM's context about the actual lesson content.

**Why "transparency" didn't help:** We added explicit messaging: "Announce transition clearly." But the act of transitioning itself caused context disruption. The LLM's attention shifted from "lesson content" to "administrative task" and didn't fully return.

### Problem 5: Unbounded Decision Space

**Symptom:** Different runs produced different state outputs even for identical sessions.

**Root Cause:** Instructions like these left too much to interpretation:
- "Summarize the session highlights"
- "Keep only relevant learning patterns"
- "Compress older sessions into summary_digest"

**Example - same session, different outputs:**

Run 1:
```json
"session_summary": "Covered backpropagation. User understood chain rule."
```

Run 2:
```json
"session_summary": "In this session, we explored the mathematical foundations of backpropagation, specifically focusing on how the chain rule from calculus enables gradient computation through neural network layers. The student demonstrated understanding by correctly explaining the flow of gradients."
```

Run 3:
```json
"session_summary": "Backprop done. Moving to gradient descent next."
```

All three are "correct" per the instructions, but the inconsistency made session continuity unreliable.

---

## Part 3: Failed Fix Attempts

### Attempt 1: More Detailed Instructions

**Hypothesis:** If we specify exactly what to include, the LLM will be more consistent.

**Implementation:** Added detailed rules like:
```json
"content_requirements": "Always output the complete, updated JSON block, including all static fields (e.g., core_mission, learning_framework) and the new additional_context."
```

**Result:** Failed. More instructions added more cognitive load. The LLM would try to follow all rules and fail at some of them. Instructions compete with each other.

**Lesson:** Instructions don't scale. Each additional instruction increases the probability of failure somewhere else.

### Attempt 2: Validation Checkpoints

**Hypothesis:** If the LLM validates its output before generating, it will catch errors.

**Implementation:** Added pre-update checks:
```json
"pre_update_check": [
  "Verify only `metadata` and `additional_context` fields are modified",
  "Confirm metadata timestamps are updated",
  "Ensure learning continuity is maintained"
]
```

**Result:** Failed. LLMs cannot reliably validate their own output. They generate tokens sequentially without the ability to diff against previous state. The "validation" became a ritual that the LLM performed verbally without actually catching errors.

**Lesson:** Self-validation is theater. LLMs will say "I have verified X" without actually verifying X.

### Attempt 3: Simpler Triggers

**Hypothesis:** If we reduce trigger complexity, state updates will be more reliable.

**Implementation:** Tried to simplify to just "session end" trigger.

**Result:** Partially worked, but the underlying problem remained: the LLM still had to output 450 lines correctly.

**Lesson:** Simplifying triggers helped, but didn't address the core regeneration problem.

### Attempt 4: Compression Rules

**Hypothesis:** If we compress old sessions into a digest, the state will be smaller and more manageable.

**Implementation:** Added:
```json
"compression_rules": [
  "summarize entire learning history into summary_digest",
  "merge consecutive minor updates",
  "keep only relevant learning patterns"
]
```

**Result:** Failed. "Relevant" is subjective. Information was lost unpredictably. Users would resume sessions and the mentor would have forgotten important context that was "compressed away."

**Lesson:** Lossy compression by LLM judgment is unreliable. You can't predict what will be lost.

---

## Part 4: The Breakthrough Insight

After multiple failed fixes, we stepped back and asked: **Why do traditional software systems not have these problems?**

Answer: Traditional systems don't ask the database to "decide what to save." They have:
- **Fixed schemas**: The structure is defined, not generated
- **Append-only logs**: New records don't modify old ones
- **Separation of concerns**: Different components do different things

The LLM was failing because we asked it to be:
- A teacher (content generation)
- A state machine (mode tracking)
- A database (state storage decisions)
- A compression algorithm (history summarization)
- A validator (output verification)

**Core insight:**
> **Predictability comes from constraints, not instructions.**

Instead of instructing the LLM what to do, we should constrain what it CAN do. The template IS the constraint.

---

## Part 5: The New Architecture (v0.31.0)

### Design Principles

1. **Separation of Concerns**: Different roles in different files
2. **Template-First Output**: Fill exact templates, don't decide content
3. **Immutable History**: Append-only, never modify existing files
4. **Minimal Output**: Session file is ~30 lines, not 450
5. **No Decision Points**: Every field has a clear, non-interpretive definition

### File Structure

```
mentor_generator/
├── mentor_generator.json              # Meta-prompt ONLY
├── templates/
│   ├── mentor_system_prompt.template  # Mentor behavior rules
│   └── course_config.template         # User profile structure

user_course/                           # Generated per user
├── mentor_system_prompt               # Static, never changes
├── course_config                      # Semi-static
└── sessions/
    ├── session_1                      # Immutable
    ├── session_2                      # Immutable
    └── ...
```

### How It Solves Each Problem

**Problem 1: Role Confusion**
- Solution: Meta-prompt and mentor are literally different files
- The LLM only sees one role at a time
- No possibility of confusion

**Problem 2: Full JSON Regeneration**
- Solution: Mentor only outputs session file (~30 lines)
- Static rules never regenerated
- Small output = fewer errors

**Problem 3: Complex Trigger Logic**
- Solution: Single trigger - session end
- No token counting
- No milestone detection
- User explicitly ends session or natural conclusion

**Problem 4: Dual-Mode Overhead**
- Solution: No modes
- Mentor teaches, then outputs session file
- No transitions, no mode tracking

**Problem 5: Unbounded Decision Space**
- Solution: Exact template with defined fields
- Every field has explicit meaning
- No "summarize however you want"

### Session File Template

```json
{
  "session_number": 5,
  "timestamp": "2026-01-28T15:30:00Z",
  "duration_approx": "45 minutes",

  "position": {
    "phase": "Phase 2: Intermediate Concepts",
    "topic_covered": "Backpropagation fundamentals",
    "next_topic": "Implementing gradient descent",
    "phase_progress": "3 of 7 topics completed"
  },

  "mastery": {
    "concepts_validated": ["chain rule application"],
    "concepts_struggling": [],
    "validation_method": "User explained in own words"
  },

  "session_summary": "2-3 sentences max",
  "learning_observations": ["array of observations"],
  "resources_suggested": [{"topic": "", "resource": "", "type": ""}],
  "mentor_notes": "Brief notes for next session"
}
```

Every field is:
- Explicitly named (no interpretation needed)
- Bounded in scope (not "summarize everything")
- Observable (mentor can fill from session context)

### Why Immutable Session Files

Old approach: One `additional_context` block that gets updated
- Risk: Corruption destroys all history
- Risk: Compression loses information unpredictably

New approach: Each session creates new file, old files never touched
- Benefit: Can't corrupt what you don't modify
- Benefit: Full history preserved
- Benefit: Clear audit trail
- Trade-off: More files to manage

The trade-off is acceptable because:
1. Users already manage multiple files in most workflows
2. File management is a solved UX problem (folders, naming)
3. Reliability gain far outweighs convenience cost

---

## Part 6: General Principles Extracted

### Principle 1: Constrain Output, Don't Instruct It

❌ Bad: "Output a summary of the session including key concepts, progress, and notes"
✅ Good: "Fill this exact template: {session_summary: '2-3 sentences', concepts_validated: [array]}"

Instructions are suggestions. Templates are constraints.

### Principle 2: Separate Roles Into Separate Contexts

❌ Bad: One file with meta-prompt + mentor + state management
✅ Good: Each role in its own file, loaded separately

LLMs can't reliably switch roles within a context. They can easily adopt a single role from a dedicated file.

### Principle 3: Minimize LLM Output Size

❌ Bad: Output 450 lines of JSON
✅ Good: Output 30 lines of JSON

Every token is a chance for error. Smaller output = fewer errors.

### Principle 4: Make Operations Append-Only

❌ Bad: "Update the existing state"
✅ Good: "Create a new state file"

Modification requires the LLM to understand previous state AND correctly transform it. Append only requires generating new content.

### Principle 5: Eliminate Judgment Calls

❌ Bad: "Keep only relevant learning patterns"
✅ Good: "List the concepts where user demonstrated understanding"

"Relevant" is a judgment call. "Demonstrated understanding" is observable.

### Principle 6: Don't Ask LLMs to Count or Measure

❌ Bad: "If token count > 60000, trigger save"
✅ Good: "At session end, output session file"

LLMs cannot count tokens, estimate context usage, or measure quantities reliably.

### Principle 7: Self-Validation is Theater

❌ Bad: "Before outputting, verify that all fields are correct"
✅ Good: Use a template that only accepts correct structure

LLMs will perform "validation" rituals without actually validating. Structure the output so invalid output is impossible.

### Principle 8: Explicit Over Implicit State

❌ Bad: "Continue from where we left off" (LLM infers state)
✅ Good: "Read session_3.json, continue from next_topic field"

Implicit state relies on LLM memory and inference. Explicit state is read from files.

---

## Part 7: What We Would Do Differently

### If Starting Over

1. **Start with file separation from day one**
   - Meta-prompt and mentor should never have been in the same file
   - The convenience of "one file" wasn't worth the reliability cost

2. **Design for minimal output from the start**
   - The 450-line full regeneration was a design smell
   - Should have asked: "What's the minimum the LLM needs to output?"

3. **Test with adversarial conditions earlier**
   - We found problems when users had long sessions
   - Should have stress-tested with 20+ turn conversations early

4. **Question every LLM decision point**
   - Every time the prompt says "decide," "evaluate," "determine" → red flag
   - Ask: "Can this be a template/lookup instead of a decision?"

### What Worked Well

1. **Mastery-gated progression** - Core pedagogical principle remains valid
2. **Persona mapping protocol** - Translating user preferences into instructions works
3. **Strict turn-taking** - "Wait for user response" rule is effective
4. **Emergency brake** - Confusion detection and recovery is valuable

These features survived the refactor because they're about teaching behavior, not state management.

---

## Part 8: Metrics for Success (v0.31.0)

How we'll know if the new architecture works:

1. **Session file consistency**: Same session should produce structurally identical files across runs
2. **No corrupted history**: Old session files remain unchanged
3. **Correct resumption**: Mentor correctly identifies starting point from session files
4. **Role clarity**: No instances of meta-prompt behavior during learning sessions
5. **User feedback**: Reduced reports of "mentor forgot what we covered"

---

## Appendix A: Code Comparison

### Old State Update (v0.30.x)

```json
"state_update_protocols": {
  "json_update_protocol": {
    "json_generation_triggers": {
      "explicit_session_end": [...],
      "major_milestone_achieved": {
        "milestones": ["concept_mastery_demonstrated", "topic_completion", ...]
      },
      "context_limit_approaching": {
        "trigger_condition": "IF current token count > 60000 THEN set CONTEXT_SAVE_REQUIRED=TRUE"
      }
    },
    "rules": {
      "content_requirements": "Always output the complete, updated JSON block, including all static fields..."
    }
  }
}
```

### New Session Output (v0.31.0)

```json
"session_output_protocol": {
  "trigger": "Session end (user signals or natural conclusion)",
  "action": "Fill exact template below",
  "template": { /* 30 lines, every field defined */ },
  "rules": [
    "Increment session_number from last session",
    "Never modify existing session files",
    "Output complete template even if some fields empty"
  ]
}
```

The difference: Old version has triggers, conditions, flags, requirements. New version has one trigger and a template.

---

## Appendix B: User Workflow Comparison

### Old Workflow

1. Run meta-prompt, get one JSON file
2. Start learning session with that JSON
3. Learn...
4. Mentor detects trigger, announces mode transition
5. Mentor outputs 450-line updated JSON
6. User copies and replaces old JSON
7. Start new chat, paste updated JSON
8. Hope nothing was corrupted

### New Workflow

1. Run meta-prompt, get TWO files (mentor_system_prompt + course_config)
2. Start learning session with both files attached
3. Learn...
4. End session, mentor outputs 30-line session_1 file
5. User saves as new file (doesn't replace anything)
6. Start new chat, attach all files (prompt + config + session_1)
7. Mentor reads files, continues from session_1.next_topic

The difference: No replacement, no corruption risk, clear file management.

---

## Appendix C: Key Quotes to Remember

> "Predictability comes from constraints, not instructions."

> "Instructions don't scale. Each additional instruction increases the probability of failure somewhere else."

> "Self-validation is theater. LLMs will say 'I have verified X' without actually verifying X."

> "Every token is a chance for error. Smaller output = fewer errors."

> "The template IS the constraint. No decisions = no confusion."

---

## Document History

- 2026-01-28: Initial version created during v0.31.0 refactor
