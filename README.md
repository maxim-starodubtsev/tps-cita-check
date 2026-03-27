## TPS Cita Check (Ukraine TPS)

Automates the **multi-step appointment flow** on the Spanish police website (Cita Previa Extranjería) to check for available appointments across multiple offices.

The checker navigates through the full booking flow — province → office → trámite → accept → entrar → fill personal data → solicitar cita — and reports whether appointments are available.

### Requirements

- Python 3.9+
- Playwright browsers installed

### Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

### Run (local macOS)

Visible browser, verbose logging:

```bash
python3 appointment_checker.py --visible --verbose
```

Headless (all config from `.env`):

```bash
python3 appointment_checker.py
```

Artifacts (logs + screenshots) go into `artifacts/`.

### Configuration

All parameters can be set via CLI flags or environment variables. Create a `.env` file in the project root (git-ignored) with `KEY=VALUE` pairs.

#### Province
| CLI flag | Env var | Default |
|----------|---------|---------|
| `--province-code` | `CITA_PROVINCE_CODE` | `29` |
| `--province-label` | `CITA_PROVINCE_LABEL` | `Málaga` |

#### Office (single or multiple)
| CLI flag | Env var | Notes |
|----------|---------|-------|
| `--office-label` | `CITA_OFFICE_LABEL` | Single office |
| `--offices` | `CITA_OFFICES` | Multiple offices, pipe-separated (`\|`). Overrides `--office-label`. Uses `\|` not comma because office names contain commas. |

Example for all 9 Málaga offices (in `.env`):
```
CITA_OFFICES=CNP Torremolinos, Calle Skal, 12, Torremolinos|CNP CREADE-MÁLAGA, Avenida Pintor Joaquín Sorolla, 145, Málaga|CNP MÁLAGA Provincial, Plaza de Manuel Azaña (TIES (HUELLAS): ZONA 1, RESTO DE TRÁMITES: ZONA 2), 3, Málaga|CNP Benalmadena, Calle Las Flores, 6, Benalmadena|CNP Fuengirola, Avenida Condes de San Isidro, 98, Fuengirola|CNP Marbella, Avenida Duque de Lerma, L3, Marbella|CNP Velez Malaga, Calle Puerta del Mar, 4, Torre del Mar|CNP Estepona, Calle Valle Inclán, 1, Estepona|CNP Antequera, Calle Ciudad de Oaxaca, S/N, Antequera
```

#### Trámite
| CLI flag | Env var | Default |
|----------|---------|---------|
| `--tramite-contains` | `CITA_TRAMITE_CONTAINS` | `TARJETA CONFLICTO UCRANIA` |

#### Personal data
| CLI flag | Env var |
|----------|---------|
| `--nie` | `CITA_NIE` |
| `--name` | `CITA_NAME` |
| `--email` | `CITA_EMAIL` |
| `--phone` | `CITA_PHONE` |

#### Telegram notifications
| CLI flag | Env var |
|----------|---------|
| `--telegram-bot-token` | `CITA_TELEGRAM_BOT_TOKEN` |
| `--telegram-chat-id` | `CITA_TELEGRAM_CHAT_ID` |

When configured, the checker sends a photo alert if an appointment is found, or an error message if the run fails.

#### Browser / artifacts
| CLI flag | Env var | Default |
|----------|---------|---------|
| `--visible` | — | headless |
| `--artifacts-dir` | `CITA_ARTIFACTS_DIR` | `artifacts` |
| `--screenshot-width` | `CITA_SCREENSHOT_WIDTH` | `800` |
| `--screenshot-max-height` | `CITA_SCREENSHOT_MAX_HEIGHT` | `1920` |
| `--extension-dir` | `CITA_EXTENSION_DIR` | bundled `chrome_extension/` |
| `--chrome-profile-dir` | `CITA_CHROME_PROFILE_DIR` | `artifacts/chrome_profile/` |

### Example `.env` file

```dotenv
CITA_NIE=Y1234567X
CITA_NAME=IVAN PETROV
CITA_EMAIL=ivan@example.com
CITA_PHONE=600123456
CITA_PROVINCE_CODE=29
CITA_PROVINCE_LABEL=Málaga
CITA_TRAMITE_CONTAINS=TARJETA CONFLICTO UCRANIA
CITA_OFFICES=CNP Torremolinos, Calle Skal, 12, Torremolinos|CNP CREADE-MÁLAGA, Avenida Pintor Joaquín Sorolla, 145, Málaga
CITA_TELEGRAM_BOT_TOKEN=123456:ABCDEF...
CITA_TELEGRAM_CHAT_ID=987654321
```

### Scheduler (macOS launchd)

The scheduler runs the checker automatically at variable intervals based on time of day (CET):

| Time window | Interval |
|-------------|----------|
| 06:00–09:00 | 5–10 min |
| 09:00–14:00 | 10–15 min |
| 14:00–20:00 | 20–30 min |
| 20:00–06:00 | 60–90 min |

**Setup:**
```bash
cp scheduler/com.tps.cita-check.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.tps.cita-check.plist
bash scheduler/run.sh --resume   # start immediately
```

**Pause/resume:**
```bash
bash scheduler/run.sh --resume   # resume from CLI
```
Or use the Telegram bot commands (see below).

The scheduler automatically pauses when:
- A cita is found (exit code 2) — resume manually after booking
- 15+ consecutive network errors — likely internet outage
- An unexpected error occurs

WAF blocks (FortiGate / "URL was rejected") apply exponential backoff but do **not** pause the scheduler.

### Telegram bot commands

When `CITA_TELEGRAM_BOT_TOKEN` and `CITA_TELEGRAM_CHAT_ID` are configured, the bot processes commands at each scheduler wake-up (~60s response latency):

| Command | Description |
|---------|-------------|
| `/status` | Scheduler state (RUNNING/PAUSED), next run ETA, WAF/retry counts, last run result with per-office breakdown |
| `/runs` | Today's run count + last 5 runs with timestamps and status |
| `/start` | Resume a paused scheduler |
| `/stop` | Pause the scheduler |
| `/help` | List all commands |

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | No appointments found — normal |
| `1` | Run failed (error) |
| `2` | Appointment may be available — Telegram alert sent |

### Tests

```bash
pytest -q
pytest tests/test_screenshot_resize.py  # single file
pytest -k test_runner_stops             # by name pattern
```

### Documentation

- `docs/WAF_RATE_LIMITING.md` — WAF behavior, F5 TSPD deep dive, scheduler design rationale
- `docs/REQUIREMENTS.md` — step-by-step requirements

### Known issues / WAF behavior

The site uses F5 BIG-IP TSPD bot detection and rate-limiting. Key behavior:

- WAF blocks appear as "The requested URL was rejected" or a FortiGate page
- Blocks are **IP-based**, not session-based — a new browser session does not bypass them
- Multi-office runs clear TSPD cookies and wait 30–60s between offices to avoid cumulative session depth triggering the WAF
- On WAF block mid-run, the checker retries from the **failed office** (not from office 1)
- See `docs/WAF_RATE_LIMITING.md` for full analysis
