# Mentor Generator

Mentor Generator creates a personalized AI learning mentor tailored to your language, knowledge level, goals, and constraints.

In a 5-minute conversation, it generates three configuration files that define your personal mentor. These files accompany you throughout your learning journey, tracking progress across sessions.

> **Important notes:**
> 1. AI models can hallucinate. The prompts contain many checks, but there is no 100% guarantee.
> 2. Don't drag sessions out - change chats often to avoid context degradation.
> 3. This is an experiment, not a production-ready solution.

## Quick Start

1. Copy the contents of `mentor_generator.json`
2. Paste into a powerful AI chat (see model recommendations below)
3. Answer 9 questions about your learning goals
4. Receive three files: `mentor_system_prompt`, `user_profile`, and `session_template`
5. Create an empty `course_history` file
6. Start learning sessions by attaching these files to new chats

> **Model recommendations:** Gemini Pro, Gemini Flash, DeepSeek, and Qwen3-Max start working immediately. ChatGPT often reads the file verbatim and asks what to do - not recommended.

## The File System

### Generated Files (You Create Once)

| File | Purpose | When to Modify |
|------|---------|----------------|
| `mentor_system_prompt` | Mentor personality, teaching rules, behavior | Never |
| `user_profile` | Your profile, constraints, curriculum | Rarely (only if constraints change) |
| `session_template` | Format for session records | Never |

### Course History (Grows During Learning)

| File | Purpose | How It Works |
|------|---------|--------------|
| `course_history` | All session records in one file | Append new record after each session |

**Key principle:** Session records are never modified. Each session appends a new record.

## Learning Workflow

### Starting a Session

1. Open a **new chat** with your AI
2. Attach `mentor_system_prompt`, `user_profile`, and `session_template`
3. Attach `course_history` (from session 2 onwards)
4. Say "Let's continue" or "Let's start"

The mentor reads all files, synthesizes your history, and continues from where you left off.

### Ending a Session

1. Signal session end ("Let's stop here", "End session", or reach a natural conclusion)
2. Mentor outputs a new session record
3. Append this record to your `course_history` file

### Why New Chats?

AI chats have context limits. Starting fresh with your files attached gives the mentor full context without old conversation clutter degrading quality.

## Answering the Questions

The meta-prompt asks 9 questions. Answer clearly and specifically - vague answers yield poor personalization.

| Question | How to Answer |
|----------|---------------|
| Language | "English", "Русский", or any language |
| Topic | "Python for Data Analysis", "History of Byzantium" |
| Experience Level | "Beginner in programming but strong in math" |
| Learning Goals | "Practice through examples and conceptual clarity" |
| Constraints | "Only laptop, Windows, 4 GB RAM" |
| Depth | "Medium tech level, focus on reasoning" |
| Subtopics | "NumPy arrays, SQL JOIN operations" |
| Time/Strategy | "DEPTH-FIRST, 1 hour on 3 weekdays" or "TIME-BOXED, finish by March" |
| Mentor Tone | "Friendly but strict", "Like Richard Feynman" |

## Sharing Your Mentor

The separation of files enables sharing:

- Share your `mentor_system_prompt` with others learning the same topic
- Each person creates their own `user_profile` and `course_history`
- Same teaching style, personalized per user

## File Format

Files are shown in JSON, but the content can be converted to YAML, Markdown, or plain text. The structure matters, not the format.

## Migration from v0.30.x

If you have an existing monolithic JSON from previous versions:

1. **Recommended:** Start fresh with the new system
2. **Manual migration:** Extract relevant sections into the new file structure
3. Your learning progress from old sessions cannot be automatically migrated

## Folder Structure

```
my_course/
├── mentor_system_prompt     # Attach every session
├── user_profile             # Attach every session
├── session_template         # Attach every session
└── course_history           # Append-only, attach from session 2+
```

## Example Projects

Real courses created with Mentor Generator:

1. [llm_from_scratch_practice](https://github.com/lefthand67/llm_from_scratch_practice)
2. [python_threading_for_ai_course](https://github.com/lefthand67/python_threading_for_ai_course)

## Pitfalls

- **Weak models:** Always use top-tier AI models - weak models lose context quickly
- **Vague answers:** Be specific in your responses during setup
- **Hallucinations:** Cross-check mentor advice with trusted sources
- **Long sessions:** Change chats often to maintain quality

## Questions?

If you have questions or want feedback on your setup, open an issue with your configuration files and scenario.
