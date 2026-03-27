# WAF Rate-Limiting & Scheduler Planning

## Observed WAF behavior

The appointment website (`icp.administracionelectronica.gob.es`) uses an application-layer firewall (WAF) that blocks automated or excessive access. Two distinct block types have been observed:

### Block type 1: "The requested URL was rejected"
- **Page content:** Plain HTML with "The requested URL was rejected. Please consult with your administrador." and a support ID.
- **Trigger:** Rate-limiting. Occurs when too many requests are made from the same IP in a short window.
- **Where it appears:** After any navigation (office selection, Aceptar click, form submission). The server responds with the block page instead of the expected content.
- **Recovery:** Requires waiting. The block lifts after a cooldown period (see timing below).

### Block type 2: FortiGate Intrusion Prevention
- **Page content:** FortiGate branded block page.
- **Trigger:** Aggressive automated patterns detected (rapid page loads, missing headers, bot signatures).
- **Where it appears:** Usually on initial page load (Step 0).
- **Recovery:** Same as above — wait and retry.

## Observed timing thresholds

| Scenario | Result |
|----------|--------|
| 1 full run (7 steps, ~25s) | Always succeeds if no prior runs |
| 2 runs back-to-back (<1 min apart) | Usually succeeds |
| 3+ runs within 5 minutes | WAF starts blocking at Step 2 or Step 4 |
| After 8–10 runs in 10 minutes | Persistent blocking for 10–20+ minutes |
| 5-minute cooldown after heavy use | Still blocked |
| 15–30 minute cooldown | Typically recovered |

### Key observations

1. **Navigation is the trigger, not page loads.** Steps 0–1 (load + verify) almost never get blocked. Steps 2 and 4 (which trigger server-side navigation via `select_option` or button click) are the primary WAF targets.

2. **The WAF tracks the IP, not the session.** Creating a new browser context (fresh cookies, new session) does not bypass the block. Only waiting or changing IP works.

3. **Blocks are "sticky."** Once the WAF starts blocking, the cooldown window appears to extend with each additional blocked request. Retrying during a block makes it worse.

4. **The block is not immediate.** Sometimes Step 2 (office select) succeeds but Step 4 (Aceptar click) gets blocked moments later. The WAF may apply a request-count threshold per time window rather than per individual request.

5. **Step 3 (trámite select) never triggers WAF** because it only changes a `<select>` value without triggering navigation/server request.

## Recommendations for scheduler design

### Safe polling interval
- **Minimum interval: 5 minutes** between full runs for sustained polling.
- **Conservative interval: 10 minutes** to avoid any risk of triggering the WAF.
- **After a WAF block: back off to 15–30 minutes** before the next attempt.

### Exponential backoff strategy
```
Base interval:     5 minutes (single check)
After 1 WAF block: 15 minutes
After 2 WAF blocks: 30 minutes
After 3 WAF blocks: 60 minutes (with alert to user)
After success:      reset to 5 minutes
```

### Architecture recommendations

1. **Single-attempt runs.** Do NOT retry within a run when WAF-blocked. Kill the browser session immediately and wait for the next scheduled slot. Retrying just extends the ban.

2. **Jitter.** Add random jitter (±30–60s) to the polling interval to avoid a perfectly periodic pattern that WAFs can fingerprint.

3. **Session reuse.** Consider keeping the browser alive between checks and only refreshing the page, rather than launching a new browser each time. Fewer TCP connections = less WAF attention.

4. **Request minimization.** If the checker only needs to verify appointment availability (not fill the form), stop at Step 4 or Step 5. Fewer navigation events per run = lower WAF risk.

5. **Notification, not automation.** The scheduler should notify the user when an appointment slot is detected, rather than attempting to complete the booking. This keeps the request count minimal and avoids WAF blocks during the critical booking window.

6. **IP rotation (optional).** If more aggressive polling is needed (<5 min), consider routing through a rotating proxy. This is not recommended as a first approach.

### Metrics to track in scheduler

| Metric | Purpose |
|--------|---------|
| `waf_blocks_count` | Track how often WAF blocks occur |
| `waf_block_step` | Which step gets blocked (Step 2 vs 4 vs 6) |
| `last_successful_run` | Time since last clean run |
| `consecutive_blocks` | Drives exponential backoff |
| `run_duration_s` | Detect slowdowns that precede blocks |

### macOS launchd scheduling

For a 5-minute interval with the checker:
```xml
<key>StartInterval</key>
<integer>300</integer>
```

