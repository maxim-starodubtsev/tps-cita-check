# Sprint 4 — Operational Hardening

**Estimated effort:** Half day
**Dependencies:** Sprint 1 (atomic writes foundation), Sprint 2 (consolidated error patterns)
**Goal:** Improve observability, eliminate shell injection, add self-monitoring.

---

## Issues

### SEC-3: Replace `run.sh` Python `-c` blocks with `state_utils.py` `High` `M`

**Problem:** `scheduler/run.sh:101-108`, `177-191`, `193-201` — shell variables interpolated into `python3 -c "..."` strings. Double-quote or semicolon in any variable = code injection.

**Files to change:**
- Create `scheduler/state_utils.py`
- `scheduler/run.sh` — replace all `python3 -c` blocks with calls to the new script

**Implementation:**
```python
#!/usr/bin/env python3
"""State file utility for the scheduler. Replaces inline python3 -c blocks."""
import json, sys, os, tempfile

def read_state(state_path):
    """Read all fields from state JSON. Prints key=value lines."""
    try:
        state = json.load(open(state_path))
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}
    for key in ["paused", "paused_ts", "paused_reason", "started_ts", "started_by",
                "consecutive_waf", "next_run_ts", "run_counter"]:
        print(f"{key}={state.get(key, '')}")

def write_state(state_path, **kwargs):
    """Atomic write of key-value pairs to state JSON."""
    try:
        state = json.load(open(state_path))
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}
    state.update(kwargs)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(state_path), suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w") as f:
            json.dump(state, f)
        os.replace(tmp_path, state_path)
    except:
        os.unlink(tmp_path)
        raise

def append_run_history(history_path, status, offices_path=None, max_entries=20):
    """Append a run entry to history JSON with cap."""
    import time
    try:
        history = json.load(open(history_path))
    except (FileNotFoundError, json.JSONDecodeError):
        history = []
    offices = []
    if offices_path:
        try:
            offices = json.load(open(offices_path))
        except (FileNotFoundError, json.JSONDecodeError):
            pass
    entry = {"ts": int(time.time()), "status": status, "offices": offices}
    history.append(entry)
    history = history[-max_entries:]
    # atomic write
    tmp_fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(history_path), suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w") as f:
            json.dump(history, f)
        os.replace(tmp_path, history_path)
    except:
        os.unlink(tmp_path)
        raise

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "read":
        read_state(sys.argv[2])
    elif cmd == "write":
        # usage: state_utils.py write /path/to/state.json key1=val1 key2=val2
        path = sys.argv[2]
        pairs = {}
        for arg in sys.argv[3:]:
            k, v = arg.split("=", 1)
            # Auto-convert types
            if v.lower() == "true": v = True
            elif v.lower() == "false": v = False
            elif v.isdigit(): v = int(v)
            pairs[k] = v
        write_state(path, **pairs)
    elif cmd == "append-history":
        # usage: state_utils.py append-history /path/to/history.json status [/path/to/offices.json]
        offices = sys.argv[4] if len(sys.argv) > 4 else None
        append_run_history(sys.argv[2], sys.argv[3], offices)
```

In `run.sh`, replace:
```bash
# Before (injection risk):
python3 -c "import json; s=json.load(open('$STATE_FILE')); s['paused']=True; ..."

# After (safe):
python3 "$SCRIPT_DIR/state_utils.py" write "$STATE_FILE" paused=true paused_ts=$(date +%s) paused_reason=cita_found
```

**Traceability:** Also resolves SEC-4 for `run.sh` state writes (atomic write in `state_utils.py`), and OPS-4 (single Python invocation for reads).

**Status:** `TODO`
**Completed:** —

---

### OPS-2: Replace FileHandler with RotatingFileHandler `Medium` `S`

**Problem:** `logging_utils.py:21-22` — `FileHandler` appends without bound. Manual 600-line truncation in `run.sh` is a rough heuristic.

**File to change:**
- `tps_cita_check/logging_utils.py:21-22`
- `scheduler/run.sh:219-224` — remove manual truncation block

**Implementation:**
```python
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    log_path,
    maxBytes=5 * 1024 * 1024,  # 5 MB
    backupCount=3,
)
```

**Status:** `TODO`
**Completed:** —

---

### OPS-3: Scheduler liveness signal `Medium` `S`

**Problem:** If launchd stops firing, `/status` still reports RUNNING. No way to detect a stuck scheduler.

**Files to change:**
- `scheduler/run.sh` — write timestamp at top of every invocation
- `tps_cita_check/bot.py` — `/status` handler checks staleness

**Implementation:**

In `run.sh`, at the very top:
```bash
date +%s > "$ARTIFACTS_DIR/last_scheduler_wake.txt"
```

In `bot.py` `/status` handler:
```python
wake_file = artifacts_dir / "last_scheduler_wake.txt"
if wake_file.exists():
    last_wake = int(wake_file.read_text().strip())
    age_min = (int(time.time()) - last_wake) // 60
    if age_min > 120:
        lines.append(f"⚠️ Scheduler may be stuck (last wake: {age_min} min ago)")
```

**Status:** `TODO`
**Completed:** —

---

### OPS-1: Structured JSON log file `Medium` `M`

**Problem:** Plain text logs. Scheduler does fragile `grep` for WAF detection. No machine-parseable output.

**File to change:**
- `tps_cita_check/logging_utils.py` — add a second handler

**Implementation:**
```python
import json
from logging.handlers import RotatingFileHandler

class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "ts": record.created,
            "level": record.levelname,
            "msg": record.getMessage(),
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
        })

json_handler = RotatingFileHandler(
    str(log_path).replace(".log", ".jsonl"),
    maxBytes=5 * 1024 * 1024,
    backupCount=3,
)
json_handler.setFormatter(JsonFormatter())
logger.addHandler(json_handler)
```

Then `run.sh` can use `jq` instead of fragile `grep`:
```bash
# Check for WAF errors in last run:
jq -r 'select(.msg | test("url was rejected|fortigate"; "i")) | .msg' "$JSONL_LOG" | tail -1
```

**Status:** `TODO`
**Completed:** —

---

### OPS-4: Consolidate 5x `python3 -c` state reads `Low` `S`

**Problem:** `run.sh:59-63` — 5 separate Python interpreter startups to read 5 fields.

**Resolution:** Covered by SEC-3 above — `state_utils.py read` prints all fields in one invocation.

In `run.sh`:
```bash
eval "$(python3 "$SCRIPT_DIR/state_utils.py" read "$STATE_FILE")"
# Now $paused, $paused_ts, $paused_reason, etc. are available as shell vars
```

**Status:** `TODO`
**Completed:** —

---

## Definition of Done

- [ ] All `python3 -c` blocks replaced with `state_utils.py` calls
- [ ] No shell variable interpolation inside Python strings in `run.sh`
- [ ] `RotatingFileHandler` active; manual truncation removed from `run.sh`
- [ ] `last_scheduler_wake.txt` written on every wake; `/status` checks staleness
- [ ] `.jsonl` structured log file produced alongside `.log`
- [ ] All changes pass `pytest -q`
- [ ] Full 9-office run succeeds with `--visible --verbose`
- [ ] PROGRESS.md updated with completion dates
