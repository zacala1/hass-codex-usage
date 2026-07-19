"""Repository-specific checks used by the validation entrypoint."""

from __future__ import annotations

import importlib
import importlib.util
import re
import subprocess
import sys
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "hass_codex_usage"
INTEGRATION_DIR = ROOT / "custom_components" / DOMAIN
JSON_FILES = (
    ROOT / "hacs.json",
    INTEGRATION_DIR / "manifest.json",
    INTEGRATION_DIR / "strings.json",
    INTEGRATION_DIR / "translations" / "en.json",
    INTEGRATION_DIR / "translations" / "ko.json",
)
COMPILE_PATHS = (
    ROOT / "custom_components",
    ROOT / "scripts",
    ROOT / "tests",
)
REQUIRED_INTEGRATION_FILES = (
    "__init__.py",
    "auth_helpers.py",
    "availability.py",
    "config_flow.py",
    "const.py",
    "coordinator.py",
    "diagnostics.py",
    "manifest.json",
    "oauth.py",
    "sensor.py",
    "strings.json",
    "translations/en.json",
    "translations/ko.json",
    "usage.py",
    "brand/icon.png",
)
INTEGRATION_MODULES = (
    "custom_components.hass_codex_usage",
    "custom_components.hass_codex_usage.auth_helpers",
    "custom_components.hass_codex_usage.availability",
    "custom_components.hass_codex_usage.config_flow",
    "custom_components.hass_codex_usage.const",
    "custom_components.hass_codex_usage.coordinator",
    "custom_components.hass_codex_usage.diagnostics",
    "custom_components.hass_codex_usage.oauth",
    "custom_components.hass_codex_usage.sensor",
    "custom_components.hass_codex_usage.usage",
)
MANIFEST_REQUIRED_KEYS = {
    "codeowners",
    "config_flow",
    "documentation",
    "domain",
    "iot_class",
    "issue_tracker",
    "name",
    "requirements",
    "version",
}
HACS_ALLOWED_KEYS = {
    "content_in_root",
    "country",
    "filename",
    "hacs",
    "hide_default_branch",
    "homeassistant",
    "name",
    "persistent_directory",
    "render_readme",
    "zip_release",
}
SENSITIVE_TRACKED_PATTERNS = (
    ".codex/*",
    ".claude/*",
    "*.jsonl",
    "*.db",
    "*.db-*",
    "*.log",
    "*auth.json",
    "*token*.json",
    "*usage*.json",
    ".env",
    ".env.*",
    ".storage/*",
    "secrets.yaml",
)
VERSION_RE = re.compile(r'^VERSION = "([^"]+)"$')
HA_VERSION_RE = re.compile(r"^\d{4}\.\d{1,2}\.\d+(?:b\d+)?$")


def check_repository_metadata(json_data: dict[Path, dict[str, Any]]) -> list[str]:
    """Validate lightweight repository metadata invariants."""
    failures: list[str] = []

    integration_dirs = [
        path
        for path in (ROOT / "custom_components").iterdir()
        if path.is_dir() and not path.name.startswith("__")
    ]
    if [path.name for path in integration_dirs] != [DOMAIN]:
        failures.append("custom_components must contain only hass_codex_usage")

    manifest = json_data.get(INTEGRATION_DIR / "manifest.json", {})
    missing_manifest_keys = sorted(MANIFEST_REQUIRED_KEYS - manifest.keys())
    if missing_manifest_keys:
        failures.append(f"manifest missing keys: {', '.join(missing_manifest_keys)}")
    if manifest.get("domain") != DOMAIN:
        failures.append(f"manifest domain must be {DOMAIN}")
    if manifest.get("config_flow") is not True:
        failures.append("manifest config_flow must be true")
    if manifest.get("requirements") != []:
        failures.append("manifest requirements must remain empty")
    if not manifest.get("issue_tracker"):
        failures.append("manifest issue_tracker must be set")
    if manifest.get("version") != integration_version():
        failures.append("manifest version must match const.VERSION")
    for relative in REQUIRED_INTEGRATION_FILES:
        if not (INTEGRATION_DIR / relative).is_file():
            failures.append(f"missing integration file: {relative}")

    hacs = json_data.get(ROOT / "hacs.json", {})
    unknown_hacs_keys = sorted(set(hacs) - HACS_ALLOWED_KEYS)
    if unknown_hacs_keys:
        failures.append(f"hacs.json unsupported keys: {', '.join(unknown_hacs_keys)}")
    if not hacs.get("name"):
        failures.append("hacs.json name must be set")
    if hacs.get("render_readme") is not True:
        failures.append("hacs.json render_readme must be true unless info.md is added")
    if not isinstance(hacs.get("homeassistant"), str) or not HA_VERSION_RE.match(
        hacs["homeassistant"]
    ):
        failures.append("hacs.json homeassistant must be a Home Assistant version string")

    if not (INTEGRATION_DIR / "brand" / "icon.png").is_file():
        failures.append("HACS brand icon is missing")

    tracked_files = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    if tracked_files.returncode:
        failures.append("git ls-files failed")
    else:
        for tracked in tracked_files.stdout.splitlines():
            normalized = tracked.replace("\\", "/")
            if any(
                fnmatch(normalized if "/" in pattern else Path(normalized).name, pattern)
                for pattern in SENSITIVE_TRACKED_PATTERNS
            ):
                failures.append(f"sensitive file is tracked: {tracked}")

    return failures


def integration_version() -> str | None:
    """Return the integration version without importing Home Assistant."""
    try:
        lines = (INTEGRATION_DIR / "const.py").read_text(encoding="utf-8").splitlines()
    except OSError:
        return None

    for line in lines:
        match = VERSION_RE.match(line)
        if match:
            return match.group(1)
    return None


def check_homeassistant_imports() -> list[str]:
    """Import integration modules when Home Assistant is installed locally."""
    if importlib.util.find_spec("homeassistant") is None:
        print("  SKIP homeassistant is not installed")
        return []

    failures: list[str] = []
    original_path = sys.path.copy()
    sys.path.insert(0, str(ROOT))
    try:
        for module_name in INTEGRATION_MODULES:
            try:
                importlib.import_module(module_name)
            except ImportError as err:
                failures.append(f"import failed: {module_name}: {err}")
            else:
                print(f"  OK {module_name}")
    finally:
        sys.path[:] = original_path

    return failures


def check_workflows() -> list[str]:
    """Validate deployment workflow guardrails."""
    release_workflow = ROOT / ".github" / "workflows" / "release.yml"
    try:
        release_text = release_workflow.read_text(encoding="utf-8")
    except OSError as err:
        return [f"release workflow missing or unreadable: {err}"]

    failures: list[str] = []
    if "tags:" not in release_text or '"v*"' not in release_text:
        failures.append("release workflow must run for v* tags")
    if "python scripts/validate.py" not in release_text:
        failures.append("release workflow must run local validation before packaging")
    if "python scripts/build_release.py" not in release_text:
        failures.append("release workflow must build the release package")
    if "softprops/action-gh-release" not in release_text:
        failures.append("release workflow must create a GitHub release")
    return failures
