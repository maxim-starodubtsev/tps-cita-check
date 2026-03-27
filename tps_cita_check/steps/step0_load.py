from __future__ import annotations

from ..screenshot_utils import save_debug_screenshot
from ..step_framework import Step, StepResult, StepStatus
from .common import ensure_not_rejected, is_fortigate_block, is_session_expired


class Step0Load(Step):
    step_id = "step0"
    title = "Load initial URL"

    def run(self, ctx) -> StepResult:
        log = ctx.logger
        cfg = ctx.config
        page = ctx.page

        try:
            # Retry a few times in case of transient WAF / FortiGate blocks.
            attempts = 3
            last_error: Exception | None = None
            for attempt in range(1, attempts + 1):
                log.info(f"[{self.step_id}] Attempt {attempt}/{attempts} loading {cfg.start_url}")
                page.goto(cfg.start_url, wait_until="load", timeout=cfg.step_timeout_ms)
                page.wait_for_load_state("domcontentloaded", timeout=cfg.step_timeout_ms)
                page.wait_for_timeout(1000)

                if is_fortigate_block(page):
                    log.warning(f"[{self.step_id}] FortiGate block detected on attempt {attempt}.")
                    last_error = RuntimeError("Session blocked: FortiGate Intrusion Prevention")
                elif is_session_expired(page):
                    log.warning(f"[{self.step_id}] Session expired detected on attempt {attempt}.")
                    raise RuntimeError("Session expired: sesión ha caducado")
                else:
                    try:
                        ensure_not_rejected(self.step_id, page, log)
                        break
                    except Exception as e:  # e.g. generic rejection page
                        last_error = e

                # Short backoff before retrying.
                page.wait_for_timeout(2_000)
            else:
                # All attempts ended up blocked.
                if last_error is not None:
                    raise last_error
                raise RuntimeError("Unable to load initial page due to repeated security blocks")

            shot = save_debug_screenshot(
                page=page,
                out_dir=ctx.run_screenshots_dir,
                filename=f"{self.step_id}_loaded.png",
                full_page=cfg.screenshot_full_page,
                width_px=cfg.screenshot_width_px,
                max_height_px=cfg.screenshot_max_height_px,
            )
            log.info(f"[{self.step_id}] Screenshot: {shot.path} ({shot.width}x{shot.height})")
            return StepResult(
                step_id=self.step_id,
                status=StepStatus.OK,
                message="Loaded initial page",
                screenshot=str(shot.path),
            )
        except Exception as e:
            try:
                shot = save_debug_screenshot(
                    page=page,
                    out_dir=ctx.run_screenshots_dir,
                    filename=f"{self.step_id}_error.png",
                    full_page=True,
                    width_px=cfg.screenshot_width_px,
                    max_height_px=cfg.screenshot_max_height_px,
                )
                screenshot = str(shot.path)
            except Exception:
                screenshot = None
            return StepResult(
                step_id=self.step_id,
                status=StepStatus.FAIL,
                message="Failed to load initial page",
                screenshot=screenshot,
                error_type=type(e).__name__,
                error_details=str(e),
            )

