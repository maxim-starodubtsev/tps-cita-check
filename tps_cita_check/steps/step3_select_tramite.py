from __future__ import annotations

from ..screenshot_utils import save_debug_screenshot
from ..step_framework import Step, StepResult, StepStatus
from .common import PlaywrightTimeout, ensure_not_rejected, is_url_rejected, retry_step


class Step3SelectTramite(Step):
    step_id = "step3"
    title = "Select trámite"

    def run(self, ctx) -> StepResult:
        log = ctx.logger
        cfg = ctx.config
        page = ctx.page

        # Mutable container so _attempt can communicate selected trámite back.
        result_data: dict = {}

        def _attempt():
            ensure_not_rejected(self.step_id, page, log)

            # After office selection, the page may reload to /selectSede and inject trámite selects asynchronously.
            page.wait_for_selector("select", timeout=cfg.step_timeout_ms)

            # Poll for additional selects up to timeout.
            deadline_ms = cfg.step_timeout_ms
            step_ms = 500
            waited = 0
            selects = page.locator("select")
            while waited < deadline_ms:
                if is_url_rejected(page):
                    raise RuntimeError("Session blocked: The requested URL was rejected")
                count = selects.count()
                if count >= 2:
                    break
                page.wait_for_timeout(step_ms)
                waited += step_ms

            selects = page.locator("select")
            selects_count = selects.count()
            log.info(f"[{self.step_id}] Selects present after office: {selects_count}")
            if selects_count < 2:
                raise RuntimeError("Trámite selects did not appear after office selection")

            keyword = cfg.tramite_contains.upper()
            tramite_select = None
            tramite_value = None
            tramite_text = None

            for idx in range(1, selects_count):
                candidate = selects.nth(idx)
                options = candidate.locator("option")
                opt_count = options.count()
                log.debug(f"[{self.step_id}] Inspecting select #{idx} options={opt_count}")
                for i in range(opt_count):
                    text = options.nth(i).inner_text().strip()
                    if keyword in text.upper():
                        tramite_select = candidate
                        tramite_value = options.nth(i).get_attribute("value")
                        tramite_text = text
                        break
                if tramite_select:
                    break

            if not tramite_select or not tramite_value:
                all_texts = []
                for idx in range(1, selects_count):
                    options = selects.nth(idx).locator("option")
                    for i in range(options.count()):
                        all_texts.append(options.nth(i).inner_text().strip())
                log.error(
                    f"[{self.step_id}] Could not find trámite containing '{cfg.tramite_contains}'. "
                    f"Available options: {all_texts}"
                )
                raise RuntimeError("Could not find requested trámite option")

            tramite_select.select_option(value=tramite_value)
            log.info(f"[{self.step_id}] Trámite selected: {tramite_text} (value={tramite_value})")
            result_data["tramite_text"] = tramite_text
            result_data["tramite_value"] = tramite_value

        try:
            retry_step(
                _attempt,
                attempts=cfg.step_retry_attempts,
                backoff_ms=cfg.step_retry_backoff_ms,
                logger=log,
                step_id=self.step_id,
                label="Trámite selection",
            )

            shot = save_debug_screenshot(
                page=page,
                out_dir=ctx.run_screenshots_dir,
                filename=f"{self.step_id}_tramite_selected.png",
                full_page=cfg.screenshot_full_page,
                width_px=cfg.screenshot_width_px,
                max_height_px=cfg.screenshot_max_height_px,
            )
            return StepResult(
                step_id=self.step_id,
                status=StepStatus.OK,
                message="Trámite selected",
                screenshot=str(shot.path),
                data={**result_data, "url": page.url},
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
                message="Trámite selection timed out",
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
                message="Trámite selection failed",
                screenshot=screenshot,
                error_type=type(e).__name__,
                error_details=str(e),
            )

