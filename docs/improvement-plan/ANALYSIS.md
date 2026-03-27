# Codebase Analysis — TPS Cita Check

**Date:** 2026-03-27
**Scope:** All source files (excluding `.venv/`, `__pycache__/`, `artifacts/`)

---

## File Inventory

| File | LOC | Role |
|------|-----|------|
| `appointment_checker.py` | 194 | CLI entrypoint |
| `process_bot_commands.py` | 37 | Scheduler bot-command stub |
| `tps_cita_check/config.py` | 104 | `CheckerConfig` frozen dataclass |
| `tps_cita_check/context.py` | 60 | `RunContext` mutable carrier |
| `tps_cita_check/runner.py` | 493 | Orchestration + multi-office loop |
| `tps_cita_check/step_framework.py` | 32 | `Step`, `StepResult`, `StepStatus` |
| `tps_cita_check/steps/common.py` | 116 | Shared helpers, `retry_step`, WAF checks |
| `tps_cita_check/steps/step0_load.py` | 83 | Load initial URL |
| `tps_cita_check/steps/step1_verify_province.py` | 128 | Verify / select province |
| `tps_cita_check/steps/step2_select_office.py` | 124 | Select office from `<select>` |
| `tps_cita_check/steps/step3_select_tramite.py` | 150 | Select trámite |
| `tps_cita_check/steps/step4_accept.py` | 101 | Click Aceptar |
| `tps_cita_check/steps/step5_entrar.py` | 96 | Click Entrar |
| `tps_cita_check/steps/step6_fill_personal_data.py` | 156 | Fill NIE + name |
| `tps_cita_check/steps/step7_solicitar_cita.py` | 116 | Click Solicitar Cita |
| `tps_cita_check/steps/step8_fill_contact_info.py` | 191 | Fill phone + email |
| `tps_cita_check/telegram.py` | 70 | Telegram Bot API |
| `tps_cita_check/bot.py` | 330 | Bot command handlers |
| `tps_cita_check/logging_utils.py` | 31 | Logger setup |
| `tps_cita_check/screenshot_utils.py` | 74 | Screenshot + resize |
| `tps_cita_check/baseline_utils.py` | 32 | Baseline image comparison |
| `tps_cita_check/stealth.py` | 19 | Stealth JS injection |
| `tps_cita_check/chrome_extension/content.js` | 39 | Extension content script |
| `tps_cita_check/chrome_extension/manifest.json` | 13 | Extension manifest |
| `scheduler/run.sh` | 226 | Bash scheduler with WAF backoff |
| `scheduler/com.tps.cita-check.plist` | 29 | launchd config |
| `tests/test_screenshot_resize.py` | 20 | Resize unit test |
| `tests/test_step_runner_stops_on_fail.py` | 71 | Runner stops-on-fail test |
| `tests/test_steps_common.py` | 29 | WAF-detection helpers test |

---

## 1. Code Quality

### CQ-1: `_load_dotenv` duplicated verbatim
- **Files:** `appointment_checker.py:18-30`, `process_bot_commands.py:8-19`
- **Problem:** Identical 12-line function in two scripts. Any change must be made in two places.
- **Fix:** Move to `tps_cita_check/env_utils.py` and import in both scripts.
- **Priority:** Medium | **Effort:** S

### CQ-2: `label.split(",")[0]` duplicated in 3 places
- **Files:** `bot.py:85-87`, `runner.py:400`, `context.py:25`
- **Problem:** Short-name extraction pattern copy-pasted. Display form vs filesystem form differ.
- **Fix:** Export `office_short_name(label: str) -> str` from `context.py` or a shared util.
- **Priority:** Low | **Effort:** S

### CQ-3: Step error-handling boilerplate copy-pasted 7 times
- **Files:** Every step file `step2` through `step8` — identical 20-line try/except blocks
- **Problem:** SRP violation. Adding a third failure category requires changing 7 files.
- **Fix:** Extract `_run_with_screenshot_on_error(step_id, cfg, page, fn, ctx)` into `steps/common.py`. Steps reduce to one-liner delegation.
- **Priority:** High | **Effort:** M

