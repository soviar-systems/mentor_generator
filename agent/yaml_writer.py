"""YAML Writer — deterministic JSON→YAML conversion.

Eliminates P3 (format conversion errors) by using yaml.dump()
instead of asking an LLM to convert formats.
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from agent.settings import settings

logger = logging.getLogger(__name__)


def write_mentor_file(output: dict) -> Path:
    """Write filled template as YAML to output directory.

    Returns the path to the written file.
    Also creates an empty course_history file if it doesn't exist.
    """
    output_dir = Path(settings["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Output directory: %s", output_dir.resolve())

    # Write mentor_system_prompt.yml
    mentor_path = output_dir / "mentor_system_prompt.yml"
    logger.info("Writing mentor file to %s", mentor_path)

    yaml_content = yaml.dump(
        output,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=120,
    )

    with open(mentor_path, "w", encoding="utf-8") as f:
        f.write(yaml_content)

    logger.info("Mentor file written: %d bytes", mentor_path.stat().st_size)

    # Create empty course_history if not exists
    history_path = output_dir / "course_history"
    if not history_path.exists():
        history_path.touch()
        logger.info("Created empty course_history at %s", history_path)
    else:
        logger.debug("course_history already exists at %s", history_path)

    return mentor_path
