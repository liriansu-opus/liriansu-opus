#!/usr/bin/env python3
"""Restore a verified terminal binding for hooks from a shared Codex daemon.

Only explicitly bound, still-identical TUI processes are rerouted. The original
cmux hook receives the unchanged payload and keeps all approval/decision logic.
No prompts or terminal input are sent. Run --install after cmux replaces hooks.
"""

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

RUNTIME = Path.home() / ".cache/lki/cmux"
MARKER = "# lki-codex-route-v1"
UUID = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\Z")


def process_fingerprint(pid):
    return subprocess.check_output(["ps", "-p", str(pid), "-o", "lstart=,comm="], text=True, timeout=2).strip()


def route_environment(payload, bindings, env, fingerprint=process_fingerprint):
    """Reject stale/reused PIDs and mismatched identities instead of guessing."""
    if not isinstance(payload, dict) or not isinstance(bindings, list):
        return env
    sid = payload.get("session_id") or payload.get("thread_id") or payload.get("sessionId")
    matches = [binding for binding in bindings if isinstance(binding, dict) and binding.get("session_id") == sid]
    if len(matches) != 1:
        return env
    binding = matches[0]
    if not all(UUID.fullmatch(str(binding.get(key, ""))) for key in ("workspace_id", "surface_id")):
        return env
    pid = binding.get("pid")
    if not isinstance(pid, int) or pid <= 1:
        return env
    expected = binding.get("fingerprint", "")
    if not isinstance(expected, str) or "codex" not in expected.lower() or fingerprint(pid) != expected:
        return env
    return dict(
        env,
        CMUX_WORKSPACE_ID=binding["workspace_id"],
        CMUX_SURFACE_ID=binding["surface_id"],
        CMUX_CODEX_PID=str(pid),
    )


def install():
    hooks_dir = Path.home() / ".cmux/hooks"
    config = json.loads((Path.home() / ".codex/hooks.json").read_text())
    originals = RUNTIME / "hook-originals"
    originals.mkdir(parents=True, exist_ok=True, mode=0o700)
    paths = set()
    for groups in config.get("hooks", {}).values():
        for group in groups:
            for hook in group.get("hooks", []):
                path = Path(hook.get("command", ""))
                if path.parent == hooks_dir and path.name.startswith("cmux-codex-hook-"):
                    paths.add(path)
    for path in sorted(paths):
        body = path.read_text()
        if MARKER in body:
            continue
        if not body.startswith("#!/bin/sh\n") or "hooks " not in body:
            raise ValueError(f"Unrecognized hook format: {path.name}")
        original = originals / path.name
        original.write_text(body)
        original.chmod(0o700)
        # Paths are generated locally and shell-quoted, never interpolated input.
        prelude = (
            "#!/bin/sh\n"
            + MARKER
            + "\nexec "
            + shlex.quote(sys.executable)
            + " "
            + shlex.quote(str(Path(__file__).resolve()))
            + " "
            + shlex.quote(str(original))
            + ' "$@"\n'
        )
        temp = path.with_suffix(".route-tmp")
        temp.write_text(prelude)
        temp.chmod(path.stat().st_mode & 0o777)
        temp.replace(path)
        print(f"Routed {path.name}")


def uninstall():
    for original in sorted((RUNTIME / "hook-originals").glob("cmux-codex-hook-*.sh")):
        target = Path.home() / ".cmux/hooks" / original.name
        if target.exists() and MARKER in target.read_text():
            target.write_text(original.read_text())
            print(f"Restored {target.name}")


def main():
    if sys.argv[1:] == ["--install"]:
        install()
        return 0
    if sys.argv[1:] == ["--uninstall"]:
        uninstall()
        return 0
    if len(sys.argv) < 2:
        raise SystemExit("Usage: codex-route.py --install | --uninstall | ORIGINAL_HOOK [ARGS]")
    raw = sys.stdin.buffer.read()
    env = dict(os.environ)
    try:
        bindings = json.loads((RUNTIME / "codex-bindings.json").read_text())
        env = route_environment(json.loads(raw), bindings, env)
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as error:
        # Keep the original hook behavior, including its native decision result.
        print(f"cmux hook binding unavailable ({type(error).__name__}); using native routing", file=sys.stderr)
    result = subprocess.run(["/bin/sh", *sys.argv[1:]], input=raw, env=env, check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
