from __future__ import annotations

from ..screenshot_utils import save_debug_screenshot
from ..step_framework import Step, StepResult, StepStatus
from .common import ensure_not_rejected, is_fortigate_block


class Step1VerifyProvince(Step):
    step_id = "step1"
    title = "Verify province selected"

    def run(self, ctx) -> StepResult:
        log = ctx.logger
        cfg = ctx.config
        page = ctx.page

        try:
            ensure_not_rejected(self.step_id, page, log)

            if is_fortigate_block(page):
                raise RuntimeError("FortiGate Intrusion Prevention page instead of province selector")

            page.wait_for_load_state("domcontentloaded", timeout=cfg.step_timeout_ms)

            # Requirement:
            # - If there is an *input* showing province value (e.g. "Málaga"), verify it's correct.
            # - Otherwise, if there is a *select*, select "Málaga" (or configured label) and proceed.

            selected_label = None
            selected = None

            # First, accept the common "PROVINCIA SELECCIONADA: Málaga" display.
            if page.locator("text=PROVINCIA SELECCIONADA").count() > 0 and page.locator(
                f"text={cfg.province_label}"
            ).count() > 0:
                selected_label = cfg.province_label
                selected = cfg.province_code
                log.info(f"[{self.step_id}] Province display verified: '{cfg.province_label}'.")
            else:
                # Next, look for an input that has Málaga value (some variants render it as a readonly input).
                province_input = page.locator(f"input[value='{cfg.province_label}']")
                if province_input.count() > 0:
                    selected_label = cfg.province_label
                    selected = cfg.province_code
                    log.info(f"[{self.step_id}] Province input detected with value '{cfg.province_label}'.")
                else:
                    # Fallback: province is a <select> (some sessions show the province selection page first).
                    page.wait_for_selector("select", timeout=cfg.step_timeout_ms)
                    selects = page.locator("select")

                    # Find the select that actually contains the province option (avoid selecting office dropdown).
                    province_select = None
                    for idx in range(selects.count()):
                        s = selects.nth(idx)
                        if s.locator(f"option:text-is('{cfg.province_label}')").count() > 0:
                            # Heuristic: province selector shouldn't include "Cualquier oficina"
                            if s.locator("option:text-is('Cualquier oficina')").count() == 0:
                                province_select = s
                                break
                            province_select = s  # keep as last resort
                    if province_select is None:
                        raise RuntimeError("Could not locate province <select> to select province")

                    # Select explicitly; if it's already selected this is a no-op.
                    try:
                        province_select.select_option(label=cfg.province_label)
                    except Exception:
                        # Some pages use codes; try by known province_code.
                        try:
                            province_select.select_option(value=cfg.province_code)
                        except Exception as e:
                            raise RuntimeError(f"Could not select province '{cfg.province_label}'") from e

                    # Verify selected option label where possible.
                    try:
                        selected_label = province_select.locator("option:checked").inner_text().strip()
                    except Exception:
                        selected_label = cfg.province_label
                    try:
                        selected = province_select.input_value()
                    except Exception:
                        selected = cfg.province_code

                    if selected_label and selected_label != cfg.province_label:
                        raise RuntimeError(
                            f"Province mismatch after selection. expected='{cfg.province_label}', got='{selected_label}'"
                        )

            shot = save_debug_screenshot(
                page=page,
                out_dir=ctx.run_screenshots_dir,
                filename=f"{self.step_id}_province_verified.png",
                full_page=cfg.screenshot_full_page,
                width_px=cfg.screenshot_width_px,
                max_height_px=cfg.screenshot_max_height_px,
            )
            log.info(
                f"[{self.step_id}] Province OK: label='{selected_label}' value='{selected}'. Screenshot: {shot.path}"
            )
            return StepResult(
                step_id=self.step_id,
                status=StepStatus.OK,
                message=f"Province verified: {cfg.province_label}",
                screenshot=str(shot.path),
                data={"selected_label": selected_label, "selected_value": selected},
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
                message="Province verification failed",
                screenshot=screenshot,
                error_type=type(e).__name__,
                error_details=str(e),
            )

