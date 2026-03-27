#!/usr/bin/env bash
# Scheduler wrapper for appointment_checker.py.
# Called every 60s by launchd; uses a next-run timestamp to implement
# time-aware variable intervals (CET):
#   20:00–06:00  → every 60–90 min (random)
#   06:00–09:00  → every 5–10 min  (random)
#   09:00–14:00  → every 10–15 min (random)
#   14:00–20:00  → every 20–30 min (random)
#
# Pauses automatically on cita availability (exit 2) or non-transient errors.
# Network errors get escalating retries (1min, 2min, ... up to 15 attempts).
# Resume with:  bash scheduler/run.sh --resume
#
# Tracks consecutive WAF blocks and applies exponential backoff.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ARTIFACTS_DIR="$PROJECT_DIR/artifacts"
STATE_FILE="$ARTIFACTS_DIR/scheduler_state.json"

cd "$PROJECT_DIR"
source .venv/bin/activate
mkdir -p "$ARTIFACTS_DIR"

# OPS-3: Write a wake timestamp so /status can detect a stuck scheduler.
date +%s > "$ARTIFACTS_DIR/last_scheduler_wake.txt"

# Process pending Telegram bot commands (non-blocking, ~60s latency)
python3 process_bot_commands.py 2>/dev/null || true

# --- Resume command ---
if [[ "${1:-}" == "--resume" ]]; then
    if [[ -f "$STATE_FILE" ]]; then
        python3 "$SCRIPT_DIR/state_utils.py" write "$STATE_FILE" \
            paused= paused_ts= paused_reason= \
            net_retries=0 next_run_ts=0 \
            started_ts="$(date +%s)" started_by=manual_cli
        echo '[scheduler] Resumed — next wake-up will run immediately.'
    else
        echo '[scheduler] No state file — nothing to resume.'
    fi
    exit 0
fi

# --- Load state (single Python invocation via state_utils.py) ---
consecutive_waf=0
run_counter=0
next_run_ts=0
paused=0
net_retries=0

if [[ -f "$STATE_FILE" ]]; then
    eval "$(python3 "$SCRIPT_DIR/state_utils.py" read "$STATE_FILE" 2>/dev/null)" || true
fi

# --- Paused? ---
if [[ "$paused" -eq 1 ]]; then
    exit 0
fi

# --- Check if it's time to run ---
current_ts=$(date +%s)

if [[ "$next_run_ts" -gt "$current_ts" ]]; then
    exit 0
fi

run_counter=$((run_counter + 1))

# --- Calculate next interval based on CET hour ---
cet_hour=$(TZ="Europe/Madrid" date +%-H)

if [[ "$cet_hour" -ge 20 ]] || [[ "$cet_hour" -lt 6 ]]; then
    next_interval=$(( RANDOM % 31 + 60 ))   # 60–90
elif [[ "$cet_hour" -ge 6 ]] && [[ "$cet_hour" -lt 9 ]]; then
    next_interval=$(( RANDOM % 6 + 5 ))     # 5–10
elif [[ "$cet_hour" -ge 9 ]] && [[ "$cet_hour" -lt 14 ]]; then
    next_interval=$(( RANDOM % 6 + 10 ))    # 10–15
else
    next_interval=$(( RANDOM % 11 + 20 ))   # 20–30
fi

# --- WAF backoff (may skip the actual run but still schedules next) ---
next_run_ts=$((current_ts + next_interval * 60))

if [[ "$consecutive_waf" -gt 0 ]]; then
    skip_mask=$(( (1 << consecutive_waf) - 1 ))
    if [[ $((run_counter & skip_mask)) -ne 0 ]]; then
        next_run_fmt=$(date -r "$next_run_ts" '+%H:%M:%S')
        echo "[scheduler] Skipping run $run_counter (WAF backoff: $consecutive_waf blocks, next at $next_run_fmt)"
        python3 "$SCRIPT_DIR/state_utils.py" write "$STATE_FILE" \
            consecutive_waf="$consecutive_waf" run_counter="$run_counter" \
            next_run_ts="$next_run_ts" net_retries=0
        exit 0
    fi
fi

# --- Run the checker ---
echo "[scheduler] Run $run_counter (CET hour=$cet_hour, next in ${next_interval}min, WAF=$consecutive_waf, net_retries=$net_retries)"

