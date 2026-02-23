"""Central settings — layered config loading.

Config hierarchy (later overrides earlier):
  1. Code defaults (DEFAULTS dict below)
  2. ~/.mentor.generator.config.yml  (global — user preferences)
  3. ./.mentor.generator.config.yml  (local — project overrides)

Every configurable value lives in DEFAULTS. Add new keys here and they
become overridable from either config file. No other module should
define its own magic constants — import from settings instead.

Usage:
    from agent.settings import settings
    settings["model"]           # "gemini-3-flash" (or override)
    settings["artifacts_dir"]   # ".mentor.generator.artifacts"
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

DEFAULTS: dict = {
    # --- LLM Provider ---
    "provider": "gemini",
    "model": "gemini-3-flash",
    "api_key_env": "GEMINI_API_KEY",

    # --- Paths ---
    "template_path": "./agent/templates/mentor_system_prompt.template.json",
    "output_dir": "./output",
    "artifacts_dir": ".mentor.generator.artifacts",

    # --- Collection ---
    "recommended_session_minutes": 45,
    "session_minutes_min": 15,
    "session_minutes_max": 180,

    # --- Pipeline ---
    "api_retries": 2,
    "api_retry_delay_sec": 5.0,

    # --- Logging ---
    "log_level": "info",
    "log_file_dir": ".mentor.generator.artifacts",
    "log_file_name": "agent.log",
}

GLOBAL_CONFIG = Path.home() / ".mentor.generator.config.yml"
LOCAL_CONFIG = Path(".mentor.generator.config.yml")


def _load_yaml(path: Path) -> dict:
    """Load a YAML file, return empty dict if missing or empty."""
    if not path.exists():
        logger.debug("Config file not found: %s", path)
        return {}
    logger.info("Loading config: %s", path)
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    logger.debug("Config contents from %s: %s", path.name, list(data.keys()))
    return data


def load_settings() -> dict:
    """Load settings: defaults → global config → local config."""
    merged = dict(DEFAULTS)

    global_overrides = _load_yaml(GLOBAL_CONFIG)
    if global_overrides:
        logger.info("Applied %d global config overrides", len(global_overrides))
        merged.update(global_overrides)

    local_overrides = _load_yaml(LOCAL_CONFIG)
    if local_overrides:
        logger.info("Applied %d local config overrides", len(local_overrides))
        merged.update(local_overrides)

    return merged


def setup_logging(level_str: str | None = None) -> None:
    """Configure logging for the entire agent package.

    Writes to both stderr (console) and a log file.
    Console shows INFO+ by default. File always captures DEBUG level
    for post-mortem debugging regardless of console log_level.

    Call this once at startup (main.py). Uses log_level from settings
    unless explicitly overridden.
    """
    level_name = (level_str or "info").upper()
    console_level = getattr(logging, level_name, logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Root logger captures everything; handlers filter by level
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Console handler — respects user's log_level setting
    console = logging.StreamHandler()
    console.setLevel(console_level)
    console.setFormatter(fmt)
    root.addHandler(console)

    # File handler — always DEBUG for post-mortem analysis
    log_dir = Path(settings.get("log_file_dir", ".mentor.generator.artifacts"))
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / settings.get("log_file_name", "agent.log")

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root.addHandler(file_handler)

    logger.debug("Logging configured: console=%s, file=%s (DEBUG)", level_name, log_file)


# Loaded once on import
settings = load_settings()
