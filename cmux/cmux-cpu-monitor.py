#!/usr/bin/env python3
"""Per-workspace CPU monitor for cmux (interval-sampling daemon).

Started from INSIDE cmux by ensure-cpu-monitor.sh (wired into ~/.lki/.profile, so
every cmux shell checks it). It CANNOT run as a LaunchAgent: cmux's control
socket is `automation.socketControlMode = cmuxOnly`, which rejects anything that
did not inherit a cmux session ("Access denied — only processes started inside
cmux can connect"). That check is on the inherited session, not live parentage,
so once started from a cmux shell this process keeps access even after it is
orphaned to launchd — but a cmux *restart* invalidates it, so on prolonged
denial we exit and let the next cmux shell start a fresh one.

Every SAMPLE_DT seconds it
takes the *interval* CPU of every process — Δ(cpu-time)/Δt, the way `top`
measures, NOT ps's lifetime %CPU decaying average — attributes it to a cmux
workspace, and surfaces the rolling AVERAGE over the last AVG_WINDOW seconds in
the stock sidebar. An average (not a peak, not the last sample) is deliberate:
launching an agent (Codex / Claude Code) pegs a core for a few seconds, and any
instantaneous or peak-holding reading paints the workspace red on every launch.
Averaged over the window, a few-second startup burst dilutes below the colour
floor, while genuinely sustained load (a build loop, a runaway agent) crosses
AMBER in ~10s and RED once it has held a core for most of the window — and the
colour drains away within one window of the load stopping. The cost: a burst
that finishes within a few seconds (a lone tsc / eslint run) no longer
registers. Accepted — those were exactly the false alarms.

Display policy: only a workspace at/above RED gets a *description* ("<heat>
<n>%"); everything quieter has its description cleared. A description is a
full-height detail row in the native sidebar, so labelling every workspace would
burn a line per workspace to say "fine". At rest the sidebar looks untouched; a
hog announces itself with exactly one extra line.

n% is per-core (Activity-Monitor style: one pegged core ≈ 100%, four ≈ 400%).

## How CPU is attributed to a workspace — and why the obvious way fails

Every cmux terminal process inherits a CMUX_WORKSPACE_ID env var, so the naive
approach is `ps -Eww | grep CMUX_WORKSPACE_ID`. Two macOS `ps` quirks break that:

  * `ps -E` (show environment) uses the *default* process selection — only
    processes sharing the caller's controlling terminal. A LaunchAgent has NO
    controlling terminal, so from the daemon that set is essentially empty; it
    also drops any detached child (e.g. an `&`/nohup build step).
  * Adding `-A` (all processes) makes `ps` *suppress* environment for almost
    every process. So "-A" and "env" are mutually exclusive here.

So instead we use the process TREE, which is tty-independent and complete:

  1. `ps -Axo pid,ppid,cputime,comm` — ALL processes, cpu-time, parent links.
  2. Find cmux terminal ROOT shells: a shell whose parent is `/usr/bin/login`
     whose parent is the cmux app. Read each root's CMUX_WORKSPACE_ID once via
     `ps -p <pid> -Eww` (explicit -p DOES show env even without a tty), cached.
  3. Attribute every process to the workspace of its nearest root ancestor by
     walking parent links — so deep subagents and detached build steps all count.

Fail-open: while cmux is unreachable it keeps sampling but writes nothing.
Only limitation: a process orphaned to launchd (its intermediate parent died)
loses the tree link and won't be attributed — rare for a live hog.
"""

import fcntl
import json
import os
import re
import signal
import subprocess
import time
from pathlib import Path
from subprocess import DEVNULL, Popen

CMUX = "/Applications/cmux.app/Contents/Resources/bin/cmux"
RUNTIME = Path(os.environ.get("CMUX_MONITOR_DIR", str(Path.home() / ".cache/lki/cmux")))
HEARTBEAT = RUNTIME / "heartbeat"

# Seconds between cpu-time snapshots (interval resolution).
SAMPLE_DT = 3
# Seconds of samples averaged for display: long enough to dilute an agent's
# startup burst to below AMBER, short enough that a real hog shows AMBER in
# ~10s and RED in ~30s.
AVG_WINDOW = 30
# Core-% heat thresholds: AMBER adds color; RED adds a description.
RED, AMBER = 100, 40
# Round display to nearest N% to debounce description writes.
BUCKET = 5
# Max descendants probed per root shell to resolve its workspace.
PROBE_LIMIT = 40
# cmux stores a workspace colour as hex, so we compare against the palette's
# values (cmux.json `workspaceColors.colors` can override these; if you retheme
# Red/Amber, update here or the monitor will rewrite the colour every reconcile).
COLOR_HEX = {"Red": "#C0392B", "Amber": "#7D6608"}