### CQ-4: `context.py:37` — `logger: any` uses Python builtin
- **File:** `tps_cita_check/context.py:37-40`
- **Problem:** `logger: any` uses the builtin `any()` function instead of `typing.Any`. Type checkers silently accept it but semantics are wrong.
- **Fix:** Use `logger: logging.Logger`, `browser: Optional[BrowserContext]`, `page: Optional[Page]`.
- **Priority:** Low | **Effort:** S

### CQ-5: `screenshot_utils.py:58` — dead `quality` parameter
- **File:** `tps_cita_check/screenshot_utils.py:58`
- **Problem:** `quality: Optional[int] = None` declared but never passed to `page.screenshot()` or `img.save()`.
- **Fix:** Remove the parameter, or wire it through.
- **Priority:** Low | **Effort:** S

### CQ-6: `runner.py:180-379` — `_run_once` is 193 lines with multiple responsibilities
- **File:** `tps_cita_check/runner.py:180-379`
- **Problem:** Handles browser launch, stealth injection, legacy mode, Phase 1, and Phase 2 (per-office loop + back-nav + TSPD clearing + province re-verify). Hard to unit test.
- **Fix:** Extract `_launch_context()` and `_run_office_loop()` helpers. `_run_once` becomes ~50 lines.
- **Priority:** Medium | **Effort:** M

### CQ-7: `runner.py:212` — `headless=False` hardcoded despite config
- **File:** `tps_cita_check/runner.py:212`
- **Problem:** `launch_persistent_context(..., headless=False)` while also injecting `--headless=new` via args. Contradictory — relies on undocumented CLI-overrides-API behaviour.
- **Fix:** Pass `headless=config.headless` and remove the manual arg injection, or document the intentional override.
- **Priority:** Medium | **Effort:** S

### CQ-8: Missing type annotations on `Step` base class
- **File:** `tps_cita_check/step_framework.py:25-31`
- **Problem:** `Step.run(self, ctx)` — `ctx` has no type annotation. No type inference for callers.
- **Fix:** Annotate `def run(self, ctx: "RunContext") -> StepResult` with `TYPE_CHECKING` guard.
- **Priority:** Low | **Effort:** S

---

## 2. Security & Vulnerabilities

### SEC-1: Telegram bot token leakable via log URLs
- **Files:** `telegram.py:16`, `bot.py:46`
- **Problem:** Token is part of the API URL. If `urllib` logs the URL on error, or if a future `logger.debug(url)` is added, the token appears in `artifacts/run.log`.
- **Fix:** Never log the raw URL. Mask the token in any error messages.
- **Priority:** High | **Effort:** S

### SEC-2: `CheckerConfig` has no repr redaction for secrets
- **Files:** `tps_cita_check/config.py`
- **Problem:** `telegram_bot_token`, `nie`, `full_name`, `email`, `phone` all print in plain text if the config is ever logged or printed.
- **Fix:** Add `field(repr=False)` to all sensitive fields.
- **Priority:** High | **Effort:** S

### SEC-3: Shell injection in `run.sh` via Python `-c` with embedded shell variables
- **Files:** `scheduler/run.sh:101-108`, `177-191`, `193-201`
- **Problem:** Shell variables interpolated into `python3 -c "..."` strings. A double-quote or semicolon in any variable would inject code.
- **Fix:** Replace inline `-c` blocks with a dedicated `scheduler/state_utils.py` script using `sys.argv`.
- **Priority:** High | **Effort:** M

### SEC-4: State file written non-atomically (race/corruption)
- **Files:** `bot.py:65-66`, `scheduler/run.sh:177-201`
- **Problem:** `write_text(json.dumps(state))` directly to target file. Kill mid-write = corrupt JSON. Next read returns `{}` silently, resetting all counters.
- **Fix:** Write to `.tmp` first, then `os.replace(tmp, target)`. One-line change.
- **Priority:** Critical | **Effort:** S

### SEC-5: `.env` not validated for dangerous content
- **File:** `appointment_checker.py:18-30`
- **Problem:** No format validation on loaded values. Malformed `CITA_ARTIFACTS_DIR` could be passed to `Path()`.
- **Fix:** Validate expected formats: NIE matches `[XYZ]\d{7}[A-Z]`, phone is digits, email contains `@`.
- **Priority:** Low | **Effort:** S

