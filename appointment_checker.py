#!/usr/bin/env python3
"""
Entrypoint wrapper around the multi-step framework in `tps_cita_check/`.

Flow: Step 0..7 (load -> verify province -> select office -> select trámite
-> accept -> entrar -> fill NIE/name and submit -> solicitar cita)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


from tps_cita_check.config import CheckerConfig
from tps_cita_check.env_utils import load_dotenv
from tps_cita_check.logging_utils import setup_logging
from tps_cita_check.runner import run_check
from tps_cita_check.telegram import send_message, send_photo


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="TPS Cita multi-step runner (Step0..Step7)")
    parser.add_argument("--visible", action="store_true", help="Run with visible browser")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")

    parser.add_argument("--province-label", default=os.getenv("CITA_PROVINCE_LABEL", "Málaga"))
    parser.add_argument("--province-code", default=os.getenv("CITA_PROVINCE_CODE", "29"))
    parser.add_argument(
        "--office-label",
        default=os.getenv("CITA_OFFICE_LABEL"),  # None → CheckerConfig.office_labels default applies
        help="Single office to check (use --offices for multiple offices)",
    )
    parser.add_argument(
        "--offices",
        default=os.getenv("CITA_OFFICES", ""),
        help=(
            "Pipe-separated (|) ordered list of offices to check. "
            "Overrides --office-label when provided. "
            "Uses | not comma because office names contain commas. "
            "Example: CITA_OFFICES env var. "
            "Available Málaga offices: "
            "CNP Torremolinos, Calle Skal, 12, Torremolinos | "
            "CNP CREADE-MÁLAGA, Avenida Pintor Joaquín Sorolla, 145, Málaga | "
            "CNP MÁLAGA Provincial, Plaza de Manuel Azaña ..., 3, Málaga | "
            "CNP Benalmadena, Calle Las Flores, 6, Benalmadena | "
            "CNP Fuengirola, Avenida Condes de San Isidro, 98, Fuengirola | "
            "CNP Marbella, Avenida Duque de Lerma, L3, Marbella | "
            "CNP Velez Malaga, Calle Puerta del Mar, 4, Torre del Mar | "
            "CNP Estepona, Calle Valle Inclán, 1, Estepona | "
            "CNP Antequera, Calle Ciudad de Oaxaca, S/N, Antequera"
        ),
    )
    parser.add_argument(
        "--tramite-contains",
        default=os.getenv("CITA_TRAMITE_CONTAINS", "TARJETA CONFLICTO UCRANIA"),
    )

    parser.add_argument("--nie", default=os.getenv("CITA_NIE", ""))
    parser.add_argument("--name", default=os.getenv("CITA_NAME", ""))
    parser.add_argument("--email", default=os.getenv("CITA_EMAIL", ""))
    parser.add_argument("--phone", default=os.getenv("CITA_PHONE", ""))

    parser.add_argument(
        "--extension-dir",
        default=os.getenv("CITA_EXTENSION_DIR", ""),
        help="Path to Chrome extension directory (default: bundled chrome_extension/)",
    )
    parser.add_argument(
        "--chrome-profile-dir",
        default=os.getenv("CITA_CHROME_PROFILE_DIR", ""),
        help="Path to persistent Chrome profile directory (default: artifacts/chrome_profile/)",
    )

    parser.add_argument(
        "--telegram-bot-token",
        default=os.getenv("CITA_TELEGRAM_BOT_TOKEN", ""),
        help="Telegram Bot API token for notifications",
    )
    parser.add_argument(
        "--telegram-chat-id",
        default=os.getenv("CITA_TELEGRAM_CHAT_ID", ""),
        help="Telegram chat ID for notifications",
    )
    parser.add_argument("--artifacts-dir", default=os.getenv("CITA_ARTIFACTS_DIR", "artifacts"))
    parser.add_argument("--screenshot-width", type=int, default=int(os.getenv("CITA_SCREENSHOT_WIDTH", "800")))
    parser.add_argument("--screenshot-max-height", type=int, default=int(os.getenv("CITA_SCREENSHOT_MAX_HEIGHT", "1920")))

    args = parser.parse_args()

    # Build ordered office list: --offices wins; fall back to single --office-label;
    # if neither given, CheckerConfig uses its own default.
    # Offices are separated by "|" (pipe) because office names contain commas.
    if args.offices:
        office_labels: tuple | None = tuple(o.strip() for o in args.offices.split("|") if o.strip())
    elif args.office_label:
        office_labels = (args.office_label,)
    else:
        office_labels = None  # let CheckerConfig supply its default

    cfg = CheckerConfig(
        province_code=args.province_code,
        province_label=args.province_label,
        **({} if office_labels is None else {"office_labels": office_labels}),
        tramite_contains=args.tramite_contains,
        nie=args.nie,
        full_name=args.name,
        email=args.email,
        phone=args.phone,
        artifacts_dir=Path(args.artifacts_dir),
        screenshot_width_px=args.screenshot_width,
        screenshot_max_height_px=args.screenshot_max_height,
        headless=not args.visible,
        extension_dir=args.extension_dir,
        chrome_profile_dir=args.chrome_profile_dir,
        telegram_bot_token=args.telegram_bot_token,
        telegram_chat_id=args.telegram_chat_id,
    )

    logger = setup_logging(cfg.artifacts_dir / "run.log", verbose=args.verbose)
    summary = run_check(config=cfg, logger=logger)

    # Write per-office results sidecar for scheduler/run.sh to include in run_history.json.
    try:
        offices_path = cfg.artifacts_dir / "last_run_offices.json"
        offices_path.write_text(json.dumps(list(summary.office_results)))
    except OSError:
        pass

    # Telegram notifications
    # Exit codes: 0 = no citas (normal), 1 = error, 2 = cita may be available
    exit_code = 0 if summary.ok else 1

    if cfg.telegram_bot_token and cfg.telegram_chat_id:
        token = cfg.telegram_bot_token
        chat_id = cfg.telegram_chat_id

        if summary.found_cita_office:
            # Appointment available — find the best screenshot: prefer step8
            # (after contact info fill) over step7.  Search in reverse so the
            # winning office's results (appended last) are found first.
            avail_step = next(
                (
                    r for r in reversed(summary.results)
                    if r.step_id in ("step8", "step7")
                    and r.data
                    and r.data.get("no_citas") is False
                    and r.screenshot
                ),
                None,
            )
            caption = f"Cita is available!\nOffice: {summary.found_cita_office}\n{cfg.start_url}"
            send_photo(
                token, chat_id,
                avail_step.screenshot if avail_step else None,
                caption=caption,
                logger=logger,
            )
            exit_code = 2
        elif not summary.ok:
            # Run failed — send error details + screenshot
            if summary.results:
                last = summary.results[-1]
                error_text = (
                    f"Run failed at {last.step_id}\n"
                    f"{last.message}\n"
                    f"Error: {last.error_type}: {last.error_details}\n\n"
                    f"If the scheduler has stopped, restart it with:\n"
                    f"bash scheduler/run.sh --resume"
                )
                if last.screenshot:
                    send_photo(token, chat_id, last.screenshot, caption=error_text, logger=logger)
                else:
                    send_message(token, chat_id, error_text, logger=logger)
            else:
                send_message(token, chat_id, "Run failed: no steps completed", logger=logger)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
