# hass-codex-usage

Home Assistant custom integration for exposing ChatGPT/Codex subscription usage
limits as sensor entities.

This project is in the initial implementation stage. It targets ChatGPT account
OAuth and the Codex usage endpoints used by the Codex client, not OpenAI API key
billing or token-cost reporting.

The current code provides:

- HACS/Home Assistant custom integration structure
- UI config flow with OAuth authorization-code entry
- PKCE state and verifier handling
- Refresh-token plumbing
- `DataUpdateCoordinator` polling
- Reauthentication flow
- Diagnostics with token redaction
- HACS and hassfest validation workflow

## Important status

This integration depends on private ChatGPT/Codex endpoints. The OAuth scope,
redirect behavior, and usage response schema still need to be verified against a
real ChatGPT account before a public release.

Do not rely on this in production yet.

## Installation

Until this is released, install it as a HACS custom repository:

1. Open HACS.
2. Add this repository URL as a custom repository.
3. Select category `Integration`.
4. Install `Codex Usage`.
5. Restart Home Assistant.

Manual installation is also possible by copying `custom_components/hass_codex_usage`
into the Home Assistant `custom_components` directory, then restarting Home
Assistant.

## Configuration

1. In Home Assistant, go to **Settings > Devices & services**.
2. Add the `Codex Usage` integration.
3. Open the displayed authorization URL in a browser.
4. Sign in with the ChatGPT account whose Codex limits should be monitored.
5. Paste either the returned authorization code or the full failed localhost
   redirect URL back into Home Assistant.

The default polling interval is 300 seconds. The options flow allows values from
60 to 3600 seconds.

## Planned sensors

- Codex session usage
- Codex session reset time
- Codex weekly usage
- Codex weekly reset time
- Codex plan
- Codex code review usage
- Codex code review reset time

## Limitations

- Only one account is expected for the first release.
- Model-specific `additional_rate_limits` are ignored for v0.1.
- OpenAI API-key usage, billing, and token cost are out of scope.
- Local Codex CLI files such as `auth.json` and JSONL history are not read.

## Development

Basic local checks:

```bash
python -m unittest discover -s tests
python -m compileall custom_components
```

GitHub Actions run hassfest and HACS validation.
