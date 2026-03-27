# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium

# Run (visible browser, verbose logging)
python3 appointment_checker.py --visible --verbose --nie "Y1234567X" --name "IVAN PETROV"

# Run with .env (all config loaded from .env file)
python3 appointment_checker.py --visible --verbose

# Scheduler (macOS launchd)
bash scheduler/install_launchd.sh  # generates plist from template + loads
bash scheduler/run.sh --resume     # resume after pause

# Tests
pytest -q                              # all tests
pytest tests/test_screenshot_resize.py # single file
pytest -k test_runner_stops            # by name pattern
```

## Architecture

**Step-based runner** that automates the Spanish police appointment website (Cita Previa Extranjería) using Playwright. The flow navigates through province → office → trámite selection → accept → entrar → fill personal data (NIE + name) and submit → solicitar cita.

### Flow

`appointment_checker.py` (CLI entrypoint) → `runner.run_check()` → sequential execution of `Step0Load` → `Step1VerifyProvince` → `Step2SelectOffice` → `Step3SelectTramite` → `Step4Accept` → `Step5Entrar` → `Step6FillPersonalData` → `Step7SolicitarCita`. Runner stops on first failure. Inter-step human-like delays (1.5–3.5s) are injected automatically. Steps 6–7 use a Chrome extension to fill forms and click buttons via DOM manipulation + `<script>` tag injection, bypassing F5 TSPD bot detection.

### Key design patterns

- **Every step** returns a `StepResult` (ok/fail/skip) with diagnostics — never raises. Exceptions are caught internally and converted to `StepResult(status=FAIL)` with `error_type` and `error_details`.
- **Every step** captures a debug screenshot on both success and failure, resized via Pillow to keep artifacts small (800×1920 max).
- **`RunContext`** carries browser/page/config across steps. Steps access `ctx.page`, `ctx.config`, `ctx.logger`.
- **`CheckerConfig`** is a frozen dataclass. All parameters have defaults and are overridable via CLI flags or `CITA_*` env vars.
- **WAF/block/session detection** (`steps/common.py`) checks for "URL was rejected", FortiGate pages, and "sesión ha caducado" (session expiry). All are retriable — on WAF mid-run the runner retries from the failed office (not from office 1); `run_check()` tracks `accumulated_office_results` and `start_office_idx` across retries.
- **Inter-office cooldown** — Between offices: back-navigate → clear F5 TSPD cookies (`_clear_tspd_cookies()` filters `TS*`-prefixed cookies) → `random.uniform(30, 60)` sleep → reload `start_url` → Step1VerifyProvince. Prevents cumulative TSPD session-depth WAF blocks across 7+ offices.
- **Chrome extension** (`chrome_extension/`) content script listens for `postMessage` and handles form filling + submission via `<script>` tag injection into the page's main world. Undetectable by F5 TSPD.
- **Stealth evasion** (`stealth.py`) injects JS via `add_init_script` to hide `navigator.webdriver`, fake plugins/languages, and stub `chrome.runtime`. Enabled by default.
- **Retry logic** — Steps 2–7 use `retry_step()` (configurable attempts + backoff). Step0 has its own built-in retry loop.
- **Baseline screenshots** — After each successful step, the runner compares the screenshot against `artifacts/baselines/`. On first run, baselines are auto-saved.
- **Persistent context** — Runner uses `launch_persistent_context()` with the Chrome extension loaded. Extensions require a display (`--visible` on macOS, Xvfb in Docker).

### Module layout

- `tps_cita_check/config.py` — `CheckerConfig` with `start_url` property
- `tps_cita_check/context.py` — `RunContext` (mutable: holds browser/page for the run)
- `tps_cita_check/runner.py` — Orchestrates Playwright `launch_persistent_context` + step loop
- `tps_cita_check/step_framework.py` — `Step` base class, `StepResult`, `StepStatus` enum
- `tps_cita_check/stealth.py` — Manual browser stealth evasion via `add_init_script`
- `tps_cita_check/chrome_extension/` — Manifest V3 extension with content script for form filling + button clicks
- `tps_cita_check/steps/` — One file per step (step0–step7), plus `common.py` for shared helpers (`retry_step`, `human_delay`, WAF checks)
- `tps_cita_check/telegram.py` — Telegram Bot API notifications (stdlib-only, fire-and-forget)
- `tps_cita_check/bot.py` — Telegram bot command handlers (`/status`, `/runs`, `/start`, `/stop`, `/help`) with idle guards and provenance info
- `tps_cita_check/screenshot_utils.py` — Screenshot capture + resize
- `tps_cita_check/baseline_utils.py` — Image size comparison, wired into runner after each successful step
- `process_bot_commands.py` — Called by `scheduler/run.sh` at each wake; polls Telegram and dispatches to `bot.py`
- `artifacts/` — Run logs + timestamped screenshot directories + `baselines/` for reference PNGs + `run_history.json` (last 20 runs) + `last_run_offices.json` (per-office results sidecar) + `scheduler_state.json` (pause/resume state with provenance fields)
- `scheduler/` — `run.sh` (time-aware scheduler with WAF backoff + pause/resume) + `com.tps.cita-check.plist.template` (launchd template; `install_launchd.sh` generates the real plist)
- `.env` — Secrets and config (git-ignored): NIE, name, Telegram token/chat ID

### Telegram notifications

`tps_cita_check/telegram.py` — stdlib-only (`urllib.request`) Telegram Bot API client. Two functions: `send_message()` and `send_photo()` (multipart/form-data). Fire-and-forget with try/except — notification failure never crashes the checker. Enabled via `--telegram-bot-token` / `--telegram-chat-id` CLI flags (or `CITA_TELEGRAM_BOT_TOKEN` / `CITA_TELEGRAM_CHAT_ID` env vars). After `run_check()` returns, `appointment_checker.py` sends a photo alert if appointments may be available (`no_citas=False`), or a text alert if the run failed.

### Testing approach

Tests mock Playwright entirely — `runner.sync_playwright` is patched, and fake page/locator objects stand in for real browser interactions. No network calls in tests.
