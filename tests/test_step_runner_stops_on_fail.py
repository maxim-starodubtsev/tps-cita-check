from __future__ import annotations

from dataclasses import dataclass

from tps_cita_check.step_framework import Step, StepResult, StepStatus
from tps_cita_check.runner import run_check
from tps_cita_check.config import CheckerConfig


class _Logger:
    def __init__(self):
        self.lines = []

    def info(self, msg: str):
        self.lines.append(("info", msg))

    def error(self, msg: str):
        self.lines.append(("error", msg))

    def warning(self, msg: str):
        self.lines.append(("warning", msg))

    def debug(self, msg: str):
        self.lines.append(("debug", msg))


class _OkStep(Step):
    def __init__(self, step_id: str):
        self.step_id = step_id
        self.title = step_id

    def run(self, ctx):
        return StepResult(step_id=self.step_id, status=StepStatus.OK, message="ok")


class _FailStep(Step):
    def __init__(self, step_id: str):
        self.step_id = step_id
        self.title = step_id

    def run(self, ctx):
        return StepResult(
            step_id=self.step_id,
            status=StepStatus.FAIL,
            message="fail",
            error_type="RuntimeError",
            error_details="boom",
        )


def test_runner_stops_after_first_failure(mocker):
    # Avoid launching real browsers in unit tests.
    fake_playwright = mocker.MagicMock()
    fake_context = mocker.MagicMock()
    fake_page = mocker.MagicMock()
    fake_context.pages = [fake_page]
    fake_playwright.chromium.launch_persistent_context.return_value = fake_context

    cm = mocker.MagicMock()
    cm.__enter__.return_value = fake_playwright
    cm.__exit__.return_value = False

    mocker.patch("tps_cita_check.runner.sync_playwright", return_value=cm)

    logger = _Logger()
    cfg = CheckerConfig(headless=True, stealth_enabled=False)
    steps = [_OkStep("s0"), _FailStep("s1"), _OkStep("s2")]
    summary = run_check(config=cfg, logger=logger, steps=steps)

    assert summary.ok is False
    assert [r.step_id for r in summary.results] == ["s0", "s1"]
