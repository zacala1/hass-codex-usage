"""Run lightweight local validation checks."""

from __future__ import annotations

import compileall
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSON_FILES = (
    ROOT / "hacs.json",
    ROOT / "custom_components" / "hass_codex_usage" / "manifest.json",
    ROOT / "custom_components" / "hass_codex_usage" / "strings.json",
    ROOT / "custom_components" / "hass_codex_usage" / "translations" / "en.json",
    ROOT / "custom_components" / "hass_codex_usage" / "translations" / "ko.json",
)
COMPILE_PATHS = (
    ROOT / "custom_components",
    ROOT / "scripts",
    ROOT / "tests",
)


def main() -> int:
    """Run validation checks."""
    failures: list[str] = []

    print("Checking JSON files...")
    for path in JSON_FILES:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as err:  # noqa: BLE001
            failures.append(f"{path.relative_to(ROOT)}: {err}")
        else:
            print(f"  OK {path.relative_to(ROOT)}")

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


if __name__ == "__main__":
    raise SystemExit(main())
