#!/usr/bin/env python3
"""Synchronize cmux sidebar status for Codex TUI workspaces.

cmux's generated Codex hooks can miss the live TUI prompt lifecycle on this
machine. This bridge is intentionally conservative: it only reads cmux state
and the terminal screen, then writes the sidebar's `codex` status to match the
visible Codex TUI state.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

CMUX = os.environ.get("CMUX_BUNDLED_CLI_PATH") or "cmux"
HOME = Path.home()
SESSION_DIR = HOME / ".codex" / "sessions"
RUNNING_ICON = "bolt.fill"
RUNNING_COLOR = "#4C8DFF"
IDLE_ICON = "pause.circle.fill"
IDLE_COLOR = "#8E8E93"
HELPER_PROCESS_LABELS = {"SkyComputerUseC", "node_repl"}
CODEX_RE = re.compile(r"\bcodex(?:-aarch64-a(?:pple-darwin)?|$)")
ROLLOUT_RE = re.compile(r"\brollout-\d{4}-\d{2}-\d{2}T[^/\s]+-([0-9a-f-]{36})\.jsonl\b", re.IGNORECASE)
TREE_WORKSPACE_RE = re.compile(r"\bworkspace\s+(workspace:\d+)\s+([0-9a-f-]{36})\b", re.IGNORECASE)
TREE_SURFACE_RE = re.compile(r"\bsurface\s+(surface:\d+)\s+([0-9a-f-]{36})\b", re.IGNORECASE)
UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)


@dataclass
class SurfaceInfo:
    workspace_ref: str
    workspace_id: str
    surface_ref: str
    surface_id: str
    pid: str
    cwd: str
    has_active_child: bool = False


def run(args: list[str], *, input_text: str | None = None, timeout: float = 4) -> subprocess.CompletedProcess[str]:
    socket_path = os.environ.get("CMUX_SOCKET_PATH")
    command = [CMUX, *args] if not socket_path else [CMUX, "--socket", socket_path, *args]
    try:
        return subprocess.run(
            command,
            input=input_text,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return subprocess.CompletedProcess(command, 124, stdout=stdout, stderr=stderr)


def output(args: list[str], *, timeout: float = 4) -> str:
    proc = run(args, timeout=timeout)
    return proc.stdout if proc.returncode == 0 else ""


def load_tree() -> tuple[dict[str, str], dict[str, str]]:
    raw = output(["tree", "--all", "--id-format", "both"], timeout=4)
    workspace_ids: dict[str, str] = {}
    surface_ids: dict[str, str] = {}
    for line in raw.splitlines():
        workspace_match = TREE_WORKSPACE_RE.search(line)
        if workspace_match:
            workspace_ids[workspace_match.group(1)] = workspace_match.group(2)
        surface_match = TREE_SURFACE_RE.search(line)
        if surface_match:
            surface_ids[surface_match.group(1)] = surface_match.group(2)
    return workspace_ids, surface_ids


def parse_top() -> tuple[dict[str, str], dict[str, str], dict[str, str], list[tuple[str, str, str]]]:
    top = output(["top", "--all", "--processes", "--flat", "--format", "tsv"], timeout=8)
    pane_to_workspace: dict[str, str] = {}
    surface_to_workspace: dict[str, str] = {}
    tag_to_workspace: dict[str, str] = {}
    process_to_parent: dict[str, str] = {}
    process_rows: list[tuple[str, str, str]] = []

    for line in top.splitlines():
        parts = line.split("\t")
        if len(parts) < 7:
            continue
        _cpu, _mem, _count, kind, ident, parent, label = parts[:7]
        if kind == "pane" and ident.startswith("pane:") and parent.startswith("workspace:"):
            pane_to_workspace[ident] = parent
        elif kind == "surface" and ident.startswith("surface:"):
            workspace = pane_to_workspace.get(parent)
            if workspace:
                surface_to_workspace[ident] = workspace
        elif kind == "tag" and ":tag:codex" in ident and parent.startswith("workspace:"):
            tag_to_workspace[ident] = parent
        elif kind == "process":
            process_to_parent[ident] = parent
            process_rows.append((ident, parent, label))

    return surface_to_workspace, tag_to_workspace, process_to_parent, process_rows


def process_container(pid: str, process_to_parent: dict[str, str]) -> tuple[str, str]:
    """Return the cmux surface/tag that owns a process tree."""
    seen: set[str] = set()
    current = pid
    while current and current not in seen:
        seen.add(current)
        parent = process_to_parent.get(current, "")
        if parent.startswith("surface:"):
            return "surface", parent
        if ":tag:" in parent:
            return "tag", parent
        current = parent
    return "", ""


def has_active_descendant(
    pid: str, process_to_parent: dict[str, str], process_rows: list[tuple[str, str, str]]
) -> bool:
    children: dict[str, list[tuple[str, str]]] = {}
    for child_pid, parent, label in process_rows:
        children.setdefault(parent, []).append((child_pid, label))

    stack = list(children.get(pid, []))
    seen: set[str] = set()
    while stack:
        child_pid, label = stack.pop()
        if child_pid in seen:
            continue
        seen.add(child_pid)
        if label and label not in HELPER_PROCESS_LABELS:
            return True
        stack.extend(children.get(child_pid, []))
    return False


def process_cwd(pid: str) -> str:
    proc = subprocess.run(
        ["lsof", "-a", "-p", pid, "-d", "cwd", "-Fn"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    for line in proc.stdout.splitlines():
        if line.startswith("n"):
            return line[1:]
    return ""


def process_command(pid: str) -> str:
    proc = subprocess.run(
        ["ps", "-p", pid, "-o", "command="],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return proc.stdout.strip()


def process_rollout_session_id(pid: str) -> str:
    try:
        proc = subprocess.run(
            ["lsof", "-p", pid],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=3,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return ""
    for line in proc.stdout.splitlines():
        if "/.codex/sessions/" not in line or "rollout-" not in line:
            continue
        match = ROLLOUT_RE.search(line)
        if match:
            return match.group(1)
    return ""


def codex_surfaces() -> list[SurfaceInfo]:
    workspace_ids, surface_ids = load_tree()
    surface_to_workspace, tag_to_workspace, process_to_parent, process_rows = parse_top()
    by_workspace: dict[str, SurfaceInfo] = {}

    for pid, _parent, label in process_rows:
        if not CODEX_RE.search(label):
            continue
        workspace_ref = ""
        surface_ref = ""
        container_kind, container_ref = process_container(pid, process_to_parent)
        if container_kind == "surface":
            surface_ref = container_ref
            workspace_ref = surface_to_workspace.get(container_ref, "")
        elif container_kind == "tag" and ":tag:codex" in container_ref:
            workspace_ref = tag_to_workspace.get(container_ref, "")
        if not workspace_ref:
            continue
        if "claude_code=" in current_status(workspace_ref):
            run(["clear-status", "codex", "--workspace", workspace_ref], timeout=4)
            continue
        cwd = process_cwd(pid)
        info = SurfaceInfo(
            workspace_ref=workspace_ref,
            workspace_id=workspace_ids.get(workspace_ref, workspace_ref),
            surface_ref=surface_ref,
            surface_id=surface_ids.get(surface_ref, surface_ref),
            pid=pid,
            cwd=cwd,
            has_active_child=has_active_descendant(pid, process_to_parent, process_rows),
        )
        by_workspace.setdefault(workspace_ref, info)

    return sorted(by_workspace.values(), key=lambda item: item.workspace_ref)


def screen_is_working(info: SurfaceInfo) -> bool:
    if info.has_active_child:
        return True
    args = ["read-screen", "--workspace", info.workspace_ref, "--lines", "18"]
    if info.surface_ref:
        args.extend(["--surface", info.surface_ref])
    text = output(args, timeout=4)
    return "• Working" in text or "\n• Thinking" in text or "Working (" in text


def current_status(workspace_ref: str) -> str:
    return output(["list-status", "--workspace", workspace_ref], timeout=3)


def infer_session_id(info: SurfaceInfo) -> str:
    open_session_id = process_rollout_session_id(info.pid)
    if open_session_id:
        return open_session_id

    cmd = process_command(info.pid)
    if "codex resume" in cmd:
        match = UUID_RE.search(cmd)
        if match:
            return match.group(0)

    candidates = sorted(SESSION_DIR.glob("20*/**/rollout-*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in candidates[:30]:
        try:
            first = path.open(encoding="utf-8").readline()
            payload = json.loads(first).get("payload", {})
        except (OSError, json.JSONDecodeError):
            continue
        if info.cwd and payload.get("cwd") != info.cwd:
            continue
        sid = payload.get("id") or payload.get("session_id")
        if sid:
            return str(sid)
    return f"codex-pid-{info.pid}"


def ensure_codex_tag(info: SurfaceInfo) -> None:
    if "codex=" in current_status(info.workspace_ref):
        return
    if not info.surface_id or not info.workspace_id:
        return
    session_id = infer_session_id(info)
    payload = json.dumps(
        {
            "hook_event_name": "SessionStart",
            "session_id": session_id,
            "cwd": info.cwd,
        }
    )
    env = os.environ.copy()
    env.update(
        {
            "CMUX_SURFACE_ID": info.surface_id,
            "CMUX_WORKSPACE_ID": info.workspace_id,
            "CMUX_CODEX_PID": info.pid,
        }
    )
    socket_path = os.environ.get("CMUX_SOCKET_PATH")
    if socket_path:
        env["CMUX_SOCKET_PATH"] = socket_path
    subprocess.run(
        [CMUX, "hooks", "codex", "session-start"],
        input=payload,
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
        timeout=5,
        check=False,
    )


def sync_once(verbose: bool = False) -> int:
    changed = 0
    infos = codex_surfaces()
    for info in infos:
        working = screen_is_working(info)
        ensure_codex_tag(info)
        value = "Running" if working else "Idle"
        icon = RUNNING_ICON if working else IDLE_ICON
        color = RUNNING_COLOR if working else IDLE_COLOR
        run(
            [
                "set-status",
                "codex",
                value,
                "--workspace",
                info.workspace_ref,
                "--icon",
                icon,
                "--color",
                color,
                "--priority",
                "100",
            ],
            timeout=4,
        )
        changed += 1
        if verbose:
            print(f"{info.workspace_ref} pid={info.pid} codex={value}", flush=True)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true", help="Keep synchronizing until interrupted.")
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if args.loop:
        while True:
            try:
                sync_once(verbose=args.verbose)
            except Exception as exc:  # noqa: BLE001 - keep the long-running LaunchAgent alive.
                print(f"codex-status-sync: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
            time.sleep(args.interval)
    else:
        sync_once(verbose=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
