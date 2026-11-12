"""Tests for repository policies recorded in AGENTS.md."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
CHECKS_SPEC = importlib.util.spec_from_file_location(
    "hass_codex_usage_validation_checks",
    ROOT / "scripts" / "validation_checks.py",
)
validation_checks = importlib.util.module_from_spec(CHECKS_SPEC)
assert CHECKS_SPEC.loader is not None
CHECKS_SPEC.loader.exec_module(validation_checks)


class RepositoryPolicyTest(unittest.TestCase):
    """Keep the no-CI/CD decision enforced and documented."""

    def test_repository_has_no_ci_config(self) -> None:
        """Fail if CI/CD automation is reintroduced."""
        self.assertEqual(validation_checks.check_no_ci_config(), [])

    def test_ci_guard_flags_workflows_and_dependabot(self) -> None:
        """Detect workflow and dependency-bot files in a repository tree."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".github" / "workflows").mkdir(parents=True)
            (root / ".github" / "dependabot.yml").write_text("version: 2\n")

            with mock.patch.object(validation_checks, "ROOT", root):
                failures = validation_checks.check_no_ci_config()

        self.assertEqual(len(failures), 2)
        self.assertTrue(any(".github/workflows" in item for item in failures))
        self.assertTrue(any("dependabot.yml" in item for item in failures))

    def test_agent_policy_is_present_and_imported_by_claude(self) -> None:
        """Keep the agent policy that forbids re-adding CI/CD."""
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")

        self.assertIn("No CI/CD automation", agents)
        self.assertIn(".github/workflows", agents)
        self.assertIn("@AGENTS.md", claude)


if __name__ == "__main__":
    unittest.main()
