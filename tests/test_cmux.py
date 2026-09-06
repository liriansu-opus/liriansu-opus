import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


monitor = load("monitor", "cmux/cmux-cpu-monitor.py")
sound = load("sound", "cmux/hooks/dedupe-sound.py")


class MonitorTests(unittest.TestCase):
    def test_rpc_empty_is_success_but_error_is_not(self):
        for raw, expected in [(' {"workspaces": []}', {}), ("{}", None), ("bad", None), ('{"workspaces": [{}]}', None)]:
            with self.subTest(raw=raw), patch.object(monitor, "cmux", return_value=raw):
                self.assertEqual(monitor.known_workspaces(), expected)

    def test_nonzero_rpc_ignores_stdout(self):
        with patch.object(monitor.subprocess, "run", return_value=Mock(returncode=1, stdout="{}", stderr="denied")):
            self.assertEqual(monitor.cmux("rpc"), "")

    def test_partial_snapshots_eventually_expire(self):
        seen = {}
        monitor.refresh_seen(seen, {"a": (), "b": ()}, 0)
        monitor.refresh_seen(seen, {"a": ()}, 30)
        self.assertEqual(set(seen), {"a", "b"})
        monitor.refresh_seen(seen, {"a": ()}, 90)
        self.assertEqual(set(seen), {"a"})

    def test_rolling_cpu_burst_sustained_and_idle(self):
        history = []
        self.assertEqual(monitor.rolling_percent(history, 0, 3, 3), 10)
        for start in range(3, 30, 3):
            pct = monitor.rolling_percent(history, start, start + 3, 3)
        self.assertEqual(pct, 100)
        self.assertEqual(monitor.rolling_percent(history, 30, 60, 0), 0)

    def test_stalled_sample_does_not_inflate_cpu(self):
        self.assertEqual(monitor.rolling_percent([], 0, 60, 60), 100)
        history = [(0, 20, 20)]
        self.assertEqual(monitor.rolling_percent(history, 20, 40, 20), 100)

    def test_write_limit_timeout_retry_and_cache(self):
        writes = monitor.PendingWrites()
        cache = {}
        children = [Mock() for _ in range(monitor.MAX_WRITES)]
        for i, child in enumerate(children):
            child.poll.return_value = None
            writes.submit((str(i), "color"), Mock(return_value=child), str(i), "Red", cache, "red", 0)
        rejected = Mock()
        writes.submit(("extra", "color"), rejected, "extra", "Red", cache, "red", 0)
        rejected.assert_not_called()
        writes.submit(("0", "color"), rejected, "0", "Amber", cache, "amber", 0)
        rejected.assert_not_called()
        writes.reap(monitor.WRITE_TIMEOUT)
        for child in children:
            child.kill.assert_called_once()
            child.poll.return_value = -9
        writes.reap(11)
        self.assertEqual(cache, {})
        self.assertEqual(writes.pending, {})
        child = Mock()
        child.poll.return_value = 0
        writes.submit(("0", "color"), Mock(return_value=child), "0", "Red", cache, "red", 12)
        writes.reap(13)
        self.assertEqual(cache, {"0": "red"})

    def test_rpc_failure_pauses_writes_and_exits_on_schedule(self):
        writes = Mock()
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(monitor, "HEARTBEAT", Path(directory) / "heartbeat"),
            patch.object(monitor, "snapshot_procs", return_value={}),
            patch.object(monitor, "find_roots", return_value={}),
            patch.object(monitor.time, "sleep"),
            patch.object(monitor.time, "monotonic", side_effect=[0, 3, 18, 33, 48, 63]),
            patch.object(monitor, "known_workspaces", side_effect=[{"a": (None, None)}, None, None, None, None]) as rpc,
        ):
            monitor.main(writes)
            self.assertEqual(rpc.call_count, 5)
            writes.submit.assert_not_called()

    def test_empty_snapshot_does_not_trigger_denial_exit(self):
        writes = Mock()
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(monitor, "HEARTBEAT", Path(directory) / "heartbeat"),
            patch.object(monitor, "snapshot_procs", return_value={}),
            patch.object(monitor, "find_roots", return_value={}),
            patch.object(monitor.time, "sleep", side_effect=[None] * 6 + [InterruptedError]),
            patch.object(monitor.time, "monotonic", side_effect=[0, 3, 18, 33, 48, 63, 78]),
            patch.object(monitor, "known_workspaces", return_value={}) as rpc,
        ):
            with self.assertRaises(InterruptedError):
                monitor.main(writes)
            self.assertEqual(rpc.call_count, 6)
            writes.submit.assert_not_called()

    def test_shutdown_reaps_children(self):
        writes = monitor.PendingWrites()
        child = Mock()
        child.poll.return_value = None
        writes.submit(("a", "color"), Mock(return_value=child), "a", "Red", {}, "red", 0)
        writes.close()
        child.kill.assert_called_once()
        child.wait.assert_called_once()

    def test_singleton_lock_releases_after_process_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            source = str(ROOT / "cmux/cmux-cpu-monitor.py")
            code = (
                "import importlib.util, time; "
                f"s=importlib.util.spec_from_file_location('m', {source!r}); "
                "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
                "m.main=lambda writes: (print('owned', flush=True), time.sleep(30)); m.run_monitor()"
            )
            env = dict(os.environ, CMUX_MONITOR_DIR=directory)
            first = subprocess.Popen([sys.executable, "-c", code], env=env, stdout=subprocess.PIPE, text=True)
            try:
                self.assertEqual(first.stdout.readline().strip(), "owned")
                second = subprocess.run(
                    [sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=5
                )
                self.assertEqual(second.returncode, 0)
                self.assertEqual(second.stdout, "")
            finally:
                first.terminate()
                first.wait(timeout=5)
                first.stdout.close()
            fast = code.replace("time.sleep(30)", "None")
            third = subprocess.run([sys.executable, "-c", fast], env=env, capture_output=True, text=True, timeout=5)
            self.assertEqual(third.stdout.strip(), "owned")


class SoundTests(unittest.TestCase):
    def invoke(self, policy):
        raw = policy if isinstance(policy, str) else json.dumps(policy)
        output = io.StringIO()
        with patch.object(sys, "stdin", io.StringIO(raw)), patch.object(sys, "stdout", output):
            sound.main()
        return output.getvalue()

    def test_rolling_window_and_independent_sessions(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(sound, "STATE_DIR", directory):
            for session, now, expected in [
                ("a", 100, True),
                ("a", 110, False),
                ("a", 125, False),
                ("b", 126, True),
                ("a", 146, True),
            ]:
                with patch.object(sound.time, "monotonic", return_value=now):
                    policy = {"effects": {"sound": True, "badge": True}, "notification": {"surfaceId": session}}
                    result = json.loads(self.invoke(policy))
                    self.assertEqual(result["effects"], {"sound": expected, "badge": True})

    def test_focus_does_not_create_anchor(self):
        policy = {"effects": {"sound": True}, "context": {"appFocused": True, "focusedPanel": True}}
        with patch.object(sound.os, "makedirs") as mkdir:
            self.assertFalse(json.loads(self.invoke(policy))["effects"]["sound"])
            mkdir.assert_not_called()

    def test_fail_open_on_bad_input_window_and_io(self):
        self.assertEqual(self.invoke("bad json"), "bad json")
        policy = {"effects": {"sound": True}, "notification": {"surfaceId": "a"}}
        for window in ("bad", "nan", "-1"):
            with patch.dict(os.environ, CMUX_SOUND_DEDUPE_WINDOW=window):
                self.assertEqual(json.loads(self.invoke(policy)), policy)
        with patch.object(sound.os, "makedirs", side_effect=OSError("unwritable")):
            self.assertEqual(json.loads(self.invoke(policy)), policy)

    def test_concurrent_notifications_only_sound_once(self):
        with tempfile.TemporaryDirectory() as directory:
            code = (
                "import importlib.util; "
                f"s=importlib.util.spec_from_file_location('s', {str(ROOT / 'cmux/hooks/dedupe-sound.py')!r}); "
                "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
                f"m.STATE_DIR={directory!r}; m.main()"
            )
            raw = json.dumps({"effects": {"sound": True}, "notification": {"surfaceId": "same"}})

            def invoke(_):
                result = subprocess.run(
                    [sys.executable, "-c", code], input=raw, text=True, capture_output=True, check=True, timeout=10
                )
                return json.loads(result.stdout)["effects"]["sound"]

            with ThreadPoolExecutor(max_workers=8) as pool:
                self.assertEqual(sum(pool.map(invoke, range(16))), 1)


if __name__ == "__main__":
    unittest.main()
