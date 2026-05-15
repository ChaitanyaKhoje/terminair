---
phase: "03"
status: findings
reviewed_files:
  - terminair/app.py
  - terminair/tests/test_app_demo.py
critical: 0
warning: 3
info: 2
---

# Phase 03: Code Review Report

**Reviewed:** 2026-05-15T00:00:00Z
**Depth:** standard
**Files Reviewed:** 2
**Status:** findings

## Summary

Phase 03 adds four `_flash_warn()` calls to the fallback branches of `_build_data_provider` in `app.py`, and one new test (`test_manifest_configured_but_missing_calls_flash_warn`) in `test_app_demo.py`. The logic is broadly sound — warnings are appropriate, fallback to `MockDataProvider` is consistent, and message text is descriptive. However, three quality/correctness issues were found that should be fixed before this code is considered stable, and two informational issues are noted.

---

## Warnings

### WR-01: Path leaked into flash message — may expose filesystem layout

**File:** `terminair/app.py:111`
**Issue:** The flash message includes the raw `manifest_path` value from config:
```python
self._flash_warn(f"dbt manifest missing at {manifest_path or 'unset'} — using demo data")
```
`manifest_path` is a `pathlib.Path` resolved from user config, which will commonly be an absolute path such as `/home/username/projects/myproject/target/manifest.json`. This path is displayed verbatim in the TUI flash bar. While this is a local developer tool and no remote user sees the message, the CLAUDE.md constraint "No prod data" and the general principle that flash messages should not dump raw filesystem state argues for truncating or just omitting the path. More concretely: if the path comes from an env-var expansion in config.yaml (e.g. `${HOME}/...`), the expanded value will be shown — potentially surprising in screen-share or screenshot contexts.

A related inconsistency: the `_logger.warning()` call on line 107–110 already uses `manifest_path or '<unset>'` (with angle brackets as a sentinel), but the flash message uses `'unset'` (without). These two representations of the same sentinel state differ silently.

**Fix:** Either omit the path from the user-visible message (path is in the log for debugging), or truncate it to just the filename:
```python
path_label = manifest_path.name if manifest_path else "unset"
self._flash_warn(f"dbt manifest missing ({path_label}) — using demo data")
```

---

### WR-02: Snowflake fallback branch silently swallows the exception — no flash_warn issued

**File:** `terminair/app.py:139-144`
**Issue:** The Snowflake client initialisation block:
```python
if active_connection.snowflake is not None:
    try:
        snowflake = SnowflakeClient()
    except Exception as exc:
        _logger.warning("Snowflake client unavailable — continuing without it: %s", exc)
```
This `except` block logs to the logger but does **not** call `self._flash_warn(...)`. All three other fallback branches in the same function were updated in Phase 03 to call `_flash_warn`. The Snowflake branch is the only one that remains silent at the UI level. The `SnowflakeClient.__init__` can raise (e.g. `FileNotFoundError` when mock mode is on and the fixture file is absent), and when it does the user has no indication from the TUI that Snowflake data is missing.

This is an inconsistency introduced by the Phase 03 change: the stated goal was to add `_flash_warn` to "four fallback branches", but the Snowflake branch is a fifth fallback that was missed.

**Fix:** Add a `_flash_warn` call consistent with the others:
```python
except Exception as exc:
    _logger.warning("Snowflake client unavailable — continuing without it: %s", exc)
    self._flash_warn("Snowflake client unavailable — continuing without it")
```

---

### WR-03: Test does not assert the content of the flash_warn message beyond the word "manifest"

**File:** `terminair/tests/test_app_demo.py:53`
**Issue:** The test verifies only that the captured message contains the substring `"manifest"`:
```python
assert "manifest" in flash_warn_calls[0].lower()
```
This assertion would pass even if the message were accidentally changed to something like `"manifest path error"` or if a future refactor changed the branch so that a *different* warning (e.g. the dbt-data-layer-unavailable branch on line 125) fires first. Both of those branches return `MockDataProvider`, so the `len == 1` check is the only guard against multiple fires — but a message from the wrong branch that happens to contain the word "manifest" would produce a false-green test.

More importantly, the test monkeypatches `_flash_warn` **after** calling `TerminairApp(file_config, demo_mode=False)` but **before** calling `app.get_data_provider()`. This is correct because `_build_data_provider` is only called lazily via `get_data_provider`. However, if someone adds an eager call in `__init__`, the monkeypatch would arrive too late and the test would silently miss the call. This ordering dependency is not documented.

**Fix:** Strengthen the assertion to check message content more specifically, and add a comment explaining the monkeypatch ordering requirement:
```python
# monkeypatch must be applied before get_data_provider(), which calls _build_data_provider lazily
monkeypatch.setattr(app, "_flash_warn", lambda text: flash_warn_calls.append(text))

provider = app.get_data_provider()

assert isinstance(provider, MockDataProvider)
assert len(flash_warn_calls) == 1, f"Expected exactly 1 warn, got: {flash_warn_calls}"
assert "missing" in flash_warn_calls[0].lower(), f"Unexpected message: {flash_warn_calls[0]}"
assert "manifest" in flash_warn_calls[0].lower(), f"Unexpected message: {flash_warn_calls[0]}"
```

---

## Info

### IN-01: _flash_warn silently swallows all exceptions — makes it impossible to detect test setup failures

**File:** `terminair/app.py:80-85`
**Issue:** The `_flash_warn` implementation:
```python
def _flash_warn(self, text: str):
    try:
        self.query_one(FlashBar).flash_warn(text)
    except Exception:
        pass
```
This pattern (copied from `_flash_error`) is intentional for production use — calling flash methods before the widget tree is mounted would otherwise crash. However, the bare `except: pass` means that **in tests**, when the app is constructed but never mounted, calling `_flash_warn` is a no-op. The test in `test_app_demo.py` correctly avoids this by monkeypatching `_flash_warn` on the instance before exercising the code. This is the right approach, but it is worth noting that any test that forgets to monkeypatch will silently observe zero calls even if the flash is fired. There is no mechanism to detect this mistake.

No immediate code change required; this is an observation about test fragility inherited from the existing `_flash_error` pattern.

---

### IN-02: Sentinel string inconsistency between logger and flash message

**File:** `terminair/app.py:109-111`
**Issue:** Minor textual inconsistency. The logger uses `"<unset>"` (with angle brackets, line 109) as a sentinel, and the flash message uses `"unset"` (without angle brackets, line 111). This is cosmetically inconsistent and could cause confusion when cross-referencing log output with UI messages:

```python
# line 109 (logger):
"dbt manifest missing at %s — using demo data",
manifest_path or "<unset>",

# line 111 (flash):
f"dbt manifest missing at {manifest_path or 'unset'} — using demo data"
```

**Fix:** Align both to the same sentinel, preferably `"<unset>"` since it is visually distinct as a placeholder:
```python
self._flash_warn(f"dbt manifest missing at {manifest_path or '<unset>'} — using demo data")
```

---

_Reviewed: 2026-05-15T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
