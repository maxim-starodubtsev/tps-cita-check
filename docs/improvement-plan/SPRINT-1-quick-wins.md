# Sprint 1 — Quick Wins

**Estimated effort:** 1-2 hours
**Dependencies:** None
**Goal:** Eliminate critical security risks and fix easy reliability bugs with minimal code changes.

---

## Issues

### SEC-4: Atomic state file writes `Critical` `S`

**Problem:** `state_path.write_text(json.dumps(state))` and `json.dump(s, open(f, 'w'))` write directly to the target file. Kill mid-write = corrupt JSON. Silent reset of all counters on next read.

**Files to change:**
- `tps_cita_check/bot.py:65-66` — `_write_state()` function
- `scheduler/run.sh:177-191`, `193-201` — inline Python state writes

**Implementation:**
```python
# bot.py — _write_state()
import tempfile, os
tmp_fd, tmp_path = tempfile.mkstemp(dir=state_path.parent, suffix=".tmp")
try:
    with os.fdopen(tmp_fd, "w") as f:
        json.dump(state, f)
    os.replace(tmp_path, state_path)
except:
    os.unlink(tmp_path)
    raise
```

For `run.sh`: extract into `scheduler/state_utils.py` (see SEC-3 in Sprint 4) or apply same write-tmp + mv pattern in the Python `-c` snippets.

**Status:** `TODO`
**Completed:** —

---

### SEC-1: Telegram token log leak risk `High` `S`

**Problem:** Token is embedded in Telegram API URL. Any `urllib` error log or future `logger.debug(url)` would expose it to `artifacts/run.log`.

**Files to change:**
- `tps_cita_check/telegram.py:16` — `send_message()`
- `tps_cita_check/telegram.py:38` — `send_photo()`
- `tps_cita_check/bot.py:46` — `get_updates()`

**Implementation:** Wrap urllib calls in try/except that masks the token before re-raising or logging:
```python
except urllib.error.URLError as e:
    logger.warning("Telegram API call failed: %s", str(e).replace(token, "***"))
```

**Status:** `TODO`
**Completed:** —

---

### SEC-2: Config repr redaction for secrets `High` `S`

**Problem:** `CheckerConfig` frozen dataclass exposes `nie`, `full_name`, `email`, `phone`, `telegram_bot_token`, `telegram_chat_id` in repr/str.

**File to change:**
- `tps_cita_check/config.py` — `CheckerConfig` field declarations

**Implementation:**
```python
@dataclass(frozen=True)
class CheckerConfig:
    nie: str = field(default="", repr=False)
    full_name: str = field(default="", repr=False)
    email: str = field(default="", repr=False)
    phone: str = field(default="", repr=False)
    telegram_bot_token: str = field(default="", repr=False)
    telegram_chat_id: str = field(default="", repr=False)
    # ... rest unchanged
```

**Status:** `TODO`
**Completed:** —

---

### ERR-2: `summary` possibly unbound in fallback return `Medium` `S`

**Problem:** `runner.py:486-491` — if `max_attempts == 0`, `summary` is never assigned → `UnboundLocalError`.

**File to change:**
- `tps_cita_check/runner.py` — `run_check()` function

**Implementation:** Before the `for attempt` loop:
```python
summary = RunSummary(ok=False, no_citas=True, results=[], office_results=())
```

**Status:** `TODO`
**Completed:** —

---

### ERR-3: `results[-1]` without empty check `Medium` `S`

**Problem:** `appointment_checker.py:177` — `summary.results[-1]` raises `IndexError` when results is empty.

**File to change:**
- `appointment_checker.py:177`

**Implementation:**
```python
if summary.results:
    last = summary.results[-1]
    # ... existing notification logic
else:
    # fallback notification for "run failed before any step completed"
    msg = "Run failed: no steps completed"
```

**Status:** `TODO`
**Completed:** —

---

### ERR-4: Silent `except Exception` in bot.py readers `Medium` `S`

**Problem:** `bot.py:51,59,98` — Telegram 401, corrupt JSON, and permission errors all return empty defaults silently.

**File to change:**
- `tps_cita_check/bot.py:51-52`, `58-60`, `97-99`

**Implementation:** Add `logger.warning(...)` before each `return`:
```python
except Exception as e:
    logger.warning("get_updates failed: %s", e)
    return []
```

**Status:** `TODO`
**Completed:** —

---

### SEC-6: `process_bot_commands.py` swallowed errors `Medium` `S`

**Problem:** `except Exception: pass` at line 36-37 hides all errors.

**File to change:**
- `process_bot_commands.py:36-37`

**Implementation:**
```python
except Exception:
    import logging
    logging.getLogger(__name__).warning("Bot command processing failed", exc_info=True)
```

**Status:** `TODO`
**Completed:** —

---

### CQ-7: `headless=False` hardcoded comment `Medium` `S`

**Problem:** `runner.py:212` passes `headless=False` while also injecting `--headless=new` via args. Contradictory.

**File to change:**
- `tps_cita_check/runner.py:212`

**Implementation:** Add clarifying comment or pass `headless=config.headless`:
```python
# headless=False required here because the Chrome extension requires a
# non-headless context API parameter; --headless=new is injected via
# args to get "new headless" mode which supports extensions.
headless=False,
```

**Status:** `TODO`
**Completed:** —

---

### MAINT-4 + CQ-5: Quick dedup + dead code removal `Low` `S`

**MAINT-4:** `API_BASE` defined identically in `telegram.py:11` and `bot.py:13`.
- **Fix:** Define once in `telegram.py`, `from .telegram import API_BASE` in `bot.py`.

**CQ-5:** Dead `quality` parameter in `screenshot_utils.py:58`.
- **Fix:** Remove the parameter.

**Status:** `TODO`
**Completed:** —

---

## Definition of Done

- [ ] All changes pass `pytest -q`
- [ ] No new warnings from `python -m py_compile` on changed files
- [ ] PROGRESS.md updated with completion dates
- [ ] Each fix verified with a manual spot-check or test
