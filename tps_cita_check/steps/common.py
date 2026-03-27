from __future__ import annotations

import random
import time

from playwright.sync_api import TimeoutError as PlaywrightTimeout


def is_url_rejected(page) -> bool:
    # Seen in screenshots: "The requested URL was rejected..."
    return page.locator("text=The requested URL was rejected").count() > 0


def is_fortigate_block(page) -> bool:
    # Seen in screenshots: "FortiGate Intrusion Prevention"
    return page.locator("text=FortiGate Intrusion Prevention").count() > 0


def is_session_expired(page) -> bool:
    # "Su sesión ha caducado por permanecer demasiado tiempo inactiva."
    return page.locator("text=sesión ha caducado").count() > 0


def is_no_cita_previa_service(page) -> bool:
    # "La provincia seleccionada no ofrece el servicio de Cita Previa Internet para ningún trámite."
    return page.locator("text=no ofrece el servicio de Cita Previa Internet").count() > 0


def is_system_error(page) -> bool:
    # "Se ha producido un error en el sistema, por favor inténtelo de nuevo."
    return page.locator("text=error en el sistema").count() > 0


def ensure_not_rejected(step_id: str, page, logger) -> None:
    if is_url_rejected(page):
        logger.error(f"[{step_id}] Session blocked by upstream protection (URL rejected).")
        raise RuntimeError("Session blocked: The requested URL was rejected")
    if is_fortigate_block(page):
        logger.error(f"[{step_id}] Session blocked by FortiGate Intrusion Prevention.")
        raise RuntimeError("Session blocked: FortiGate Intrusion Prevention")
    if is_session_expired(page):
        logger.error(f"[{step_id}] Server session expired (caducado).")
        raise RuntimeError("Session expired: sesión ha caducado")
    if is_no_cita_previa_service(page):
        logger.error(f"[{step_id}] Province has no Cita Previa service (Volver page).")
        raise RuntimeError("No Cita Previa service: no ofrece el servicio")
    if is_system_error(page):
        logger.error(f"[{step_id}] Website returned system error page.")
        raise RuntimeError("System error: Se ha producido un error en el sistema")


def wait_network_idle(page, timeout_ms: int) -> None:
    page.wait_for_load_state("load", timeout=timeout_ms)


def human_delay(page, min_ms: int, max_ms: int) -> int:
    """Wait a random amount of time (human-like). Returns ms waited."""
    delay = random.randint(min_ms, max_ms)
    page.wait_for_timeout(delay)
    return delay


RETRIABLE_PATTERNS = (
    "url was rejected",
    "fortigate",
    "sesión ha caducado",
    "no ofrece el servicio",
    "error en el sistema",
    "timeout",
)


def is_retriable_error(error_text: str) -> bool:
    """Return True if *error_text* matches any known transient/retriable error pattern."""
    text = (error_text or "").lower()
    return any(p in text for p in RETRIABLE_PATTERNS)


def _is_waf_error(exc: Exception) -> bool:
    # "timeout" is retriable at step level but not a WAF/block signal.
    msg = str(exc).lower()
    return any(p in msg for p in RETRIABLE_PATTERNS if p != "timeout")


def retry_step(fn, *, attempts: int, backoff_ms: int, logger, step_id: str, label: str):
    """Call *fn()* up to *attempts* times, sleeping *backoff_ms* between failures.

    WAF/block errors are never retried at the step level — they are re-raised
    immediately so the runner can restart with a fresh browser session.

    On success returns fn()'s result.  On final failure re-raises the exception
    so the step's outer try/except can convert it to a StepResult(FAIL).
    """
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            # WAF blocks can't be recovered within the same session — bail out fast.
            if _is_waf_error(exc):
                logger.error(f"[{step_id}] {label} hit WAF block, skipping retries: {exc}")
                raise
            if attempt < attempts:
                logger.warning(
                    f"[{step_id}] {label} attempt {attempt}/{attempts} failed: {exc}. "
                    f"Retrying in {backoff_ms}ms…"
                )
                time.sleep(backoff_ms / 1000.0)
            else:
                logger.error(f"[{step_id}] {label} failed after {attempts} attempts: {exc}")
    raise last_exc  # type: ignore[misc]


def _try_screenshot(step_id: str, ctx, suffix: str):
    """Attempt to take a screenshot, returning the path or None on failure."""
    try:
        from ..screenshot_utils import save_debug_screenshot
        shot = save_debug_screenshot(
            page=ctx.page,
            out_dir=ctx.run_screenshots_dir,
            filename=f"{step_id}_{suffix}.png",
            full_page=True,
            width_px=ctx.config.screenshot_width_px,
            max_height_px=ctx.config.screenshot_max_height_px,
        )
        return str(shot.path)
    except Exception as exc:
        ctx.logger.debug(f"[{step_id}] Screenshot on error failed: {exc}")
        return None


def run_step_safely(step_id: str, title: str, ctx, inner_fn):
    """Wrap a step's core logic with standardised error handling + screenshot.

    *inner_fn* receives *ctx* and must return a StepResult on success.
    Timeout and generic exceptions are caught, a screenshot is taken, and a
    FAIL StepResult is returned — the step never raises.
    """
    from ..step_framework import StepResult, StepStatus
    try:
        return inner_fn(ctx)
    except PlaywrightTimeout as exc:
        screenshot = _try_screenshot(step_id, ctx, "timeout")
        return StepResult(
            step_id=step_id,
            status=StepStatus.FAIL,
            message=f"{title} timed out",
            screenshot=screenshot,
            error_type=type(exc).__name__,
            error_details=str(exc),
        )
    except Exception as exc:
        screenshot = _try_screenshot(step_id, ctx, "error")
        return StepResult(
            step_id=step_id,
            status=StepStatus.FAIL,
            message=f"{title} failed",
            screenshot=screenshot,
            error_type=type(exc).__name__,
            error_details=str(exc),
        )


__all__ = [
    "PlaywrightTimeout",
    "RETRIABLE_PATTERNS",
    "ensure_not_rejected",
    "human_delay",
    "is_retriable_error",
    "is_url_rejected",
    "is_fortigate_block",
    "is_no_cita_previa_service",
    "is_session_expired",
    "is_system_error",
    "retry_step",
    "run_step_safely",
    "wait_network_idle",
]

