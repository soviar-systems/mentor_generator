"""Artifact persistence — save/load pipeline artifacts.

Artifacts live in .mentor.generator.artifacts/ (configurable via artifacts_dir).

Files:
  answers.yml            — user answers from the questionnaire
  creative_response.txt  — raw LLM response (labeled text blocks)
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from pathlib import Path

import yaml

from agent.collector import UserAnswers
from agent.settings import settings

logger = logging.getLogger(__name__)


def _artifacts_path() -> Path:
    """Get artifacts directory path, create if needed."""
    path = Path(settings["artifacts_dir"])
    logger.debug("Artifacts directory: %s (resolved: %s)", path, path.resolve())
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_answers(answers: UserAnswers) -> Path:
    """Save UserAnswers to answers.yml. Returns the file path."""
    filepath = _artifacts_path() / "answers.yml"
    logger.info("Saving answers to %s", filepath)
    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(asdict(answers), f, allow_unicode=True, sort_keys=False)
    logger.debug("Answers saved: %d bytes", filepath.stat().st_size)
    return filepath


def load_answers() -> UserAnswers:
    """Load UserAnswers from answers.yml."""
    filepath = _artifacts_path() / "answers.yml"
    if not filepath.exists():
        logger.error("Answers file not found: %s", filepath.resolve())
        raise FileNotFoundError(
            f"No saved answers at {filepath}. Run collection first."
        )
    logger.info("Loading answers from %s", filepath)
    with open(filepath, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    answers = UserAnswers()
    for key, value in data.items():
        if hasattr(answers, key):
            setattr(answers, key, str(value))
    logger.debug("Loaded answers: topic=%s, strategy=%s", answers.topic, answers.strategy)
    return answers


def save_creative_response(raw_text: str) -> Path:
    """Save raw LLM response to creative_response.txt."""
    filepath = _artifacts_path() / "creative_response.txt"
    logger.info("Saving creative response to %s", filepath)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(raw_text)
    logger.debug("Creative response saved: %d chars", len(raw_text))
    return filepath


def load_creative_response() -> str:
    """Load raw LLM response from creative_response.txt."""
    filepath = _artifacts_path() / "creative_response.txt"
    if not filepath.exists():
        logger.error("Creative response file not found: %s", filepath.resolve())
        raise FileNotFoundError(
            f"No saved creative response at {filepath}. Run API call first."
        )
    logger.info("Loading creative response from %s", filepath)
    with open(filepath, encoding="utf-8") as f:
        text = f.read()
    logger.debug("Loaded creative response: %d chars", len(text))
    return text


def has_answers() -> bool:
    exists = (_artifacts_path() / "answers.yml").exists()
    logger.debug("has_answers: %s", exists)
    return exists


def has_creative_response() -> bool:
    exists = (_artifacts_path() / "creative_response.txt").exists()
    logger.debug("has_creative_response: %s", exists)
    return exists
