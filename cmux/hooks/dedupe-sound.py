#!/usr/bin/env python3
"""cmux notification policy hook: don't re-crow an unattended session.

cmux pipes a notification "policy" JSON to this hook on stdin; whatever JSON we
write on stdout becomes the effective policy. We only ever touch effects.sound;
every visual (pane ring, sidebar, badge, banner) is left untouched.

Goal: a session should crow ONCE, then stay silent until you actually deal with
it — not nag every few seconds. Three mechanisms, OR'd:

  0. Actively-viewing: if cmux is frontmost (context.appFocused) AND the alert
     targets the panel you're focused on (context.focusedPanel), you already see
     it — stay silent. Other (background) sessions still crow, even while cmux is
     frontmost. No dedup anchor is rolled here, so the next alert crows the moment
     you look away. This is the only mechanism that needs no session key.

The other two are keyed per agent session (surfaceId, falling back to workspaceId):

  1. Rolling window: while a session keeps firing within WINDOW seconds of its
     last alert, the anchor rolls forward, so a busy/looping session crows once
     and stays silent until it goes quiet for a full WINDOW (then re-arms).

  2. Reset-on-view: if the session still has an UNREAD notification older than a
     couple seconds (i.e. you were already alerted and haven't looked), stay
     silent. Focusing the workspace makes cmux clear/read its notifications, which
     re-arms the next crow. This is queried live via `cmux list-notifications`.

Fail-open by design: any parse/IO/query error leaves the policy unchanged, so the
worst case is "it still crows" — never a swallowed notification.

Tunables (env): CMUX_SOUND_DEDUPE_WINDOW (seconds, default 20).
"""

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime

WINDOW = float(os.environ.get("CMUX_SOUND_DEDUPE_WINDOW", "20"))
SELF_EXCLUDE = 2.0  # ignore unread newer than this — it's the current alert itself
STATE_DIR = os.path.join(os.environ.get("TMPDIR", "/tmp"), "cmux-sound-dedupe")
CMUX_FALLBACK = "/Applications/cmux.app/Contents/Resources/bin/cmux"


def _iso_epoch(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()


def _unread_for(key):
    """Live unread notifications whose surface/workspace matches key."""
    test = os.environ.get("CMUX_SOUND_DEDUPE_TEST_JSON")  # for offline unit tests
    if test:
        with open(test) as f:
            data = json.load(f)
    else:
        cmux = shutil.which("cmux") or CMUX_FALLBACK
        out = subprocess.run(
            [cmux, "list-notifications", "--json"],
            capture_output=True,
            text=True,
            timeout=2,
        ).stdout
        data = json.loads(out) if out.strip() else []
    return [n for n in data if not n.get("is_read") and (n.get("surface_id") == key or n.get("workspace_id") == key)]


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

        os.makedirs(STATE_DIR, exist_ok=True)
        safe = "".join(c for c in str(key) if c.isalnum() or c in "-_") or "default"
        path = os.path.join(STATE_DIR, safe)
        now = time.time()
        try:
            with open(path) as f:
                last = float(f.read().strip() or 0)
        except (OSError, ValueError):
            last = 0.0

        suppress = False
        if now - last < WINDOW:
            suppress = True  # (1) rolling: session is actively firing -> already crowed
        else:
            try:  # (2) reset-on-view: a still-unread prior alert means "not looked at yet"
                pending = [n for n in _unread_for(key) if now - _iso_epoch(n.get("created_at", "")) > SELF_EXCLUDE]
                if pending:
                    suppress = True
            except Exception:
                pass  # query failed -> don't suppress on this basis (fail-open)

        if suppress:
            effects["sound"] = False
        # Roll the anchor on every sound-eligible alert so a continuously-firing
        # session never re-crows until it has been quiet for a full WINDOW.
        try:
            with open(path, "w") as f:
                f.write(str(now))
        except OSError:
            pass
        sys.stdout.write(json.dumps(policy))
    except Exception:
        sys.stdout.write(raw)  # fail-open: never swallow a notification


if __name__ == "__main__":
    main()
