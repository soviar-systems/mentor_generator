"""Template Engine — deterministic placeholder injection.

Reads the template from agent/templates/mentor_system_prompt.template.json.
Replaces ONLY <placeholder> values with user answers + creative payload.
Every other value passes through verbatim — the LLM never touches this template.
"""

from __future__ import annotations

import copy
import json
import logging
import re
import uuid
from datetime import date

from agent.collector import UserAnswers
from agent.creative_engine import CreativePayload
from agent.settings import settings

logger = logging.getLogger(__name__)

_PLACEHOLDER_RE = re.compile(r"<[^>]+>")

# Keys whose subtrees contain <...> markers that are NOT compile-time
# placeholders. These are runtime templates filled by the mentor AI
# during learning sessions. Imported by validator.py and tests.
RUNTIME_TEMPLATE_KEYS = frozenset({"session_record_template"})


def load_template() -> dict:
    """Load the mentor_system_prompt template from disk."""
    template_path = settings["template_path"]
    logger.info("Loading template from %s", template_path)

    with open(template_path, encoding="utf-8") as f:
        template = json.load(f)

    logger.info("Template loaded: %d top-level keys", len(template))
    logger.debug("Top-level keys: %s", list(template.keys()))
    return template


def fill_template(
    template: dict,
    answers: UserAnswers,
    payload: CreativePayload,
) -> dict:
    """Fill template placeholders with user answers and creative payload.

    Returns a new dict — the original template is not modified.
    Every placeholder path is explicit. If the template adds a new
    placeholder, this function must be updated to fill it.
    """
    logger.info("Filling template placeholders")
    output = copy.deepcopy(template)

    # --- metadata ---
    meta = output["metadata"]
    meta["course_id"] = str(uuid.uuid4())[:8]
    meta["created"] = date.today().isoformat()
    meta["topic"] = answers.topic
    meta["tags"] = payload.tags
    logger.debug("metadata: course_id=%s, topic=%s", meta["course_id"], meta["topic"])

    # --- core_mission ---
    output["core_mission"] = payload.core_mission
    logger.debug("core_mission filled")

    # --- mentor_profile ---
    profile = output["mentor_profile"]
    profile["persona_name"] = payload.persona_name
    profile["expertise"] = payload.expertise
    profile["tone"] = payload.tone
    profile["teaching_style"]["role_specifics"] = payload.role_specifics
    logger.debug("mentor_profile: persona=%s", payload.persona_name)

    # --- user_profile ---
    user = output["user_profile"]
    user["user_language"] = answers.mentor_language
    user["initial_assessment"]["level"] = _assess_level(answers.experience_level)
    user["initial_assessment"]["description"] = answers.experience_level
    user["professional_skills"] = _split_items(answers.environment)
    user["learning_goals"] = _split_items(answers.learning_goals)
    user["depth_preference"] = _infer_depth(answers.learning_goals)
    logger.debug("user_profile: level=%s, depth=%s",
                 user["initial_assessment"]["level"], user["depth_preference"])

    # --- environment_and_strategy ---
    env = output["environment_and_strategy"]
    env["available_resources"] = answers.environment
    env["constraints"] = answers.environment
    env["pacing"]["choice"] = answers.strategy
    env["pacing"]["user_time_input"] = answers.time_input
    logger.debug("environment_and_strategy: strategy=%s", answers.strategy)

    # --- curriculum ---
    output["curriculum"]["phases"] = [
        {
            "phase_number": phase.phase_number,
            "title": phase.title,
            "focus": phase.focus,
            "topics": phase.topics,
            "hands_on": phase.hands_on,
            "estimated_sessions": phase.estimated_sessions,
        }
        for phase in payload.curriculum_phases
    ]
    output["curriculum"]["subtopics_requested"] = _split_items(answers.subtopics)
    logger.debug("curriculum: %d phases", len(payload.curriculum_phases))

    # --- session_protocols: greeting texts ---
    first = output["session_protocols"]["first_session_protocol"]
    first["welcome_message"]["greeting_text"] = payload.greeting_first

    subseq = output["session_protocols"]["subsequent_session_protocol"]
    subseq["continuation_greeting"]["greeting_text"] = payload.greeting_continuation
    logger.debug("session greeting texts filled")

    # --- interaction_flow: persona_adaptation ---
    output["interaction_flow"]["emergency_brake_rules"]["persona_adaptation"] = (
        payload.persona_adaptation
    )
    logger.debug("persona_adaptation filled")

    # --- Post-fill verification ---
    remaining = _find_remaining_placeholders(output)
    if remaining:
        logger.warning("Unfilled placeholders remain (%d):", len(remaining))
        for path in remaining:
            logger.warning("  %s", path)
    else:
        logger.info("All placeholders filled — 0 remaining")

    return output


def _find_remaining_placeholders(obj: object, path: str = "") -> list[str]:
    """Walk the output and find any remaining <placeholder> values.

    Skips keys in RUNTIME_TEMPLATE_KEYS — those are runtime templates
    filled by the mentor AI during sessions, not by our compiler.
    """
    found: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in RUNTIME_TEMPLATE_KEYS:
                continue
            found.extend(_find_remaining_placeholders(value, f"{path}.{key}"))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            found.extend(_find_remaining_placeholders(item, f"{path}[{i}]"))
    elif isinstance(obj, str) and _PLACEHOLDER_RE.search(obj):
        found.append(f"{path}: {obj}")
    return found


def _assess_level(experience: str) -> str:
    """Map experience description to beginner/intermediate/advanced."""
    low = experience.lower()
    if any(w in low for w in ("beginner", "начинающ", "новичок", "zero", "no experience")):
        return "beginner"
    if any(w in low for w in ("advanced", "expert", "profession", "senior", "продвинут")):
        return "advanced"
    return "intermediate"


def _infer_depth(goals: str) -> str:
    """Infer depth preference from learning goals."""
    low = goals.lower()
    if any(w in low for w in ("overview", "broad", "general", "обзор")):
        return "overview"
    if any(w in low for w in ("expert", "deep", "master", "глубок")):
        return "expert"
    if any(w in low for w in ("hands-on", "practical", "практич")):
        return "hands-on"
    return "intermediate"


def _split_items(text: str) -> list[str]:
    """Split a comma/semicolon-separated string into a list."""
    if not text:
        return []
    items = re.split(r"[,;]\s*", text)
    return [item.strip() for item in items if item.strip()]
