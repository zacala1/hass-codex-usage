# hass-codex-usage

[![Latest release](https://img.shields.io/github/v/release/zacala1/hass-codex-usage)](https://github.com/zacala1/hass-codex-usage/releases/latest)
[![Validate](https://github.com/zacala1/hass-codex-usage/actions/workflows/validate.yml/badge.svg)](https://github.com/zacala1/hass-codex-usage/actions/workflows/validate.yml)

Home Assistant custom integration for showing ChatGPT Codex subscription usage
limits as sensor entities.

The integration signs in with a ChatGPT account through the Codex OAuth flow and
polls the ChatGPT Codex usage endpoint directly from Home Assistant. It does not
read local Codex CLI files, JSONL history, OpenAI API keys, billing data, or token
cost data.

This integration uses private ChatGPT/Codex endpoints. OAuth with PKCE, the
localhost redirect, and `chatgpt.com/backend-api/wham/usage` have been verified
against one real ChatGPT account, but the endpoint is not a public API and may
change without notice.

Requires Home Assistant 2025.12.0 or newer.

## Installation

[![Open your Home Assistant instance and add this repository to HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=zacala1&repository=hass-codex-usage&category=integration)

Install with the button above, or add the repository manually:

1. Open HACS.
2. Open the three-dot menu and select **Custom repositories**.
3. Add `https://github.com/zacala1/hass-codex-usage`.
4. Select category **Integration**.
5. Select **Codex Usage**, then select **Download**.
6. Restart Home Assistant.

Manual installation is also possible:

1. Download `hass_codex_usage.zip` from the
   [latest release](https://github.com/zacala1/hass-codex-usage/releases/latest).
2. Create `/config/custom_components/hass_codex_usage` in your Home Assistant
   configuration, then extract the ZIP contents directly into that directory.
3. Restart Home Assistant.

## Updating

HACS tracks published GitHub releases and installs the packaged
`hass_codex_usage.zip` asset. When a new version is available, install it from
**Settings > Updates**, or open HACS and select **Redownload** for Codex Usage.
Restart Home Assistant after the download.

If HACS does not show a newly published version yet, open the repository's
three-dot menu and select **Update information**, then check for the update
again. Updating repository information only refreshes HACS metadata; it does not
install the integration update.

## Configuration

1. In Home Assistant, go to **Settings > Devices & services**.
2. Add the `Codex Usage` integration.
3. Open the authorization link shown by Home Assistant.
4. Sign in with the ChatGPT account whose Codex limits should be monitored.
5. Paste the returned authorization code or full localhost redirect URL.

The browser may show a `localhost refused to connect` page after authorization.
That is expected because the integration uses the Codex localhost redirect URI
only to receive a code in the address bar. Copy the full URL from the browser
address bar and paste it into the same Home Assistant setup dialog.

The default polling interval is 300 seconds. The options flow accepts values from
60 to 3600 seconds.

## Authentication Notes

The setup flow intentionally follows the same pattern as similar Home Assistant
usage integrations: one authorization link and one paste field. It does not ask
for a name during setup; the config entry title is derived from the ChatGPT
account email or account identifier when OpenAI returns one.

Authorization codes are one-time use. If the setup dialog is closed, an error is
shown, or the redirect URL was copied from an older attempt, start the integration
setup again and use the new authorization link.

If Home Assistant shows a translation placeholder error after updating the
integration, restart Home Assistant so it reloads the integration translations.

## Sensors

- `sensor.codex_session_usage_remaining`
- `sensor.codex_session_reset_time`
- `sensor.codex_weekly_usage_remaining`
- `sensor.codex_weekly_reset_time`
- `sensor.codex_plan`
- `sensor.codex_code_review_usage_remaining`
- `sensor.codex_code_review_reset_time`
- `sensor.codex_extra_usage_remaining`
- `sensor.codex_extra_usage_reset_time`
- `sensor.codex_extra_usage_balance`
- `sensor.codex_extra_usage_used`
- `sensor.codex_extra_usage_limit`

Percentage sensors report the amount remaining, matching the current Codex usage
display. Reset sensors report Home Assistant timestamp values. Sensor attributes
include the account email when available, integration version, last successful
update time, API endpoint, and relevant rate-limit window metadata when the
endpoint provides it.

Extra usage sensors expose the current `credits.balance` separately from the
`spend_control.individual_limit` used amount, limit, remaining percentage, and
reset time. If an account or plan does not return one of these fields, its fixed
sensor remains available in the entity registry but its state is unavailable.

Code review sensors read the current `codex_auto_review` entry in
`additional_rate_limits`. If the endpoint does not return that entry, their
states are unavailable.

## Notes

- Multiple ChatGPT accounts can be added as separate Home Assistant config
  entries when each login returns a stable OpenAI account identifier.
- Other model-specific `additional_rate_limits` entries are not exposed as
  dynamic sensors.

## Development

Run local validation:

```bash
python scripts/validate.py
```

Build the release zip:

```bash
python scripts/build_release.py
```

Before publishing a release, run validation, push `main`, then create and push a
version tag such as `v0.3.0`. The tag must match the integration version. The
release workflow reruns local validation, hassfest, and HACS validation before it
builds and attaches `hass_codex_usage.zip` to the GitHub release.
