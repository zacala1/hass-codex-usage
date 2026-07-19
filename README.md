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

## 한국어 안내

설정 화면, 재인증 안내, 오류 메시지와 센서 이름은 한국어를 지원합니다.
설치 후 예전 번역이 계속 보이면 Home Assistant를 재시작하세요. 사용자가 직접
변경한 엔티티 이름은 새 번역으로 자동 변경되지 않을 수 있습니다.

HACS에서 업데이트할 때는 저장소 메뉴의 **Update information**으로 새 버전
정보를 불러온 뒤 **Download/Redownload**를 선택하고 Home Assistant를
재시작하세요. 메타데이터 새로고침만으로는 통합 구성요소가 업데이트되지
않습니다.

잔여 사용량 센서는 남은 비율을 표시합니다. Codex 서버가 7일 제한만 반환하면
주간 센서는 값을 표시하지만 5시간 세션 센서는 `Unknown`으로 표시될 수
있습니다. 추가 사용 한도나 코드 리뷰 제한도 계정 응답에 해당 항목이 없으면
`Unknown`이 정상이며, 임의의 값으로 채우지 않습니다.

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
`hass_codex_usage.zip` asset. When a new version is available, open the
repository menu and select **Update information**, choose
**Download/Redownload**, then restart Home Assistant. You can also install an
available update from **Settings > Updates**.

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
The integration provides English and Korean UI translations. Home Assistant may
preserve entity names that the user customized manually.

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
- `sensor.codex_rate_limit_reset_credits_available`

Percentage sensors report the amount remaining, matching the current Codex usage
display. Reset sensors report Home Assistant timestamp values. Sensor attributes
include the account email when available, integration version, last successful
update time, API endpoint, and relevant rate-limit window metadata when the
endpoint provides it.

The integration identifies an approximately five-hour session window and an
approximately seven-day weekly window by `limit_window_seconds`. It does not
assume that `primary_window` always means session or that `secondary_window`
always means weekly. If the endpoint returns only a seven-day window, the weekly
sensors use that window and the session sensors remain `Unknown` rather than
reporting the same limit twice. Known daily, monthly, and annual windows are not
relabelled as session or weekly limits; the corresponding fixed sensors remain
`Unknown`.

Extra usage sensors expose the current `credits.balance` separately from the
`spend_control.individual_limit` used amount, limit, remaining percentage, and
reset time. If an account or plan does not return the individual-limit object,
its fixed sensors remain in the entity registry but Home Assistant shows their
state as `Unknown`/unavailable. A zero `credits.balance` does not imply that an
individual extra-usage limit exists.

Code review sensors read the current `codex_auto_review` entry in
`additional_rate_limits`. If the endpoint does not return that entry, their
states are `Unknown`/unavailable. These unavailable states reflect missing
optional backend data rather than a failure of the other sensors.

The `sensor.codex_rate_limit_reset_credits_available` sensor reports the number
of available rate-limit reset credits from
`rate_limit_reset_credits.available_count`. When at least one credit is
available, the integration also reads the current reset-credit detail endpoint
and exposes its allowlisted credit details as sensor attributes. A detail
request failure does not make the main usage sensors unavailable. The session
and weekly sensor attributes also expose the current `rate_limit_reached_type`
value when the backend returns it.

## Notes

- Multiple ChatGPT accounts can be added as separate Home Assistant config
  entries when each login returns a stable OpenAI account identifier.
- Other model-specific `additional_rate_limits` entries are not exposed as
  dynamic sensors.

## Development

Run local validation:

```powershell
python scripts/validate.py
.venv/Scripts/python.exe scripts/validate.py
```

Validate and build the release ZIP:

```bash
python scripts/build_release.py --check
python scripts/build_release.py
```

Before publishing a release, run validation, push `main`, then create and push a
version tag named `v<manifest version>`. Do not reuse a version that was already
published. The tag must match both `manifest.json` and `const.py`. The release
workflow reruns local validation, tag validation, hassfest, and HACS validation
before it builds and attaches `hass_codex_usage.zip` to the GitHub release.

After publication, verify that GitHub marks the intended version as Latest, the
published ZIP contains only the reviewed root-level integration files, and its
SHA-256 digest matches a fresh local deterministic build.
