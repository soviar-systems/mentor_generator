# Fix: UnicodeDecodeError on Cyrillic input in collector

## Context

When running the questionnaire with an `interview_model` configured (LiteLLM → Gemini), Cyrillic input to `input()` crashes with `UnicodeDecodeError` at `collector.py:183`. The log shows:
- Q2 input corrupted: "п" doubled at the start ("ппрограммирование" instead of "программирование")
- Q3 crashes: `byte 0xd1 in position 29: invalid continuation byte`
- `asyncio: Using selector: EpollSelector` appears at crash time — LiteLLM's deferred async cleanup (aiohttp sessions) fires during `input()`, injecting stray bytes into the stdin stream

System locale is correctly set to UTF-8; this is a runtime interference issue, not a configuration problem.

## Approach: Safe input wrapper with retry

### 1. Add `_safe_input()` helper to `collector.py`

```python
def _safe_input(prompt: str = "") -> str:
    """Read input with UnicodeDecodeError recovery."""
    try:
        return input(prompt)
    except UnicodeDecodeError:
        logger.warning("Encoding error reading input, draining buffer")
        try:
            sys.stdin.buffer.readline()  # drain corrupted bytes
        except Exception:
            pass
        print("  (Input error — please re-enter)")
        return input(prompt)
```

- First attempt: normal `input()` (zero overhead in the happy path)
- On `UnicodeDecodeError`: drain the corrupted buffer via `sys.stdin.buffer.readline()`, print a user-friendly message, then retry once with a fresh `input()`
- If the second `input()` also fails, let the exception propagate (indicates a deeper issue)

### 2. Replace all `input()` calls in `collector.py`

6 call sites:
- Line 173: `raw = input("> ").strip()` — Q0 greeting
- Line 183: `raw = input("> ").strip()` — Q1–Q6 loop
- Line 193: `raw = input("> ").strip()` — Q8–Q9 loop
- Line 235: `choice = input(enter_prompt).strip()` — Q7 strategy menu
- Line 255: `custom = input(...)`.strip()` — session length
- Line 270: `raw_date = input("  Deadline (YYYY-MM-DD): ").strip()` — deadline

All become `_safe_input(...)`.strip()`.

### 3. Add `import sys` to collector.py

Needed for `sys.stdin.buffer.readline()` in the fallback path.

### 4. Add test for the wrapper

New test in `agent/tests/test_collector.py` that verifies `_safe_input` retries on `UnicodeDecodeError` using `monkeypatch` on `builtins.input`.

## Files to modify

- `agent/collector.py` — add `_safe_input()`, replace 6 `input()` calls
- `agent/tests/test_collector.py` — new file, test for `_safe_input` retry behavior

## Verification

1. `uv run pytest agent/tests/ -v` — all tests pass (including new test)
2. Manual: `uv run python -m agent.main` with Cyrillic input — no crash