The checker itself should handle backoff logic (not launchd), since launchd cannot dynamically adjust intervals. The scheduler wrapper should:
1. Check a state file for `consecutive_blocks`
2. If above threshold, skip this invocation and log why
3. Run the checker
4. Update the state file with result

## F5 TSPD bot detection — deep dive

The site uses **F5 BIG-IP TSPD** (Traffic Security Policy for Devices) for bot detection. Key findings:

### Detection mechanism
1. An obfuscated inline JS script runs on every page load (`<apm_do_not_touch>` wrapper)
2. External TSPD script (`/TSPD/...?type=17`) performs browser fingerprinting
3. `TS*` cookies are set based on the fingerprint (7 cookies observed: `TSPD_101`, `TSPD_101_DID`, `TS01629f81`, `TSf1e2d148029`, `TSf1e2d148077`, `TSb5dce861027`, `TS00000000076`)
4. Dynatrace RUM (`ruxitagentjs_...`) provides additional monitoring

### What triggers blocking on `/acValidarEntrada`
The personal data submission endpoint has **enhanced F5 protection** that other endpoints don't have. Testing confirmed:

| Scenario | Result |
|----------|--------|
| Playwright Chromium → Steps 0–5 navigation | PASS |
| Playwright Chromium → Step 6 form POST | BLOCKED |
| Real Chrome via CDP → Steps 0–5 navigation | PASS |
| Real Chrome via CDP → Step 6 form POST | BLOCKED |
| Real Chrome via CDP → Playwright `btn.click()` on manually-submitted page | BLOCKED |
| Real Chrome → Manual form fill + manual click | **PASS** |

**Root cause**: F5 TSPD detects **CDP-dispatched input events** (mouse clicks, keystrokes sent via Chrome DevTools Protocol). Even when using real Chrome with valid cookies and fingerprint, Playwright's `btn.click()` is detectable. The TSPD system validates input event authenticity at a level below the DOM — CDP Input.dispatchMouseEvent is distinguishable from real OS-level input.

### Solution: Chrome extension + script injection
Step 6 uses a bundled Manifest V3 Chrome extension (`tps_cita_check/chrome_extension/`). The content script listens for `postMessage` events and injects form-filling logic into the page's **main world** via `<script>` tag injection. This approach:

- Runs as trusted page JavaScript, indistinguishable from user-initiated code
- Bypasses CDP-based detection entirely — no `Input.dispatchMouseEvent` or `Page.evaluate` is used for the form submission
- Works with Playwright's `launch_persistent_context()` (extensions require a non-headless context on macOS)

## Multi-office TSPD cumulative session depth

When checking multiple offices in a single browser session, the TSPD `TS*` cookies accumulate session depth. After ~7–8 offices (approximately 48+ server-side navigation events), the WAF begins blocking at Step 2 of the next office.

**Root cause**: The TSPD cookies (`TSPD_101`, `TSPD_101_DID`, `TS01629f81`, etc.) encode a per-session request counter. This counter resets only when the cookies are cleared. Restarting the browser without clearing cookies does **not** reset the counter because the persistent Chrome profile preserves them across launches.

**Solution implemented**: Between each office, the runner:
1. Calls `_clear_tspd_cookies()` — filters `context.cookies()` for names starting with `TS` (case-insensitive), clears all cookies, re-adds non-TS cookies
2. Waits `random.uniform(30, 60)` seconds
3. Reloads `start_url` (fresh TSPD handshake with clean counter)
4. Runs Step1VerifyProvince before proceeding to Step2

This allows 9-office runs to complete successfully even when a WAF block occurs mid-run, because the retry starts from the failed office with freshly cleared TSPD state.

## Current implementation status

- Runner-level WAF retry: implemented (3 attempts, escalating backoff), retries **from failed office** (not from office 1)
- Per-step WAF detection: implemented (immediate bail-out, no wasted retries)
- Stealth evasion: minimal (webdriver hiding only; aggressive patches hurt F5 TSPD)
- Inter-step delays: implemented (1.5–3.5s random delays)
- Inter-office TSPD clearing: implemented (`_clear_tspd_cookies()` + 30–60s cooldown + reload)
- Chrome extension form filling: implemented (Steps 6–7, bypasses CDP input detection)
- Scheduler: implemented (launchd + `scheduler/run.sh`, variable intervals by time-of-day)
- Telegram bot: implemented (`/status`, `/runs`, `/start`, `/stop`, `/help`)
