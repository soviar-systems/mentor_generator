"""LLM provider abstraction. Universal provider via litellm."""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Minimal interface: one method, one call."""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """Send prompt to LLM, return raw text response."""


@dataclass
class LiteLLMProvider(LLMProvider):
    """Universal LLM provider via litellm. Supports 100+ models."""

    model: str              # litellm format: provider/model-name
    api_base: str = ""      # for custom endpoints (optional)

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        from litellm import completion

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict = {"model": self.model, "messages": messages}
        if self.api_base:
            kwargs["api_base"] = self.api_base

        logger.info("Calling LLM model=%s", self.model)
        logger.debug("Prompt length: %d chars, system prompt: %d chars",
                      len(prompt), len(system_prompt))

        response = completion(**kwargs)
        text = response.choices[0].message.content

        logger.info("LLM response received: %d chars", len(text))
        logger.debug("Response preview: %.200s...", text)
        return text


def extract_json(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown code fences."""
    text = text.strip()
    if text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.debug("Direct JSON parse failed, trying code fence extraction")

    match = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            logger.debug("Code fence JSON parse failed")

    logger.error("Could not extract JSON from response (first 500 chars): %.500s", text)
    raise ValueError(f"Could not extract JSON from LLM response:\n{text[:500]}")


def create_provider(config: dict) -> LiteLLMProvider:
    """Factory: create provider from config dict.

    Expects ``model`` key to be present (settings.DEFAULTS guarantees this).
    """
    model = config["model"]
    api_base = config.get("api_base", "")

    logger.info("Creating LLM provider: model=%s, api_base=%s",
                model, api_base or "(default)")
    return LiteLLMProvider(model=model, api_base=api_base)
