"""Telegram Bot API notifications (stdlib-only, no extra dependencies)."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from pathlib import Path

API_BASE = "https://api.telegram.org/bot{token}"


def _mask_token(msg: str, token: str) -> str:
    """Replace the bot token in error messages to avoid leaking it to logs."""
    return msg.replace(token, "***") if token else msg


def send_message(token: str, chat_id: str, text: str, logger: logging.Logger) -> bool:
    """Send a plain-text message. Returns True on success."""
    url = f"{API_BASE.format(token=token)}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            logger.info(f"[telegram] sendMessage OK (HTTP {resp.status})")
            return True
    except (urllib.error.URLError, OSError) as exc:
        logger.warning("[telegram] sendMessage failed: %s", _mask_token(str(exc), token))
        return False


def send_photo(
    token: str,
    chat_id: str,
    photo_path: str | Path,
    caption: str,
    logger: logging.Logger,
) -> bool:
    """Send a photo with caption via multipart/form-data. Returns True on success."""
    url = f"{API_BASE.format(token=token)}/sendPhoto"
    boundary = "----TpsCitaCheck"

    photo_path = Path(photo_path)
    if not photo_path.exists():
        logger.warning(f"[telegram] photo not found: {photo_path}")
        return False

    photo_bytes = photo_path.read_bytes()
    filename = photo_path.name

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
        f"{chat_id}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="caption"\r\n\r\n'
        f"{caption}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="photo"; filename="{filename}"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode() + photo_bytes + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            logger.info(f"[telegram] sendPhoto OK (HTTP {resp.status})")
            return True
    except (urllib.error.URLError, OSError) as exc:
        logger.warning("[telegram] sendPhoto failed: %s", _mask_token(str(exc), token))
        return False
