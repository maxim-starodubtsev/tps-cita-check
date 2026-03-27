from __future__ import annotations

from tps_cita_check.steps.common import is_url_rejected


class _FakeLocator:
    def __init__(self, count: int):
        self._count = count

    def count(self) -> int:
        return self._count


class _FakePage:
    def __init__(self, rejected: bool):
        self._rejected = rejected

    def locator(self, selector: str):
        if selector == "text=The requested URL was rejected":
            return _FakeLocator(1 if self._rejected else 0)
        return _FakeLocator(0)


def test_is_url_rejected_true() -> None:
    assert is_url_rejected(_FakePage(True)) is True


def test_is_url_rejected_false() -> None:
    assert is_url_rejected(_FakePage(False)) is False

