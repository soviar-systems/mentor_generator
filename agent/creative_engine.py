"""Creative Engine — single LLM call for all judgment work.

The LLM produces labeled text blocks. Code parses them into structured data.
The LLM never generates JSON — it only generates content.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from agent.collector import UserAnswers
from agent.provider import LLMProvider
from agent.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class CurriculumPhase:
    """One phase of the generated curriculum."""

    phase_number: int
    title: str
    focus: str
    topics: list[str]
    hands_on: str
    estimated_sessions: str


@dataclass
class CreativePayload:
    """Everything the LLM generates. Template engine consumes this."""

    persona_name: str
    expertise: list[str]
    tone: list[str]
    role_specifics: str
    persona_adaptation: str
    greeting_first: str
    greeting_continuation: str
    core_mission: str
    curriculum_phases: list[CurriculumPhase]
    tags: list[str]


SYSTEM_PROMPT = """\
You are a curriculum designer and persona mapper. You receive a user profile \
and produce labeled creative content blocks. Output ONLY the labeled sections \
described in the prompt. No commentary outside the sections."""

PROMPT_TEMPLATE = """\
Based on the following user profile, produce creative content for a learning mentor.

## User Profile
- Dialogue language: {dialogue_language}
- Mentor teaching language: {mentor_language}
- Topic: {topic}
- Experience level: {experience_level}
- Learning goals: {learning_goals}
- Environment/tools: {environment}
- Subtopics requested: {subtopics}
- Strategy: {strategy}
- Time input: {time_input}
- Mastery verification method: {mastery_method}
- Desired persona: {persona}

## Output format

Write EXACTLY these sections, each starting with the label on its own line.
Do not add any other sections. Write content in {mentor_language}.

PERSONA_NAME:
A concrete name for the mentor (e.g., "Professor Ada", "Coach Mike"). \
If user gave a generic description, invent a fitting name. One line only.

EXPERTISE:
3-5 topic expertise areas, one per line.

TONE:
2-4 voice characteristics — verbal mannerisms, signature phrases. One per line.

ROLE_SPECIFICS:
The persona's teaching method or approach. 1-2 sentences on one line.

PERSONA_ADAPTATION:
A comforting phrase the mentor uses when the student is struggling. \
Should feel natural to the persona. One line. Empty if no persona.

GREETING_FIRST:
A warm welcome for the FIRST session. Introduce the mentor by name, state the topic. \
2-4 sentences. Must feel like a real person.

GREETING_CONTINUATION:
A warm greeting for RETURNING sessions. Acknowledge the student is back. 1-2 sentences.

CORE_MISSION:
One sentence: "Personalized mentor and learning partner for [topic] focused on [goals]."

TAGS:
3-5 relevant tags for course metadata, one per line.

CURRICULUM:
Design 3-5 phases with 3-7 topics each. Use this exact format for EACH phase:

PHASE 1: [title]
FOCUS: [what this phase covers]
TOPICS:
- [topic 1]
- [topic 2]
- [topic 3]
HANDS_ON: [practical component]
SESSIONS: [estimated session count, e.g., "3-5 sessions"]

