from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CheckerConfig:
    base_url: str = "https://icp.administracionelectronica.gob.es/icpco/citar"
    locale: str = "es"

    # Step 1: province verification (default Málaga).
    # The initial URL already preselects the province using `p=<code>`.
    province_code: str = "29"
    province_label: str = "Málaga"

    # Step 2: ordered list of offices to check.  The runner tries them in sequence;
    # if no appointment is found at one office it navigates back and tries the next.
    # The first entry is the primary office (default: Torremolinos).
    office_labels: tuple = ("CNP Torremolinos, Calle Skal, 12, Torremolinos",)

    # Step 3: trámite selection (default Conflicto Ucrania).
    tramite_contains: str = "TARJETA CONFLICTO UCRANIA"

    # Personal data (for later steps; kept configurable now).
    nie: str = ""
    full_name: str = ""
    email: str = ""
    phone: str = ""

    # Artifacts
    artifacts_dir: Path = Path("artifacts")
    screenshots_dirname: str = "screenshots"
    baselines_dirname: str = "baselines"

    # Screenshot sizing
    screenshot_width_px: int = 800
    screenshot_max_height_px: int = 1920
    screenshot_full_page: bool = True

    # Behavior
    headless: bool = False
    ignore_https_errors: bool = True
    step_timeout_ms: int = 30_000

    # Stealth / anti-detection
    user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
    stealth_enabled: bool = True

    # Chrome extension directory (auto-resolved to bundled chrome_extension/ if empty).
    extension_dir: str = ""

    # Persistent Chrome profile directory for launch_persistent_context.
    chrome_profile_dir: str = ""

    # Inter-step human-like delays
    step_delay_min_ms: int = 1_500
    step_delay_max_ms: int = 3_500

    # Per-step retry (for transient errors like timeouts)
    step_retry_attempts: int = 3
    step_retry_backoff_ms: int = 3_000

    # Runner-level retry (for WAF blocks — restarts the entire flow)
    run_retry_attempts: int = 3
    run_retry_base_backoff_s: float = 10.0

    # Telegram notifications
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    @property
    def resolved_extension_dir(self) -> Path:
        if self.extension_dir:
            return Path(self.extension_dir)
        return Path(__file__).parent / "chrome_extension"

    @property
    def resolved_chrome_profile_dir(self) -> Path:
        if self.chrome_profile_dir:
            return Path(self.chrome_profile_dir)
        return self.artifacts_dir / "chrome_profile"

    @property
    def office_label(self) -> str:
        """Convenience: first (primary) office label. Kept for backward compatibility."""
        return self.office_labels[0] if self.office_labels else ""

    @property
    def start_url(self) -> str:
        return f"{self.base_url}?p={self.province_code}&locale={self.locale}"

    @property
    def screenshots_dir(self) -> Path:
        return self.artifacts_dir / self.screenshots_dirname

    @property
    def baselines_dir(self) -> Path:
        return self.artifacts_dir / self.baselines_dirname

