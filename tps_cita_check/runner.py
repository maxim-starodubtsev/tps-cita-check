from __future__ import annotations

import random
import shutil
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

from playwright.sync_api import sync_playwright

from .baseline_utils import compare_images_by_size
from .config import CheckerConfig
from .context import RunContext
from .screenshot_utils import baseline_path_for
from .stealth import apply_stealth_sync
from .step_framework import Step, StepResult, StepStatus
from .steps.common import human_delay, is_retriable_error
from .steps.step0_load import Step0Load
from .steps.step1_verify_province import Step1VerifyProvince
from .steps.step2_select_office import Step2SelectOffice
from .steps.step3_select_tramite import Step3SelectTramite
from .steps.step4_accept import Step4Accept
from .steps.step5_entrar import Step5Entrar
from .steps.step6_fill_personal_data import Step6FillPersonalData
from .steps.step7_solicitar_cita import Step7SolicitarCita
from .steps.step8_fill_contact_info import Step8FillContactInfo


@dataclass(frozen=True)
class RunSummary:
    ok: bool
    results: List[StepResult]
    # Office where an appointment was found (None = not found or run errored out).
    found_cita_office: Optional[str] = None
    # Per-office outcomes: tuple of {"label": str, "status": str} dicts.
    # Status values: "no_citas", "cita_found", "error".
    office_results: tuple = ()


def _handle_baseline(res: StepResult, config: CheckerConfig, logger) -> None:
    """Compare or bootstrap a baseline screenshot for a successful step."""
    if not res.screenshot:
        return
    actual = Path(res.screenshot)
    if not actual.exists():
        return

    baseline = baseline_path_for(
        baselines_dir=config.baselines_dir,
        step_id=res.step_id,
        name="ok",
    )

    if not baseline.exists():
        shutil.copy2(actual, baseline)
        logger.info(f"[baseline] {res.step_id}: saved new baseline → {baseline}")
        return

    cmp = compare_images_by_size(baseline, actual)
    if cmp.ok:
        logger.info(f"[baseline] {res.step_id}: OK ({cmp.reason})")
    else:
        logger.warning(f"[baseline] {res.step_id}: MISMATCH ({cmp.reason})")


def _save_page_source(step_id: str, page, out_dir: Path, logger) -> None:
    """Save full page HTML source for offline diagnosis."""
    try:
        html = page.content()
        path = out_dir / f"{step_id}_page.html"
        path.write_text(html, encoding="utf-8")
        logger.info(f"[source] {step_id}: saved {len(html)} bytes → {path}")
    except Exception as exc:
        logger.warning(f"[source] {step_id}: could not save page source: {exc}")


def _is_retriable_failure(res: StepResult) -> bool:
    """Return True if the step failed due to a transient error (WAF, session expiry,
    no-service, system error, or timeout).  Step-level retries are exhausted before
    this is called, so a timeout here means the site was genuinely slow/unresponsive
    and a fresh browser session from the same office is worth attempting.
    """
    if res.status == StepStatus.OK:
        return False
    return is_retriable_error(res.error_details)


def _navigate_back_to_province(page, config: CheckerConfig, logger) -> bool:
    """Return to the province/office selection page after a "no citas" result.

    Strategy:
    1. Try to click Salir or Volver on the current page (exits the appointment flow).
    2. After any click (or if no button was found) check whether the office select
       ``#sede`` is now visible.  If it is, we are already on the right page.
    3. If the office select is NOT visible we may have landed on the province
       selection form (id="form" select with all provinces).  In that case
       navigate directly to ``start_url`` (``?p=<code>``) which pre-selects the
       province and shows the office selection page — equivalent to manually
       picking the province and clicking "Aceptar".

    Returns True when we reach the office selection page, False on failure.
    """
    try:
        for selector, label in [
            ("input[value='Salir']", "Salir input"),
            ("button:has-text('Salir')", "Salir button"),
            ("a:has-text('Salir')", "Salir link"),
            ("input[value='Volver']", "Volver input"),
            ("button:has-text('Volver')", "Volver button"),
            ("a:has-text('Volver')", "Volver link"),
        ]:
            btn = page.locator(selector)
            if btn.count() > 0:
                try:
                    with page.expect_navigation(wait_until="load", timeout=config.step_timeout_ms):
                        btn.first.click()
                    logger.info(f"[back] Clicked '{label}'")
                    break
                except Exception as nav_exc:
                    logger.debug(f"[back] '{label}' click did not cause navigation: {nav_exc}")

        # After a Salir/Volver click we may land on the province selection form
        # (select#form with all provinces + Aceptar button) rather than directly
        # on the office selection page.  Detect this and navigate to start_url,
        # which is equivalent to selecting the province and clicking Aceptar.
        if page.locator("select#sede").count() == 0:
            logger.info(
                "[back] Office select not visible (on province form or result page); "
                f"navigating to start URL: {config.start_url}"
            )
            page.goto(config.start_url, wait_until="load", timeout=config.step_timeout_ms)

        logger.info(f"[back] On office selection page (url={page.url})")
        return True

    except Exception as e:
        logger.error(f"[back] Back navigation failed: {e}")
        return False


