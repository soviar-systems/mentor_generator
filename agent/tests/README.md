# Tests — Developer Guide

## Quick Start

```bash
uv run pytest agent/tests/ -v
```

All tests run offline — **0 API calls, 0 network access**.

## Architecture

The tests validate the **compile stage** of the pipeline:

```
mock_answers.yml ─┐
                  ├─→ parse → fill template → validate → YAML
mock_creative_response.txt ─┘
```

This mirrors the real pipeline's compile stage (`main.py --skip-collect --skip-api`), but with fixture files instead of real artifacts.

### What is NOT tested here

- **Collect stage** — interactive CLI input (`collector.py`). No stdin mocking.
- **Create stage** — LLM API call (`creative_engine.generate_creative`). Would need a real API key.
- **End-to-end** — Run `python -m agent.main` manually with a real API key for full pipeline validation.

## Test Cases

| Test | What it validates |
|------|-------------------|
| `test_parse_creative_response` | Parser extracts all 10 labeled sections from LLM output text |
| `test_fill_template_no_placeholders` | All compile-time `<placeholder>` markers are filled |
| `test_validate_passes` | Structural validator returns 0 errors on filled output |
| `test_yaml_roundtrip` | `yaml.dump → yaml.safe_load` preserves all keys and phases |
| `test_template_preserves_underscore_fields` | All `_`-prefixed guidance fields survive the pipeline |

## Fixtures

Located in `agent/tests/fixtures/`:

### `mock_answers.yml`

Simulates user answers from the collect stage. Maps directly to `UserAnswers` dataclass fields. To modify: keep all fields present, values are strings.

### `mock_creative_response.txt`

Simulates raw LLM output from the create stage. Uses the labeled text block format that `parse_creative_response()` expects:

```
PERSONA_NAME:
<value>

EXPERTISE:
<line per item>

CURRICULUM:

PHASE 1: <title>
FOCUS: <text>
TOPICS:
- <topic>
HANDS_ON: <text>
SESSIONS: <range>
```

All 10 section labels must be present: `PERSONA_NAME`, `EXPERTISE`, `TONE`, `ROLE_SPECIFICS`, `PERSONA_ADAPTATION`, `GREETING_FIRST`, `GREETING_CONTINUATION`, `CORE_MISSION`, `TAGS`, `CURRICULUM`.

## Runtime vs Compile-Time Placeholders

The template contains two kinds of `<...>` markers:

- **Compile-time** — filled by the agent from user answers + LLM output (e.g., `<topic>`, `<persona_name>`). Tests verify these are all filled.
- **Runtime** — filled by the mentor AI during learning sessions (everything inside `session_record_template`). Tests skip these.

The single source of truth is `RUNTIME_TEMPLATE_KEYS` in `agent/template_engine.py`. Both `validator.py` and the tests import it from there — no duplication.

## Adding a New Test

1. If the test needs new fixture data, add files to `fixtures/`.
2. Use the existing `_load_mock_answers()` and `_load_mock_creative_response()` helpers.
3. If testing a new module, import it and follow the pattern of loading fixtures → calling the function → asserting the result.
4. Keep tests offline — no API calls, no network, no file writes outside `/tmp`.

## Replacing Fixtures with Real Artifacts

After a successful `python -m agent.main` run, real artifacts are saved in `.mentor.generator.artifacts/`:

```
.mentor.generator.artifacts/
├── answers.yml
└── creative_response.txt
```

These can be copied to `fixtures/` to replace the mock data:

```bash
cp .mentor.generator.artifacts/answers.yml agent/tests/fixtures/mock_answers.yml
cp .mentor.generator.artifacts/creative_response.txt agent/tests/fixtures/mock_creative_response.txt
```

Then re-run tests to verify the real data passes all checks.
