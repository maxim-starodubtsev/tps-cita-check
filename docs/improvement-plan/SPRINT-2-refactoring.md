# Sprint 2 — Refactoring

**Estimated effort:** Half day
**Dependencies:** Sprint 1 (for clean base to refactor on)
**Goal:** Eliminate code duplication, reduce boilerplate, and improve module boundaries.

---

## Issues

### CQ-3: Extract step error-handler boilerplate `High` `M`

**Problem:** Every step (`step2`–`step8`) has identical 20-line try/except blocks: catch `PlaywrightTimeout` → screenshot → `StepResult(FAIL)`; catch `Exception` → screenshot → `StepResult(FAIL)`. This is duplicated 7 times.

**Files to change:**
- `tps_cita_check/steps/common.py` — add `run_step_safely()` helper
- `tps_cita_check/steps/step2_select_office.py` through `step8_fill_contact_info.py` — simplify `run()` methods

**Implementation:**
```python
# steps/common.py
def run_step_safely(
    step_id: str,
    ctx: "RunContext",
    inner_fn: Callable[["RunContext"], StepResult],
) -> StepResult:
    """Wraps a step's core logic with standardized error handling + screenshot."""
    try:
        return inner_fn(ctx)
    except PlaywrightTimeoutError as e:
        screenshot = _try_screenshot(step_id, ctx, "timeout")
        return StepResult(FAIL, error_type="timeout", error_details=str(e), screenshot=screenshot)
    except Exception as e:
        screenshot = _try_screenshot(step_id, ctx, "error")
        return StepResult(FAIL, error_type="exception", error_details=str(e), screenshot=screenshot)

def _try_screenshot(step_id, ctx, suffix):
    try:
        return save_debug_screenshot(ctx.page, ctx.config, f"{step_id}_{suffix}")
    except Exception as e:
        ctx.logger.debug(f"[{step_id}] Screenshot on error failed: {e}")
        return None
```

Each step becomes:
```python
def run(self, ctx):
    return run_step_safely(self.step_id, ctx, self._inner_run)

def _inner_run(self, ctx):
    # ... actual step logic, no try/except needed
```

**Traceability:** Also resolves ERR-1 (screenshot fallback logging).

**Status:** `TODO`
**Completed:** —

---

### CQ-1: Deduplicate `_load_dotenv` `Medium` `S`

**Problem:** Identical function in `appointment_checker.py:18-30` and `process_bot_commands.py:8-19`.

**Files to change:**
- Create `tps_cita_check/env_utils.py` with the shared function
- `appointment_checker.py` — replace with `from tps_cita_check.env_utils import load_dotenv`
- `process_bot_commands.py` — replace with `from tps_cita_check.env_utils import load_dotenv`

**Status:** `TODO`
**Completed:** —

---

### MAINT-5: Consolidate `_is_retriable_failure` / `_is_waf_error` `Medium` `S`

**Problem:** `runner.py:79-95` and `steps/common.py:63-71` both check identical error strings with different interfaces.

**Files to change:**
- `tps_cita_check/steps/common.py` — add unified `is_retriable_error(error_text: str) -> bool`
- `tps_cita_check/runner.py` — replace `_is_retriable_failure` with call to the common function

**Implementation:**
```python
# steps/common.py
RETRIABLE_PATTERNS = [
    "url was rejected", "fortigate",
    "sesión ha caducado", "no ofrece el servicio",
    "error en el sistema", "timeout",
]

def is_retriable_error(error_text: str) -> bool:
    text = (error_text or "").lower()
    return any(p in text for p in RETRIABLE_PATTERNS)
```

**Status:** `TODO`
**Completed:** —

---

### ERR-5: FortiGate dead-branch in step0 retry loop `Medium` `S`

**Problem:** `step0_load.py:27-30` — FortiGate check logs warning but never sets `last_error`, never triggers retry correctly.

**File to change:**
- `tps_cita_check/steps/step0_load.py:27-30`

**Implementation:**
```python
if is_fortigate_block(page):
    logger.warning("[step0] FortiGate block detected, retrying...")
    last_error = RuntimeError("FortiGate block detected")
    await asyncio.sleep(backoff)
    continue
```

**Status:** `TODO`
**Completed:** —

---

### ERR-6: `page.goto` after cooldown has no error handling `Medium` `S`

**Problem:** `runner.py:365` — navigation timeout after inter-office cooldown propagates up without screenshot or `StepResult`.

**File to change:**
- `tps_cita_check/runner.py:365`

**Implementation:**
```python
try:
    page.goto(config.start_url, timeout=config.navigation_timeout_ms, wait_until="domcontentloaded")
except Exception as e:
    logger.warning("Navigation after cooldown failed: %s", e)
    # Treat as retriable — will be caught by outer retry loop
    break
```

**Status:** `TODO`
**Completed:** —

---

### CQ-6: Extract `_launch_context` and `_run_office_loop` from `_run_once` `Medium` `M`

**Problem:** `runner.py:180-379` — 193 lines with browser launch + stealth + legacy mode + Phase 1 + Phase 2 all interleaved.

**Files to change:**
- `tps_cita_check/runner.py`

**Implementation plan:**
1. Extract `_launch_context(config, logger) -> (playwright, context, page)` — handles `launch_persistent_context`, stealth injection, extension loading
2. Extract `_run_office_loop(ctx, config, steps, start_office_idx) -> (results, completed_normally)` — handles per-office iteration, back-nav, TSPD clearing
3. `_run_once(config, logger, start_office_idx)` becomes a coordinator calling both

**Status:** `TODO`
**Completed:** —

---

### MAINT-1: Remove duplicate default office label `Medium` `S`

**Problem:** Default office label string appears in both `config.py:20` and `appointment_checker.py:49`.

**File to change:**
- `appointment_checker.py:49` — remove argparse `default=` for `--office-label`, use `default=None`
- Let `CheckerConfig.__post_init__` or the constructor supply the canonical default

**Status:** `TODO`
**Completed:** —

---

## Definition of Done

- [ ] All 7 step files simplified to use `run_step_safely()` wrapper
- [ ] `_load_dotenv` exists in exactly one place
- [ ] `_is_retriable_failure` and `_is_waf_error` replaced by single `is_retriable_error()`
- [ ] `_run_once` is under 80 lines
- [ ] All changes pass `pytest -q`
- [ ] PROGRESS.md updated with completion dates
