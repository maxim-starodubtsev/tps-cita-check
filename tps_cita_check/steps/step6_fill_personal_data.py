from __future__ import annotations

from ..screenshot_utils import save_debug_screenshot
from ..step_framework import Step, StepResult, StepStatus
from .common import ensure_not_rejected, human_delay, retry_step, run_step_safely


_ENTRY_URL = "https://icp.administracionelectronica.gob.es/icpco/acEntrada"


class Step6FillPersonalData(Step):
    step_id = "step6"
    title = "Fill NIE + Name and submit"

    def run(self, ctx) -> StepResult:
        return run_step_safely(self.step_id, self.title, ctx, self._inner_run)

    def _inner_run(self, ctx) -> StepResult:
        log = ctx.logger
        cfg = ctx.config
        page = ctx.page

        if not cfg.nie:
            return StepResult(
                step_id=self.step_id,
                status=StepStatus.FAIL,
                message="NIE not provided (use --nie or CITA_NIE)",
                error_type="ValueError",
                error_details="nie is empty",
            )
        if not cfg.full_name:
            return StepResult(
                step_id=self.step_id,
                status=StepStatus.FAIL,
                message="Name not provided (use --name or CITA_NAME)",
                error_type="ValueError",
                error_details="full_name is empty",
            )

        attempt_num = 0

        def _attempt():
            nonlocal attempt_num
            attempt_num += 1

            # On retry, navigate back to the entry form (WAF block page is a dead end).
            if attempt_num > 1:
                log.info(f"[{self.step_id}] Retry: navigating back to {_ENTRY_URL}")
                page.goto(_ENTRY_URL, wait_until="load", timeout=cfg.step_timeout_ms)
                human_delay(page, 1000, 2000)

            ensure_not_rejected(self.step_id, page, log)

            # Dismiss cookie banner via JS (no CDP input events).
            dismissed = page.evaluate("""() => {
                const link = document.getElementById('cookie_action_close_header');
                if (link && link.offsetParent !== null) { link.click(); return true; }
                return false;
            }""")
            if dismissed:
                log.info(f"[{self.step_id}] Cookie banner dismissed (JS)")
                page.wait_for_timeout(500)

            # Wait for form inputs.
            text_inputs = page.locator("input[type='text']:visible")
            text_inputs.first.wait_for(state="visible", timeout=cfg.step_timeout_ms)
            count = text_inputs.count()
            log.info(f"[{self.step_id}] Found {count} visible text inputs")
            if count < 2:
                raise RuntimeError(f"Expected at least 2 text inputs, found {count}")

            # Fill form fields via DOM and submit by calling the page's envia().
            # Using page.evaluate (Runtime.evaluate) is safe — F5 TSPD only
            # detects CDP-dispatched *input* events (click, focus, keypress),
            # not script evaluation.
            log.info(f"[{self.step_id}] Filling form via JS and calling envia()")
            with page.expect_navigation(wait_until="load", timeout=cfg.step_timeout_ms):
                page.evaluate("""(data) => {
                    const nie = document.getElementById('txtIdCitado');
                    const name = document.getElementById('txtDesCitado');
                    nie.value = data.nie;
                    nie.dispatchEvent(new Event('input', {bubbles: true}));
                    nie.dispatchEvent(new Event('change', {bubbles: true}));
                    name.value = data.name;
                    name.dispatchEvent(new Event('input', {bubbles: true}));
                    name.dispatchEvent(new Event('change', {bubbles: true}));
                    envia();
                }""", {"nie": cfg.nie, "name": cfg.full_name})

            ensure_not_rejected(self.step_id, page, log)

        retry_step(
            _attempt,
            attempts=cfg.step_retry_attempts,
            backoff_ms=cfg.step_retry_backoff_ms,
            logger=log,
            step_id=self.step_id,
            label="Personal data submission",
        )

        shot = save_debug_screenshot(
            page=page,
            out_dir=ctx.run_screenshots_dir,
            filename=f"{self.step_id}_after_personal_data.png",
            full_page=cfg.screenshot_full_page,
            width_px=cfg.screenshot_width_px,
            max_height_px=cfg.screenshot_max_height_px,
        )
        log.info(f"[{self.step_id}] Personal data submitted. url={page.url}")
        return StepResult(
            step_id=self.step_id,
            status=StepStatus.OK,
            message="Personal data submitted",
            screenshot=str(shot.path),
            data={"url": page.url},
        )