# Consecutive failed cmux reads (~1min) before we exit, so a fresh monitor can
# be started inside the new cmux instance.
MAX_DENIED = 4
DEBUG = os.environ.get("CMUX_CPU_DEBUG") == "1"  # per-cycle heartbeat on stdout


LAST_ERR = ""


def cmux(*args):
    # Blocking read call (rpc). Short timeout: under heavy machine load the cmux
    # socket occasionally stalls a few seconds; cap it so a read can't drag out a
    # sample cycle.
    global LAST_ERR
    try:
        r = subprocess.run([CMUX, *args], capture_output=True, text=True, timeout=6)
        LAST_ERR = f"rc={r.returncode} err={r.stderr.strip()[:120]!r} out={r.stdout.strip()[:60]!r}"
        return r.stdout if r.returncode == 0 else ""
    except Exception as e:
        LAST_ERR = f"EXC {e!r}"
        return ""


def write_desc(wid, desc):
    # desc None => clear the description entirely (no sidebar row for this
    # workspace at all). Fire-and-forget: description writes must NEVER block the
    # sample loop. Under heavy load a single set-description can stall for
    # seconds on the cmux socket; launching it detached (output to /dev/null, no
    # pipe, no wait) keeps sampling responsive. Debouncing upstream keeps the
    # process count tiny.
    args = (
        ["workspace-action", "--action", "clear-description", "--workspace", wid]
        if desc is None
        else ["workspace-action", "--action", "set-description", "--workspace", wid, "--description", desc]
    )
    try:
        return Popen([CMUX, *args], stdout=DEVNULL, stderr=DEVNULL, stdin=DEVNULL)
    except Exception:
        return None


def write_color(wid, color):
    # color None => clear it. Fire-and-forget, same reasoning as write_desc.
    args = (
        ["workspace-action", "--action", "clear-color", "--workspace", wid]
        if color is None
        else ["workspace-action", "--action", "set-color", "--workspace", wid, "--color", color]
    )
    try:
        return Popen([CMUX, *args], stdout=DEVNULL, stderr=DEVNULL, stdin=DEVNULL)
    except Exception:
        return None


def parse_cputime(ct):
    """'[dd-]HH:MM:SS.ss' / 'MM:SS.ss' -> seconds (float), or None."""
    days = 0
    if "-" in ct:
        d, ct = ct.split("-", 1)
        try:
            days = int(d)
        except ValueError:
            return None
    try:
        parts = [float(x) for x in ct.split(":")]
    except ValueError:
        return None
    while len(parts) < 3:
        parts.insert(0, 0.0)
    return days * 86400 + parts[0] * 3600 + parts[1] * 60 + parts[2]


