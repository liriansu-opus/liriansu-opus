"""Unit tests for scripts/sync-agent-rules.py."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "sync-agent-rules.py"
SPEC = importlib.util.spec_from_file_location("sync_agent_rules", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class SyncAgentRulesTests(unittest.TestCase):
    def test_combines_public_and_private(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            public = root / "repo" / "agents" / "GLOBAL.md"
            public.parent.mkdir(parents=True)
            public.write_text("# Public\n\n- Rule A\n", encoding="utf-8")

            private = root / "private.md"
            private.write_text("# Private\n\n- Rule B\n", encoding="utf-8")

            target = root / "out" / "AGENTS.md"
            changed = MOD.sync_targets(public, private, [target])
            self.assertEqual(changed, [target])

            content = target.read_text(encoding="utf-8")
            self.assertIn("# Public", content)
            self.assertIn("- Rule A", content)
            self.assertIn("# Private", content)
            self.assertIn("- Rule B", content)

            # Check mode should now pass with no drift.
            self.assertEqual(MOD.sync_targets(public, private, [target], check=True), [])

    def test_public_only_when_private_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            public = root / "repo" / "agents" / "GLOBAL.md"
            public.parent.mkdir(parents=True)
            public.write_text("# Public\n\n- Rule A\n", encoding="utf-8")

            missing_private = root / "missing.md"
            target = root / "GEMINI.md"
            MOD.sync_targets(public, missing_private, [target])

            content = target.read_text(encoding="utf-8")
            self.assertIn("- Rule A", content)
            self.assertNotIn("Private", content)

    def test_check_detects_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            public = root / "repo" / "agents" / "GLOBAL.md"
            public.parent.mkdir(parents=True)
            public.write_text("# Public\n\n- Rule A\n", encoding="utf-8")

            target = root / "AGENTS.md"
            target.write_text("stale content\n", encoding="utf-8")

            drifted = MOD.sync_targets(public, None, [target], check=True)
            self.assertEqual(drifted, [target])
            self.assertEqual(target.read_text(encoding="utf-8"), "stale content\n")

    def test_refuses_symlink_into_public_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            public = root / "repo" / "agents" / "GLOBAL.md"
            public.parent.mkdir(parents=True)
            public.write_text("# Public\n", encoding="utf-8")

            target = root / "AGENTS.md"
            target.symlink_to(public)

            with self.assertRaises(RuntimeError):
                MOD.sync_targets(public, None, [target])


if __name__ == "__main__":
    unittest.main()
