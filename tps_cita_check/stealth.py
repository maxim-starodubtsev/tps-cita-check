from __future__ import annotations

_STEALTH_JS = """
// Hide webdriver flag — the only patch that matters.
// Chromium's --disable-blink-features=AutomationControlled already hides
// most automation signals, but navigator.webdriver can still leak.
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// DO NOT patch navigator.plugins, navigator.languages, chrome.runtime,
// or permissions.query.  The site uses F5 BIG-IP TSPD bot detection which
// fingerprints the browser environment.  Returning fake Plugin objects or
// stubbing chrome.runtime creates detectable artifacts that cause the F5
// system to generate an invalid token, leading to WAF rejection on form POST.
"""


def apply_stealth_sync(context) -> None:
    """Inject stealth evasion scripts into a Playwright BrowserContext."""
    context.add_init_script(_STEALTH_JS)
