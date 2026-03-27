from __future__ import annotations

from pathlib import Path

from PIL import Image

from tps_cita_check.screenshot_utils import _resize_image_in_place


def test_resize_caps_width_and_height(tmp_path: Path) -> None:
    p = tmp_path / "x.png"
    Image.new("RGB", (2000, 6000), color=(255, 255, 255)).save(p)

    res = _resize_image_in_place(p, target_width=800, max_height=1920)

    img = Image.open(p)
    assert img.size[0] <= 800
    assert img.size[1] <= 1920
    assert res.resized is True