EXIT_CODE=0
python3 appointment_checker.py --verbose 2>&1 | tee "$ARTIFACTS_DIR/scheduler_last_run.log" || EXIT_CODE=$?

# --- Analyze result ---
should_pause=0
run_status="error"
pause_reason="unknown_error"

if [[ "$EXIT_CODE" -eq 0 ]]; then
    # No citas — normal, continue scheduling.
    consecutive_waf=0
    net_retries=0
    run_status="ok"

elif [[ "$EXIT_CODE" -eq 2 ]]; then
    # Cita may be available — notification sent, pause scheduler.
    consecutive_waf=0
    net_retries=0
    should_pause=1
    run_status="cita_found"
    pause_reason="cita_found"
    echo "[scheduler] PAUSED — cita may be available. Resume with: bash scheduler/run.sh --resume"

elif grep -qi "ERR_INTERNET_DISCONNECTED\|ERR_NAME_NOT_RESOLVED\|ERR_NETWORK_CHANGED\|ERR_CONNECTION_REFUSED\|nodename nor servname" "$ARTIFACTS_DIR/scheduler_last_run.log" 2>/dev/null; then
    # Network error — escalating retry (1min, 2min, ..., 15min).
    net_retries=$((net_retries + 1))
    consecutive_waf=0
    run_status="network_error"

    if [[ "$net_retries" -ge 15 ]]; then
        should_pause=1
        pause_reason="network_error"
        echo "[scheduler] PAUSED — no internet after $net_retries retries. Resume with: bash scheduler/run.sh --resume"
    else
        # Override next_run_ts with escalating backoff: retry N = N minutes.
        next_run_ts=$((current_ts + net_retries * 60))
        next_run_fmt=$(date -r "$next_run_ts" '+%H:%M:%S')
        echo "[scheduler] Network error (retry $net_retries/15, next at $next_run_fmt in ${net_retries}min)"
    fi

elif grep -qi "url was rejected\|fortigate\|no ofrece el servicio\|sesión ha caducado\|error en el sistema" "$ARTIFACTS_DIR/scheduler_last_run.log" 2>/dev/null; then
    # Transient site error (WAF, session expired, no-service, system error page) — continue scheduling.
    consecutive_waf=$((consecutive_waf + 1))
    net_retries=0
    run_status="waf_error"
    echo "[scheduler] Transient error (consecutive: $consecutive_waf) — will retry on next schedule"

else
    # Unknown error — pause scheduler.
    net_retries=0
    consecutive_waf=0
    should_pause=1
    run_status="error"
    pause_reason="unknown_error"
    echo "[scheduler] PAUSED — run failed. Resume with: bash scheduler/run.sh --resume"
fi

# Save state atomically.
if [[ "$should_pause" -eq 1 ]]; then
    python3 "$SCRIPT_DIR/state_utils.py" write "$STATE_FILE" \
        consecutive_waf="$consecutive_waf" run_counter="$run_counter" \
        next_run_ts="$next_run_ts" paused=true net_retries="$net_retries" \
        paused_ts="$(date +%s)" paused_reason="$pause_reason"
else
    python3 "$SCRIPT_DIR/state_utils.py" write "$STATE_FILE" \
        consecutive_waf="$consecutive_waf" run_counter="$run_counter" \
        next_run_ts="$next_run_ts" net_retries="$net_retries" \
        paused= paused_ts= paused_reason=
fi

# Append run to history.
python3 "$SCRIPT_DIR/state_utils.py" append-history \
    "$ARTIFACTS_DIR/run_history.json" "$run_status" \
    "$ARTIFACTS_DIR/last_run_offices.json"

# --- Cleanup old screenshot dirs ---
SCREENSHOTS_DIR="$ARTIFACTS_DIR/screenshots"
if [[ -d "$SCREENSHOTS_DIR" ]]; then
    # Keep last 3 screenshot dirs on success, last 10 on failure.
    if [[ "$EXIT_CODE" -eq 0 ]]; then
        keep=3
    else
        keep=10
    fi
    # Dirs are named YYYYMMDD_HHMMSS, so reverse-sorted = newest first.
    to_delete=$(ls -1r "$SCREENSHOTS_DIR" 2>/dev/null | tail -n +$((keep + 1)))
    for dir in $to_delete; do
        rm -rf "$SCREENSHOTS_DIR/$dir"
    done
fi

exit 0
