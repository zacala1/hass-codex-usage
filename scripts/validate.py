"""Run lightweight local validation checks."""

from __future__ import annotations

import compileall
import json
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from validation_checks import (  # noqa: E402
    COMPILE_PATHS,
    JSON_FILES,
    ROOT,
    check_homeassistant_imports,
    check_repository_metadata,
    check_workflows,
    integration_version as integration_version,
)


def main() -> int:
    """Run validation checks."""
    failures: list[str] = []
    json_data: dict[Path, dict[str, Any]] = {}

    print("Checking JSON files...")
    for path in JSON_FILES:
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as err:
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

    print("Checking release package contents...")
    package_check = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_release.py"), "--check"],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    if package_check.stdout:
        print(package_check.stdout, end="")
    if package_check.stderr:
        print(package_check.stderr, end="", file=sys.stderr)
    if package_check.returncode:
        failures.append("release package check failed")

    print("Checking optional Home Assistant imports...")
    failures.extend(check_homeassistant_imports())

    print("Checking GitHub workflows...")
    failures.extend(check_workflows())

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