def _clear_tspd_cookies(context, logger) -> None:
    """Remove F5 TSPD bot-detection cookies to reset the WAF session counter.

    TSPD cookies follow the naming pattern ``TS[hex…]`` and are used by the
    F5 BIG-IP ASM/TSPD module to track per-session request counts.  Clearing
    them between offices makes each office check appear as a fresh session to
    the WAF, preventing the cumulative-request threshold from being hit.

    All other cookies (app session, locale, etc.) are preserved so the page
    state remains intact for the next office.
    """
    try:
        all_cookies = context.cookies()
        tspd = [c for c in all_cookies if c["name"].upper().startswith("TS")]
        if tspd:
            keep = [c for c in all_cookies if not c["name"].upper().startswith("TS")]
            context.clear_cookies()
            if keep:
                context.add_cookies(keep)
            logger.info(
                f"[runner] Cleared {len(tspd)} TSPD cookie(s): "
                f"{[c['name'] for c in tspd]}"
            )
        else:
            logger.debug("[runner] No TSPD cookies found to clear")
    except Exception as exc:
        logger.warning(f"[runner] TSPD cookie clear failed (non-fatal): {exc}")


def _run_once(
    *,
    config: CheckerConfig,
    logger,
    run_id: str,
    start_office_idx: int = 0,
    _override_steps: list[Step] | None = None,
) -> RunSummary:
    """Execute the full step pipeline once (single browser session).

    Normal mode (``_override_steps=None``): runs Step0 + Step1 once, then
    iterates over config.office_labels starting from ``start_office_idx``.

    Legacy/test mode (``_override_steps`` provided): runs the given steps in
    order and stops on first failure (mirrors the old sequential behaviour).
    """
    ctx = RunContext(config=config, logger=logger, run_id=run_id)
    ctx.ensure_artifact_dirs()

    results: list[StepResult] = []
    found_cita_office: str | None = None
    completed_normally = False

    ext_dir = str(config.resolved_extension_dir)
    profile_dir = str(config.resolved_chrome_profile_dir)

    with sync_playwright() as p:
        # Extensions require a real browser. Use --headless=new (Chrome 112+) for
        # invisible mode with full extension support; fall back to visible for debugging.
        headless_args = [] if not config.headless else ["--headless=new"]
        # headless=False is intentional here: the Playwright API parameter must be
        # False so the persistent context initialises in "headed" mode, which is
        # required for Chrome extensions. When config.headless is True, we inject
        # --headless=new via args to get Chrome's "new headless" mode that still
        # supports extensions. The CLI flag overrides the API parameter.
        context = p.chromium.launch_persistent_context(
            profile_dir,
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                f"--disable-extensions-except={ext_dir}",
                f"--load-extension={ext_dir}",
                *headless_args,
            ],
            viewport={"width": 1280, "height": 720},
            locale="es-ES",
            user_agent=config.user_agent,
            ignore_https_errors=config.ignore_https_errors,
        )

        if config.stealth_enabled:
            apply_stealth_sync(context)
            logger.info("Stealth evasion scripts injected")

        page = context.pages[0] if context.pages else context.new_page()
        ctx.context = context
        ctx.page = page

        def _run_step(step: Step) -> StepResult:
            """Run one step: add human delay, log, execute, save page source, handle baseline."""
            # Skip delay before the very first step.
            if results:
                delay = human_delay(page, config.step_delay_min_ms, config.step_delay_max_ms)
                logger.info(f"[delay] {delay}ms before {step.step_id}")
            logger.info(f"--- {step.step_id}: {step.title} ---")
            res = step.run(ctx)
            results.append(res)
            _save_page_source(step.step_id, page, ctx.run_screenshots_dir, logger)
            if res.status == StepStatus.OK:
                logger.info(f"[{res.step_id}] OK: {res.message}")
                _handle_baseline(res, config, logger)
            else:
                logger.error(
                    f"[{res.step_id}] FAILED: {res.message} ({res.error_type}: {res.error_details})"
                )
            return res

        # ── Legacy sequential mode (used by tests via _override_steps) ─────────
        if _override_steps is not None:
            for step in _override_steps:
                res = _run_step(step)
                if res.status != StepStatus.OK:
                    break
            context.close()
            ok = all(r.status == StepStatus.OK for r in results) and len(results) == len(_override_steps)
            return RunSummary(ok=ok, results=results)

        # ── Phase 1: load the page and verify province (runs only once) ──────────
        for step in [Step0Load(), Step1VerifyProvince()]:
            res = _run_step(step)
            if res.status != StepStatus.OK:
                context.close()
                return RunSummary(ok=False, results=results)

        # ── Phase 2: per-office loop ──────────────────────────────────────────────
        offices = config.office_labels
        inner_step_classes = [
            Step3SelectTramite,
            Step4Accept,
            Step5Entrar,
            Step6FillPersonalData,
            Step7SolicitarCita,
            Step8FillContactInfo,
        ]

        office_results: list[dict] = []

        for office_idx, office_label in enumerate(offices):
            if office_idx < start_office_idx:
                continue  # already processed in a previous attempt
            is_last_office = office_idx == len(offices) - 1
            ctx.office_idx = office_idx
            logger.info(
                f"[runner] Office {office_idx + 1}/{len(offices)}: {office_label}"
            )

            # Step 2: select this specific office.
            res2 = _run_step(Step2SelectOffice(office_label=office_label))
            if res2.status != StepStatus.OK:
                office_results.append({"label": office_label, "status": "error"})
                break

            # Steps 3–8 for this office.
            office_error = False
            step7_result: StepResult | None = None
            step8_result: StepResult | None = None
            for StepClass in inner_step_classes:
                res = _run_step(StepClass())
                if res.status != StepStatus.OK:
                    office_error = True
                    break
                if res.step_id == "step7":
                    step7_result = res
                elif res.step_id == "step8":
                    step8_result = res

            if office_error:
                office_results.append({"label": office_label, "status": "error"})
                break  # Hard failure — stop everything.

            # Step8 is authoritative when it ran; fall back to step7.
            # step8 always runs but returns no screenshot when the contact form was
            # absent (result page was already present after step7).
            final_step = step8_result or step7_result

            # Log the best available screenshot for this office.
            best_screenshot = (
                (step8_result.screenshot if step8_result and step8_result.screenshot else None)
                or (step7_result.screenshot if step7_result and step7_result.screenshot else None)
            )
            if best_screenshot:
                logger.info(
                    f"[runner] Office {office_idx + 1} screenshot: {best_screenshot}"
                )

            # Determine appointment availability.
            no_citas = (
                final_step.data.get("no_citas")
                if final_step and final_step.data
                else None
            )

            if no_citas is False:
                # Appointment is available at this office!
                office_results.append({"label": office_label, "status": "cita_found"})
                found_cita_office = office_label
                completed_normally = True
                logger.info(f"[runner] Appointment AVAILABLE at: {office_label}")
                break

            office_results.append({"label": office_label, "status": "no_citas"})
            logger.info(f"[runner] No appointments at: {office_label}")

            if is_last_office:
                completed_normally = True
            else:
                # Navigate back to province/office page and re-verify province.
                back_ok = _navigate_back_to_province(page, config, logger)
                if not back_ok:
                    logger.error("[runner] Back navigation failed; stopping office loop")
                    break
                # Clear TSPD tracking cookies so the next office starts with a
                # fresh WAF session counter (prevents cumulative-request blocking).
                _clear_tspd_cookies(ctx.context, logger)
                # Inter-office cooldown: 30–60s to avoid time-windowed rate limits.
                cooldown_s = random.uniform(30, 60)
                logger.info(f"[runner] Inter-office cooldown: {cooldown_s:.1f}s")
                time.sleep(cooldown_s)
                # Reload the start URL so the next office gets a brand-new TSPD
                # session cookie from the WAF (cookie jar was cleared above).
                page.goto(config.start_url, wait_until="load", timeout=config.step_timeout_ms)
                res_prov = _run_step(Step1VerifyProvince())
                if res_prov.status != StepStatus.OK:
                    logger.error("[runner] Province re-verification failed after navigating back")
                    break

        context.close()

    ok = all(r.status == StepStatus.OK for r in results) and completed_normally
    return RunSummary(
        ok=ok,
        results=results,
        found_cita_office=found_cita_office,
        office_results=tuple(office_results),
    )


