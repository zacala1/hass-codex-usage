"""Run lightweight local validation checks."""

from __future__ import annotations

import compileall
import json
import subprocess
import sys
import unittest
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
    "*auth.json",
    "*token*.json",
    ".storage/*",
)


def main() -> int:
    """Run validation checks."""
    failures: list[str] = []
    json_data: dict[Path, dict[str, Any]] = {}

    print("Checking JSON files...")
    for path in JSON_FILES:
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
        except Exception as err:  # noqa: BLE001
            failures.append(f"{path.relative_to(ROOT)}: {err}")
        else:
            if isinstance(parsed, dict):
                json_data[path] = parsed
            print(f"  OK {path.relative_to(ROOT)}")

    print("Checking repository metadata...")
    failures.extend(check_repository_metadata(json_data))

    print("Running unit tests...")
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)
    if not result.wasSuccessful():
        failures.append("unit tests failed")

    print("Compiling Python files...")
    for path in COMPILE_PATHS:
        if not compileall.compile_dir(path, quiet=1):
            failures.append(f"compile failed: {path.relative_to(ROOT)}")

    print("Checking git diff whitespace...")
    diff_check = subprocess.run(
        ["git", "diff", "--check"],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    if diff_check.returncode:
        failures.append("git diff --check failed")
        if diff_check.stdout:
            print(diff_check.stdout, end="")
        if diff_check.stderr:
            print(diff_check.stderr, end="", file=sys.stderr)

    if failures:
        print("Validation failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("Validation passed.")
    return 0


def check_repository_metadata(json_data: dict[Path, dict[str, Any]]) -> list[str]:
    """Validate lightweight repository metadata invariants."""
    failures: list[str] = []

    custom_components_dir = ROOT / "custom_components"
    integration_dirs = [
        path
        for path in custom_components_dir.iterdir()
        if path.is_dir() and not path.name.startswith("__")
    ]
    if [path.name for path in integration_dirs] != [DOMAIN]:
        failures.append("custom_components must contain only hass_codex_usage")

    manifest_path = INTEGRATION_DIR / "manifest.json"
    manifest = json_data.get(manifest_path, {})
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

    hacs_path = ROOT / "hacs.json"
    hacs = json_data.get(hacs_path, {})
    unknown_hacs_keys = sorted(set(hacs) - HACS_ALLOWED_KEYS)
    if unknown_hacs_keys:
        failures.append(f"hacs.json unsupported keys: {', '.join(unknown_hacs_keys)}")
    if not hacs.get("name"):
        failures.append("hacs.json name must be set")
    if hacs.get("render_readme") is not True:
        failures.append("hacs.json render_readme must be true unless info.md is added")

    brand_icon = INTEGRATION_DIR / "brand" / "icon.png"
    if not brand_icon.is_file():
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
            if any(fnmatch(normalized, pattern) for pattern in SENSITIVE_TRACKED_PATTERNS):
                failures.append(f"sensitive file is tracked: {tracked}")

    return failures


if __name__ == "__main__":
    raise SystemExit(main())
