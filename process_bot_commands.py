#!/usr/bin/env python3
"""Process pending Telegram bot commands. Called by scheduler/run.sh at each wake."""

import os
from pathlib import Path

from tps_cita_check.env_utils import load_dotenv


try:
    load_dotenv()
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
    # Never crash the scheduler, but make the failure observable.
    import logging
    logging.getLogger(__name__).warning("Bot command processing failed", exc_info=True)
