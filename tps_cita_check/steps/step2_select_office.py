from __future__ import annotations

from ..screenshot_utils import save_debug_screenshot
from ..step_framework import Step, StepResult, StepStatus
from .common import ensure_not_rejected, retry_step, run_step_safely


class Step2SelectOffice(Step):
    step_id = "step2"
    title = "Select office"

    def __init__(self, office_label: str | None = None) -> None:
        # Allow the runner to supply a per-iteration office label; falls back to
        # ctx.config.office_label (first entry of office_labels) if not given.
        self._office_label = office_label

    def run(self, ctx) -> StepResult:
        return run_step_safely(self.step_id, self.title, ctx, self._inner_run)

    def _inner_run(self, ctx) -> StepResult:
        log = ctx.logger
        cfg = ctx.config
        page = ctx.page
        # Use the injected label, or fall back to the config default.
        office_label = self._office_label if self._office_label is not None else cfg.office_label

        def _attempt():
            ensure_not_rejected(self.step_id, page, log)

            page.wait_for_selector("text=PROVINCIA SELECCIONADA", timeout=cfg.step_timeout_ms)
            selects = page.locator("select")
            if selects.count() < 1:
                raise RuntimeError("Office <select> not found")
            office_select = selects.nth(0)

            # Try exact label first; if it triggers navigation, wait for it.
            try:
                with page.expect_navigation(wait_until="load", timeout=cfg.step_timeout_ms):
                    office_select.select_option(label=office_label)
                log.info(f"[{self.step_id}] Office selected by label: {office_label}")
            except Exception as e:
                log.warning(f"[{self.step_id}] Label select failed, trying fallback: {e}")
                options = office_select.locator("option")
                found_value = None
                found_text = None
                for i in range(options.count()):
                    text = options.nth(i).inner_text().strip()
                    if office_label in text:
                        found_value = options.nth(i).get_attribute("value")
                        found_text = text
                        break
                if not found_value:
                    raise RuntimeError(f"Could not find office option for '{office_label}'")
                with page.expect_navigation(wait_until="load", timeout=cfg.step_timeout_ms):
                    office_select.select_option(value=found_value)
                log.info(f"[{self.step_id}] Office selected by value: {found_text} (value={found_value})")

            ensure_not_rejected(self.step_id, page, log)

        retry_step(
            _attempt,
            attempts=cfg.step_retry_attempts,
            backoff_ms=cfg.step_retry_backoff_ms,
            logger=log,
            step_id=self.step_id,
            label="Office selection",
        )

        shot = save_debug_screenshot(
            page=page,
            out_dir=ctx.run_screenshots_dir,
            filename=f"{self.step_id}_office_selected.png",
            full_page=cfg.screenshot_full_page,
            width_px=cfg.screenshot_width_px,
            max_height_px=cfg.screenshot_max_height_px,
        )
        return StepResult(
            step_id=self.step_id,
            status=StepStatus.OK,
            message="Office selected",
            screenshot=str(shot.path),
            data={"url_after": page.url},
        )
