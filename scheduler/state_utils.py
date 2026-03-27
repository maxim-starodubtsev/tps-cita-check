#!/usr/bin/env python3
"""State file utility for the scheduler. Replaces inline python3 -c blocks in run.sh.

Usage:
    state_utils.py read <state_path>
        Print all state fields as key=value lines (suitable for shell eval).
        Boolean values are printed as 0/1 for bash compatibility.

    state_utils.py write <state_path> key1=val1 [key2=val2 ...]
        Atomically update the state JSON with the given key=value pairs.
        Empty value (key=) removes the key from state.

    state_utils.py append-history <history_path> <status> [offices_path]
        Append a timestamped run entry to history JSON (capped at 20 entries).
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time


_STATE_FIELDS = [
    "paused", "paused_ts", "paused_reason",
    "started_ts", "started_by",
    "consecutive_waf", "next_run_ts", "run_counter", "net_retries",
]


def _atomic_write(path: str, data) -> None:
    dir_ = os.path.dirname(os.path.abspath(path)) or "."
    tmp_fd, tmp_path = tempfile.mkstemp(dir=dir_, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w") as f:
            json.dump(data, f)
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _read_state_json(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def cmd_read(state_path: str) -> None:
    """Print all state fields as key=value lines for shell eval."""
    state = _read_state_json(state_path)
    for key in _STATE_FIELDS:
        val = state.get(key, "")
        if isinstance(val, bool):
            val = 1 if val else 0
        elif val is None:
            val = ""
        print(f"{key}={val}")


def _parse_value(v: str):
    """Convert string value to appropriate Python type for JSON storage."""
    if v.lower() == "true":
        return True
    if v.lower() == "false":
        return False
    if v.lstrip("-").isdigit():
        return int(v)
    return v


def cmd_write(state_path: str, pairs: dict) -> None:
    """Atomically update state JSON. Empty string value deletes the key."""
    state = _read_state_json(state_path)
    for k, v in pairs.items():
        if v == "" or v is None:
            state.pop(k, None)
        else:
            state[k] = v
    _atomic_write(state_path, state)


def cmd_append_history(
    history_path: str, status: str, offices_path: str | None = None
) -> None:
    """Append timestamped run entry to history JSON, capped at 20 entries."""
    try:
        with open(history_path) as f:
            history = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        history = []

    offices: list = []
    if offices_path:
        try:
            with open(offices_path) as f:
                offices = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    history.append({"ts": int(time.time()), "status": status, "offices": offices})
    history = history[-20:]
    _atomic_write(history_path, history)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "read":
        cmd_read(sys.argv[2])
    elif cmd == "write":
        path = sys.argv[2]
        pairs: dict = {}
        for arg in sys.argv[3:]:
            k, _, v = arg.partition("=")
            pairs[k] = _parse_value(v) if v else ""
        cmd_write(path, pairs)
    elif cmd == "append-history":
        offices_arg = sys.argv[4] if len(sys.argv) > 4 else None
        cmd_append_history(sys.argv[2], sys.argv[3], offices_arg)
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)