### SEC-6: `process_bot_commands.py:36-37` — bare `except Exception: pass`
- **File:** `process_bot_commands.py:36-37`
- **Problem:** All errors silently discarded. Import errors, logic bugs, permission errors are invisible.
- **Fix:** Replace `pass` with `logging.warning("Bot command processing failed", exc_info=True)`.
- **Priority:** Medium | **Effort:** S

---

## 3. Error Handling & Reliability

### ERR-1: Screenshot fallback blocks silently swallow errors
- **Files:** `step2:93,114`, `step3:119,140`, `step4:70,91`, `step5:66,87`, `step6:126,147`, `step7:86,107`, `step8:161,182`
- **Problem:** `except Exception: screenshot = None` — no log of why screenshot capture failed.
- **Fix:** `except Exception as e: logger.debug(f"Screenshot on error failed: {e}"); screenshot = None`
- **Priority:** Medium | **Effort:** S

### ERR-2: `runner.py:486-491` — `summary` possibly unbound in fallback return
- **File:** `tps_cita_check/runner.py:486-491`
- **Problem:** If `max_attempts == 0`, `summary` is never assigned. `UnboundLocalError` at runtime.
- **Fix:** Initialise `summary = RunSummary(ok=False, results=[], ...)` before the loop.
- **Priority:** Medium | **Effort:** S

### ERR-3: `appointment_checker.py:177` — `summary.results[-1]` without empty check
- **File:** `appointment_checker.py:177`
- **Problem:** If `results` is empty (browser context failed to open), `IndexError` at notification stage.
- **Fix:** Guard with `if summary.results:` before indexing.
- **Priority:** Medium | **Effort:** S

### ERR-4: `bot.py:51,59,98` — silent `except Exception: return []`
- **Files:** `tps_cita_check/bot.py:51-52`, `58-60`, `97-99`
- **Problem:** Telegram 401 indistinguishable from network timeout. Corrupt state file indistinguishable from missing one.
- **Fix:** Log exception at `WARNING` level, keep `return []`/`{}` non-raising behaviour.
- **Priority:** Medium | **Effort:** S

### ERR-5: `step0_load.py` — FortiGate dead-branch in retry loop
- **File:** `tps_cita_check/steps/step0_load.py:27-30`
- **Problem:** FortiGate check logs warning but never sets `last_error`, never `break`s. Falls through to `ensure_not_rejected` which doesn't check FortiGate pages. Exhausts all attempts with wrong error message.
- **Fix:** Set `last_error = RuntimeError("FortiGate block")` and `continue` to backoff.
- **Priority:** Medium | **Effort:** S

### ERR-6: `runner.py:365` — `page.goto` after cooldown has no error handling
- **File:** `tps_cita_check/runner.py:365`
- **Problem:** Navigation timeout propagates up with no screenshot and no `StepResult`. Silent failure.
- **Fix:** Wrap in try/except; log URL and exception before proceeding.
- **Priority:** Medium | **Effort:** S

### ERR-7: Inter-office cooldown uses blocking `time.sleep`
- **File:** `tps_cita_check/runner.py:362`
- **Problem:** `time.sleep(30-60s)` blocks the thread. SIGTERM during sleep is not handled.
- **Fix:** Use repeated short `time.sleep(1)` with signal flag check, or `page.wait_for_timeout()`.
- **Priority:** Low | **Effort:** S

---

## 4. Performance & Scalability

### PERF-1: `step3` polling loop re-queries DOM every 500ms
- **File:** `tps_cita_check/steps/step3_select_tramite.py:26-39`
- **Problem:** Manual polling loop instead of Playwright's built-in wait.
- **Fix:** Replace with `page.locator("select").nth(1).wait_for(state="attached", timeout=...)`.
- **Priority:** Low | **Effort:** S

### PERF-2: Baselines keyed by step only, not per-office
- **File:** `tps_cita_check/runner.py:56-58`
- **Problem:** 9 offices overwrite the same baseline. Layout differences across offices are masked.
- **Fix:** Key baselines by `step_id + office_slug`.
- **Priority:** Low | **Effort:** S

