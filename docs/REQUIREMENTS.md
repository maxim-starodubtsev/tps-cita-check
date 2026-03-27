# Requirements (Step-based framework)

## Goal
Automate navigation on the Spanish appointment website to reach the next page **after selecting**:
- Province: **Málaga** (parameterized, default preselected via URL)
- Office: **Torremolinos** (parameterized)
- Trámite: **Conflicto Ucrania** (parameterized)
Then click **Aceptar**.

The implementation must be a multi-step runner (Step0..Step6) with strong diagnostics:
- If any step fails, logs must clearly identify **which step**, **what was expected**, **what was observed**, and likely failure type (site blocked, missing element, timeout, navigation issues, etc.).
- Each step must capture a debug screenshot.
- Screenshots must be resized to a stable size (target width ~800px; height capped ~1920px) to keep artifacts small and readable.

## Step 0: Load website by initial URL
**Input**:
- `base_url` (default `https://icp.administracionelectronica.gob.es/icpco/citar`)
- `province_code` (default `29`)
- `locale` (default `es`)

**Action**:
- Navigate to `base_url?p=<province_code>&locale=<locale>`
- Wait for network idle.

**Expected**:
- Page loads successfully.
- If a "requested URL was rejected" block page appears, fail with a clear error.

**Artifacts**:
- Screenshot: `step0_loaded.png` (or `step0_error.png` on failure)

## Step 1: Verify province is selected
**Input**:
- `province_label` (default `Málaga`)

**Action**:
- Ensure the province `<select>` exists.
- Verify the checked option label equals `province_label`.

**Expected**:
- Province is already selected as the initial URL should open the province-preselected flow.

**Artifacts**:
- Screenshot: `step1_province_verified.png` (or `step1_error.png`)

## Step 2: Select office (Torremolinos)
**Input**:
- `office_label` (default `CNP Torremolinos, Calle Skal, 12, Torremolinos`)

**Action**:
- Find the office `<select>` (first select on the page).
- Select the office by exact label (fallback by partial matching if label changes).
- Wait for navigation, because selecting office reloads the next page.

**Expected**:
- Office selection triggers navigation to the next page.
- If blocked by upstream protection, fail with clear error.

**Artifacts**:
- Screenshot: `step2_office_selected.png` (or `step2_error.png` / `step2_timeout.png`)

## Step 3: Select trámite (Conflicto Ucrania)
**Input**:
- `tramite_contains` (default contains `TARJETA CONFLICTO UCRANIA`)

**Action**:
- After office selection, wait for trámite selects to appear (the site injects them asynchronously).
- Search all non-office selects for an option containing `tramite_contains` (case-insensitive).
- Select that option.

**Expected**:
- The option matching "POLICÍA TARJETA CONFLICTO UCRANIA..." is selected.

**Artifacts**:
- Screenshot: `step3_tramite_selected.png` (or `step3_error.png` / `step3_timeout.png`)

## Step 4: Click Aceptar
**Action**:
- Validate no visible error dialog indicating missing selections (e.g. "Por favor, selecciona un trámite.").
- Click `Aceptar` and wait for navigation.

**Expected**:
- The user reaches the next page after the selection screen.

**Artifacts**:
- Screenshot: `step4_after_accept.png` (or `step4_error.png` / `step4_timeout.png`)

## Step 5: Click Entrar
**Action**:
- Click the `Entrar` button on the info/disclaimer page.
- Wait for navigation to the personal data form.

**Expected**:
- The page navigates to `/icpco/acEntrada` with the NIE/Name input form.

**Artifacts**:
- Screenshot: `step5_after_entrar.png` (or `step5_error.png` / `step5_timeout.png`)

## Step 6: Fill NIE + Name and submit
**Input**:
- `nie` (required — via `--nie` flag or `CITA_NIE` env var)
- `full_name` (required — via `--name` flag or `CITA_NAME` env var)

**Action**:
- Dismiss cookie banner ("Acepto") if present.
- Type NIE into the first text input (keystroke-by-keystroke with random delays).
- Type full name into the second text input (same typing approach).
- Click `Aceptar` to submit the personal data form.
- Wait for navigation.

**Expected**:
- The form is submitted and the page navigates to the next stage (appointment slot selection or "no appointments available" message).

**Artifacts**:
- Screenshot: `step6_after_personal_data.png` (or `step6_error.png` / `step6_timeout.png`)

## Testing requirements
- Step runner and all step implementations must be covered with automated tests.
- Tests should validate:
  - Step sequencing and stop-on-failure behavior.
  - Detection of URL rejection block page.
  - Selector scanning logic for trámite options.
  - Screenshot resizing logic (unit test on a generated image).

## Development note
Later enhancement: run periodically (e.g. every 5–10 minutes) via `launchd` or cron on macOS.
See [WAF_RATE_LIMITING.md](WAF_RATE_LIMITING.md) for observed rate-limiting behavior and scheduler design constraints.

