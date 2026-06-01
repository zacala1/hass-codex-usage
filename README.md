# hass-codex-usage

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

## Installation

Install as a HACS custom repository:

1. Open HACS.
2. Add this repository URL as a custom repository.
3. Select category `Integration`.
4. Install `Codex Usage`.
5. Restart Home Assistant.

Manual installation is also possible by copying
`custom_components/hass_codex_usage` into the Home Assistant
`custom_components` directory, then restarting Home Assistant.

## Configuration

1. In Home Assistant, go to **Settings > Devices & services**.
2. Add the `Codex Usage` integration.
3. Open the displayed authorization URL in a browser.
4. Sign in with the ChatGPT account whose Codex limits should be monitored.
5. Paste either the returned authorization code or the full localhost redirect
   URL back into Home Assistant.

The default polling interval is 300 seconds. The options flow accepts values from
60 to 3600 seconds.

## Sensors

- `sensor.codex_session_usage`
- `sensor.codex_session_reset_time`
- `sensor.codex_weekly_usage`
- `sensor.codex_weekly_reset_time`
- `sensor.codex_plan`
- `sensor.codex_code_review_usage`
- `sensor.codex_code_review_reset_time`

Usage sensors report percentages. Reset sensors report Home Assistant timestamp
values. Sensor attributes include the account email when available, integration
version, last successful update time, API endpoint, and relevant rate-limit
window metadata when the endpoint provides it.

## Notes

- Only one ChatGPT account is expected for the first release.
- Model-specific `additional_rate_limits` entries are not exposed as dynamic
  sensors.

## Development

Run local validation:

```bash
python scripts/validate.py
```

Build the release zip:

```bash
python scripts/build_release.py
```