{strategy_instruction}"""


def _strategy_instruction(answers: UserAnswers) -> str:
    """Add strategy-specific guidance to the prompt."""
    recommended = settings["recommended_session_minutes"]
    if answers.strategy == "TIME-BOXED":
        return (
            f"IMPORTANT: The user has a TIME-BOXED strategy. {answers.time_input}. "
            f"Design the curriculum to fit within this timeline. "
            f"Each session is ~{recommended} min."
        )
    return (
        f"The user chose DEPTH-FIRST strategy ({answers.time_input}). "
        f"Design for thorough mastery — session counts are estimates."
    )


def generate_creative(provider: LLMProvider, answers: UserAnswers) -> str:
    """Single API call: produce all creative content from user answers.

    Returns the raw LLM response text. The caller saves it as an artifact
    and passes it to parse_creative_response() separately.
    """
    prompt = PROMPT_TEMPLATE.format(
        dialogue_language=answers.dialogue_language,
        mentor_language=answers.mentor_language,
        topic=answers.topic,
        experience_level=answers.experience_level,
        learning_goals=answers.learning_goals,
        environment=answers.environment,
        subtopics=answers.subtopics,
        strategy=answers.strategy,
        time_input=answers.time_input,
        mastery_method=answers.mastery_method,
        persona=answers.persona,
        strategy_instruction=_strategy_instruction(answers),
    )

    logger.info("Sending creative prompt to LLM (%d chars)", len(prompt))
    logger.debug("Prompt:\n%s", prompt)

    raw_response = provider.generate(prompt, system_prompt=SYSTEM_PROMPT)

    logger.info("Received creative response: %d chars", len(raw_response))
    logger.debug("Raw response:\n%s", raw_response)

    return raw_response


# ---------------------------------------------------------------------------
# Deterministic parser: labeled text blocks → CreativePayload
# ---------------------------------------------------------------------------

def parse_creative_response(text: str) -> CreativePayload:
    """Parse labeled LLM output into CreativePayload. Pure code, no LLM."""
    logger.info("Parsing creative response (%d chars)", len(text))
    sections = _split_sections(text)
    logger.info("Found %d sections: %s", len(sections), list(sections.keys()))

    missing = [label for label in _SECTION_LABELS if label not in sections]
    if missing:
        logger.warning("Missing sections in LLM response: %s", missing)

    persona_name = _require(sections, "PERSONA_NAME").strip()
    expertise = _lines(sections, "EXPERTISE")
    tone = _lines(sections, "TONE")
    role_specifics = _require(sections, "ROLE_SPECIFICS").strip()
    persona_adaptation = sections.get("PERSONA_ADAPTATION", "").strip()
    greeting_first = _require(sections, "GREETING_FIRST").strip()
    greeting_continuation = _require(sections, "GREETING_CONTINUATION").strip()
    core_mission = _require(sections, "CORE_MISSION").strip()
    tags = _lines(sections, "TAGS")
    curriculum_phases = _parse_curriculum(sections.get("CURRICULUM", ""))

    if not curriculum_phases:
        logger.error("No curriculum phases found in response")
        raise ValueError("LLM response contains no curriculum phases.")

    logger.info(
        "Parsed: persona=%s, %d expertise, %d tone, %d phases, %d tags",
        persona_name, len(expertise), len(tone),
        len(curriculum_phases), len(tags),
    )
    for phase in curriculum_phases:
        logger.debug(
            "  Phase %d: %s (%d topics, %s)",
            phase.phase_number, phase.title,
            len(phase.topics), phase.estimated_sessions,
        )

    return CreativePayload(
        persona_name=persona_name,
        expertise=expertise,
        tone=tone,
        role_specifics=role_specifics,
        persona_adaptation=persona_adaptation,
        greeting_first=greeting_first,
        greeting_continuation=greeting_continuation,
        core_mission=core_mission,
        curriculum_phases=curriculum_phases,
        tags=tags,
    )


# Section labels the parser looks for (order matters for splitting)
_SECTION_LABELS = [
    "PERSONA_NAME", "EXPERTISE", "TONE", "ROLE_SPECIFICS",
    "PERSONA_ADAPTATION", "GREETING_FIRST", "GREETING_CONTINUATION",
    "CORE_MISSION", "TAGS", "CURRICULUM",
]


def _split_sections(text: str) -> dict[str, str]:
    """Split text into {LABEL: content} by finding label lines."""
    label_pattern = re.compile(
        r"^\s*(" + "|".join(_SECTION_LABELS) + r")\s*:\s*$",
        re.MULTILINE,
    )

    matches = list(label_pattern.finditer(text))
    logger.debug("Found %d section headers in response", len(matches))
    sections: dict[str, str] = {}

    for i, match in enumerate(matches):
        label = match.group(1)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[label] = text[start:end].strip()

    return sections


def _require(sections: dict[str, str], key: str) -> str:
    """Get a required section or raise."""
    if key not in sections or not sections[key].strip():
        logger.error("Required section missing or empty: %s", key)
        raise ValueError(f"LLM response missing required section: {key}")
    return sections[key]


def _lines(sections: dict[str, str], key: str) -> list[str]:
    """Get a section as a list of non-empty lines."""
    raw = sections.get(key, "")
    return [
        line.lstrip("- ").strip()
        for line in raw.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _parse_curriculum(text: str) -> list[CurriculumPhase]:
    """Parse PHASE N: ... blocks into CurriculumPhase objects."""
    phase_pattern = re.compile(r"^PHASE\s+(\d+)\s*:\s*(.+)$", re.MULTILINE)
    matches = list(phase_pattern.finditer(text))
    logger.debug("Found %d curriculum phase headers", len(matches))

    phases: list[CurriculumPhase] = []
    for i, match in enumerate(matches):
        phase_num = int(match.group(1))
        title = match.group(2).strip()

        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end]

        focus = _extract_field(block, "FOCUS")
        topics = _extract_list(block, "TOPICS")
        hands_on = _extract_field(block, "HANDS_ON")
        sessions = _extract_field(block, "SESSIONS")

        phases.append(CurriculumPhase(
            phase_number=phase_num,
            title=title,
            focus=focus,
            topics=topics,
            hands_on=hands_on,
            estimated_sessions=sessions,
        ))

    return phases


def _extract_field(block: str, label: str) -> str:
    """Extract a single-line field like 'FOCUS: ...' from a text block."""
    pattern = re.compile(rf"^\s*{label}\s*:\s*(.+)$", re.MULTILINE)
    match = pattern.search(block)
    return match.group(1).strip() if match else ""


def _extract_list(block: str, label: str) -> list[str]:
    """Extract a list field (lines starting with -) after a label."""
    pattern = re.compile(rf"^\s*{label}\s*:\s*$", re.MULTILINE)
    match = pattern.search(block)
    if not match:
        return []

    items: list[str] = []
    for line in block[match.end():].splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            items.append(stripped[2:].strip())
        elif stripped and not stripped.startswith("-"):
            break
    return items
