from __future__ import annotations

from ..screenshot_utils import save_debug_screenshot
from ..step_framework import Step, StepResult, StepStatus
from .common import PlaywrightTimeout, ensure_not_rejected, retry_step, wait_network_idle


class Step5Entrar(Step):
    step_id = "step5"
    title = "Click Entrar"

    def run(self, ctx) -> StepResult:
        log = ctx.logger
        cfg = ctx.config
        page = ctx.page

        def _attempt():
            ensure_not_rejected(self.step_id, page, log)

            # Wait for the Entrar button to be visible before calling its JS function.
            page.locator("#btnEntrar").wait_for(state="visible", timeout=cfg.step_timeout_ms)

            # Submit via JS — avoids CDP click which triggers F5 TSPD WAF.
            with page.expect_navigation(wait_until="load", timeout=cfg.step_timeout_ms):
                page.evaluate("() => { document.forms[0].submit(); }")

            ensure_not_rejected(self.step_id, page, log)
            wait_network_idle(page, cfg.step_timeout_ms)

        try:
            retry_step(
                _attempt,
                attempts=cfg.step_retry_attempts,
                backoff_ms=cfg.step_retry_backoff_ms,
                logger=log,
                step_id=self.step_id,
                label="Entrar click",
            )

            shot = save_debug_screenshot(
                page=page,
                out_dir=ctx.run_screenshots_dir,
                filename=f"{self.step_id}_after_entrar.png",
                full_page=cfg.screenshot_full_page,
                width_px=cfg.screenshot_width_px,
                max_height_px=cfg.screenshot_max_height_px,
            )
            log.info(f"[{self.step_id}] Clicked Entrar. url={page.url}")
            return StepResult(
                step_id=self.step_id,
                status=StepStatus.OK,
                message="Entered appointment flow",
                screenshot=str(shot.path),
                data={"url": page.url},
            )
        except PlaywrightTimeout as e:
            try:
                shot = save_debug_screenshot(
                    page=page,
                    out_dir=ctx.run_screenshots_dir,
                    filename=f"{self.step_id}_timeout.png",
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
                message="Entrar click timed out",
                screenshot=screenshot,
                error_type=type(e).__name__,
                error_details=str(e),
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
                message="Entrar step failed",
                screenshot=screenshot,
                error_type=type(e).__name__,
                error_details=str(e),
            )
