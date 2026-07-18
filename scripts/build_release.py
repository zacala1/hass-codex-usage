"""Build the release zip for the Codex Usage integration."""

from __future__ import annotations

import argparse
import sys
import zipfile
from fnmatch import fnmatch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "hass_codex_usage"
INTEGRATION_DIR = ROOT / "custom_components" / DOMAIN
DEFAULT_OUTPUT = ROOT / "dist" / f"{DOMAIN}.zip"
REQUIRED_FILES = (
    INTEGRATION_DIR / "__init__.py",
    INTEGRATION_DIR / "auth_helpers.py",
    INTEGRATION_DIR / "config_flow.py",
    INTEGRATION_DIR / "const.py",
    INTEGRATION_DIR / "coordinator.py",
    INTEGRATION_DIR / "diagnostics.py",
    INTEGRATION_DIR / "manifest.json",
    INTEGRATION_DIR / "oauth.py",
    INTEGRATION_DIR / "sensor.py",
    INTEGRATION_DIR / "strings.json",
    INTEGRATION_DIR / "translations" / "ko.json",
    INTEGRATION_DIR / "translations" / "en.json",
    INTEGRATION_DIR / "usage.py",
    INTEGRATION_DIR / "brand" / "icon.png",
)
EXCLUDED_DIRS = {"__pycache__"}
EXCLUDED_PATTERNS = (
    ".env",
    ".env.*",
    "*.pyc",
    "*.pyo",
    "*.jsonl",
    "*.db",
    "*.db-*",
    "*.log",
    "*auth.json",
    "*token*.json",
    "*usage*.json",
    ".storage/*",
    "secrets.yaml",
)


class ReleasePackageError(ValueError):
    """Raised when release package contents or output are invalid."""


def main() -> int:
    """Run the release builder."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path to the zip file to create.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate package contents without writing a zip file.",
    )
    args = parser.parse_args()

    try:
        package_files = validate_package_files()
    except ReleasePackageError as err:
        print(f"Release package validation failed: {err}", file=sys.stderr)
        return 1

    if args.check:
        print(f"Release package check passed ({len(package_files)} files).")
        return 0

    try:
        output = resolve_output(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in package_files:
                archive.write(path, path.relative_to(ROOT).as_posix())
    except ReleasePackageError as err:
        print(f"Release package build failed: {err}", file=sys.stderr)
        return 1

    print(f"Wrote {output.relative_to(ROOT)} ({len(package_files)} files).")
    return 0


def validate_package_files() -> list[Path]:
    """Return package files after validating release contents."""
    if not INTEGRATION_DIR.is_dir():
        raise ReleasePackageError(f"missing integration directory: {INTEGRATION_DIR}")

    missing = [path.relative_to(ROOT).as_posix() for path in REQUIRED_FILES if not path.is_file()]
    if missing:
        raise ReleasePackageError(f"missing required files: {', '.join(missing)}")

    package_files: list[Path] = []
    for path in sorted(INTEGRATION_DIR.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(INTEGRATION_DIR)
        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue
        relative_text = relative.as_posix()
        if any(fnmatch(relative_text, pattern) for pattern in EXCLUDED_PATTERNS):
            raise ReleasePackageError(
                f"refusing sensitive or generated file: {relative_text}"
            )
        package_files.append(path)

    if not package_files:
        raise ReleasePackageError("release package would be empty")
    return package_files


def resolve_output(path: Path) -> Path:
    """Resolve and validate the output zip path."""
    output = path if path.is_absolute() else ROOT / path
    output = output.resolve()
    if output.suffix.lower() != ".zip":
        raise ReleasePackageError("output path must end in .zip")
    if not output.is_relative_to(ROOT):
        raise ReleasePackageError(f"output must stay inside the repository: {output}")
    return output


if __name__ == "__main__":
    raise SystemExit(main())
