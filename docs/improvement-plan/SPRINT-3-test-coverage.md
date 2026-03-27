# Sprint 3 — Test Coverage

**Estimated effort:** Half-to-full day
**Dependencies:** Sprint 2 (refactored code is easier to test)
**Goal:** Cover the critical untested paths — multi-office loop, retry logic, bot handlers.

---

## Issues

### TEST-1 + TEST-4: Multi-office loop tests `High` `M`

**Problem:** The entire Phase 2 (per-office loop) has zero test coverage. Only the legacy `_override_steps` path is tested.

**File to create:**
- `tests/test_multi_office_runner.py`

**Test cases to cover:**
```
1. All offices return no_citas → completed_normally=True, ok=True, no_citas=True
2. Office 3 of 5 finds cita → stops early, ok=True, no_citas=False, found_cita_office set
3. Office 2 hits timeout → retry from office 2 (not office 1)
4. WAF block mid-run → retry from failed office index
5. All offices fail → ok=False
6. Single office config → flat screenshot dir (no per-office subdir)
7. Back-navigation + TSPD cookie clearing called between offices
```

**Test approach:** Mock Playwright entirely (same pattern as existing `test_step_runner_stops_on_fail.py`). Create mock steps that return configurable `StepResult`s per office.

**Status:** `TODO`
**Completed:** —

---

### TEST-2: `_is_retriable_failure` table-driven tests `High` `S`

**Problem:** String matching logic for retry decisions has no coverage.

**File to create:**
- `tests/test_retriable_errors.py`

**Test cases:**
```python
@pytest.mark.parametrize("error_text,expected", [
    ("URL was rejected", True),
    ("FortiGate block page", True),
    ("La sesión ha caducado", True),
    ("No ofrece el servicio solicitado", True),
    ("Error en el sistema", True),
    ("Timeout waiting for selector", True),
    ("No hay citas disponibles", False),
    ("Unexpected element not found", False),
    ("", False),
    (None, False),
])
def test_is_retriable_error(error_text, expected):
    assert is_retriable_error(error_text) == expected
```

**Depends on:** MAINT-5 (consolidated function in `steps/common.py`) from Sprint 2.

**Status:** `TODO`
**Completed:** —

---

### TEST-3: Bot command handler tests `High` `M`

**Problem:** `/status`, `/runs`, `/start`, `/stop`, `/help` — no tests. State file interactions, idle guards, provenance untested.

**File to create:**
- `tests/test_bot_commands.py`

**Test cases:**
```
1. /status when running — shows RUNNING, next run ETA, last run summary
2. /status when paused — shows PAUSED, paused_reason, paused_ts
3. /start when paused — writes started_ts, started_by="bot_command", returns confirmation
4. /start when running — idle guard returns "already running", no state write
5. /stop when running — writes paused_ts, paused_reason="user_stop_bot", returns confirmation
6. /stop when paused — idle guard returns "already paused", no state write
7. /runs with empty history — returns "no runs today"
8. /runs with 5 recent runs — returns formatted list
9. /help — returns command list text
10. Unknown command — no response (or error message)
```

**Test approach:** Create temp `state.json` and `run_history.json` files via `tmp_path` fixture. Mock Telegram API calls. Verify state file mutations and response text.

**Status:** `TODO`
**Completed:** —

---

### TEST-5: `_navigate_back_to_province` tests `Medium` `M`

**Problem:** Three navigation paths — Salir/Volver click, reload, fallback — with no coverage.

**File to create:**
- `tests/test_back_navigation.py`

**Test cases:**
```
1. "Salir" button visible → clicks it → province select visible → success
2. "Salir" button visible → clicks it → province select NOT visible → reloads start_url
3. No "Salir" button → "Volver" button visible → clicks it
4. No buttons visible → reloads start_url directly
5. Reload also fails → raises/returns error
```

**Status:** `TODO`
**Completed:** —

---

### TEST-6: `_load_dotenv` edge cases `Medium` `S`

**Problem:** No coverage for multiline values, quoted values, comment lines, empty values.

**File to create:**
- `tests/test_env_utils.py`

**Test cases:**
```
1. Standard KEY=VALUE lines
2. Quoted values: KEY="value with spaces"
3. Single-quoted: KEY='value'
4. Comment lines: # this is a comment
5. Empty lines (ignored)
6. Values with = signs: KEY=foo=bar
7. Pipe-delimited offices: CITA_OFFICES=A|B|C
8. Missing file → no error, no env changes
9. Existing env vars NOT overwritten
```

**Depends on:** CQ-1 (`_load_dotenv` extracted to `env_utils.py`) from Sprint 2.

**Status:** `TODO`
**Completed:** —

---

### Opportunistic: TEST-7 + TEST-8 `Low` `S`

**TEST-7:** Replace hand-rolled `_Logger` in `test_step_runner_stops_on_fail.py` with `MagicMock()`.

**TEST-8:** Pin `run_retry_attempts=1` and all relevant fields in test fixtures.

**Status:** `TODO`
**Completed:** —

---

## Definition of Done

- [ ] `pytest -q` passes with all new test files
- [ ] Multi-office loop: at least 5 test cases covering happy path, early stop, retry-from-offset
- [ ] Bot commands: at least 8 test cases covering all 5 commands + idle guards
- [ ] `_is_retriable_failure`: parametrized test with 10+ cases
- [ ] Coverage for `_navigate_back_to_province` all 3 paths
- [ ] PROGRESS.md updated with completion dates
