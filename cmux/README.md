# cmux helpers

`ensure-cpu-monitor.sh` starts the monitor from an interactive cmux shell, preserving socket access. The monitor holds a nonblocking `flock` for its lifetime; duplicate starts exit and the OS releases the lock after a crash. No process-name matching or broad `pkill` is used.

Runtime files live in `~/.cache/lki/cmux` (`CMUX_MONITOR_DIR` overrides the monitor directory): `monitor.lock` contains the owning PID, `heartbeat` is touched after valid workspace reads, and `monitor.log` captures errors. Do not delete an active lock file. Four failed RPC reads, spaced 15 seconds apart, stop the monitor; opening another cmux shell starts it again. A cmux restart may therefore need a new shell after the old monitor exits. To stop a monitor manually, verify the PID in the lock file against its command before sending SIGTERM.

When migrating from the old heartbeat-based launcher, stop the old monitor once before opening a new cmux shell: the old version does not participate in the new lock protocol.

Workspace snapshots may be partial: missing entries expire after 90 seconds. An empty valid list is distinct from an RPC failure. RPC failures pause sidebar writes. At most eight write processes run concurrently, with one per workspace field; writes lasting ten seconds are killed and reaped, and failed writes are retried. Shutdown also reaps outstanding writers.

CPU readings average interval CPU time over 30 seconds, prorating intervals that cross the window boundary. A full core is 100%; Amber starts at 40%, Red and an extra description row at 100%. Orphaned processes whose parent chain no longer reaches a cmux shell cannot be attributed. Sidebar descriptions and colors are owned by this monitor while it is running.

The notification hook only adjusts sound, never calls the cmux CLI, and keeps its rolling 20-second dedupe window under `~/.cache/lki/cmux/sound`. Thirty-two fixed lock files serialize read/update operations across processes; expired session entries are pruned when their stripe is used. Invalid input, invalid window settings, and state IO failures pass the original policy through. Focused notifications do not advance the window.

Run `make test` for process-lock, RPC failure, write timeout, rolling CPU, and concurrent sound-dedupe regression tests. The macOS CI job exercises OS-level file locking and process cleanup; live cmux socket/UI behavior still requires a macOS session.
