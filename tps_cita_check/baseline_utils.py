from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image


@dataclass(frozen=True)
class BaselineComparison:
    ok: bool
    baseline_path: Path
    actual_path: Path
    reason: str


def compare_images_by_size(baseline: Path, actual: Path) -> BaselineComparison:
    """
    Lightweight baseline check (no pixel-diff dependency):
    - validates both images exist and have the same dimensions.
    This catches major layout breakages cheaply. Can be upgraded later.
    """
    if not baseline.exists():
        return BaselineComparison(False, baseline, actual, "baseline_missing")
    if not actual.exists():
        return BaselineComparison(False, baseline, actual, "actual_missing")

    b = Image.open(baseline)
    a = Image.open(actual)
    if b.size != a.size:
        return BaselineComparison(False, baseline, actual, f"size_mismatch baseline={b.size} actual={a.size}")
    return BaselineComparison(True, baseline, actual, "size_match")

