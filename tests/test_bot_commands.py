"""TEST-3: Bot command handler unit tests."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from tps_cita_check.bot import (
    _handle_help,
    _handle_runs,
    _handle_start,
    _handle_status,
    _handle_stop,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _write_state(path: Path, **kwargs) -> None:
    path.write_text(json.dumps(kwargs))


def _write_history(path: Path, entries: list) -> None:
    path.write_text(json.dumps(entries))


def _now() -> int:
    return int(time.time())


# ── /status ───────────────────────────────────────────────────────────────────


def test_status_running(tmp_path):
    state = tmp_path / "state.json"
    hist = tmp_path / "history.json"
    _write_state(
        state,
        paused=False,
        run_counter=5,
        consecutive_waf=1,
        net_retries=0,
        next_run_ts=_now() + 600,
        started_ts=_now() - 3600,
        started_by="bot_command",
    )
    _write_history(hist, [])

    reply = _handle_status(state, hist)
    assert "RUNNING" in reply
    assert "Total runs: 5" in reply
    assert "WAF blocks: 1" in reply


def test_status_paused(tmp_path):
    state = tmp_path / "state.json"
    hist = tmp_path / "history.json"
    ts = _now() - 120
    _write_state(
        state,
        paused=True,
        run_counter=3,
        consecutive_waf=0,
        net_retries=0,
        paused_ts=ts,
        paused_reason="user_stop_bot",
    )
    _write_history(hist, [])

    reply = _handle_status(state, hist)
    assert "PAUSED" in reply
    assert "Telegram /stop" in reply  # paused_reason label


def test_status_missing_state_file(tmp_path):
    """If state file is absent, /status should not crash and show defaults."""
    hist = tmp_path / "history.json"
    _write_history(hist, [])
    reply = _handle_status(tmp_path / "missing.json", hist)
    assert "Scheduler status:" in reply


def test_status_shows_last_run(tmp_path):
    state = tmp_path / "state.json"
    hist = tmp_path / "history.json"
    _write_state(state, paused=False, run_counter=1, consecutive_waf=0, net_retries=0, next_run_ts=0)
    _write_history(hist, [{"ts": _now() - 300, "status": "ok", "offices": [
        {"label": "CNP Torremolinos, Calle Skal", "status": "no_citas"},
    ]}])

    reply = _handle_status(state, hist)
    assert "CNP Torremolinos" in reply  # per-office short name


# ── /runs ─────────────────────────────────────────────────────────────────────


def test_runs_empty_history(tmp_path):
    hist = tmp_path / "history.json"
    _write_history(hist, [])
    reply = _handle_runs(hist)
    assert "Runs today" in reply


def test_runs_shows_last5(tmp_path):
    hist = tmp_path / "history.json"
    now = _now()
    entries = [{"ts": now - i * 60, "status": "ok", "offices": []} for i in range(7)]
    _write_history(hist, entries)
    reply = _handle_runs(hist)
    assert "Last 5 runs:" in reply
    # Should show at most 5 entries
    assert reply.count("✅ No citas") <= 5


def test_runs_missing_history_file(tmp_path):
    reply = _handle_runs(tmp_path / "missing.json")
    assert "Runs today" in reply


# ── /start ────────────────────────────────────────────────────────────────────


def test_start_when_paused(tmp_path):
    state = tmp_path / "state.json"
    hist = tmp_path / "history.json"
    _write_state(state, paused=True, paused_ts=_now() - 60, paused_reason="user_stop_bot")
    _write_history(hist, [])

    reply = _handle_start(state, hist)

    assert "Resumed" in reply
    new_state = json.loads(state.read_text())
    assert "paused" not in new_state  # key removed
    assert new_state["started_by"] == "bot_command"
    assert "started_ts" in new_state


def test_start_when_already_running(tmp_path):
    state = tmp_path / "state.json"
    hist = tmp_path / "history.json"
    _write_state(state, paused=False, started_ts=_now() - 100, started_by="bot_command")
    _write_history(hist, [])

    original_state = json.loads(state.read_text())
    reply = _handle_start(state, hist)

    assert "already running" in reply.lower()
    # State file should NOT be mutated
    assert json.loads(state.read_text()) == original_state


# ── /stop ─────────────────────────────────────────────────────────────────────


def test_stop_when_running(tmp_path):
    state = tmp_path / "state.json"
    hist = tmp_path / "history.json"
    _write_state(state, paused=False, run_counter=2)
    _write_history(hist, [])

    reply = _handle_stop(state, hist)

    assert "Paused" in reply
    new_state = json.loads(state.read_text())
    assert new_state["paused"] is True
    assert new_state["paused_reason"] == "user_stop_bot"
    assert "paused_ts" in new_state


def test_stop_when_already_paused(tmp_path):
    state = tmp_path / "state.json"
    hist = tmp_path / "history.json"
    ts = _now() - 120
    _write_state(state, paused=True, paused_ts=ts, paused_reason="user_stop_bot")
    _write_history(hist, [])

    original_state = json.loads(state.read_text())
    reply = _handle_stop(state, hist)

    assert "already paused" in reply.lower()
    # State file should NOT be mutated
    assert json.loads(state.read_text()) == original_state


# ── /help ─────────────────────────────────────────────────────────────────────


def test_help_lists_all_commands():
    reply = _handle_help()
    for cmd in ["/status", "/runs", "/start", "/stop", "/help"]:
        assert cmd in reply
