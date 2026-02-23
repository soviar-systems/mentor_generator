"""CLI data collection — 0 API calls without interview LLM, N calls with.

When interview_provider is configured, all localizable texts are
pre-translated before the questionnaire starts (or served from cache).
The interview loop then runs identically to the English-only version,
just with translated strings. User answers are stored as-is — the
creative LLM handles any language via the dialogue_language field.
"""

from __future__ import annotations

import hashlib
import locale
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


# ---------------------------------------------------------------------------
# Localizable text constants
# ---------------------------------------------------------------------------

_GREETING_TEXT = "What language would you prefer to communicate in?"

_QUESTIONS: list[tuple[str, str]] = [
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

_STRATEGY_MENU_TEXT = (
    "Which learning strategy is your priority?\n"
    "\n"
    "  [1] DEPTH-FIRST (Mastery-Gated)\n"
    "      Progression based solely on verified mastery.\n"
    "      No deadlines — understanding comes first.\n"
    "\n"
    "  [2] TIME-BOXED (Speed-First)\n"
    "      Course must finish by a specific deadline.\n"
    "      Content depth may be reduced to meet the timeline."
)

_QUESTIONS_AFTER_STRATEGY: list[tuple[str, str]] = [
    ("mastery_method",
     "How should the mentor verify your progress and mastery?\n"
     "(e.g., practical assignments, quizzes, Socratic questioning, code review)"),
    ("persona",
     "What tone or persona should the mentor adopt?\n"
     "(e.g., 'a supportive coach', 'a strict professor', 'Pyotr Tchaikovsky', 'a friendly peer')"),
]

# --- Locale detection ---

_LOCALE_MAP: dict[str, str] = {
    "en": "English",  "ru": "Russian",   "de": "German",
    "fr": "French",   "es": "Spanish",   "it": "Italian",
    "pt": "Portuguese", "zh": "Chinese", "ja": "Japanese",
    "ko": "Korean",  "ar": "Arabic",    "hi": "Hindi",
    "tr": "Turkish", "pl": "Polish",    "nl": "Dutch",
    "sv": "Swedish", "uk": "Ukrainian", "cs": "Czech",
}


def _detect_locale_language() -> str:
    """Detect system language from locale setting."""
    try:
        loc = locale.getlocale()[0] or ""
    except ValueError:
        return "English"
    prefix = loc[:2].lower() if len(loc) >= 2 else ""
    return _LOCALE_MAP.get(prefix, "English")


# ---------------------------------------------------------------------------
# Source hash for cache invalidation
# ---------------------------------------------------------------------------

def _all_localizable_texts() -> list[str]:
    """All texts that need translation, including formatted prompts."""
    recommended = settings["recommended_session_minutes"]
    texts = [_GREETING_TEXT]
    texts.extend(text for _, text in _QUESTIONS)
    texts.append(_STRATEGY_MENU_TEXT)
    texts.append("Enter 1 or 2: ")
    texts.append("Please enter 1 or 2.")
    texts.append(
        f"Recommended session length: {recommended} minutes.\n"
        f"  This gives enough time for explanation, practice, and mastery checks\n"
        f"  without fatigue."
    )
    texts.append(
        f"Press Enter to accept {recommended} min, "
        f"or type your preferred session length in minutes: "
    )
    texts.append("Enter your deadline date.")
    texts.append("Invalid date format. Use YYYY-MM-DD (e.g., 2026-06-01).")
    texts.append("Deadline must be in the future.")
    texts.extend(text for _, text in _QUESTIONS_AFTER_STRATEGY)
    return texts


def interview_source_hash() -> str:
    """Hash all localizable interview texts for cache invalidation."""
    texts = _all_localizable_texts()
    return hashlib.sha256("\n".join(texts).encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Questionnaire
# ---------------------------------------------------------------------------

def collect_interactive(interview_provider=None, interview_cache=None) -> UserAnswers:
    """Run the 9-question CLI questionnaire. Returns UserAnswers.

    Args:
        interview_provider: optional LLM provider for translating questions.
            When set, questions are shown in the user's language. Answers are
            stored as-is (the creative LLM handles any language).
        interview_cache: optional InterviewCache for reusing translations.
    """
    answers = UserAnswers()
    logger.info("Starting interactive questionnaire")
    print("\n=== Mentor Generator ===\n")

    detected_lang = _detect_locale_language()
    logger.info("Detected system locale language: %s", detected_lang)

    # Q0: Language preference — shown in detected locale language
    greeting = _GREETING_TEXT
    if interview_provider and detected_lang != "English":
        from agent.interviewer import translate_interview
        q0_translations = translate_interview(
            interview_provider, detected_lang, [_GREETING_TEXT], interview_cache,
        )
        greeting = q0_translations.get(_GREETING_TEXT, _GREETING_TEXT)

    print(f"\n[0] {greeting}")
    raw = input("> ").strip()
    answers.dialogue_language = raw if raw else detected_lang
    logger.debug("Q0 (dialogue_language): %s", answers.dialogue_language)

    # Pre-translate remaining texts to user's chosen language
    t = _build_translator(interview_provider, answers.dialogue_language, interview_cache)

    # Q1-Q6
    for i, (field_name, prompt_text) in enumerate(_QUESTIONS, start=1):
        print(f"\n[Q{i}] {t(prompt_text)}")
        raw = input("> ").strip()
        setattr(answers, field_name, raw)
        logger.debug("Q%d (%s): %s", i, field_name, raw)

    # Q7: Strategy — deterministic choice
    _collect_strategy(answers, t)

    # Q8-Q9
    for j, (field_name, prompt_text) in enumerate(_QUESTIONS_AFTER_STRATEGY, start=8):
        print(f"\n[Q{j}] {t(prompt_text)}")
        raw = input("> ").strip()
        setattr(answers, field_name, raw)
        logger.debug("Q%d (%s): %s", j, field_name, raw)

    logger.info("Questionnaire complete: topic=%s, strategy=%s", answers.topic, answers.strategy)
    print("\n--- All answers collected. ---\n")
    return answers


def _build_translator(interview_provider, language, interview_cache):
    """Pre-translate all texts and return a lookup function.

    Returns a callable t(text) -> translated_text. If no provider is
    configured or language is English, returns identity (no-op).
    """
    if not interview_provider or language.lower() == "english":
        return lambda text: text

    from agent.interviewer import translate_interview

    all_texts = _all_localizable_texts()
    translations = translate_interview(
        interview_provider, language, all_texts, interview_cache,
    )
    logger.info("Pre-translated %d texts to %s", len(translations), language)

    return lambda text: translations.get(text, text)


# ---------------------------------------------------------------------------
# Q7: Strategy
# ---------------------------------------------------------------------------

def _collect_strategy(answers: UserAnswers, t) -> None:
    """Q7: Deterministic strategy selection with follow-up."""
    recommended = settings["recommended_session_minutes"]

    print(f"\n[Q7] {t(_STRATEGY_MENU_TEXT)}\n")

    enter_prompt = t("Enter 1 or 2: ")
    retry_msg = "  " + t("Please enter 1 or 2.")
    while True:
        choice = input(enter_prompt).strip()
        if choice in ("1", "2"):
            break
        print(retry_msg)

    if choice == "1":
        answers.strategy = "DEPTH-FIRST"
        logger.debug("Strategy: %s", answers.strategy)

        session_info = (
            f"Recommended session length: {recommended} minutes.\n"
            f"  This gives enough time for explanation, practice, and mastery checks\n"
            f"  without fatigue."
        )
        print(f"\n  {t(session_info)}")

        accept_prompt = (
            f"Press Enter to accept {recommended} min, "
            f"or type your preferred session length in minutes: "
        )
        custom = input(f"  {t(accept_prompt)}").strip()

        if custom:
            minutes = _parse_minutes(custom, recommended)
            answers.time_input = f"{minutes} min sessions"
        else:
            answers.time_input = f"{recommended} min sessions"
        logger.info("DEPTH-FIRST: %s", answers.time_input)

    else:
        answers.strategy = "TIME-BOXED"
        logger.debug("Strategy: %s", answers.strategy)

        print(f"\n  {t('Enter your deadline date.')}")
        while True:
            raw_date = input("  Deadline (YYYY-MM-DD): ").strip()
            deadline = _parse_date(raw_date)
            if deadline is None:
                logger.debug("Invalid date input: %s", raw_date)
                print(f"  {t('Invalid date format. Use YYYY-MM-DD (e.g., 2026-06-01).')}")
                continue
            if deadline <= date.today():
                logger.debug("Deadline in the past: %s", raw_date)
                print(f"  {t('Deadline must be in the future.')}")
                continue
            break

        days_left = (deadline - date.today()).days
        weeks_left = days_left / 7
        answers.time_input = (
            f"Deadline: {deadline.isoformat()}, "
            f"{days_left} days ({weeks_left:.1f} weeks) remaining"
        )
        logger.info("TIME-BOXED: %s", answers.time_input)
        print(f"\n  {days_left} days ({weeks_left:.1f} weeks)")


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
