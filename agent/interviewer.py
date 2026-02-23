"""Interview translation — pre-translate all questions, cache results.

Before the questionnaire starts, all localizable texts (questions, menus,
prompts) are translated in one pass and stored in a dict. The collector
then uses this dict as a lookup table — identical flow to the current
English-only version, just with translated strings.

Cache: translations are persisted to a JSON file keyed by (language,
original_text). A source hash invalidates the entire cache when the
original texts change. After the first run for a given language, all
subsequent runs are 0 LLM calls.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from agent.provider import LLMProvider

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a translation assistant. You translate text accurately and concisely. "
    "Keep any examples in parentheses. "
    "Keep [1]/[2] markers and English terms DEPTH-FIRST/TIME-BOXED as-is. "
    "Output ONLY the translation, no commentary."
)


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

class InterviewCache:
    """Persistent cache for interview question translations.

    Keyed by (language, original_text). Invalidated when source questions
    change (detected via source_hash mismatch).
    """

    def __init__(self, path: Path, source_hash: str):
        self.path = path
        self.source_hash = source_hash
        self._data = self._load()
        self._dirty = False

    def _load(self) -> dict:
        if not self.path.exists():
            return {"source_hash": self.source_hash, "languages": {}}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Could not read interview cache (%s), starting fresh", e)
            return {"source_hash": self.source_hash, "languages": {}}
        if data.get("source_hash") != self.source_hash:
            logger.info("Interview questions changed (hash mismatch), clearing cache")
            return {"source_hash": self.source_hash, "languages": {}}
        lang_count = len(data.get("languages", {}))
        logger.info("Loaded interview cache: %d language(s)", lang_count)
        return data

    def get(self, language: str, key: str) -> str | None:
        return self._data.get("languages", {}).get(language, {}).get(key)

    def set(self, language: str, key: str, value: str) -> None:
        self._data.setdefault("languages", {}).setdefault(language, {})[key] = value
        self._dirty = True

    def save(self) -> None:
        """Write cache to disk (only if changed since load)."""
        if not self._dirty:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Interview cache saved to %s", self.path)

    @staticmethod
    def clear(path: Path) -> None:
        """Delete the cache file."""
        if path.exists():
            path.unlink()
            logger.info("Interview cache cleared: %s", path)


# ---------------------------------------------------------------------------
# Translation
# ---------------------------------------------------------------------------

def translate_interview(
    provider: LLMProvider,
    language: str,
    texts: list[str],
    cache: InterviewCache | None = None,
) -> dict[str, str]:
    """Pre-translate all interview texts before the questionnaire starts.

    Returns a mapping {original_english_text: translated_text}.
    Uses cache when available; new translations are added to the cache.
    """
    translations: dict[str, str] = {}
    to_translate: list[str] = []

    for text in texts:
        if cache:
            cached = cache.get(language, text)
            if cached is not None:
                translations[text] = cached
                continue
        to_translate.append(text)

    if not to_translate:
        logger.info("All %d texts served from cache", len(translations))
        return translations

    logger.info("Translating %d texts to %s (%d from cache)",
                len(to_translate), language, len(translations))

    for text in to_translate:
        translated = _translate_one(provider, language, text)
        translations[text] = translated
        if cache:
            cache.set(language, text, translated)

    return translations


def _translate_one(provider: LLMProvider, language: str, text: str) -> str:
    """Translate a single text. Returns original on failure."""
    prompt = (
        f"Translate the following text to {language}. "
        f"Output only the translation.\n\n"
        f"{text}"
    )
    try:
        result = provider.generate(prompt, system_prompt=SYSTEM_PROMPT)
        return result.strip()
    except Exception as e:
        logger.warning("Translation failed (%s), using original", e)
        return text
