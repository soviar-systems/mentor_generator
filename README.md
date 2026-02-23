# Mentor Generator

Mentor Generator creates a personalized AI learning mentor tailored to your language, knowledge level, goals, and constraints. It outputs a single YAML configuration file that defines your personal mentor — personality, teaching rules, curriculum, and session record format — all in one place.

> **Important notes:**
> 1. AI models can hallucinate. The system contains many checks, but there is no 100% guarantee.
> 2. Don't drag learning sessions out — change chats often to avoid context degradation.
> 3. This is an experiment, not a production-ready solution.

## Quick Start (Agent CLI)

The primary way to use Mentor Generator is the Python CLI agent.

### Prerequisites

- Python 3.10–3.13
- [uv](https://docs.astral.sh/uv/) package manager
- A Gemini API key ([get one here](https://aistudio.google.com/apikey))

### Installation

```bash
git clone https://github.com/lefthand67/mentor_generator.git
cd mentor_generator
uv sync
```

### Configuration

Set your API key as an environment variable:

```bash
export GEMINI_API_KEY="your-api-key-here"
```

Or create a global config file at `~/.mentor.generator.config.yml`:

```yaml
api_key_env: GEMINI_API_KEY
```

You can also create a local config `.mentor.generator.config.yml` in the project root to override settings per project.

### Generate a Mentor

```bash
uv run python -m agent.main
```

The agent walks you through 9 questions:

| # | Question | Example Answer |
|---|----------|----------------|
| 0 | Preferred communication language | "English", "Русский" |
| Q1 | Mentor's teaching language | "English" |
| Q2 | Topic to learn | "Python for Data Analysis", "History of Byzantium" |
| Q3 | Current experience level | "Beginner in programming but strong in math" |
| Q4 | Target depth and learning goals | "Practical how-to skills with deep understanding" |
| Q5 | Environment, tools, constraints | "Only laptop, Windows, 4 GB RAM" |
| Q6 | Specific subtopics to cover | "NumPy arrays, SQL JOIN operations" |
| Q7 | Learning strategy | DEPTH-FIRST (mastery-gated) or TIME-BOXED (deadline-driven) |
| Q8 | Mastery verification method | "Practical assignments and Socratic questioning" |
| Q9 | Mentor tone/persona | "Friendly but strict", "Like Richard Feynman" |

After you answer, the agent makes **one** LLM call, fills the template, validates the output, and writes two files:

```
output/
├── mentor_system_prompt.yml   # Your complete mentor configuration (YAML)
└── course_history             # Empty file, grows during learning
```

### CLI Options

```bash
# Full pipeline (questionnaire → API call → compile)
uv run python -m agent.main

# Skip questionnaire, reuse saved answers (re-call API)
uv run python -m agent.main --skip-collect

# Skip questionnaire + API, recompile from saved artifacts only
uv run python -m agent.main --skip-collect --skip-api
```

Answers and API responses are cached in `.mentor.generator.artifacts/` so you can iterate on the compile step without re-answering questions or spending API calls.

## How the Agent Works

The agent runs a three-stage pipeline:

```
Collect (0 API calls)  →  Create (1 API call)  →  Compile (0 API calls)
       CLI questionnaire       LLM generates           Template filling,
       gathers 9 answers       creative content         validation, YAML output
```

1. **Collect** — CLI questionnaire gathers your answers (no API calls)
2. **Create** — One LLM call generates creative content (persona, expertise, curriculum phases). The LLM returns labeled text blocks, not structured data
3. **Compile** — Deterministic code parses the response, injects it into the template, validates structure, and writes YAML

This architecture means the LLM is a **creative engine**, not a compiler. All structural decisions are made by code, eliminating template drift and format errors.

## Learning Sessions

After generating your mentor, see [agent/USAGE.md](agent/USAGE.md) for the full learning workflow — how to start sessions, continue from where you left off, and manage your course history.

## Web Chat Workflow (Legacy)

If you prefer not to install anything, you can use the original web-chat workflow:

1. Copy the contents of `web_version/mentor_generator.json`
2. Paste into a powerful AI chat (Gemini Pro, DeepSeek, Qwen3-Max)
3. Answer 9 questions interactively
4. The AI validates and outputs one YAML file
5. Save the file and create an empty `course_history`

> **Note:** The web-chat workflow is preserved for backward compatibility. The agent CLI is recommended — it produces more reliable output because structural decisions are made by code, not by the LLM.

## Project Structure

```
mentor_generator/
├── agent/                        # Python CLI (primary product)
│   ├── main.py                   # Pipeline orchestrator
│   ├── collector.py              # CLI questionnaire (0 API calls)
│   ├── creative_engine.py        # Single LLM call + parser
│   ├── template_engine.py        # Deterministic template filling
│   ├── validator.py              # Structural validation
│   ├── yaml_writer.py            # YAML output
│   ├── settings.py               # Layered config
│   ├── provider.py               # LLM provider abstraction
│   ├── templates/                # Output schema template
│   ├── USAGE.md                  # Post-generation user guide
│   └── tests/                    # Golden-file tests (0 API calls)
├── web_version/                  # Legacy web-chat workflow
│   └── mentor_generator.json     # Original meta-prompt
├── architecture/                 # ADRs, postmortems, research
├── pyproject.toml
└── CLAUDE.md
```

## Running Tests

```bash
uv run pytest agent/tests/ -v
```

All tests are offline (0 API calls) — they use golden fixtures to verify the pipeline.

## Example Projects

Real courses created with Mentor Generator:

1. [llm_from_scratch_practice](https://github.com/lefthand67/llm_from_scratch_practice)
2. [python_threading_for_ai_course](https://github.com/lefthand67/python_threading_for_ai_course)

## Pitfalls

- **Weak models:** Use top-tier AI models for learning sessions — weak models lose context quickly
- **Vague answers:** Be specific during setup — vague answers yield poor personalization
- **Hallucinations:** Cross-check mentor advice with trusted sources
- **Long sessions:** Change chats often to maintain quality

## Questions?

If you have questions or want feedback on your setup, open an issue with your configuration files and scenario.
