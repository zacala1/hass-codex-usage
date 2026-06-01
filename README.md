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

HACS requires a public GitHub repository for normal custom-repository installs.
While this repository is private, use manual installation or copy the integration
directory directly into the target Home Assistant config directory.

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

- `sensor.codex_session_usage`
- `sensor.codex_session_reset_time`
- `sensor.codex_weekly_usage`
- `sensor.codex_weekly_reset_time`
- `sensor.codex_plan`
- `sensor.codex_code_review_usage`
- `sensor.codex_code_review_reset_time`
- `sensor.codex_extra_usage_enabled`
- `sensor.codex_extra_usage`
- `sensor.codex_extra_usage_credits`
- `sensor.codex_extra_usage_limit`
- `sensor.codex_spark_usage`
- `sensor.codex_spark_reset_time`
- `sensor.codex_spark_weekly_usage`
- `sensor.codex_spark_weekly_reset_time`

Usage sensors report percentages. Reset sensors report Home Assistant timestamp
values. Sensor attributes include the account email when available, integration
version, last successful update time, API endpoint, and relevant rate-limit
window metadata when the endpoint provides it.

Extra usage sensors expose Codex flexible credits when the ChatGPT usage endpoint
returns credit or spend-control fields. Current Codex responses usually expose a
remaining credit balance through `credits.balance`; usage percent and limit values
are only available when the endpoint also returns explicit spend or limit fields.
If the account or plan does not expose those fields, the affected optional
sensors are not created. Disabled extra usage is reported as `0` usage, `0`
credits limit, and `false` enabled.

Codex Spark sensors expose the model-specific `additional_rate_limits` entry
when the endpoint returns a Spark limit. Code review sensors require a code-review
rate-limit entry from the usage endpoint; OpenAI may instead expose code-review
percentages only on the web dashboard, in which case those sensors are not
created.

## Notes

- Multiple ChatGPT accounts can be added as separate Home Assistant config
  entries when each login returns a stable OpenAI account identifier.
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

Before publishing a release, run validation, push `main`, then create and push a
version tag such as `v0.2.0`. The release workflow reruns validation before it
builds and attaches `hass_codex_usage.zip` to the GitHub release.
