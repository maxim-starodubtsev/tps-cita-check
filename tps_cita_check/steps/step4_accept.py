from __future__ import annotations

from ..screenshot_utils import save_debug_screenshot
from ..step_framework import Step, StepResult, StepStatus
from .common import ensure_not_rejected, retry_step, run_step_safely, wait_network_idle


class Step4Accept(Step):
    step_id = "step4"
    title = "Click Aceptar"

    def run(self, ctx) -> StepResult:
        return run_step_safely(self.step_id, self.title, ctx, self._inner_run)

    def _inner_run(self, ctx) -> StepResult:
        log = ctx.logger
        cfg = ctx.config
        page = ctx.page

        def _attempt():
            ensure_not_rejected(self.step_id, page, log)

            # Some error dialogs show up if trámite isn't selected.
            if page.locator("text=Por favor, selecciona un trámite").count() > 0:
                raise RuntimeError("Page reports missing trámite selection")

            # Wait for the Aceptar button to be visible before calling its JS function.
            page.locator("#btnAceptar").wait_for(state="visible", timeout=cfg.step_timeout_ms)

            # Call envia() via JS — avoids CDP click which triggers F5 TSPD WAF.
            with page.expect_navigation(wait_until="load", timeout=cfg.step_timeout_ms):
                page.evaluate("() => { envia(); }")

            ensure_not_rejected(self.step_id, page, log)
            wait_network_idle(page, cfg.step_timeout_ms)

        retry_step(
            _attempt,
            attempts=cfg.step_retry_attempts,
            backoff_ms=cfg.step_retry_backoff_ms,
            logger=log,
            step_id=self.step_id,
            label="Aceptar click",
        )

        shot = save_debug_screenshot(
            page=page,
            out_dir=ctx.run_screenshots_dir,
            filename=f"{self.step_id}_after_accept.png",
            full_page=cfg.screenshot_full_page,
            width_px=cfg.screenshot_width_px,
            max_height_px=cfg.screenshot_max_height_px,
        )
        log.info(f"[{self.step_id}] Clicked Aceptar. url={page.url}")
        return StepResult(
            step_id=self.step_id,
            status=StepStatus.OK,
            message="Accepted selection",
            screenshot=str(shot.path),
            data={"url": page.url},
        )
