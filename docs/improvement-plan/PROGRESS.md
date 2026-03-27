# Progress Tracker — TPS Cita Check Improvement Plan

**Last updated:** 2026-03-27

## Summary

| Sprint | Issues | Done | In Progress | Blocked | Remaining |
|--------|--------|------|-------------|---------|-----------|
| Sprint 1 — Quick Wins | 9 | 0 | 0 | 0 | 9 |
| Sprint 2 — Refactoring | 7 | 0 | 0 | 0 | 7 |
| Sprint 3 — Test Coverage | 6 | 0 | 0 | 0 | 6 |
| Sprint 4 — Operational | 5 | 0 | 0 | 0 | 5 |
| **Total** | **27** | **0** | **0** | **0** | **27** |

---

## All Issues by Status

### Critical

| ID | Issue | Sprint | Status | Notes |
|----|-------|--------|--------|-------|
| SEC-4 | Atomic state file writes | 1 | `TODO` | |

### High

| ID | Issue | Sprint | Status | Notes |
|----|-------|--------|--------|-------|
| SEC-1 | Telegram token log leak risk | 1 | `TODO` | |
| SEC-2 | Config repr redaction for secrets | 1 | `TODO` | |
| SEC-3 | Shell injection in `run.sh` `-c` blocks | 4 | `TODO` | |
| CQ-3 | Step error-handler boilerplate (7 files) | 2 | `TODO` | |
| TEST-1 | Multi-office loop tests | 3 | `TODO` | |
| TEST-2 | `_is_retriable_failure` tests | 3 | `TODO` | |
| TEST-3 | Bot command handler tests | 3 | `TODO` | |
| TEST-4 | Multi-office path test (not legacy) | 3 | `TODO` | |

### Medium

| ID | Issue | Sprint | Status | Notes |
|----|-------|--------|--------|-------|
| SEC-6 | `process_bot_commands.py` swallowed errors | 1 | `TODO` | |
| ERR-1 | Screenshot fallback silent errors | 2 | `TODO` | |
| ERR-2 | `summary` possibly unbound | 1 | `TODO` | |
| ERR-3 | `results[-1]` without empty check | 1 | `TODO` | |
| ERR-4 | Silent `except` in bot.py readers | 1 | `TODO` | |
| ERR-5 | FortiGate dead-branch in step0 | 2 | `TODO` | |
| ERR-6 | `page.goto` after cooldown unhandled | 2 | `TODO` | |
| CQ-1 | `_load_dotenv` duplicated | 2 | `TODO` | |
| CQ-6 | `_run_once` SRP violation | 2 | `TODO` | |
| CQ-7 | `headless=False` hardcoded | 1 | `TODO` | |
| MAINT-1 | Default office label in 2 places | 1 | `TODO` | |
| MAINT-5 | `_is_retriable_failure` duplicates `_is_waf_error` | 2 | `TODO` | |
| OPS-1 | Unstructured log format | 4 | `TODO` | |
| OPS-2 | No log rotation | 4 | `TODO` | |
| OPS-3 | No scheduler liveness signal | 4 | `TODO` | |
| TEST-5 | `_navigate_back_to_province` untested | 3 | `TODO` | |
| TEST-6 | `_load_dotenv` edge cases untested | 3 | `TODO` | |

### Low

| ID | Issue | Sprint | Status | Notes |
|----|-------|--------|--------|-------|
| CQ-2 | `label.split(",")[0]` duplication | — | `TODO` | Opportunistic |
| CQ-4 | `context.py` `any` vs `Any` type | — | `TODO` | Opportunistic |
| CQ-5 | Dead `quality` parameter | 1 | `TODO` | |
| CQ-8 | Missing `Step` type annotations | — | `TODO` | Opportunistic |
| ERR-7 | Blocking `time.sleep` in cooldown | — | `TODO` | Opportunistic |
| MAINT-2 | Mutable list in frozen dataclass | — | `TODO` | Opportunistic |
| MAINT-3 | `Step` base class not enforced | — | `TODO` | Opportunistic |
| MAINT-4 | `API_BASE` defined twice | 1 | `TODO` | |
| MAINT-6 | `_ENTRY_URL` hardcoded in step6 | — | `TODO` | Opportunistic |
| PERF-1 | step3 polling loop | — | `TODO` | Opportunistic |
| PERF-2 | Baselines not per-office | — | `TODO` | Opportunistic |
| PERF-3 | Browser restart undocumented | — | `TODO` | Opportunistic |
| PERF-4 | Screenshot encode/decode overhead | — | `TODO` | Opportunistic |
| SEC-5 | `.env` not validated | — | `TODO` | Opportunistic |
| TEST-7 | Hand-rolled `_Logger` stub | — | `TODO` | Opportunistic |
| TEST-8 | Hardcoded config defaults in tests | — | `TODO` | Opportunistic |
| OPS-4 | 5x `python3 -c` state reads | 4 | `TODO` | |
| OPS-5 | Plist hardcodes username | — | `TODO` | Opportunistic |
| OPS-6 | Fragile screenshot cleanup loop | — | `TODO` | Opportunistic |
| OPS-7 | Baselines directory never pruned | — | `TODO` | Opportunistic |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-03-27 | Initial analysis complete. 27 issues identified across 7 dimensions. 4 sprints planned. |
