from __future__ import annotations

import json
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


class _JsonFormatter(logging.Formatter):
    """Emit each log record as a single JSON line for machine-parseable logs."""

    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({
            "ts": record.created,
            "level": record.levelname,
            "msg": record.getMessage(),
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
        })


def setup_logging(log_path: Path, verbose: bool = False) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)

    level = logging.DEBUG if verbose else logging.INFO
    logger = logging.getLogger("tps_cita_check")
    logger.setLevel(level)

    # Avoid duplicate handlers if called multiple times (tests).
    if logger.handlers:
        return logger

    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # Rotating text log (5 MB, 3 backups) — replaces manual tail truncation in run.sh.
    fh = RotatingFileHandler(
        log_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    fh.setLevel(level)
    fh.setFormatter(fmt)

    # Structured JSONL log alongside the text log (same rotation policy).
    jsonl_path = log_path.with_suffix(".jsonl")
    jh = RotatingFileHandler(
        jsonl_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    jh.setLevel(level)
    jh.setFormatter(_JsonFormatter())

    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(level)
    sh.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(jh)
    logger.addHandler(sh)
    return logger
