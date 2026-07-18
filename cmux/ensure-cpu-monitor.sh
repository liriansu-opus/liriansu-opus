#!/bin/bash
# Ensure the cmux per-workspace CPU monitor is running — started from INSIDE cmux.
#
# cmux's control socket is `automation.socketControlMode = cmuxOnly`: it only
# accepts processes that inherited a cmux session. A LaunchAgent is therefore
# permanently locked out ("Access denied — only processes started inside cmux can
# connect"). A process started from a cmux shell keeps that access even after it
# is orphaned to launchd, so starting it here — from every cmux shell — is both
# necessary and sufficient. A cmux *restart* invalidates the inherited session,
# which is what the heartbeat check below detects.
#
# Invoked from ~/.lki/.profile, gated on $CMUX_WORKSPACE_ID, so it is a no-op in
# non-cmux shells. Cost when healthy: a single `find` on the heartbeat file.
set -u

MONITOR="$HOME/.lki/cmux/cmux-cpu-monitor.py"
HEARTBEAT=/tmp/cmux-cpu-monitor.alive
PATTERN='cmux-cpu-monitor\.py'

[ -n "${CMUX_WORKSPACE_ID:-}" ] || exit 0
[ -f "$MONITOR" ] || exit 0

# A fresh heartbeat means a monitor is alive AND can still reach cmux. Don't use
# the state file for this: a locked-out monitor keeps writing that just fine,
# since sampling needs no socket.
if [ -n "$(find "$HEARTBEAT" -mmin -2 2>/dev/null)" ]; then
  exit 0
fi

# Stale or missing: either nothing is running, or an old monitor lost socket
# access when cmux restarted. Clear it out and start one from this shell.
pkill -f "$PATTERN" >/dev/null 2>&1
nohup /usr/bin/python3 "$MONITOR" >/dev/null 2>&1 &

# Claim the heartbeat immediately so sibling shells starting at the same moment
# (cmux restores every workspace at once) don't each spawn their own monitor.
: > "$HEARTBEAT"
exit 0
