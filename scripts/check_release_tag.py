# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Check that a release tag matches the integration manifest version."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "custom_components" / "hass_codex_usage" / "manifest.json"


class ReleaseTagError(ValueError):
    """Raised when release tag validation cannot succeed."""


def manifest_version() -> str:
    """Return the integration version declared in the manifest."""
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        raise ReleaseTagError(f"cannot read integration manifest: {err}") from err

    version = manifest.get("version") if isinstance(manifest, dict) else None
    if not isinstance(version, str) or not version:
        raise ReleaseTagError("integration manifest has no valid version")
    return version


def validate_release_tag(tag: str) -> None:
    """Raise when the release tag differs from the manifest version."""
    expected = f"v{manifest_version()}"
    if tag != expected:
        raise ReleaseTagError(
            f"release tag {tag!r} does not match manifest version {expected!r}"
        )


def main(argv: Sequence[str] | None = None) -> int:
    """Validate a release tag given on the command line."""
    parser = argparse.ArgumentParser()
    parser.add_argument("tag", help="Release tag to check, for example v0.3.3.")
    args = parser.parse_args(argv)

    try:
        validate_release_tag(args.tag)
    except ReleaseTagError as err:
        print(f"Release tag validation failed: {err}", file=sys.stderr)
        return 1

    print(f"Release tag {args.tag} matches the integration manifest.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
