"""Golden-file integration test — 0 API calls.

Tests the compile stage: parse creative response → fill template → validate → YAML.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from agent.creative_engine import parse_creative_response
from agent.template_engine import RUNTIME_TEMPLATE_KEYS, fill_template, load_template
from agent.validator import validate

FIXTURES = Path(__file__).parent / "fixtures"


def _load_mock_answers():
    """Load mock answers from fixture file."""
    with open(FIXTURES / "mock_answers.yml", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    from agent.collector import UserAnswers
    answers = UserAnswers()
    for key, value in data.items():
        if hasattr(answers, key):
            setattr(answers, key, str(value))
    return answers


def _load_mock_creative_response() -> str:
    with open(FIXTURES / "mock_creative_response.txt", encoding="utf-8") as f:
        return f.read()


def test_parse_creative_response():
    """Creative response parser produces all required fields."""
    text = _load_mock_creative_response()
    payload = parse_creative_response(text)

    assert payload.persona_name == "Senior Dev Alex"
    assert len(payload.expertise) >= 3
    assert len(payload.tone) >= 2
    assert payload.role_specifics != ""
    assert payload.greeting_first != ""
    assert payload.greeting_continuation != ""
    assert payload.core_mission != ""
    assert len(payload.curriculum_phases) >= 3
    assert len(payload.tags) >= 3

    # Check curriculum structure
    for phase in payload.curriculum_phases:
        assert phase.phase_number > 0
        assert phase.title != ""
        assert len(phase.topics) >= 2


def test_fill_template_no_placeholders():
    """Filled template has no remaining <placeholder> markers."""
    answers = _load_mock_answers()
    text = _load_mock_creative_response()
    payload = parse_creative_response(text)
    template = load_template()

    output = fill_template(template, answers, payload)

    # Walk entire output looking for <...> strings
    remaining = _find_placeholders(output)
    assert remaining == [], f"Unfilled placeholders: {remaining}"


def test_validate_passes():
    """Filled template passes all validation checks."""
    answers = _load_mock_answers()
    text = _load_mock_creative_response()
    payload = parse_creative_response(text)
    template = load_template()

    output = fill_template(template, answers, payload)
    errors = validate(output, template)

    assert errors == [], f"Validation errors: {errors}"


def test_yaml_roundtrip():
    """Filled template survives YAML dump→load roundtrip."""
    answers = _load_mock_answers()
    text = _load_mock_creative_response()
    payload = parse_creative_response(text)
    template = load_template()

    output = fill_template(template, answers, payload)

    yaml_str = yaml.dump(output, sort_keys=False, allow_unicode=True,
                         default_flow_style=False)
    reloaded = yaml.safe_load(yaml_str)

    # All 15 top-level keys survive
    for key in output:
        assert key in reloaded, f"Key lost in YAML roundtrip: {key}"

    # Curriculum phases survive
    assert len(reloaded["curriculum"]["phases"]) == len(output["curriculum"]["phases"])


def test_template_preserves_underscore_fields():
    """All _-prefixed guidance fields from template are in output."""
    answers = _load_mock_answers()
    text = _load_mock_creative_response()
    payload = parse_creative_response(text)
    template = load_template()

    output = fill_template(template, answers, payload)

    underscore_keys = _collect_underscore_keys(template)
    output_keys = _collect_underscore_keys(output)

    missing = underscore_keys - output_keys
    assert missing == set(), f"Dropped guidance fields: {missing}"


# --- Helpers ---

def _find_placeholders(obj, path="") -> list[str]:
    import re
    pattern = re.compile(r"<[^>]+>")
    found = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in RUNTIME_TEMPLATE_KEYS:
                continue
            found.extend(_find_placeholders(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            found.extend(_find_placeholders(item, f"{path}[{i}]"))
    elif isinstance(obj, str) and pattern.search(obj):
        found.append(f"{path}: {obj}")
    return found


def _collect_underscore_keys(obj, path="") -> set[str]:
    keys = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.startswith("_"):
                keys.add(f"{path}.{k}")
            if isinstance(v, dict):
                keys.update(_collect_underscore_keys(v, f"{path}.{k}"))
    return keys
