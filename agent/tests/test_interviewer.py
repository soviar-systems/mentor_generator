"""Interviewer translation tests — 0 API calls.

Uses a MockProvider to verify translation logic and caching
without any real LLM calls. Mock responses are generic placeholders —
these tests verify plumbing (call count, cache hits, fallback), not
translation quality.
"""

from __future__ import annotations

from pathlib import Path

from agent.interviewer import InterviewCache, translate_interview
from agent.provider import LLMProvider


class MockProvider(LLMProvider):
    """Returns pre-configured responses in order."""

    def __init__(self, responses: list[str]):
        self.responses = list(responses)
        self.calls: list[tuple[str, str]] = []

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        self.calls.append((prompt, system_prompt))
        return self.responses.pop(0)


def test_translate_interview_calls_provider():
    """Each text gets one provider call, result is returned."""
    provider = MockProvider(["translated_a", "translated_b"])
    texts = ["question_one", "question_two"]

    result = translate_interview(provider, "Russian", texts)

    assert result["question_one"] == "translated_a"
    assert result["question_two"] == "translated_b"
    assert len(provider.calls) == len(texts)


def test_translate_interview_uses_cache(tmp_path: Path):
    """Cached translations skip the provider entirely."""
    cache_path = tmp_path / "cache.json"
    cache = InterviewCache(cache_path, source_hash="abc123")
    cache.set("Russian", "question_one", "cached_translation")

    provider = MockProvider(["fresh_translation"])
    texts = ["question_one", "question_two"]

    result = translate_interview(provider, "Russian", texts, cache=cache)

    assert result["question_one"] == "cached_translation"  # from cache
    assert result["question_two"] == "fresh_translation"    # from provider
    assert len(provider.calls) == 1  # only the uncached text


def test_translate_one_fallback_on_error():
    """Provider failure returns original text, no crash."""

    class FailingProvider(LLMProvider):
        def generate(self, prompt: str, system_prompt: str = "") -> str:
            raise ConnectionError("simulated failure")

    original = "some question"
    result = translate_interview(FailingProvider(), "Russian", [original])

    assert result[original] == original  # graceful fallback


def test_cache_invalidates_on_hash_change(tmp_path: Path):
    """Cache is cleared when source questions change (hash mismatch)."""
    cache_path = tmp_path / "cache.json"

    # Seed via API with one hash
    old_cache = InterviewCache(cache_path, source_hash="old_hash")
    old_cache.set("Russian", "question", "old_translation")
    old_cache.save()

    # Reload with a different hash — old data should be gone
    new_cache = InterviewCache(cache_path, source_hash="new_hash")
    assert new_cache.get("Russian", "question") is None


def test_cache_save_roundtrip(tmp_path: Path):
    """Cache persists to disk and reloads correctly."""
    cache_path = tmp_path / "cache.json"
    cache = InterviewCache(cache_path, source_hash="abc123")
    cache.set("Russian", "question", "translation")
    cache.save()

    # Reload from disk with same hash
    cache2 = InterviewCache(cache_path, source_hash="abc123")
    assert cache2.get("Russian", "question") == "translation"
