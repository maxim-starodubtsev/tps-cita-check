"""TEST-5: Unit tests for _navigate_back_to_province."""
from __future__ import annotations

from unittest.mock import MagicMock

from tps_cita_check.config import CheckerConfig
from tps_cita_check.runner import _navigate_back_to_province


def _make_page(salir_count=0, volver_count=0, sede_count=0):
    """Create a mock page with configurable locator counts."""
    page = MagicMock()

    def mock_locator(selector):
        loc = MagicMock()
        if selector == "input[value='Salir']":
            loc.count.return_value = salir_count
        elif selector == "button:has-text('Volver')" or selector == "input[value='Volver']":
            loc.count.return_value = volver_count
        elif selector == "select#sede":
            loc.count.return_value = sede_count
        else:
            loc.count.return_value = 0
        return loc

    page.locator.side_effect = mock_locator
    # expect_navigation is used as a context manager
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=None)
    cm.__exit__ = MagicMock(return_value=False)
    page.expect_navigation.return_value = cm
    return page


def _make_cfg():
    return CheckerConfig(headless=True, stealth_enabled=False)


def test_salir_button_clicks_and_returns_true():
    """Salir button visible + office select visible → click + return True, no reload."""
    page = _make_page(salir_count=1, sede_count=1)
    cfg = _make_cfg()
    logger = MagicMock()

    result = _navigate_back_to_province(page, cfg, logger)

    assert result is True
    # Since #sede was visible after clicking Salir, page.goto should NOT be called.
    page.goto.assert_not_called()


def test_salir_click_leads_to_reload_when_sede_not_visible():
    """Salir click succeeds but we land on province form (no #sede) → reload start_url."""
    page = _make_page(salir_count=1, sede_count=0)
    cfg = _make_cfg()
    logger = MagicMock()

    result = _navigate_back_to_province(page, cfg, logger)

    assert result is True
    page.goto.assert_called_once_with(
        cfg.start_url, wait_until="load", timeout=cfg.step_timeout_ms
    )


def test_volver_button_used_when_salir_absent():
    """No Salir button, but Volver button present → click Volver."""
    page = _make_page(salir_count=0, volver_count=1, sede_count=1)
    cfg = _make_cfg()
    logger = MagicMock()

    result = _navigate_back_to_province(page, cfg, logger)

    assert result is True


def test_no_buttons_reloads_start_url():
    """No Salir/Volver buttons visible → navigate directly to start_url."""
    page = _make_page(salir_count=0, volver_count=0, sede_count=0)
    cfg = _make_cfg()
    logger = MagicMock()

    result = _navigate_back_to_province(page, cfg, logger)

    assert result is True
    page.goto.assert_called_once_with(
        cfg.start_url, wait_until="load", timeout=cfg.step_timeout_ms
    )


def test_exception_during_navigation_returns_false():
    """Any exception during back navigation returns False (never raises)."""
    page = MagicMock()
    page.locator.side_effect = RuntimeError("browser crashed")
    cfg = _make_cfg()
    logger = MagicMock()

    result = _navigate_back_to_province(page, cfg, logger)

    assert result is False
    logger.error.assert_called_once()
