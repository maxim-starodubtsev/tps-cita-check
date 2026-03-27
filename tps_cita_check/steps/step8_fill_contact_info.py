from __future__ import annotations

from ..screenshot_utils import save_debug_screenshot
from ..step_framework import Step, StepResult, StepStatus
from .common import ensure_not_rejected, retry_step, run_step_safely


class Step8FillContactInfo(Step):
    step_id = "step8"
    title = "Fill contact info (phone + email) if contact form present"

    def run(self, ctx) -> StepResult:
        return run_step_safely(self.step_id, self.title, ctx, self._inner_run)

    def _inner_run(self, ctx) -> StepResult:
        log = ctx.logger
        cfg = ctx.config
        page = ctx.page

        ensure_not_rejected(self.step_id, page, log)

        # Detect whether the contact info form is on screen.
        # The form is "Paso 2 de 5" — INFORMACIÓN COMPLEMENTARIA with phone +
        # email fields.  It appears after step7 clicks "Solicitar Cita" when the
        # site requires contact details before showing appointment availability.
        is_contact_form = page.locator("#txtTelefonoCitado").count() > 0

        if not is_contact_form:
            # We are already on a result page (e.g. "no hay citas disponibles").
            # Step7 navigated directly here; confirm the no_citas flag from body.
            body_text = page.evaluate("document.body.innerText")
            has_no_citas = "no hay citas disponibles" in body_text.lower()
            log.info(
                f"[{self.step_id}] Contact form not present — "
                f"result already on page (no_citas={has_no_citas})"
            )
            shot = save_debug_screenshot(
                page=page,
                out_dir=ctx.run_screenshots_dir,
                filename=f"{self.step_id}_result.png",
                full_page=cfg.screenshot_full_page,
                width_px=cfg.screenshot_width_px,
                max_height_px=cfg.screenshot_max_height_px,
            )
            return StepResult(
                step_id=self.step_id,
                status=StepStatus.OK,
                message="Contact form not present — result already on page",
                screenshot=str(shot.path),
                data={"no_citas": has_no_citas},
            )

        # ── Contact info form is visible ────────────────────────────────────────
        log.info(f"[{self.step_id}] Contact info form detected (Paso 2 de 5)")

        if not cfg.phone:
            return StepResult(
                step_id=self.step_id,
                status=StepStatus.FAIL,
                message="Phone not provided (use --phone or CITA_PHONE)",
                error_type="ValueError",
                error_details="phone is empty",
            )
        if not cfg.email:
            return StepResult(
                step_id=self.step_id,
                status=StepStatus.FAIL,
                message="Email not provided (use --email or CITA_EMAIL)",
                error_type="ValueError",
                error_details="email is empty",
            )

        def _attempt():
            ensure_not_rejected(self.step_id, page, log)

            log.info(
                f"[{self.step_id}] Filling phone + email via JS and calling enviar()"
            )
            # Fill all three fields via direct value assignment (same pattern as
            # step6) and dispatch input/change events so any JS listeners fire.
            # emailDOS has class "noPaste" which blocks browser paste but does not
            # affect programmatic .value assignment.
            # enviar() on this page validates the fields then does:
            #   document.procedimientos.action = "acOfertarCita";
            #   document.procedimientos.submit();
            with page.expect_navigation(
                wait_until="load", timeout=cfg.step_timeout_ms
            ):
                page.evaluate(
                    """(data) => {
                        const phone  = document.getElementById('txtTelefonoCitado');
                        const email1 = document.getElementById('emailUNO');
                        const email2 = document.getElementById('emailDOS');

                        phone.value = data.phone;
                        phone.dispatchEvent(new Event('input',  {bubbles: true}));
                        phone.dispatchEvent(new Event('change', {bubbles: true}));

                        email1.value = data.email;
                        email1.dispatchEvent(new Event('input',  {bubbles: true}));
                        email1.dispatchEvent(new Event('change', {bubbles: true}));

                        email2.value = data.email;
                        email2.dispatchEvent(new Event('input',  {bubbles: true}));
                        email2.dispatchEvent(new Event('change', {bubbles: true}));

                        enviar();
                    }""",
                    {"phone": cfg.phone, "email": cfg.email},
                )

            ensure_not_rejected(self.step_id, page, log)

        retry_step(
            _attempt,
            attempts=cfg.step_retry_attempts,
            backoff_ms=cfg.step_retry_backoff_ms,
            logger=log,
            step_id=self.step_id,
            label="Contact info submission",
        )

        body_text = page.evaluate("document.body.innerText")
        has_no_citas = "no hay citas disponibles" in body_text.lower()

        shot = save_debug_screenshot(
            page=page,
            out_dir=ctx.run_screenshots_dir,
            filename=f"{self.step_id}_after_contact_info.png",
            full_page=cfg.screenshot_full_page,
            width_px=cfg.screenshot_width_px,
            max_height_px=cfg.screenshot_max_height_px,
        )
        log.info(f"[{self.step_id}] Contact info submitted. url={page.url}")

        if has_no_citas:
            log.info(f"[{self.step_id}] No appointments available")
        else:
            log.info(
                f"[{self.step_id}] Page loaded after contact info — "
                "check screenshot for appointment availability"
            )

        return StepResult(
            step_id=self.step_id,
            status=StepStatus.OK,
            message="No citas disponibles" if has_no_citas else "Contact info submitted — check screenshot",
            screenshot=str(shot.path),
            data={"url": page.url, "no_citas": has_no_citas},
        )
