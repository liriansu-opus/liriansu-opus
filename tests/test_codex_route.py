import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "cmux/hooks/codex-route.py"
SPEC = importlib.util.spec_from_file_location("codex_route", SCRIPT)
ROUTE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ROUTE)


class CodexRouteTests(unittest.TestCase):
    def setUp(self):
        self.binding = {
            "session_id": "thread-1",
            "workspace_id": "11111111-1111-1111-1111-111111111111",
            "surface_id": "22222222-2222-2222-2222-222222222222",
            "pid": 42,
            "fingerprint": "Thu Oct 22 10:00:00 2026 /usr/local/bin/codex",
        }
        self.env = {"CMUX_WORKSPACE_ID": "stale", "UNCHANGED": "yes"}

    def route(self, payload=None, bindings=None, fingerprint=None):
        return ROUTE.route_environment(
            payload or {"session_id": "thread-1"},
            bindings if bindings is not None else [self.binding],
            self.env,
            fingerprint or (lambda pid: self.binding["fingerprint"]),
        )

    def test_verified_session_restores_only_target_and_pid(self):
        env = self.route()
        self.assertEqual(env["CMUX_WORKSPACE_ID"], self.binding["workspace_id"])
        self.assertEqual(env["CMUX_SURFACE_ID"], self.binding["surface_id"])
        self.assertEqual(env["CMUX_CODEX_PID"], "42")
        self.assertEqual(env["UNCHANGED"], "yes")
        self.assertEqual(self.env["CMUX_WORKSPACE_ID"], "stale")

    def test_pid_reuse_does_not_retarget_hook(self):
        self.assertEqual(self.route(fingerprint=lambda pid: "different start time /bin/codex"), self.env)

    def test_other_threads_and_ambiguous_bindings_keep_native_routing(self):
        self.assertEqual(self.route({"session_id": "child-thread"}), self.env)
        self.assertEqual(self.route(bindings=[self.binding, self.binding]), self.env)

    def test_malformed_binding_does_not_override_target(self):
        self.binding["fingerprint"] = 123
        self.assertEqual(self.route(), self.env)
        self.binding["surface_id"] = "not-a-surface"
        self.assertEqual(self.route(), self.env)
        self.assertEqual(ROUTE.route_environment([], [], self.env), self.env)

    def test_original_hook_payload_decision_and_exit_status_are_preserved(self):
        # Real subprocess boundary; no live cmux calls or permission decisions.
        with tempfile.TemporaryDirectory() as tmp:
            original = Path(tmp) / "original.sh"
            received = Path(tmp) / "payload.json"
            original.write_text('cat > "$ROUTE_TEST_PAYLOAD"\nprintf \'%s\' \'{"decision":"original"}\'\nexit 7\n')
            payload = json.dumps({"session_id": "unbound", "tool_input": {"value": "`$unchanged`"}}).encode()
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(original)],
                input=payload,
                capture_output=True,
                env={**os.environ, "HOME": tmp, "ROUTE_TEST_PAYLOAD": str(received)},
                check=False,
            )
            self.assertEqual(received.read_bytes(), payload)
            self.assertEqual(result.stdout, b'{"decision":"original"}')
            self.assertEqual(result.returncode, 7)


if __name__ == "__main__":
    unittest.main()
