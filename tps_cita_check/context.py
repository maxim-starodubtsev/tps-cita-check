from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import CheckerConfig


def _office_slug(label: str) -> str:
    """Derive a short, filesystem-safe slug from an office label.

    Takes the text before the first comma (e.g. "CNP Torremolinos"),
    lowercases it, strips accents, replaces spaces with underscores, and
    removes any remaining characters that are not alphanumeric, hyphen or
    underscore.

    Examples:
        "CNP Torremolinos, Calle Skal, 12, Torremolinos" → "cnp_torremolinos"
        "CNP CREADE-MÁLAGA, Avenida ..."                 → "cnp_creade-malaga"
        "CNP MÁLAGA Provincial, ..."                     → "cnp_malaga_provincial"
    """
    short = label.split(",")[0].strip().lower()
    # Decompose accented chars (e.g. Á → A + combining accent) then drop accents.
    short = unicodedata.normalize("NFD", short)
    short = "".join(c for c in short if unicodedata.category(c) != "Mn")
    short = short.replace(" ", "_")
    short = re.sub(r"[^\w-]", "", short)
    return short


@dataclass
class RunContext:
    config: CheckerConfig
    logger: any

    browser: Optional[any] = None
    context: Optional[any] = None
    page: Optional[any] = None

    run_id: str = "run"
    # Current office index in the multi-office loop (0-based). Updated by runner.
    office_idx: int = 0

    def ensure_artifact_dirs(self) -> None:
        self.config.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.config.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.config.baselines_dir.mkdir(parents=True, exist_ok=True)

    @property
    def run_screenshots_dir(self) -> Path:
        base = self.config.screenshots_dir / self.run_id
        # When checking multiple offices, keep screenshots in per-office subdirectories.
        if len(self.config.office_labels) > 1:
            label = self.config.office_labels[self.office_idx]
            return base / f"office_{_office_slug(label)}"
        return base