### PERF-3: Full browser restart on retry is intentional but undocumented
- **File:** `tps_cita_check/runner.py:206-223`
- **Problem:** Each retry calls `launch_persistent_context()` — fresh Chrome process. 1-3s overhead.
- **Fix:** Add comment confirming this is deliberate (fresh TSPD session).
- **Priority:** Low | **Effort:** S

### PERF-4: Screenshot encode/decode on every step
- **File:** `tps_cita_check/screenshot_utils.py:44-45`
- **Problem:** Full PNG → Pillow open → resize → re-save. 72 cycles per 9-office run.
- **Fix:** Use `page.screenshot(scale="css")` to halve size on HiDPI before Pillow resize.
- **Priority:** Low | **Effort:** S

---

## 5. Testability & Test Coverage

### TEST-1: Multi-office loop entirely untested
- **Problem:** 4 test cases total. Entire Phase 2 (per-office loop) has zero coverage. Missing: all-offices-no-citas, cita-found-stops-early, back-navigation paths.
- **Fix:** Multi-office runner tests with mocked Playwright steps.
- **Priority:** High | **Effort:** M

### TEST-2: WAF retry / `_is_retriable_failure` untested
- **Problem:** The function that decides whether to retry from failed office has no test coverage. String matching logic is subtle.
- **Fix:** Table-driven test: `[(error_details, expected_bool), ...]`.
- **Priority:** High | **Effort:** S

### TEST-3: Bot command handlers untested
- **Problem:** `/status`, `/runs`, `/start`, `/stop`, `/help` — no tests. State file interactions, idle guards, provenance fields untested.
- **Fix:** Bot handler tests with temp state file and run history fixtures.
- **Priority:** High | **Effort:** M

### TEST-4: Only legacy `_override_steps` path tested, not real multi-office path
- **File:** `tests/test_step_runner_stops_on_fail.py:51-71`
- **Problem:** `run_check(steps=steps)` exercises legacy path only. Multi-office loop completely untested.
- **Fix:** Add test exercising `run_check(config=cfg_with_two_offices)` with mocked steps.
- **Priority:** High | **Effort:** M

### TEST-5: `_navigate_back_to_province` untested
- **Problem:** Three navigation paths (Salir/Volver click, reload, fallback) with no coverage.
- **Fix:** Mock page state for each path, verify correct navigation method is used.
- **Priority:** Medium | **Effort:** M

### TEST-6: `_load_dotenv` edge cases untested
- **Problem:** Multiline values, quoted values, comment lines, empty values.
- **Fix:** Unit tests with temp `.env` files.
- **Priority:** Medium | **Effort:** S

### TEST-7: Hand-rolled `_Logger` stub breaks on `logger.critical()`
- **File:** `tests/test_step_runner_stops_on_fail.py:10-26`
- **Problem:** Missing methods cause `AttributeError` instead of meaningful failures.
- **Fix:** Replace with `unittest.mock.MagicMock()` or `logging.getLogger("test")`.
- **Priority:** Low | **Effort:** S

### TEST-8: Hard-coded default config in tests is brittle
- **File:** `tests/test_step_runner_stops_on_fail.py:66`
- **Problem:** Default changes (e.g. `run_retry_attempts` raised from 3 to 5) cause unexpected behaviour.
- **Fix:** Pin all relevant fields explicitly: `run_retry_attempts=1`.
- **Priority:** Low | **Effort:** S

---

## 6. Maintainability & Architecture

### MAINT-1: Default office label defined in two places
- **Files:** `config.py:20`, `appointment_checker.py:49`
- **Problem:** Same default string repeated. One source of truth violated.
- **Fix:** Remove argparse default; let `CheckerConfig` be the single source.
- **Priority:** Medium | **Effort:** S

### MAINT-2: `RunSummary.results` is mutable list in frozen dataclass
- **File:** `tps_cita_check/runner.py:34`
- **Problem:** `frozen=True` prevents rebinding but list contents are still mutable.
- **Fix:** Change to `tuple[StepResult, ...]`.
- **Priority:** Low | **Effort:** S

