#!/usr/bin/env python3
"""cmux notification policy hook: per-session (per-surface) sound de-dupe.

cmux pipes a notification "policy" JSON to this hook on stdin; whatever JSON we
write on stdout becomes the effective policy. We only ever touch effects.sound:
if the same agent session (surfaceId) already rang within WINDOW_SECONDS, we set
effects.sound = false so the repeat is silent — every visual (pane ring, sidebar
highlight, dock badge, desktop banner) is left untouched. Different sessions ring
independently. The window is anchored on the FIRST ring, so a session that keeps
needing you still gets a periodic reminder (one ring per window), not a burst.

Fail-open by design: any parse/IO error echoes stdin unchanged, so the worst case
is "no de-dupe" (sound still plays) — never a silenced notification.

Tunables (env): CMUX_SOUND_DEDUPE_WINDOW (seconds, default 15).
"""
import sys
import os
import json
import time

WINDOW_SECONDS = float(os.environ.get("CMUX_SOUND_DEDUPE_WINDOW", "15"))
STATE_DIR = os.path.join(os.environ.get("TMPDIR", "/tmp"), "cmux-sound-dedupe")


def main():
    raw = sys.stdin.read()
    try:
        policy = json.loads(raw)
        effects = policy.get("effects")
        notif = policy.get("notification") or {}
        # Only act on a policy that would actually play a sound.
        if not isinstance(effects, dict) or not effects.get("sound", False):
            sys.stdout.write(raw)
            return
        key = (
            notif.get("surfaceId") or notif.get("surface_id")
            or notif.get("workspaceId") or notif.get("workspace_id")
        )
        if not key:
            sys.stdout.write(raw)
            return
        os.makedirs(STATE_DIR, exist_ok=True)
        safe = "".join(c for c in str(key) if c.isalnum() or c in "-_") or "default"
        path = os.path.join(STATE_DIR, safe)
        now = time.time()
        last = 0.0
        try:
            with open(path) as f:
                last = float(f.read().strip() or 0)
        except (OSError, ValueError):
            last = 0.0
        if now - last < WINDOW_SECONDS:
            effects["sound"] = False  # repeat within window -> silence, keep anchor
        else:
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
