#!/usr/bin/env python3
"""Process pending Telegram bot commands. Called by scheduler/run.sh at each wake."""

import os
from pathlib import Path


def _load_dotenv(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.is_file():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("\"'")
        os.environ.setdefault(key, value)


try:
    _load_dotenv()
    token = os.getenv("CITA_TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("CITA_TELEGRAM_CHAT_ID", "")
    if token and chat_id:
        from tps_cita_check.bot import process_commands

        process_commands(
            token=token,
            chat_id=chat_id,
            state_path=Path("artifacts/scheduler_state.json"),
            run_history_path=Path("artifacts/run_history.json"),
            offset_path=Path("artifacts/bot_offset.txt"),
        )
except Exception:
    pass  # Never crash the scheduler
