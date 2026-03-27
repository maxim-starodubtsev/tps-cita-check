from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class StepStatus(str, Enum):
    OK = "ok"
    FAIL = "fail"
    SKIP = "skip"


@dataclass(frozen=True)
class StepResult:
    step_id: str
    status: StepStatus
    message: str
    screenshot: Optional[str] = None
    error_type: Optional[str] = None
    error_details: Optional[str] = None
    data: Optional[dict[str, Any]] = None


class Step:
    step_id: str
    title: str

    def run(self, ctx) -> StepResult:  # pragma: no cover
        raise NotImplementedError

