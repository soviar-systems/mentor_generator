"""Structural validation — real checks, not theater.

Compares the filled output against the original template to catch
missing keys, unfilled placeholders, and dropped guidance fields.
"""

from __future__ import annotations

import logging
import re

from agent.template_engine import RUNTIME_TEMPLATE_KEYS

logger = logging.getLogger(__name__)

_PLACEHOLDER_RE = re.compile(r"<[^>]+>")

REQUIRED_TOP_LEVEL_KEYS = [
    "_template_notes", "metadata", "core_mission", "pedagogical_principles",
    "mentor_profile", "mentor_self_control", "user_profile",
    "environment_and_strategy", "curriculum", "course_history_protocol",
    "session_protocols", "interaction_flow", "learning_framework",
    "context_management", "session_output_protocol",
]


def validate(output: dict, template: dict) -> list[str]:
    """Validate filled output against template. Returns list of errors."""
    errors: list[str] = []

    _check_top_level_keys(output, errors)
    _check_no_placeholders(output, errors)
    _check_underscore_fields(output, template, errors)
    _check_curriculum(output, errors)
    _check_pacing(output, errors)

    if errors:
        logger.warning("Validation found %d errors:", len(errors))
        for err in errors:
            logger.warning("  %s", err)
    else:
        logger.info("Validation passed — 0 errors")

    return errors


def _check_top_level_keys(output: dict, errors: list[str]) -> None:
    """Check all 15 required top-level keys are present."""
    for key in REQUIRED_TOP_LEVEL_KEYS:
        if key not in output:
            errors.append(f"Missing top-level key: {key}")
            logger.error("Missing top-level key: %s", key)

    extra = set(output.keys()) - set(REQUIRED_TOP_LEVEL_KEYS)
    if extra:
        logger.debug("Extra top-level keys (OK): %s", extra)


def _check_no_placeholders(obj: object, errors: list[str], path: str = "") -> None:
    """Check no <placeholder> markers remain in output.

    Skips keys in RUNTIME_TEMPLATE_KEYS — those are runtime templates
    filled by the mentor AI during sessions, not by our compiler.
    """
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in RUNTIME_TEMPLATE_KEYS:
                continue
            _check_no_placeholders(value, errors, f"{path}.{key}")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _check_no_placeholders(item, errors, f"{path}[{i}]")
    elif isinstance(obj, str) and _PLACEHOLDER_RE.search(obj):
        errors.append(f"Unfilled placeholder at {path}: {obj}")


def _check_underscore_fields(
    output: dict, template: dict, errors: list[str], path: str = "",
) -> None:
    """Check all _-prefixed keys from template are preserved in output."""
    if not isinstance(template, dict) or not isinstance(output, dict):
        return

    for key, value in template.items():
        if key.startswith("_"):
            if key not in output:
                errors.append(f"Dropped guidance field: {path}.{key}")
                logger.error("Dropped guidance field: %s.%s", path, key)

        # Recurse into nested dicts
        if isinstance(value, dict) and key in output:
            _check_underscore_fields(output[key], value, errors, f"{path}.{key}")


def _check_curriculum(output: dict, errors: list[str]) -> None:
    """Check curriculum has phases with required fields."""
    curriculum = output.get("curriculum", {})
    phases = curriculum.get("phases", [])

    if not phases:
        errors.append("curriculum.phases is empty — no phases generated")
        return

    required_phase_keys = ["phase_number", "title", "focus", "topics",
                           "hands_on", "estimated_sessions"]
    for i, phase in enumerate(phases):
        for key in required_phase_keys:
            if key not in phase:
                errors.append(f"curriculum.phases[{i}] missing key: {key}")

    logger.debug("Curriculum validated: %d phases", len(phases))


def _check_pacing(output: dict, errors: list[str]) -> None:
    """Check pacing.choice is a valid strategy."""
    env = output.get("environment_and_strategy", {})
    pacing = env.get("pacing", {})
    choice = pacing.get("choice", "")

    if choice not in ("DEPTH-FIRST", "TIME-BOXED"):
        errors.append(f"Invalid pacing.choice: '{choice}' (expected DEPTH-FIRST or TIME-BOXED)")
