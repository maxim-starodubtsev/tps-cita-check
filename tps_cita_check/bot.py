"""Telegram bot command processor (stdlib-only, no extra dependencies)."""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from .telegram import API_BASE, _mask_token

_log = logging.getLogger(__name__)

RUN_STATUS_LABELS = {
    "ok": "✅ No citas",
    "cita_found": "🎉 Cita found",
    "network_error": "🌐 Network error",
    "waf_error": "🚫 WAF block",
    "error": "❌ Error",
}

OFFICE_STATUS_LABELS = {
    "no_citas": "✅ no citas",
    "cita_found": "🎉 AVAILABLE",
    "error": "❌ error",
}

PAUSE_REASON_LABELS = {
    "user_stop_bot": "Telegram /stop",
    "cita_found": "Cita found",
    "network_error": "Network error",
    "unknown_error": "Unknown error",
}

STARTED_BY_LABELS = {
    "bot_command": "Telegram /start",
    "manual_cli": "manual CLI",
}


def get_updates(token: str, offset: int, timeout: int = 0) -> list[dict]:
    """Call GET /getUpdates non-blocking. Returns empty list on any error."""
    url = f"{API_BASE.format(token=token)}/getUpdates?offset={offset}&timeout={timeout}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
            return data.get("result", [])
    except Exception as exc:
        _log.warning("get_updates failed: %s", _mask_token(str(exc), token))
        return []


def _read_state(state_path: Path) -> dict:
    if state_path.exists():
        try:
            return json.loads(state_path.read_text())
        except Exception as exc:
            _log.warning("Failed to read state from %s: %s", state_path, exc)
    return {}


def _write_state(state_path: Path, state: dict) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=str(state_path.parent), suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w") as f:
            json.dump(state, f)
        os.replace(tmp_path, str(state_path))
    except BaseException:
        os.unlink(tmp_path)
        raise


def _fmt_run_status(status: str) -> str:
    return RUN_STATUS_LABELS.get(status, f"? {status}")


def _fmt_pause_reason(reason: str) -> str:
    return PAUSE_REASON_LABELS.get(reason, reason)


def _fmt_started_by(started_by: str) -> str:
    return STARTED_BY_LABELS.get(started_by, started_by)


def _fmt_office_status(status: str) -> str:
    return OFFICE_STATUS_LABELS.get(status, status)


def _office_short_name(label: str) -> str:
    """Extract the short name from a full office label (text before first comma)."""
    return label.split(",")[0].strip()


