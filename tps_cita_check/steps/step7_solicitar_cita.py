from __future__ import annotations

from ..screenshot_utils import save_debug_screenshot
from ..step_framework import Step, StepResult, StepStatus
from .common import PlaywrightTimeout, ensure_not_rejected, retry_step


class Step7SolicitarCita(Step):
    step_id = "step7"
    title = "Click Solicitar Cita"

    def run(self, ctx) -> StepResult:
        log = ctx.logger
        cfg = ctx.config
        page = ctx.page

        try:
            ensure_not_rejected(self.step_id, page, log)

            # The site may skip straight to "no hay citas disponibles" after
            # step 6, without showing an intermediate "Solicitar Cita" page.
            # Check the current page first before waiting for #btnEnviar.
            body_text = page.evaluate("document.body.innerText")
            already_has_result = "no hay citas disponibles" in body_text.lower()

            if already_has_result:
                log.info(f"[{self.step_id}] Result already on page (no intermediate step)")
            else:
                # Intermediate page with Solicitar Cita button.
                def _attempt():
                    btn = page.locator("#btnEnviar")
                    btn.wait_for(state="visible", timeout=cfg.step_timeout_ms)
                    log.info(f"[{self.step_id}] #btnEnviar visible, calling enviar('solicitud') via JS")

                    with page.expect_navigation(wait_until="load", timeout=cfg.step_timeout_ms):
                        page.evaluate("() => { enviar('solicitud'); }")

                    ensure_not_rejected(self.step_id, page, log)

                retry_step(
                    _attempt,
                    attempts=cfg.step_retry_attempts,
                    backoff_ms=cfg.step_retry_backoff_ms,
                    logger=log,
                    step_id=self.step_id,
                    label="Solicitar Cita click",
                )

                body_text = page.evaluate("document.body.innerText")

            has_no_citas = "no hay citas disponibles" in body_text.lower()

            shot = save_debug_screenshot(
                page=page,
                out_dir=ctx.run_screenshots_dir,
                filename=f"{self.step_id}_solicitar_cita.png",
                full_page=cfg.screenshot_full_page,
                width_px=cfg.screenshot_width_px,
                max_height_px=cfg.screenshot_max_height_px,
            )
            log.info(f"[{self.step_id}] Solicitar Cita result. url={page.url}")

            if has_no_citas:
                log.info(f"[{self.step_id}] No appointments available")
            else:
                log.info(f"[{self.step_id}] Page loaded — check screenshot for availability")

            return StepResult(
                step_id=self.step_id,
                status=StepStatus.OK,
                message="No citas disponibles" if has_no_citas else "Solicitar Cita page loaded",
                screenshot=str(shot.path),
                data={"url": page.url, "no_citas": has_no_citas},
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
                message="Solicitar Cita timed out",
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
                message="Solicitar Cita failed",
                screenshot=screenshot,
                error_type=type(e).__name__,
                error_details=str(e),
            )
