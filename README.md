# hass-codex-usage

Home Assistant custom integration for exposing ChatGPT/Codex subscription usage
limits as sensor entities.

This project is in the initial implementation stage. The current code provides
the HACS/Home Assistant integration skeleton, OAuth code-entry flow, token
refresh plumbing, polling coordinator, and the planned v0.1 sensor set.

## Planned sensors

- Codex session usage
- Codex session reset time
- Codex weekly usage
- Codex weekly reset time
- Codex plan
- Codex code review usage
- Codex code review reset time

## Status

The OpenAI OAuth scope, redirect behavior, and usage response schema still need
to be verified against a real ChatGPT account before a public release.
