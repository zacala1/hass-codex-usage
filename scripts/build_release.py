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
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
ZIP_FILE_MODE = 0o100644
REQUIRED_FILES = (
    INTEGRATION_DIR / "__init__.py",
    INTEGRATION_DIR / "availability.py",
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
        output = build_archive(args.output, package_files)
    except ReleasePackageError as err:
        print(f"Release package build failed: {err}", file=sys.stderr)
        return 1

    print(f"Wrote {output.relative_to(ROOT)} ({len(package_files)} files).")
    return 0


def validate_package_files() -> list[Path]:
    """Return package files after validating release contents."""
    if not INTEGRATION_DIR.is_dir():
        raise ReleasePackageError(f"missing integration directory: {INTEGRATION_DIR}")
    if INTEGRATION_DIR.is_symlink():
        raise ReleasePackageError("refusing symlinked integration directory")

    for required_path in REQUIRED_FILES:
        try:
            required_path.relative_to(INTEGRATION_DIR)
        except ValueError as err:
            raise ReleasePackageError(
                f"required file is outside the integration directory: {required_path}"
            ) from err
        symlink = first_symlink_component(required_path)
        if symlink is not None:
            raise ReleasePackageError(
                "refusing symlinked path: "
                f"{symlink.relative_to(INTEGRATION_DIR).as_posix()}"
            )

    missing = [
        path.relative_to(ROOT).as_posix()
        for path in REQUIRED_FILES
        if not path.is_file()
    ]
    if missing:
        raise ReleasePackageError(f"missing required files: {', '.join(missing)}")

    expected_files = set(REQUIRED_FILES)
    package_files: list[Path] = []
    unexpected_files: list[str] = []
    for path in sorted(INTEGRATION_DIR.rglob("*")):
        relative = path.relative_to(INTEGRATION_DIR)
        if path.is_symlink():
            raise ReleasePackageError(f"refusing symlinked path: {relative.as_posix()}")
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue
        relative_text = relative.as_posix()
        if any(fnmatch(relative_text, pattern) for pattern in EXCLUDED_PATTERNS):
            raise ReleasePackageError(
                f"refusing sensitive or generated file: {relative_text}"
            )
        if path not in expected_files:
            unexpected_files.append(relative_text)
            continue
        package_files.append(path)

    if unexpected_files:
        raise ReleasePackageError(
            f"unexpected integration files: {', '.join(unexpected_files)}"
        )
    return package_files


def build_archive(path: Path, package_files: list[Path] | None = None) -> Path:
    """Build a HACS release archive rooted at the integration contents."""
    files = validate_package_files() if package_files is None else package_files
    output = resolve_output(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for package_file in sorted(
            files,
            key=lambda candidate: candidate.relative_to(INTEGRATION_DIR).as_posix(),
        ):
            archive_path = package_file.relative_to(INTEGRATION_DIR).as_posix()
            archive_info = zipfile.ZipInfo(archive_path, date_time=ZIP_TIMESTAMP)
            archive_info.compress_type = zipfile.ZIP_DEFLATED
            archive_info.create_system = 3
            archive_info.external_attr = ZIP_FILE_MODE << 16
            archive.writestr(archive_info, package_file.read_bytes())
    return output


def first_symlink_component(path: Path) -> Path | None:
    """Return the first symlink between the integration root and a file."""
    relative = path.relative_to(INTEGRATION_DIR)
    candidate = INTEGRATION_DIR
    for part in relative.parts:
        candidate /= part
        if candidate.is_symlink():
            return candidate
    return None


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
