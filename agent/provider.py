"""LLM provider abstraction. Gemini implementation first."""

from __future__ import annotations

import json
import logging
import os
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
class GeminiProvider(LLMProvider):
    """Google Gemini via google-generativeai SDK."""

    model: str = "gemini-3-flash"
    api_key_env: str = "GEMINI_API_KEY"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        import google.generativeai as genai

        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            logger.error("API key env var %s is not set", self.api_key_env)
            raise RuntimeError(
                f"Environment variable {self.api_key_env} is not set. "
                f"Get a free key at https://aistudio.google.com/apikey"
            )

        logger.info("Calling Gemini model=%s", self.model)
        logger.debug("Prompt length: %d chars, system prompt: %d chars",
                      len(prompt), len(system_prompt))

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            self.model,
            system_instruction=system_prompt or None,
        )
        response = model.generate_content(prompt)

        logger.info("Gemini response received: %d chars", len(response.text))
        logger.debug("Response preview: %.200s...", response.text)
        return response.text


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


def create_provider(config: dict) -> LLMProvider:
    """Factory: create provider from config dict."""
    provider_name = config.get("provider", "gemini")
    logger.info("Creating LLM provider: %s", provider_name)
    if provider_name == "gemini":
        provider = GeminiProvider(
            model=config.get("model", "gemini-3-flash"),
            api_key_env=config.get("api_key_env", "GEMINI_API_KEY"),
        )
        logger.debug("GeminiProvider: model=%s, api_key_env=%s",
                      provider.model, provider.api_key_env)
        return provider
    raise ValueError(f"Unknown provider: {provider_name}")
