# Progress Tracker — TPS Cita Check Improvement Plan

**Last updated:** 2026-03-27 — All 28 planned issues complete

## Summary

| Sprint | Issues | Done | In Progress | Blocked | Remaining |
|--------|--------|------|-------------|---------|-----------|
| Sprint 1 — Quick Wins | 9 | 9 | 0 | 0 | 0 |
| Sprint 2 — Refactoring | 7 | 7 | 0 | 0 | 0 |
| Sprint 3 — Test Coverage | 6 | 6 | 0 | 0 | 0 |
| Sprint 4 — Operational | 5 | 5 | 0 | 0 | 0 |
| Pre-done | 1 | 1 | 0 | 0 | 0 |
| **Total** | **28** | **28** | **0** | **0** | **0** |

---

## All Issues by Status

### Critical

| ID | Issue | Sprint | Status | Notes |
|----|-------|--------|--------|-------|
| SEC-4 | Atomic state file writes | 1 | `DONE` | bot.py: write-tmp + os.replace |

### High

| ID | Issue | Sprint | Status | Notes |
|----|-------|--------|--------|-------|
| SEC-1 | Telegram token log leak risk | 1 | `DONE` | _mask_token() in telegram.py + bot.py |
| SEC-2 | Config repr redaction for secrets | 1 | `DONE` | field(repr=False) on 6 fields |
| SEC-3 | Shell injection in `run.sh` `-c` blocks | 4 | `DONE` | state_utils.py replaces all python3 -c blocks |
| CQ-3 | Step error-handler boilerplate (7 files) | 2 | `DONE` | run_step_safely() + _try_screenshot() in common.py; steps 2-8 refactored |
| TEST-1 | Multi-office loop tests | 3 | `DONE` | test_multi_office_runner.py: 6 _run_office_loop unit tests |
| TEST-2 | `_is_retriable_failure` tests | 3 | `DONE` | test_retriable_errors.py: 17 parametrized cases |
| TEST-3 | Bot command handler tests | 3 | `DONE` | test_bot_commands.py: 12 tests for all 5 handlers |
| TEST-4 | Multi-office path test (not legacy) | 3 | `DONE` | test_multi_office_runner.py: run_check integration test |

### Medium

| ID | Issue | Sprint | Status | Notes |
|----|-------|--------|--------|-------|
| SEC-6 | `process_bot_commands.py` swallowed errors | 1 | `DONE` | warning log + exc_info=True |
| ERR-1 | Screenshot fallback silent errors | 2 | `DONE` | Resolved by CQ-3: _try_screenshot() in common.py |
| ERR-2 | `summary` possibly unbound | 1 | `DONE` | init before loop |
| ERR-3 | `results[-1]` without empty check | 1 | `DONE` | guard + fallback msg |
| ERR-4 | Silent `except` in bot.py readers | 1 | `DONE` | warning logs in 3 functions |
| ERR-5 | FortiGate dead-branch in step0 | 2 | `DONE` | set last_error in FortiGate branch |
| ERR-6 | `page.goto` after cooldown unhandled | 2 | `DONE` | wrapped in try/except with warning log |
| CQ-1 | `_load_dotenv` duplicated | 2 | `DONE` | extracted to tps_cita_check/env_utils.py |
| CQ-6 | `_run_once` SRP violation | 2 | `DONE` | extracted _launch_context + _run_office_loop |
| CQ-7 | `headless=False` hardcoded | 1 | `DONE` | clarifying comment added |
| MAINT-1 | Default office label in 2 places | 2 | `DONE` | argparse default=None; CheckerConfig supplies canonical default |
| MAINT-5 | `_is_retriable_failure` duplicates `_is_waf_error` | 2 | `DONE` | RETRIABLE_PATTERNS + is_retriable_error() in common.py |
| OPS-1 | Unstructured log format | 4 | `DONE` | _JsonFormatter + JSONL RotatingFileHandler in logging_utils.py |
| OPS-2 | No log rotation | 4 | `DONE` | RotatingFileHandler (5 MB, 3 backups); run.sh truncation removed |
| OPS-3 | No scheduler liveness signal | 4 | `DONE` | run.sh writes last_scheduler_wake.txt; /status warns if >120 min |
| TEST-5 | `_navigate_back_to_province` untested | 3 | `DONE` | test_back_navigation.py: 5 tests |
| TEST-6 | `_load_dotenv` edge cases untested | 3 | `DONE` | test_env_utils.py: 9 tests for env_utils.load_dotenv |

### Low

| ID | Issue | Sprint | Status | Notes |
|----|-------|--------|--------|-------|
| CQ-2 | `label.split(",")[0]` duplication | — | `TODO` | Opportunistic |
| CQ-4 | `context.py` `any` vs `Any` type | — | `TODO` | Opportunistic |
| CQ-5 | Dead `quality` parameter | 1 | `DONE` | Removed param + Optional import |
| CQ-8 | Missing `Step` type annotations | — | `TODO` | Opportunistic |
| ERR-7 | Blocking `time.sleep` in cooldown | — | `TODO` | Opportunistic |
| MAINT-2 | Mutable list in frozen dataclass | — | `TODO` | Opportunistic |
| MAINT-3 | `Step` base class not enforced | — | `TODO` | Opportunistic |
| MAINT-4 | `API_BASE` defined twice | 1 | `DONE` | Imported from telegram.py in SEC-1 |
| MAINT-6 | `_ENTRY_URL` hardcoded in step6 | — | `TODO` | Opportunistic |
| PERF-1 | step3 polling loop | — | `TODO` | Opportunistic |
| PERF-2 | Baselines not per-office | — | `TODO` | Opportunistic |
| PERF-3 | Browser restart undocumented | — | `TODO` | Opportunistic |
| PERF-4 | Screenshot encode/decode overhead | — | `TODO` | Opportunistic |
| SEC-5 | `.env` not validated | — | `TODO` | Opportunistic |
| TEST-7 | Hand-rolled `_Logger` stub | — | `TODO` | Opportunistic |
| TEST-8 | Hardcoded config defaults in tests | — | `TODO` | Opportunistic |
| OPS-4 | 5x `python3 -c` state reads | 4 | `DONE` | Single eval invocation via state_utils.py read |
| OPS-5 | Plist hardcodes username | — | `DONE` | Fixed pre-plan: template + install_launchd.sh |
| OPS-6 | Fragile screenshot cleanup loop | — | `TODO` | Opportunistic |
| OPS-7 | Baselines directory never pruned | — | `TODO` | Opportunistic |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-03-27 | Initial analysis complete. 27 issues identified across 7 dimensions. 4 sprints planned. |
| 2026-03-27 | **Sprint 1 complete.** 9 issues done: SEC-4, SEC-1, SEC-2, ERR-2, ERR-3, ERR-4, SEC-6, CQ-7, MAINT-4+CQ-5. OPS-5 verified as pre-done. |
| 2026-03-27 | **Sprint 2 complete.** 7 issues done: CQ-3, CQ-1, MAINT-5, ERR-5, ERR-6, MAINT-1, CQ-6. ERR-1 resolved as part of CQ-3. |
| 2026-03-27 | **Sprint 3 complete.** 6 issues done: TEST-1, TEST-2, TEST-3, TEST-4, TEST-5, TEST-6. 56 tests total, all passing. |
| 2026-03-27 | **Sprint 4 complete.** 5 issues done: SEC-3, OPS-4 (state_utils.py), OPS-1, OPS-2 (RotatingFileHandler + JSONL), OPS-3 (liveness signal). All 28 planned issues complete. |
