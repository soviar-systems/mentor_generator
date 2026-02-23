"""Pipeline orchestrator — entry point for the mentor generator agent.

Usage:
    python -m agent.main                  # full pipeline
    python -m agent.main --skip-collect   # reuse saved answers, re-call API
    python -m agent.main --skip-api       # reuse answers + response, recompile only
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

from agent import artifacts
from agent.collector import collect_interactive, interview_source_hash
from agent.creative_engine import generate_creative, parse_creative_response
from agent.provider import create_provider
from agent.settings import settings, setup_logging
from agent.template_engine import fill_template, load_template
from agent.validator import validate
from agent.yaml_writer import write_mentor_file

logger = logging.getLogger(__name__)


def main() -> None:
    args = _parse_args()
    setup_logging(settings["log_level"])
    logger.info("Mentor Generator Agent starting")
    logger.info("Settings: model=%s, template=%s",
                settings["model"], settings["template_path"])

    # --- HTTPS proxy (must be set before any LLM calls) ---
    https_proxy = settings.get("https_proxy", "")
    if https_proxy:
        os.environ["HTTPS_PROXY"] = https_proxy
        logger.info("HTTPS proxy set: %s", https_proxy)

    # --- Interview provider (optional, for localized questionnaire) ---
    interview_provider = None
    interview_cache = None
    if not args.skip_collect and settings.get("interview_model"):
        try:
            interview_config = {
                "model": settings["interview_model"],
                "api_key": settings.get("interview_api_key") or settings.get("api_key", ""),
                "api_base": settings.get("interview_api_base") or settings.get("api_base", ""),
            }
            interview_provider = create_provider(interview_config)
            logger.info("Interview provider ready: %s", settings["interview_model"])

            from agent.interviewer import InterviewCache
            cache_path = Path(settings["artifacts_dir"]) / "interview_cache.json"
            interview_cache = InterviewCache(cache_path, interview_source_hash())
        except Exception as e:
            logger.warning("Interview LLM unavailable (%s), using English", e)
            interview_provider = None
            interview_cache = None

    # --- Stage 1: Collect ---
    if args.skip_collect:
        logger.info("Stage 1: SKIPPED (--skip-collect), loading from artifacts")
        answers = artifacts.load_answers()
        logger.info("Loaded answers: topic=%s, strategy=%s", answers.topic, answers.strategy)
    else:
        logger.info("Stage 1: Collecting user answers")
        answers = collect_interactive(interview_provider, interview_cache)
        if interview_cache:
            interview_cache.save()
        path = artifacts.save_answers(answers)
        logger.info("Answers saved to %s", path)

    # --- Stage 2: Create (API call) ---
    if args.skip_api:
        logger.info("Stage 2: SKIPPED (--skip-api), loading from artifacts")
        raw_response = artifacts.load_creative_response()
    else:
        logger.info("Stage 2: Calling LLM for creative content")
        provider = create_provider(settings)
        raw_response = _call_with_retries(provider, answers)
        path = artifacts.save_creative_response(raw_response)
        logger.info("Creative response saved to %s", path)

    # --- Stage 3: Compile (always runs) ---
    logger.info("Stage 3: Compiling mentor file")

    payload = parse_creative_response(raw_response)
    logger.info("Parsed creative payload: persona=%s, %d phases",
                payload.persona_name, len(payload.curriculum_phases))

    template = load_template()
    output = fill_template(template, answers, payload)

    errors = validate(output, template)
    if errors:
        print(f"\nValidation FAILED — {len(errors)} errors:")
        for err in errors:
            print(f"  - {err}")
        logger.error("Validation failed with %d errors, aborting", len(errors))
        sys.exit(1)

    mentor_path = write_mentor_file(output)

    # --- Done ---
    print(f"\nMentor file generated: {mentor_path}")
    print(f"Course history file:   {mentor_path.parent / 'course_history'}")
    _print_usage_guide()
    logger.info("Generation complete: %s", mentor_path)


def _call_with_retries(provider, answers) -> str:
    """Call LLM with retry logic."""
    max_retries = settings["api_retries"]
    delay = settings["api_retry_delay_sec"]

    for attempt in range(max_retries + 1):
        try:
            return generate_creative(provider, answers)
        except Exception as e:
            if attempt < max_retries:
                logger.warning("API call failed (attempt %d/%d): %s",
                               attempt + 1, max_retries + 1, e)
                logger.info("Retrying in %.1f seconds...", delay)
                time.sleep(delay)
            else:
                logger.error("API call failed after %d attempts: %s",
                             max_retries + 1, e)
                print(f"\nAPI call failed after {max_retries + 1} attempts: {e}")
                print("Your answers are saved. Re-run with --skip-collect to retry.")
                sys.exit(1)
    # Unreachable: loop always returns or calls sys.exit
    raise RuntimeError("Unreachable")


def _print_usage_guide() -> None:
    """Print USAGE.md contents after generation."""
    usage_path = Path(__file__).parent / "USAGE.md"
    if usage_path.exists():
        print("\n" + "=" * 60)
        with open(usage_path, encoding="utf-8") as f:
            print(f.read())
    else:
        logger.debug("USAGE.md not found at %s", usage_path)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a personalized AI learning mentor file.",
    )
    parser.add_argument(
        "--skip-collect", action="store_true",
        help="Skip questionnaire, reuse saved answers from artifacts",
    )
    parser.add_argument(
        "--skip-api", action="store_true",
        help="Skip API call, reuse saved creative response from artifacts",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