_OFFICE_LOG_ICONS = {
    "no_citas": "✅",
    "cita_found": "🎉",
    "error": "❌",
}


def _log_run_summary(logger, config: CheckerConfig, office_results: tuple) -> None:
    """Log a per-office result table at the end of every run."""
    labels = config.office_labels
    if not labels:
        return
    total = len(labels)
    checked = len(office_results)
    result_by_label = {o["label"]: o["status"] for o in office_results}

    logger.info("[runner] ── Office check summary " + "─" * 36)
    for i, label in enumerate(labels):
        short = label.split(",")[0].strip()
        if label in result_by_label:
            status = result_by_label[label]
            icon = _OFFICE_LOG_ICONS.get(status, "?")
            status_str = f"{icon} {status}"
        else:
            status_str = "— not checked"
        logger.info(f"[runner]   {i + 1:>2}. {short:<30} {status_str}")
    logger.info(f"[runner] ── Checked {checked}/{total} offices " + "─" * 29)


def run_check(*, config: CheckerConfig, logger, steps: Iterable[Step] | None = None) -> RunSummary:
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    logger.info("=" * 70)
    logger.info("Starting TPS cita flow")
    logger.info(f"Run id: {run_id}")
    logger.info(f"Headless: {config.headless}")
    logger.info(f"Stealth: {config.stealth_enabled}")
    logger.info(f"Start URL: {config.start_url}")
    logger.info(f"Offices to check ({len(config.office_labels)}): {list(config.office_labels)}")

    max_attempts = config.run_retry_attempts
    accumulated_office_results: list[dict] = []
    start_office_idx = 0
    merged_office_results: tuple = ()

    # Initialise summary so the fallback return after the loop is safe even if
    # max_attempts == 0 (should not happen, but prevents UnboundLocalError).
    summary = RunSummary(ok=False, results=[])

    for attempt in range(1, max_attempts + 1):
        summary = _run_once(
            config=config,
            logger=logger,
            run_id=run_id,
            start_office_idx=start_office_idx,
            _override_steps=list(steps) if steps is not None else None,
        )

        merged_office_results = tuple(accumulated_office_results) + summary.office_results

        if summary.ok:
            _log_run_summary(logger, config, merged_office_results)
            return RunSummary(
                ok=True,
                results=summary.results,
                found_cita_office=summary.found_cita_office,
                office_results=merged_office_results,
            )

        # Check if the failure was WAF-related and we can retry from the failed office.
        last_result = summary.results[-1] if summary.results else None
        if last_result and _is_retriable_failure(last_result) and attempt < max_attempts:
            # Accumulate the offices that completed successfully in this attempt.
            successful = [o for o in summary.office_results if o["status"] != "error"]
            failed = [o for o in summary.office_results if o["status"] == "error"]
            accumulated_office_results.extend(successful)

            # Compute which office to start from on the next attempt.
            if failed:
                failed_label = failed[0]["label"]
                offices_list = list(config.office_labels)
                try:
                    start_office_idx = offices_list.index(failed_label)
                except ValueError:
                    start_office_idx = len(accumulated_office_results)
            # If no failed office entry (WAF hit Step0/Step1), start_office_idx unchanged.

            backoff_s = config.run_retry_base_backoff_s * attempt  # escalating backoff
            retry_office = config.office_labels[start_office_idx] if start_office_idx < len(config.office_labels) else "?"
            logger.warning(
                f"[runner] WAF block on attempt {attempt}/{max_attempts}. "
                f"Offices done: {len(accumulated_office_results)}/{len(config.office_labels)}. "
                f"Retrying from office {start_office_idx + 1} ({retry_office}) in {backoff_s:.1f}s…"
            )
            time.sleep(backoff_s)
            # Keep the same run_id so retry screenshots land in the same directory.
            continue

        # Non-WAF failure or final attempt — stop.
        _log_run_summary(logger, config, merged_office_results)
        return RunSummary(
            ok=False,
            results=summary.results,
            found_cita_office=summary.found_cita_office,
            office_results=merged_office_results,
        )

    # Fallback: loop exhausted (should not normally be reached).
    _log_run_summary(logger, config, merged_office_results)
    return RunSummary(
        ok=False,
        results=summary.results,
        found_cita_office=summary.found_cita_office,
        office_results=merged_office_results,
    )

