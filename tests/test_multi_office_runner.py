"""TEST-1 + TEST-4: Multi-office loop and run_check integration tests."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tps_cita_check.config import CheckerConfig
from tps_cita_check.runner import _run_office_loop, run_check
from tps_cita_check.step_framework import Step, StepResult, StepStatus


# ── Helpers ──────────────────────────────────────────────────────────────────


def _ok(step_id: str, no_citas: bool | None = None) -> StepResult:
    data: dict = {}
    if no_citas is not None:
        data["no_citas"] = no_citas
    return StepResult(step_id=step_id, status=StepStatus.OK, message="ok", data=data)


def _fail(step_id: str, err: str = "boom") -> StepResult:
    return StepResult(
        step_id=step_id,
        status=StepStatus.FAIL,
        message="fail",
        error_type="RuntimeError",
        error_details=err,
    )


def _make_run_step(results: list[StepResult]):
    """Return a _run_step callable that yields results in sequence."""
    it = iter(results)

    def _run_step(step: Step) -> StepResult:
        return next(it)

    return _run_step


def _make_ctx():
    ctx = MagicMock()
    return ctx


# One complete office worth of OK results (steps 2-8), step8 has no_citas flag.
def _office_ok(no_citas: bool = True) -> list[StepResult]:
    steps = ["step2", "step3", "step4", "step5", "step6", "step7", "step8"]
    results = []
    for s in steps:
        if s in ("step7", "step8"):
            results.append(_ok(s, no_citas=no_citas))
        else:
            results.append(_ok(s))
    return results


def _province_recheck() -> list[StepResult]:
    """Step1VerifyProvince result inserted between offices."""
    return [_ok("step1")]


# ── _run_office_loop unit tests (TEST-1) ─────────────────────────────────────


@patch("tps_cita_check.runner.time.sleep")
@patch("tps_cita_check.runner._clear_tspd_cookies")
@patch("tps_cita_check.runner._navigate_back_to_province", return_value=True)
def test_all_offices_no_citas(mock_back, mock_clear, mock_sleep):
    """Two offices both return no_citas → completed_normally=True, ok status."""
    cfg = CheckerConfig(
        office_labels=("Office A", "Office B"),
        headless=True, stealth_enabled=False,
        nie="X1234567Y", full_name="Test User",
    )
    results_seq = _office_ok(no_citas=True) + _province_recheck() + _office_ok(no_citas=True)

    found, completed, office_results = _run_office_loop(
        ctx=_make_ctx(),
        config=cfg,
        start_office_idx=0,
        _run_step=_make_run_step(results_seq),
        logger=MagicMock(),
    )

    assert found is None
    assert completed is True
    assert len(office_results) == 2
    assert all(o["status"] == "no_citas" for o in office_results)
    mock_sleep.assert_called_once()  # exactly one inter-office cooldown
    mock_clear.assert_called_once()


@patch("tps_cita_check.runner.time.sleep")
@patch("tps_cita_check.runner._clear_tspd_cookies")
@patch("tps_cita_check.runner._navigate_back_to_province", return_value=True)
def test_office_with_cita_found_stops_early(mock_back, mock_clear, mock_sleep):
    """Office 2 of 3 finds cita → loop stops, found_cita_office set, no cooldown for office 3."""
    cfg = CheckerConfig(
        office_labels=("Office A", "Office B", "Office C"),
        headless=True, stealth_enabled=False,
        nie="X1234567Y", full_name="Test User",
    )
    results_seq = (
        _office_ok(no_citas=True)   # Office A: no citas
        + _province_recheck()
        + _office_ok(no_citas=False)  # Office B: CITA FOUND — loop ends here
    )

    found, completed, office_results = _run_office_loop(
        ctx=_make_ctx(),
        config=cfg,
        start_office_idx=0,
        _run_step=_make_run_step(results_seq),
        logger=MagicMock(),
    )

    assert found == "Office B"
    assert completed is True
    assert len(office_results) == 2  # A and B only (C not reached)
    assert office_results[0]["status"] == "no_citas"
    assert office_results[1]["status"] == "cita_found"
    # Only one cooldown (between A and B)
    assert mock_sleep.call_count == 1


@patch("tps_cita_check.runner.time.sleep")
@patch("tps_cita_check.runner._clear_tspd_cookies")
@patch("tps_cita_check.runner._navigate_back_to_province", return_value=True)
def test_office_step2_failure_stops_loop(mock_back, mock_clear, mock_sleep):
    """Step2 failure for the first office marks it as error and stops."""
    cfg = CheckerConfig(
        office_labels=("Office A", "Office B"),
        headless=True, stealth_enabled=False,
        nie="X1234567Y", full_name="Test User",
    )
    results_seq = [_fail("step2", err="Session blocked: The requested URL was rejected")]

    found, completed, office_results = _run_office_loop(
        ctx=_make_ctx(),
        config=cfg,
        start_office_idx=0,
        _run_step=_make_run_step(results_seq),
        logger=MagicMock(),
    )

    assert found is None
    assert completed is False
    assert len(office_results) == 1
    assert office_results[0]["status"] == "error"
    mock_sleep.assert_not_called()


@patch("tps_cita_check.runner.time.sleep")
@patch("tps_cita_check.runner._clear_tspd_cookies")
@patch("tps_cita_check.runner._navigate_back_to_province", return_value=True)
def test_start_office_idx_skips_earlier_offices(mock_back, mock_clear, mock_sleep):
    """start_office_idx=1 skips Office A, processes Office B only."""
    cfg = CheckerConfig(
        office_labels=("Office A", "Office B"),
        headless=True, stealth_enabled=False,
        nie="X1234567Y", full_name="Test User",
    )
    results_seq = _office_ok(no_citas=True)  # Only Office B needs results

    found, completed, office_results = _run_office_loop(
        ctx=_make_ctx(),
        config=cfg,
        start_office_idx=1,
        _run_step=_make_run_step(results_seq),
        logger=MagicMock(),
    )

    assert completed is True
    assert len(office_results) == 1
    assert office_results[0]["label"] == "Office B"
    mock_sleep.assert_not_called()  # no cooldown when only one office processed


@patch("tps_cita_check.runner.time.sleep")
@patch("tps_cita_check.runner._clear_tspd_cookies")
@patch("tps_cita_check.runner._navigate_back_to_province", return_value=False)
def test_back_navigation_failure_stops_loop(mock_back, mock_clear, mock_sleep):
    """_navigate_back_to_province returning False stops the loop after first office."""
    cfg = CheckerConfig(
        office_labels=("Office A", "Office B"),
        headless=True, stealth_enabled=False,
        nie="X1234567Y", full_name="Test User",
    )
    results_seq = _office_ok(no_citas=True)

    found, completed, office_results = _run_office_loop(
        ctx=_make_ctx(),
        config=cfg,
        start_office_idx=0,
        _run_step=_make_run_step(results_seq),
        logger=MagicMock(),
    )

    assert completed is False
    assert len(office_results) == 1
    assert office_results[0]["status"] == "no_citas"


@patch("tps_cita_check.runner.time.sleep")
@patch("tps_cita_check.runner._clear_tspd_cookies")
@patch("tps_cita_check.runner._navigate_back_to_province", return_value=True)
def test_single_office_no_cooldown(mock_back, mock_clear, mock_sleep):
    """Single office config completes normally without any cooldown sleep."""
    cfg = CheckerConfig(
        office_labels=("Office A",),
        headless=True, stealth_enabled=False,
        nie="X1234567Y", full_name="Test User",
    )
    results_seq = _office_ok(no_citas=True)

    found, completed, office_results = _run_office_loop(
        ctx=_make_ctx(),
        config=cfg,
        start_office_idx=0,
        _run_step=_make_run_step(results_seq),
        logger=MagicMock(),
    )

    assert completed is True
    mock_sleep.assert_not_called()
    mock_back.assert_not_called()


# ── run_check integration test via _run_office_loop mock (TEST-4) ─────────────


def test_run_check_multi_office_path(mocker):
    """run_check in normal (non-legacy) mode calls _run_office_loop and builds RunSummary."""
    fake_playwright = mocker.MagicMock()
    fake_context = mocker.MagicMock()
    fake_page = mocker.MagicMock()
    fake_context.pages = [fake_page]
    fake_playwright.chromium.launch_persistent_context.return_value = fake_context

    cm = mocker.MagicMock()
    cm.__enter__.return_value = fake_playwright
    cm.__exit__.return_value = False
    mocker.patch("tps_cita_check.runner.sync_playwright", return_value=cm)

    # Mock Phase 1 steps to return OK.
    class _OkStep(Step):
        def __init__(self, step_id, **_):
            self.step_id = step_id
            self.title = step_id

        def run(self, ctx):
            return _ok(self.step_id)

    mocker.patch("tps_cita_check.runner.Step0Load", lambda: _OkStep("step0"))
    mocker.patch("tps_cita_check.runner.Step1VerifyProvince", lambda: _OkStep("step1"))

    # Mock _run_office_loop to return a known result.
    expected_office_results = [
        {"label": "Office A", "status": "no_citas"},
        {"label": "Office B", "status": "no_citas"},
    ]
    mocker.patch(
        "tps_cita_check.runner._run_office_loop",
        return_value=(None, True, expected_office_results),
    )

    cfg = CheckerConfig(
        office_labels=("Office A", "Office B"),
        headless=True,
        stealth_enabled=False,
        run_retry_attempts=1,
        nie="X1234567Y",
        full_name="Test User",
    )
    from tps_cita_check.bot import _handle_help  # ensure bot module importable
    logger = mocker.MagicMock()
    logger.info = mocker.MagicMock()
    logger.error = mocker.MagicMock()
    logger.warning = mocker.MagicMock()
    logger.debug = mocker.MagicMock()

    summary = run_check(config=cfg, logger=logger)

    assert summary.ok is True
    assert summary.found_cita_office is None
    assert len(summary.office_results) == 2
    assert summary.office_results[0]["status"] == "no_citas"
