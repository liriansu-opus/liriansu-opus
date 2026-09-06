#!/bin/bash
# Launch from inside cmux so the monitor inherits socket access. The Python
# process holds an exclusive flock for its lifetime; extra launches exit.
set -eu

[ -n "${CMUX_WORKSPACE_ID:-}" ] || exit 0
MONITOR="$HOME/.lki/cmux/cmux-cpu-monitor.py"
[ -f "$MONITOR" ] || exit 0
RUNTIME="${CMUX_MONITOR_DIR:-$HOME/.cache/lki/cmux}"
mkdir -p "$RUNTIME"
nohup /usr/bin/python3 "$MONITOR" >>"$RUNTIME/monitor.log" 2>&1 </dev/null &
