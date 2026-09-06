#!/usr/bin/env python3
"""cmux notification policy hook: don't re-crow an unattended session.

cmux pipes a notification "policy" JSON to this hook on stdin; whatever JSON we
write on stdout becomes the effective policy. We only ever touch effects.sound;
every visual (pane ring, sidebar, badge, banner) is left untouched.

Goal: a busy session should crow once, then stay silent until it has been quiet
for a full rolling window — not nag every few seconds. Two mechanisms are OR'd:

  0. Actively-viewing: if cmux is frontmost (context.appFocused) AND the alert
     targets the panel you're focused on (context.focusedPanel), you already see
     it — stay silent. Other (background) sessions still crow, even while cmux is
     frontmost. No dedup anchor is rolled here, so the next alert crows the moment
     you look away. This is the only mechanism that needs no session key.

The rolling window is keyed per agent session (surfaceId, falling back to
workspaceId):

  1. Rolling window: while a session keeps firing within WINDOW seconds of its
     last alert, the anchor rolls forward, so a busy/looping session crows once
     and stays silent until it goes quiet for a full WINDOW (then re-arms).

The hook deliberately does not call the cmux CLI. Notification policy evaluation
already runs inside cmux; reconnecting with `cmux list-notifications` from that
hook can feed socket/main-thread work back into notification and sidebar layout.

Fail-open by design: any parse/IO error leaves the policy unchanged, so the
worst case is "it still crows" — never a swallowed notification.

Tunables (env): CMUX_SOUND_DEDUPE_WINDOW (seconds, default 20).
"""

import fcntl
import hashlib
import json
import math
import os
import sys
import time

STATE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "lki", "cmux", "sound")


def main():
    raw = sys.stdin.read()
    try:
        policy = json.loads(raw)
        effects = policy.get("effects")
        notif = policy.get("notification") or {}
        if not isinstance(effects, dict) or not effects.get("sound", False):
            sys.stdout.write(raw)
            return

        # (0) Actively-viewing: if cmux is frontmost AND this notification targets
        # the panel I'm focused on, I already see it — stay silent. No dedup anchor
        # is rolled, so the moment I look away the next alert crows normally.
        # Visuals (ring/badge/flash) are untouched, as always.
        context = policy.get("context") or {}
        if context.get("appFocused") and context.get("focusedPanel"):
            effects["sound"] = False
            sys.stdout.write(json.dumps(policy))
            return

        key = notif.get("surfaceId") or notif.get("surface_id") or notif.get("workspaceId") or notif.get("workspace_id")
        if not key:
            sys.stdout.write(raw)
            return

        window = float(os.environ.get("CMUX_SOUND_DEDUPE_WINDOW", "20"))
        if not math.isfinite(window) or window < 0:
            raise ValueError("invalid dedupe window")
        os.makedirs(STATE_DIR, mode=0o700, exist_ok=True)
        # Fixed lock stripes bound disk usage without unlinking a live lock inode.
        stripe = int.from_bytes(hashlib.sha256(str(key).encode()).digest()[:2], "big") % 32
        path = os.path.join(STATE_DIR, str(stripe))
        with open(path, "a+") as state:
            fcntl.flock(state, fcntl.LOCK_EX)
            state.seek(0)
            try:
                anchors = json.load(state)
            except ValueError:
                anchors = {}
            now = time.monotonic()
            anchors = {k: v for k, v in anchors.items() if 0 <= now - v < window}
            suppress = str(key) in anchors
            anchors[str(key)] = now
            state.seek(0)
            state.truncate()
            json.dump(anchors, state)
            state.flush()
        # Only change sound after a successful state write (fail open on IO errors).
        if suppress:
            effects["sound"] = False
        sys.stdout.write(json.dumps(policy))
    except Exception:
        sys.stdout.write(raw)  # fail-open: never swallow a notification


if __name__ == "__main__":
    main()
