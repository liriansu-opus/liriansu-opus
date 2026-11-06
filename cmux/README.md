# cmux helpers

## Attention sidebar

`sidebars/attention-first.js` is an English, native custom sidebar. Its compact
default list follows workspace keyboard order, with a status and shortcut on
each row. Needs you and Running are filters; Options can enable status grouping.
Rows open the workspace and matching terminal. Each terminal has one row;
helper agents registered on the same terminal contribute to its status without
creating extra rows. Agents in different terminals remain separate.
Workspaces without a detected agent stay reachable with No agent. Existing
workspace and tab names are preserved.

Only cmux's native unread notifications add a bright blue dot with a soft halo
and a blue row background. Notifications on any panel highlight the workspace's
rows, including while background agents are working. Jump to Unread (⌘⇧U),
reading, dismissing, and marking unread all use that same native state; the
sidebar reflects changes on its next refresh (about one second). Ready for
review and Mark reviewed affect the local status only. Snooze marks the native
notifications read as described below, so Jump to Unread skips the saved item.
Each row also shows a folder icon and the final component of its working
directory. The active agent's directory takes precedence, followed by its terminal
and workspace directory; conventional home directories display `~`. Directory
names and paths are searchable.

Install with the Custom Sidebars beta enabled (validated on cmux 0.65.2):

```bash
mkdir -p ~/.config/cmux/sidebars
ln -s ~/.lki/cmux/sidebars/attention-first.js ~/.config/cmux/sidebars/attention-first.js
cmux sidebar validate attention-first
cmux sidebar select attention-first
```

The link command refuses to replace an existing file. To return to the built-in
view, right-click the sidebar toggle in the title bar and choose the default
workspace view. Source edits hot-reload; `cmux sidebar validate attention-first`
checks the file without restarting cmux.

Click a row to open its terminal and reveal its available actions. They collapse when focus moves to another row, including through keyboard shortcuts, and stay collapsed when focus returns. Pending
requests can be saved with Snooze, which moves them into a collapsed Snoozed
section with no timer. Expand that section and choose Unsnooze to restore an item.
Snooze marks the workspace's native notifications read; when multiple terminal
rows share a workspace, it marks only that terminal's notifications read.
Review responses can be marked reviewed.
An idle session can be added with Review later. Active input requests must be
answered in the terminal; the sidebar never sends input or grants permission.
If a previously observed request remains after the agent becomes idle, use
Mark resolved only after checking the terminal. Options controls review counts,
grouping, row density, branch details, and collapsed sections. Search does not read or
display conversation transcripts.

Status rules:

- `needs_input` creates a pending request. Reading or selecting its terminal
  does not clear it. A new running turn clears the previous request.
- Background children and helper agents on the same terminal keep its row
  Running until all work stops, even when the main agent pauses. They do not
  create review indicators or clear another agent's unresolved input request.
- An observed Running → Idle/Ended transition offers the response for review;
  it does **not** assert that the task succeeded. Initially idle sessions do
  not manufacture review items. Unread messages and open PRs alone do not count.
- A new input-request event cancels the previous snooze. A lost connection
  exposes any unresolved input request instead of hiding it behind a reminder.
- Missing or unrecognized signals remain explicit. Workspace-level
  inferred task lanes are not used to assign a result to an individual agent.

The cmux JS runtime has no persistent storage. Snoozes, review dispositions,
observed transitions, and display preferences last only for the current sidebar
instance. Reloading rebuilds the view from live signals. A pending review that
exists only in local state must be re-added after reload; this is not a durable
task inbox. Input requests still reported by cmux reappear automatically.

`make test-sidebar` runs the state-transition tests with Node.js. `make test`
includes these tests and the Python helper tests. The actual sidebar needs no
Node.js process, polling daemon, or third-party packages.

## CPU monitor and notification hooks

`ensure-cpu-monitor.sh` starts the monitor from an interactive cmux shell, preserving socket access. The monitor holds a nonblocking `flock` for its lifetime; duplicate starts exit and the OS releases the lock after a crash. No process-name matching or broad `pkill` is used.

Runtime files live in `~/.cache/lki/cmux` (`CMUX_MONITOR_DIR` overrides the monitor directory): `monitor.lock` contains the owning PID, `heartbeat` is touched after valid workspace reads, and `monitor.log` captures errors. Do not delete an active lock file. Four failed RPC reads, spaced 15 seconds apart, stop the monitor; opening another cmux shell starts it again. A cmux restart may therefore need a new shell after the old monitor exits. To stop a monitor manually, verify the PID in the lock file against its command before sending SIGTERM.

When migrating from the old heartbeat-based launcher, stop the old monitor once before opening a new cmux shell: the old version does not participate in the new lock protocol.

Workspace snapshots may be partial: missing entries expire after 90 seconds. An empty valid list is distinct from an RPC failure. RPC failures pause sidebar writes. At most eight write processes run concurrently, with one per workspace field; writes lasting ten seconds are killed and reaped, and failed writes are retried. Shutdown also reaps outstanding writers.

CPU readings average interval CPU time over 30 seconds, prorating intervals that cross the window boundary. A full core is 100%; Amber starts at 40%, Red and an extra description row at 100%. Orphaned processes whose parent chain no longer reaches a cmux shell cannot be attributed. Sidebar descriptions and colors are owned by this monitor while it is running.

The notification hook only adjusts sound, never calls the cmux CLI, and keeps its rolling 20-second dedupe window under `~/.cache/lki/cmux/sound`. Thirty-two fixed lock files serialize read/update operations across processes; expired session entries are pruned when their stripe is used. Invalid input, invalid window settings, and state IO failures pass the original policy through. Focused notifications do not advance the window.

Run `make test` for process-lock, RPC failure, write timeout, rolling CPU, and concurrent sound-dedupe regression tests. The macOS CI job exercises OS-level file locking and process cleanup; live cmux socket/UI behavior still requires a macOS session.
