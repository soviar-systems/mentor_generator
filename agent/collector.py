"""CLI data collection — 0 API calls. Reads questions from mentor_generator.json."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime

from agent.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class UserAnswers:
    """All data collected from the 9-question questionnaire."""

    dialogue_language: str = ""      # greeting step
    mentor_language: str = ""        # Q1
    topic: str = ""                  # Q2
    experience_level: str = ""       # Q3
    learning_goals: str = ""         # Q4
    environment: str = ""            # Q5
    subtopics: str = ""              # Q6
    strategy: str = ""               # Q7: DEPTH-FIRST or TIME-BOXED
    time_input: str = ""             # Q7: computed time info
    mastery_method: str = ""         # Q8
    persona: str = ""                # Q9


# Questions for all fields except strategy (handled separately)
_QUESTIONS: list[tuple[str, str]] = [
    ("dialogue_language",
     "Здравствуйте! Какой язык вам удобнее для дальнейшего взаимодействия?\n"
     "Hello! What language would you prefer to communicate in?"),
    ("mentor_language",
     "Which language should the learning mentor use when teaching you?"),
    ("topic",
     "What topic or subject do you want to learn?\n"
     "(e.g., Quantum Physics, Oil Painting, Python Programming, Ancient History)"),
    ("experience_level",
     "What is your current experience or starting level?\n"
     "(e.g., absolute beginner, self-taught enthusiast, professional looking to specialize)"),
    ("learning_goals",
     "What is your target depth and primary learning goal?\n"
     "(e.g., broad theoretical overview, practical how-to skills, deep expert-level mastery)"),
    ("environment",
     "What environment, tools, or constraints do you have?\n"
     "(e.g., access to a laboratory, specific software, a musical instrument, a library)"),
    ("subtopics",
     "Are there specific subtopics or focus areas you want covered?\n"
     "(e.g., 'focus on landscape techniques' or 'skip the introductory math')"),
]

_QUESTIONS_AFTER_STRATEGY: list[tuple[str, str]] = [
    ("mastery_method",
     "How should the mentor verify your progress and mastery?\n"
     "(e.g., practical assignments, quizzes, Socratic questioning, code review)"),
    ("persona",
     "What tone or persona should the mentor adopt?\n"
     "(e.g., 'a supportive coach', 'a strict professor', 'Pyotr Tchaikovsky', 'a friendly peer')"),
]


def collect_interactive() -> UserAnswers:
    """Run the 9-question CLI questionnaire. Returns UserAnswers."""
    answers = UserAnswers()
    logger.info("Starting interactive questionnaire")
    print("\n=== Mentor Generator ===\n")

    # Questions 0-6 (greeting + Q1-Q6)
    for i, (field_name, prompt_text) in enumerate(_QUESTIONS):
        label = f"[{i}] " if i == 0 else f"[Q{i}] "
        print(f"\n{label}{prompt_text}")
        raw = input("> ").strip()
        setattr(answers, field_name, raw)
        logger.debug("Q%d (%s): %s", i, field_name, raw)

    # Q7: Strategy — deterministic choice
    _collect_strategy(answers)

    # Q8-Q9
    for j, (field_name, prompt_text) in enumerate(_QUESTIONS_AFTER_STRATEGY, start=8):
        print(f"\n[Q{j}] {prompt_text}")
        raw = input("> ").strip()
        setattr(answers, field_name, raw)
        logger.debug("Q%d (%s): %s", j, field_name, raw)

    logger.info("Questionnaire complete: topic=%s, strategy=%s", answers.topic, answers.strategy)
    print("\n--- All answers collected. ---\n")
    return answers


def _collect_strategy(answers: UserAnswers) -> None:
    """Q7: Deterministic strategy selection with follow-up."""
    recommended = settings["recommended_session_minutes"]

    print(
        "\n[Q7] Which learning strategy is your priority?\n"
        "\n"
        "  [1] DEPTH-FIRST (Mastery-Gated)\n"
        "      Progression based solely on verified mastery.\n"
        "      No deadlines — understanding comes first.\n"
        "\n"
        "  [2] TIME-BOXED (Speed-First)\n"
        "      Course must finish by a specific deadline.\n"
        "      Content depth may be reduced to meet the timeline.\n"
    )

    while True:
        choice = input("Enter 1 or 2: ").strip()
        if choice in ("1", "2"):
            break
        print("  Please enter 1 or 2.")

    if choice == "1":
        answers.strategy = "DEPTH-FIRST"
        logger.debug("Strategy: %s", answers.strategy)
        print(
            f"\n  Recommended session length: {recommended} minutes.\n"
            f"  This gives enough time for explanation, practice, and mastery checks\n"
            f"  without fatigue."
        )
        custom = input(
            f"  Press Enter to accept {recommended} min, "
            f"or type your preferred session length in minutes: "
        ).strip()

        if custom:
            minutes = _parse_minutes(custom, recommended)
            answers.time_input = f"{minutes} min sessions"
        else:
            answers.time_input = f"{recommended} min sessions"
        logger.info("DEPTH-FIRST: %s", answers.time_input)

    else:
        answers.strategy = "TIME-BOXED"
        logger.debug("Strategy: %s", answers.strategy)
        print("\n  Enter your deadline date.")
        while True:
            raw_date = input("  Deadline (YYYY-MM-DD): ").strip()
            deadline = _parse_date(raw_date)
            if deadline is None:
                logger.debug("Invalid date input: %s", raw_date)
                print("  Invalid date format. Use YYYY-MM-DD (e.g., 2026-06-01).")
                continue
            if deadline <= date.today():
                logger.debug("Deadline in the past: %s", raw_date)
                print("  Deadline must be in the future.")
                continue
            break

        days_left = (deadline - date.today()).days
        weeks_left = days_left / 7
        answers.time_input = (
            f"Deadline: {deadline.isoformat()}, "
            f"{days_left} days ({weeks_left:.1f} weeks) remaining"
        )
        logger.info("TIME-BOXED: %s", answers.time_input)
        print(f"\n  {days_left} days ({weeks_left:.1f} weeks) until deadline.")


def _parse_minutes(raw: str, default: int) -> int:
    """Extract a minute value from user input, clamp to 15-180."""
    digits = "".join(c for c in raw if c.isdigit())
    if digits:
        result = max(15, min(180, int(digits)))
        logger.debug("Parsed session minutes: %d (from '%s')", result, raw)
        return result
    logger.debug("Could not parse minutes from '%s', using default %d", raw, default)
    return default


def _parse_date(raw: str) -> date | None:
    """Parse YYYY-MM-DD date string."""
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None