def snapshot_procs():
    """{pid: (ppid, cputime_secs, comm)} for ALL processes (tty-independent)."""
    try:
        out = subprocess.run(
            ["ps", "-Axo", "pid=,ppid=,cputime=,comm="],
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout
    except Exception:
        return {}
    procs = {}
    for line in out.splitlines():
        p = line.split(None, 3)
        if len(p) < 4:
            continue
        secs = parse_cputime(p[2])
        if secs is None:
            continue
        procs[p[0]] = (p[1], secs, p[3])
    return procs


def read_env_wid(pids):
    """{pid: workspace_id} by reading each pid's env via explicit -p (tty-free)."""
    if not pids:
        return {}
    try:
        out = subprocess.run(
            ["ps", "-p", ",".join(pids), "-Eww", "-o", "pid=,command="],
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout
    except Exception:
        return {}
    result = {}
    for line in out.splitlines():
        p = line.split(None, 1)
        if len(p) < 2:
            continue
        m = re.search(r"CMUX_WORKSPACE_ID=([0-9A-Fa-f-]+)", p[1])
        if m:
            result[p[0]] = m.group(1)
    return result


def workspace_of_pid(procs, roots):
    """pid -> workspace_id, by walking parent links up to a known root shell."""
    memo = {}

    def resolve(pid):
        chain = []
        cur = pid
        hops = 0
        while cur in procs and hops < 64:
            if cur in memo:
                w = memo[cur]
                break
            if cur in roots:
                w = roots[cur]
                break
            chain.append(cur)
            cur = procs[cur][0]  # ppid
            hops += 1
        else:
            w = None
        for c in chain:
            memo[c] = w
        return w

    return {pid: resolve(pid) for pid in procs}


def known_workspaces():
    """Return a valid workspace snapshot, or None on RPC/schema failure."""
    try:
        data = json.loads(cmux("rpc", "workspace.list"))
        rows = data["workspaces"]
        if not isinstance(rows, list):
            return None
        result = {}
        for row in rows:
            if not isinstance(row["id"], str) or not row["id"]:
                return None
            result[row["id"]] = (row.get("description"), row.get("custom_color"))
        return result
    except (ValueError, KeyError, TypeError):
        return None


WORKSPACE_TTL = 90
WRITE_TIMEOUT = 10
MAX_WRITES = 8


def refresh_seen(seen, snapshot, now):
    """Tolerate partial snapshots but eventually forget closed workspaces."""
    if snapshot is not None:
        seen.update(dict.fromkeys(snapshot, now))
    for wid in list(seen):
        if now - seen[wid] >= WORKSPACE_TTL:
            del seen[wid]


class PendingWrites:
    """Bound RPC children and serialize writes to each workspace field."""

    def __init__(self):
        self.pending = {}

    def submit(self, key, writer, wid, value, cache, cached_value, now):
        if key in self.pending or len(self.pending) >= MAX_WRITES:
            return
        process = writer(wid, value)
        if process is not None:
            self.pending[key] = (process, now, cache, cached_value)

    def reap(self, now):
        for key, (process, started, cache, value) in list(self.pending.items()):
            status = process.poll()
            if status is None and now - started >= WRITE_TIMEOUT:
                process.kill()
                # Keep the slot occupied until a later poll reaps the child.
                continue
            if status is not None:
                if status == 0:
                    cache[key[0]] = value
                del self.pending[key]

    def close(self):
        for process, _, _, _ in self.pending.values():
            if process.poll() is None:
                process.kill()
            process.wait()
        self.pending.clear()


def description_for(pct):
    """The one extra sidebar line, or None for no line at all.

    Colour already says "this one is hot" at zero cost, so a line is spent only
    on a workspace pegging a whole core (>= RED) — the case where you actually
    want the number. Anything below is colour-only.
    """
    if pct >= RED:
        return f"\U0001f7e5 {pct}%"
    return None


def color_for(pct):
    """Heat colour for the workspace row, or None to clear it.

    This is the zero-space signal: cmux paints it as a rail/tint on the row
    itself (workspaceColors.indicatorStyle), costing no extra line.
    """
    if pct >= RED:
        return "Red"
    if pct >= AMBER:
        return "Amber"
    return None


def find_roots(procs, root_cache):
    """Refresh the {root_shell_pid: workspace_id} cache from the current tree.

    The root shell's OWN environment is often unreadable: cmux spawns it through
    setuid `/usr/bin/login`, and `ps -E` then returns no environment for it (this
    varies with how the surface was started — a restored `-/bin/zsh` resume shell
    hides it where a plain bash one did not). So don't trust the root; probe its
    descendants and take the first that exposes CMUX_WORKSPACE_ID. Every process
    under one root belongs to the same workspace, so any hit resolves the root.
    """
    cmux_app = {pid for pid, (pp, ct, comm) in procs.items() if comm.endswith("cmux.app/Contents/MacOS/cmux")}
    logins = {pid for pid, (pp, ct, comm) in procs.items() if comm == "/usr/bin/login" and pp in cmux_app}
    roots = {pid for pid, (pp, ct, comm) in procs.items() if pp in logins}

    for pid in list(root_cache):  # drop roots whose shell has exited
        if pid not in roots:
            del root_cache[pid]

    unknown = [r for r in roots if r not in root_cache]
    if unknown:
        children = {}
        for pid, (pp, _ct, _comm) in procs.items():
            children.setdefault(pp, []).append(pid)
        for r in unknown:
            probe, stack = [], [r]
            while stack and len(probe) < PROBE_LIMIT:
                cur = stack.pop()
                probe.append(cur)
                stack.extend(children.get(cur, ()))
            env = read_env_wid(probe)
            if env:
                root_cache[r] = next(iter(env.values()))
    return root_cache


KNOWN_REFRESH = 15  # seconds between workspace-list refreshes (cheap, slow-changing)


def rolling_percent(history, start, end, cpu_seconds):
    """Weight partial intervals by overlap, including samples longer than the window."""
    history.append((start, end, cpu_seconds))
    cutoff = end - AVG_WINDOW
    history[:] = [(a, b, v) for a, b, v in history if b > cutoff]
    total = sum(v * (b - max(a, cutoff)) / (b - a) for a, b, v in history if b > a)
    return 100.0 * total / AVG_WINDOW


def main(writes):
    prev = {pid: ct for pid, (pp, ct, comm) in snapshot_procs().items()}
    previous_at = time.monotonic()
    root_cache = {}  # root_shell_pid -> workspace_id (stable, cached)
    history = {}  # workspace_id -> [(interval_start, interval_end, cpu_seconds)]
    seen, known_at = {}, float("-inf")
    reachable = False
    denied = 0  # consecutive failed cmux reads
    written_color = {}  # workspace_id -> last colour hex we believe cmux holds
    written = {}

    while True:
        time.sleep(SAMPLE_DT)
        procs = snapshot_procs()
        now = time.monotonic()
        writes.reap(now)
        roots = find_roots(procs, root_cache)
        pid_wid = workspace_of_pid(procs, roots)

        # Δcpu-time summed per workspace, in CPU-SECONDS — deliberately not a
        # percentage. Dividing by the nominal SAMPLE_DT here used to inflate
        # readings exactly when the machine was busiest: the loop's own work
        # (ps, cmux rpc) stretches a tick well past 3s under load, so a real
        # 300% read as 600%. Cpu-seconds carry their own time weighting; the
        # display step divides by the window span instead.
        agg = {}
        for pid, (_pp, ct, _comm) in procs.items():
            wid = pid_wid.get(pid)
            if wid is None or pid not in prev:
                continue
            dc = ct - prev[pid]
            if dc > 0:
                agg[wid] = agg.get(wid, 0.0) + dc
        prev = {pid: ct for pid, (pp, ct, comm) in procs.items()}

        # workspace membership changes slowly — refresh on a timer, not every tick.
        # Reconcile our sent-cache against cmux's ACTUAL descriptions: if a write
        # was dropped (socket contention) or an external change landed, trust
        # reality so the next tick re-sends. Self-heals fire-and-forget failures.
        if now - known_at >= KNOWN_REFRESH:
            ws = known_workspaces()
            reachable = ws is not None
            if not reachable:
                denied += 1
                if denied >= MAX_DENIED:
                    return
            else:
                denied = 0
                HEARTBEAT.touch()
                for wid, (actual_desc, actual_color) in ws.items():
                    written[wid] = actual_desc
                    written_color[wid] = actual_color
            refresh_seen(seen, ws, now)
            known_at = now

        ids = set(seen)
        for store in (history, written, written_color):
            for k in list(store):
                if k not in ids:
                    del store[k]

        for wid in ids:
            hist = history.setdefault(wid, [])
            avg = rolling_percent(hist, previous_at, now, agg.get(wid, 0.0))
            pct = int(round(avg / BUCKET) * BUCKET)
            desc = description_for(pct)
            color = color_for(pct)
            want_hex = COLOR_HEX.get(color)
            if reachable and written.get(wid) != desc:
                writes.submit((wid, "description"), write_desc, wid, desc, written, desc, now)
            if reachable and written_color.get(wid) != want_hex:
                writes.submit((wid, "color"), write_color, wid, color, written_color, want_hex, now)

        previous_at = now

        if DEBUG:
            print(
                f"roots={len(roots)} active={len(ids)} pending={len(writes.pending)} "
                f"reachable={reachable} lastcmux={LAST_ERR}",
                flush=True,
            )


def run_monitor():
    # The kernel releases flock on crash/exit. Never unlink the lock file:
    # replacing its inode would let two processes both acquire a lock.
    RUNTIME.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (RUNTIME / "monitor.lock").open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        lock.seek(0)
        lock.truncate()
        lock.write(str(os.getpid()))
        lock.flush()

        def stop(_signum, _frame):
            raise SystemExit(0)

        signal.signal(signal.SIGTERM, stop)
        writes = PendingWrites()
        try:
            main(writes)
        finally:
            writes.close()
            HEARTBEAT.unlink(missing_ok=True)


if __name__ == "__main__":
    run_monitor()
