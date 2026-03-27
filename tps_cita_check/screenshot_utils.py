from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from PIL import Image


@dataclass(frozen=True)
class ScreenshotResult:
    path: Path
    width: int
    height: int
    resized: bool


def _resize_image_in_place(
    path: Path,
    target_width: int,
    max_height: int,
) -> ScreenshotResult:
    img = Image.open(path)
    original_w, original_h = img.size

    resized = False
    new_w = original_w
    new_h = original_h

    if original_w > target_width:
        scale = target_width / float(original_w)
        new_w = target_width
        new_h = int(original_h * scale)
        resized = True

    if new_h > max_height:
        # If extremely tall, cap height and adjust width proportionally.
        scale = max_height / float(new_h)
        new_h = max_height
        new_w = int(new_w * scale)
        resized = True

    if resized:
        img = img.resize((new_w, new_h), Image.LANCZOS)
        img.save(path, optimize=True)

    return ScreenshotResult(path=path, width=new_w, height=new_h, resized=resized)


def save_debug_screenshot(
    *,
    page,
    out_dir: Path,
    filename: str,
    full_page: bool,
    width_px: int,
    max_height_px: int,
) -> ScreenshotResult:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / filename

    # PNG is best for legibility; keep it simple.
    page.screenshot(path=str(path), full_page=full_page)

    # Resize to speed up storage + diffs and keep baseline manageable.
    return _resize_image_in_place(path, target_width=width_px, max_height=max_height_px)


def baseline_path_for(*, baselines_dir: Path, step_id: str, name: str) -> Path:
    baselines_dir.mkdir(parents=True, exist_ok=True)
    safe = name.replace("/", "_")
    return baselines_dir / f"{step_id}_{safe}.png"