### MAINT-3: `Step` base class attributes not enforced
- **File:** `tps_cita_check/step_framework.py:25-31`
- **Problem:** `step_id` and `title` not abstract. Missing them raises `AttributeError` at runtime.
- **Fix:** Use `abc.ABC` with `@property @abstractmethod`, or `ClassVar[str]`.
- **Priority:** Low | **Effort:** S

### MAINT-4: `API_BASE` defined identically in `telegram.py` and `bot.py`
- **Files:** `telegram.py:11`, `bot.py:13`
- **Problem:** Same constant in two files.
- **Fix:** Define once in `telegram.py`, import in `bot.py`.
- **Priority:** Low | **Effort:** S

### MAINT-5: `_is_retriable_failure` duplicates `_is_waf_error` with subtle differences
- **Files:** `runner.py:79-95`, `steps/common.py:63-71`
- **Problem:** Both check same error strings with different interfaces.
- **Fix:** Consolidate into one function in `steps/common.py`.
- **Priority:** Medium | **Effort:** S

### MAINT-6: `step6` hardcodes `_ENTRY_URL` bypassing `CheckerConfig`
- **File:** `tps_cita_check/steps/step6_fill_personal_data.py:8`
- **Problem:** If base URL changes, this step needs a separate update.
- **Fix:** Derive from `cfg.base_url` or add `entry_url` property to `CheckerConfig`.
- **Priority:** Low | **Effort:** S

---

## 7. Operational Concerns

### OPS-1: Unstructured log format — no machine-parseable output
- **File:** `tps_cita_check/logging_utils.py:19`
- **Problem:** Plain text logs. Scheduler does fragile `grep` for WAF detection.
- **Fix:** Add JSON `RotatingFileHandler` alongside human-readable one. Each record: `{"ts", "level", "run_id", "step", "event", "office"}`.
- **Priority:** Medium | **Effort:** M

### OPS-2: No log rotation — `FileHandler` appends unboundedly
- **File:** `tps_cita_check/logging_utils.py:21-22`
- **Problem:** Log grows without bound when run outside scheduler. 600-line truncation in `run.sh` covers barely 2-3 full runs.
- **Fix:** Replace with `RotatingFileHandler(maxBytes=5*1024*1024, backupCount=3)`. Remove manual truncation from `run.sh`.
- **Priority:** Medium | **Effort:** S

### OPS-3: No liveness signal from scheduler
- **Files:** `scheduler/run.sh`, `scheduler/com.tps.cita-check.plist`
- **Problem:** If launchd stops firing (macOS update, sleep/wake), `/status` reports RUNNING while nothing runs.
- **Fix:** Write `artifacts/last_scheduler_wake.txt` at every `run.sh` invocation. `/status` warns if >2h stale.
- **Priority:** Medium | **Effort:** S

### OPS-4: `run.sh` reads state 5 times with 5 separate `python3 -c` processes
- **File:** `scheduler/run.sh:59-63`
- **Problem:** 5 Python interpreter startups per scheduler wake (~0.5-1s overhead).
- **Fix:** Single `python3 -c` printing all fields, parsed with `read`.
- **Priority:** Low | **Effort:** S

### OPS-5: launchd plist hardcodes absolute path with username
- **File:** `scheduler/com.tps.cita-check.plist:11-12`, `24-25`
- **Problem:** Cannot commit meaningfully; breaks on path/user change.
- **Fix:** Generate from template via `setup_launchd.sh` using `$(pwd)` / `$(whoami)`.
- **Priority:** Low | **Effort:** S

### OPS-6: Screenshot cleanup in `run.sh` uses fragile `ls`+`rm -rf` loop
- **File:** `scheduler/run.sh:213-216`
- **Problem:** Fragile if directory names contain spaces. String concatenation with `$dir` could hit unintended paths.
- **Fix:** Use `find ... -maxdepth 1 -type d | sort -r | tail -n +N | xargs rm -rf`.
- **Priority:** Low | **Effort:** S

### OPS-7: Baselines directory never pruned
- **File:** `tps_cita_check/runner.py:56-58`
- **Problem:** Old baselines accumulate if step IDs change or new steps are added.
- **Fix:** Sweep at runner startup: remove baselines for step IDs not in the current step list.
- **Priority:** Low | **Effort:** S