def _fmt_ts(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def _read_run_history(run_history_path: Path) -> list[dict]:
    if run_history_path.exists():
        try:
            return json.loads(run_history_path.read_text())
        except Exception as exc:
            _log.warning("Failed to read run history from %s: %s", run_history_path, exc)
    return []


def _last_run_line(run_history_path: Path) -> str:
    history = _read_run_history(run_history_path)
    if not history:
        return "Last run: —"
    last = history[-1]
    ts_str = _fmt_ts(last["ts"])
    status_str = _fmt_run_status(last.get("status", ""))
    return f"Last run: {ts_str} — {status_str}"


def _office_lines(run_history_path: Path) -> list[str]:
    """Return indented per-office status lines from the most recent run_history entry."""
    history = _read_run_history(run_history_path)
    if not history:
        return []
    offices = history[-1].get("offices", [])
    if not offices:
        return []
    return [
        f"  {_office_short_name(o['label'])} — {_fmt_office_status(o.get('status', ''))}"
        for o in offices
    ]


def _handle_status(state_path: Path, run_history_path: Path) -> str:
    state = _read_state(state_path)
    paused = state.get("paused", False)
    run_counter = state.get("run_counter", 0)
    consecutive_waf = state.get("consecutive_waf", 0)
    net_retries = state.get("net_retries", 0)
    next_run_ts = state.get("next_run_ts", 0)

    lines = ["Scheduler status:"]
    if paused:
        lines.append("State: PAUSED ⏸")
        paused_ts = state.get("paused_ts")
        paused_reason = state.get("paused_reason")
        if paused_ts and paused_reason:
            lines.append(f"Stopped: {_fmt_ts(paused_ts)} — {_fmt_pause_reason(paused_reason)}")
        elif paused_ts:
            lines.append(f"Stopped: {_fmt_ts(paused_ts)}")
    else:
        lines.append("State: RUNNING ▶")
        now = int(time.time())
        if next_run_ts > now:
            mins_left = (next_run_ts - now) // 60
            next_time = datetime.fromtimestamp(next_run_ts).strftime("%H:%M")
            lines.append(f"Next run: {next_time} (in {mins_left} min)")
        else:
            lines.append("Next run: now (overdue)")
        started_ts = state.get("started_ts")
        started_by = state.get("started_by")
        if started_ts and started_by:
            lines.append(f"Running since: {_fmt_ts(started_ts)} ({_fmt_started_by(started_by)})")
        elif started_ts:
            lines.append(f"Running since: {_fmt_ts(started_ts)}")
    lines += [
        f"Total runs: {run_counter}",
        f"WAF blocks: {consecutive_waf}",
        f"Net retries: {net_retries}",
        _last_run_line(run_history_path),
    ]
    lines.extend(_office_lines(run_history_path))
    return "\n".join(lines)


def _handle_runs(run_history_path: Path) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    history = _read_run_history(run_history_path)
    today_runs = [e for e in history if _fmt_ts(e["ts"]).startswith(today)]
    lines = [f"Runs today ({today}): {len(today_runs)}"]
    last5 = history[-5:][::-1]  # last 5 in reverse chronological order
    if last5:
        lines.append("")
        lines.append("Last 5 runs:")
        for entry in last5:
            ts_str = _fmt_ts(entry["ts"])
            status_str = _fmt_run_status(entry.get("status", ""))
            lines.append(f"  {ts_str} — {status_str}")
    return "\n".join(lines)


def _handle_start(state_path: Path, run_history_path: Path) -> str:
    state = _read_state(state_path)
    if not state.get("paused"):
        # Already running — guard
        lines = [
            "Scheduler is already running ▶",
            "Use /stop to pause it.",
            "",
            _last_run_line(run_history_path),
        ]
        started_ts = state.get("started_ts")
        started_by = state.get("started_by")
        if started_ts and started_by:
            lines.append(f"Running since: {_fmt_ts(started_ts)} ({_fmt_started_by(started_by)})")
        elif started_ts:
            lines.append(f"Running since: {_fmt_ts(started_ts)}")
        return "\n".join(lines)

    now = int(time.time())
    state.pop("paused", None)
    state.pop("paused_ts", None)
    state.pop("paused_reason", None)
    state["net_retries"] = 0
    state["next_run_ts"] = 0
    state["started_ts"] = now
    state["started_by"] = "bot_command"
    _write_state(state_path, state)
    lines = [
        "Resumed ▶  Scheduler will run on next wake-up.",
        "",
        _last_run_line(run_history_path),
        f"Started: {_fmt_ts(now)} via {_fmt_started_by('bot_command')}",
    ]
    return "\n".join(lines)


def _handle_stop(state_path: Path, run_history_path: Path) -> str:
    state = _read_state(state_path)
    if state.get("paused"):
        # Already stopped — guard
        lines = [
            "Scheduler is already paused ⏸",
            "Use /start to resume it.",
            "",
            _last_run_line(run_history_path),
        ]
        paused_ts = state.get("paused_ts")
        paused_reason = state.get("paused_reason")
        if paused_ts and paused_reason:
            lines.append(f"Stopped: {_fmt_ts(paused_ts)} — {_fmt_pause_reason(paused_reason)}")
        elif paused_ts:
            lines.append(f"Stopped: {_fmt_ts(paused_ts)}")
        return "\n".join(lines)

    now = int(time.time())
    state["paused"] = True
    state["paused_ts"] = now
    state["paused_reason"] = "user_stop_bot"
    _write_state(state_path, state)
    lines = [
        "Paused ⏸  Send /start to resume.",
        "",
        _last_run_line(run_history_path),
        f"Stopped: {_fmt_ts(now)} via {_fmt_pause_reason('user_stop_bot')}",
    ]
    return "\n".join(lines)


def _handle_help() -> str:
    return (
        "TPS Cita Check \u2014 Bot Commands:\n"
        "/status \u2014 Scheduler state, next run ETA, WAF/retry counts\n"
        "/runs   \u2014 Run history and today's count\n"
        "/start  \u2014 Resume scheduler\n"
        "/stop   \u2014 Pause scheduler\n"
        "/help   \u2014 This message"
    )


def _send_reply(token: str, chat_id: str, text: str) -> None:
    from tps_cita_check.telegram import send_message

    send_message(token, chat_id, text, _log)


def process_commands(
    token: str,
    chat_id: str,
    state_path: Path,
    run_history_path: Path,
    offset_path: Path,
) -> None:
    """Poll for pending Telegram commands and handle them (non-blocking)."""
    offset = 0
    if offset_path.exists():
        try:
            offset = int(offset_path.read_text().strip())
        except (ValueError, OSError):
            offset = 0

    updates = get_updates(token, offset)
    for update in updates:
        update_id = update.get("update_id", 0)
        offset = update_id + 1  # advance offset regardless

        message = update.get("message") or update.get("edited_message")
        if not message:
            continue

        # Security: only respond to the configured chat
        msg_chat_id = str(message.get("chat", {}).get("id", ""))
        if msg_chat_id != str(chat_id):
            _log.warning(f"[bot] Ignoring message from unauthorized chat {msg_chat_id}")
            continue

        text = (message.get("text") or "").strip()
        if not text.startswith("/"):
            continue

        # Strip @BotName suffix if present (e.g. /start@MyBot)
        command = text.split()[0].split("@")[0].lower()

        try:
            if command == "/status":
                reply = _handle_status(state_path, run_history_path)
            elif command == "/runs":
                reply = _handle_runs(run_history_path)
            elif command == "/start":
                reply = _handle_start(state_path, run_history_path)
            elif command == "/stop":
                reply = _handle_stop(state_path, run_history_path)
            elif command == "/help":
                reply = _handle_help()
            else:
                reply = f"Unknown command: {command}\nSend /help for available commands."
            _send_reply(token, chat_id, reply)
        except Exception as exc:
            _log.warning(f"[bot] Error handling command {command}: {exc}")

    if updates:
        try:
            offset_path.parent.mkdir(parents=True, exist_ok=True)
            offset_path.write_text(str(offset))
        except OSError as exc:
            _log.warning(f"[bot] Failed to save offset: {exc}")
