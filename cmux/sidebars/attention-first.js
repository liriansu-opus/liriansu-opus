// Attention first: live, per-terminal triage for cmux custom sidebars.
// Install and rollback instructions: ../README.md.
// The JS host has no persistent storage. Local marks reset on reload.
// No terminal input, permissions, or workspace status is modified.
// Snooze marks the corresponding native notifications read.

function createAttentionModel() {
  const records = new Map();
  let current = [];
  let open = null;
  const epoch = (value) => (Number.isFinite(Number(value)) && Number(value) > 0 ? Number(value) : 0);
  const directoryName = (value) => {
    const trimmed = String(value || "").trim();
    if (!trimmed) return "";
    const path = trimmed.replace(/\/+$/, "");
    if (!path) return "/";
    if (path === "~" || path === "/root" || /^\/(Users|home)\/[^/]+$/.test(path)) return "~";
    return path.split("/").pop();
  };
  const provider = (agent) => {
    const kind = String(agent.kind || agent.name || "").toLowerCase();
    if (kind.includes("claude")) return "Claude";
    if (kind.includes("codex")) return "Codex";
    if (kind.includes("opencode")) return "OpenCode";
    if (kind === "omp" || kind === "pi") return "Pi";
    return "Agent";
  };

  function update(workspaces, now) {
    now = epoch(now);
    const output = [];
    for (const w of Array.isArray(workspaces) ? workspaces : []) {
      if (!w || !w.id) continue;
      const available = (Array.isArray(w.agents) ? w.agents : []).filter((a) => a && a.id);
      const tabs = Array.isArray(w.tabs) ? w.tabs : [];
      const terminalGroups = new Map();
      const isWorking = (a) => a.status === "working" || (a.children || []).some((c) => c.running);
      for (const agent of available) {
        const tab = tabs.find((t) => t.id === agent.panelId || (agent.surfaceId && t.surfaceId === agent.surfaceId));
        const id = (tab && tab.id) || agent.panelId || agent.surfaceId || agent.id;
        if (!terminalGroups.has(id)) terminalGroups.set(id, []);
        terminalGroups.get(id).push(agent);
      }
      const sessions = terminalGroups.size ? Array.from(terminalGroups.entries()) : [["workspace", []]];
      for (const [terminalId, peers] of sessions) {
        // Hooks also register helper CLIs on their parent's terminal. Keep one
        // row and one lifecycle per terminal, including while its owner pauses.
        const recordKey = w.id + ":terminal:" + terminalId;
        let rec = records.get(recordKey);
        const rank = (a) => a.status === "needs_input" ? 5
          : rec && rec.pending && rec.pending.lane === "need" && rec.pending.owner === a.id && a.status !== "working" ? 4
          : isWorking(a) ? 3 : a.status === "idle" ? 2 : a.status === "ended" ? 1 : 0;
        const a = peers.slice().sort((a, b) => rank(b) - rank(a)
          || epoch(b.lastActivityAt) - epoch(a.lastActivityAt) || a.id.localeCompare(b.id))[0] || null;
        const key = recordKey;
        const tab = a ? tabs.find((t) => t.id === a.panelId || (a.surfaceId && t.surfaceId === a.surfaceId)) : null;
        const directory = (a && a.directory) || (tab && tab.directory)
          || (!a && (tabs.find((t) => t.focused) || {}).directory) || w.directory || "";
        const runningIds = new Set();
        for (const peer of peers) {
          if (peer !== a && isWorking(peer)) runningIds.add(peer.id);
          for (const child of peer.children || []) if (child && child.running) runningIds.add(child.id);
        }
        const children = runningIds.size;
        const backgroundActive = children > 0 || (peers.some(isWorking) && peers.some((p) => p.status === "idle"));
        const disconnected = !!(w.remote && w.remote.target && w.remote.connected === false);
        const raw = a ? a.status : "unknown";
        const phase = disconnected ? "unknown" : raw === "needs_input" ? "need"
          : raw === "working" || children > 0 ? "working"
          : raw === "idle" || raw === "ended" ? "idle" : "unknown";
        const stamp = a ? epoch(a.sinceEpoch) || epoch(a.lastActivityAt) : 0;
        if (!rec) {
          rec = { phase: null, stamp: 0, pending: null, snoozed: false, reviewed: false, started: now };
          records.set(recordKey, rec);
        }
        const newRequest = phase === "need" && (rec.phase !== "need" || rec.pending?.owner !== a.id || (stamp && stamp !== rec.stamp));
        if (newRequest) {
          rec.pending = { lane: "need", at: stamp || now, owner: a.id };
          rec.snoozed = false;
          rec.reviewed = false;
        } else if (phase === "working" && (!rec.pending || rec.pending.lane !== "need"
          || peers.some((peer) => peer.id === rec.pending.owner && peer.status === "working"))) {
          // A real new turn clears the previous request and any local disposition.
          rec.pending = null;
          rec.snoozed = false;
          rec.reviewed = false;
        } else if (rec.phase === "working" && phase === "idle" && !(rec.pending && rec.pending.lane === "need")) {
          // Review the response, not a claim that the task succeeded.
          rec.pending = { lane: "review", at: now };
          rec.snoozed = false;
          rec.reviewed = false;
        }
        if (phase !== rec.phase) rec.started = stamp || now;
        rec.phase = phase;
        rec.stamp = stamp;
        rec.seenAt = now;
        // Loss of a connection must be visible even during a snooze.
        const lane = phase === "unknown" ? (rec.pending && rec.pending.lane === "need" ? "need" : "unknown") : rec.pending
          ? rec.snoozed ? "snoozed" : rec.pending.lane
          : rec.reviewed && phase === "idle" ? "done" : phase;
        let reason = "No agent session";
        if (lane === "need") reason = phase === "unknown" ? "Status unknown · request still unresolved" : phase === "need" ? "Waiting for your input" : "Previous request still unresolved";
        if (lane === "review") reason = raw === "ended" ? "Session ended · check the outcome" : "Turn stopped · review the response";
        if (lane === "working") reason = children ? children + " background task" + (children === 1 ? "" : "s") + " running" : "Working · no action needed";
        if (lane === "idle" && a) reason = raw === "ended" ? "Session ended · outcome unverified" : "Idle · no pending request observed";
        if (lane === "snoozed") reason = "Saved for later · restore when ready";
        if (lane === "unknown") reason = rec.pending ? "Status unknown · request still unresolved" : disconnected ? "Connection unavailable" : a ? "No reliable agent status" : "Agent status unavailable";
        if (lane === "done") reason = "Reviewed by you";
        output.push({
          // tabs.surfaceId is the public surface.* target. Some host versions
          // expose an internal tab UUID in agents.surfaceId instead.
          key, workspaceId: w.id, surfaceId: tab && tab.surfaceId ? tab.surfaceId : a && (a.panelId || a.surfaceId),
          title: w.title || "Untitled workspace", agent: a ? provider(a) : "Workspace",
          directory, directoryName: directoryName(directory),
          branch: w.branch || "", lane, reason, phase, children, backgroundActive,
          selected: !!w.selected && (tab ? !!tab.focused : sessions.length === 1),
          // The row also represents its workspace: notifications on another
          // terminal or a browser panel must not disappear from this view.
          unread: Number(w.unread) > 0 || tabs.some((t) => t.hasUnread),
          at: rec.pending ? rec.pending.at : rec.started,
          index: Number.isFinite(w.index) ? w.index : 0,
          hasAgent: !!a, unresolved: !!rec.pending,
          multi: sessions.length > 1,
          // Stable panel label disambiguates terminals without showing prompts.
          panel: sessions.length > 1 ? (tab && tab.title ? tab.title : a ? provider(a) : "Terminal") : "",
        });
      }
    }
    // Focus lands asynchronously and may pass through a sibling terminal, so a
    // row closes only when focus leaves after having reached it.
    const focused = output.find((r) => r.selected);
    if (open && focused) {
      if (focused.key === open.key) open.reached = true;
      else if (open.reached) open = null;
    }
    for (const r of output) r.open = !!open && open.key === r.key;
    current = output;
    const live = new Set(output.map((r) => r.key));
    for (const [key, rec] of records) {
      if (!live.has(key) && (now - rec.seenAt > 300 || records.size > 512)) records.delete(key);
    }
    return output;
  }

  function act(key, action, now) {
    const row = current.find((r) => r.key === key);
    const rec = row && records.get(row.key);
    if (!row || !rec) return "This session is no longer available.";
    if (action === "snooze") {
      if (!["need", "review"].includes(row.lane)) return "Only pending requests can be snoozed.";
      rec.snoozed = true;
      if (open && open.key === key) open = null;
      return "Saved in Snoozed. Restore it whenever you're ready.";
    }
    if (action === "unsnooze") {
      rec.snoozed = false;
      return "Restored to the main list.";
    }
    if (action === "review") {
      if (row.phase !== "idle") return "Wait for the agent to stop before marking it for review.";
      if (rec.pending && rec.pending.lane === "need") return "Reply in the terminal to resolve the pending request.";
      rec.pending = { lane: "review", at: epoch(now) };
      rec.reviewed = false;
      rec.snoozed = false;
      return "Added to Ready for review.";
    }
    if (action === "accept") {
      if (row.lane !== "review" || row.phase !== "idle") return "Only an idle response awaiting review can be marked reviewed.";
      rec.pending = null;
      rec.reviewed = true;
      rec.snoozed = false;
      return "Marked reviewed. New work will clear this mark.";
    }
    if (action === "resolve") {
      if (row.phase !== "idle" || !rec.pending || rec.pending.lane !== "need") return "Resolve active input requests in the terminal.";
      rec.pending = null;
      rec.reviewed = true;
      rec.snoozed = false;
      return "Marked resolved by you.";
    }
    return "No action taken.";
  }

  function openActions(key) {
    open = { key, reached: false };
  }

  return { update, act, openActions };
}

function installAttentionSidebar() {
  const model = createAttentionModel();
  const [revision, setRevision] = signal(0);
  const [query, setQuery] = signal("");
  const [filter, setFilter] = signal("all");
  const [includeReviews, setIncludeReviews] = signal(true);
  const [compact, setCompact] = signal(true);
  const [grouped, setGrouped] = signal(false);
  const [context, setContext] = signal(false);
  const [message, setMessage] = signal("");
  const [collapsed, setCollapsed] = signal(["idle", "snoozed", "done"]);
  const clock = () => Number(data.clock()?.epoch) || 0;
  const rows = computed(() => {
    revision();
    return model.update(data.workspaces() ?? [], clock());
  });
  const needsYou = (r) => r.lane === "need" || (includeReviews() && r.lane === "review");
  const visible = computed(() => {
    const term = query().trim().toLowerCase();
    return rows().filter((r) => (!term || [r.title, r.agent, r.panel, r.reason, r.branch, r.directory, r.directoryName].join(" ").toLowerCase().includes(term))
      && (filter() === "all" || (filter() === "need" ? needsYou(r) : r.lane === "working")));
  });
  const meta = {
    need: { label: "NEEDS YOU", icon: "hand.raised.fill", color: "#D9943D" },
    review: { label: "READY FOR REVIEW", icon: "checkmark.bubble", color: "#72A886" },
    working: { label: "RUNNING", icon: "arrow.triangle.2.circlepath", color: "#669BC6" },
    idle: { label: "IDLE", icon: "pause.circle", color: "secondary" },
    snoozed: { label: "SNOOZED", icon: "clock", color: "secondary" },
    unknown: { label: "UNAVAILABLE", icon: "questionmark.circle", color: "#A18CB8" },
    done: { label: "REVIEWED", icon: "checkmark.circle", color: "secondary" },
  };
  const order = ["need", "review", "working", "unknown", "snoozed", "idle", "done"];
  // Match cmux's native unread queue (including Jump to Unread). Local review
  // marks and background work must neither create nor hide a notification dot.
  const highlighted = (r) => r.unread;
  function rowBackground(r) {
    if (r.lane === "need") return r.selected ? "#D9943D2A" : "#D9943D14";
    if (highlighted(r)) return r.selected ? "#5BA7F738" : "#5BA7F71C";
    return r.selected ? "#78A78C24" : null;
  }
  function elapsed(r) {
    if (r.lane === "snoozed") return "";
    if (!r.at || !clock()) return "";
    const secs = Math.max(0, clock() - r.at);
    return secs < 60 ? "now" : secs < 3600 ? Math.floor(secs / 60) + "m" : Math.floor(secs / 3600) + "h";
  }
  function jump(key) {
    const r = rows().find((item) => item.key === key);
    if (!r) { setMessage("This session is no longer available."); return; }
    model.openActions(key);
    setRevision(revision() + 1);
    cmux("workspace.select", { workspace_id: r.workspaceId });
    if (r.surfaceId) cmux("surface.focus", { workspace_id: r.workspaceId, surface_id: r.surfaceId });
  }
  function perform(key, action) {
    rows(); // Reconcile live state before accepting a local disposition.
    setMessage(model.act(key, action, clock()));
    setRevision(revision() + 1);
    const r = rows().find((item) => item.key === key);
    if (action === "snooze" && r && r.lane === "snoozed") {
      if (!collapsed().includes("snoozed")) setCollapsed([...collapsed(), "snoozed"]);
      // Keep Jump to Unread from returning to a request the user put away.
      const target = { tab_id: r.workspaceId };
      if (r.multi && r.surfaceId) target.surface_id = r.surfaceId;
      cmux("notification.mark_read", target);
    }
  }
  function sectionRows(lane) {
    return visible().filter((r) => r.lane === lane).sort((a, b) =>
      (["need", "review"].includes(lane) ? a.at - b.at : a.index - b.index) || a.key.localeCompare(b.key));
  }
  function orderedRows() {
    return visible().slice().sort((a, b) => a.index - b.index || a.key.localeCompare(b.key));
  }
  function shortcut(r) {
    const last = Math.max(...rows().map((item) => item.index));
    if (r.index === last && last >= 8) return "⌘9";
    return r.index < 8 ? "⌘" + (r.index + 1) : "";
  }
  function actions(r) {
    if (!r.open) return [];
    const out = [];
    if (["need", "review"].includes(r.lane)) out.push({ id: "snooze", label: "Snooze" });
    if (r.lane === "snoozed") out.push({ id: "unsnooze", label: "Unsnooze" });
    if (r.lane === "review") out.push({ id: "accept", label: "Mark reviewed" });
    if (["idle", "done"].includes(r.lane)) out.push({ id: "review", label: "Review later" });
    if (r.lane === "need" && r.phase === "idle") out.push({ id: "resolve", label: "Mark resolved" });
    return out;
  }
  function sessionRow(r) {
    return VStack({ spacing: 2 }, [
      HStack({ spacing: 8 }, [
        Image(() => meta[r().lane].icon).font(12).color(() => meta[r().lane].color).fixedSize(),
        VStack({ spacing: 2 }, [
          Text(() => r().title).font(12).weight(() => highlighted(r()) ? "semibold" : "medium").lineLimit(1).truncation("tail"),
          Text(() => ({ need: "Needs you", review: "Ready for review", working: "Running", idle: "Idle", snoozed: "Snoozed", unknown: r().hasAgent ? "Unavailable" : "No agent", done: "Reviewed" })[r().lane] + " · " + r().agent + (r().panel ? " / " + r().panel : ""))
            .font(10).color(() => r().lane === "need" ? meta.need.color : "secondary").lineLimit(() => compact() ? 1 : 2),
          ForEach({ items: () => r().directoryName ? [r().directoryName] : [], key: (name) => name }, (name) =>
            HStack({ spacing: 4 }, [
              Image("folder").font(9).color("secondary").fixedSize(),
              Text(name).font(10).color("secondary").lineLimit(1).truncation("tail").marquee(),
            ])),
          ForEach({ items: () => compact() ? [] : [r().reason], key: (reason) => reason }, (reason) =>
            Text(reason).font(10).color("secondary").lineLimit(2)),
          ForEach({ items: () => context() && r().branch ? [r().branch] : [], key: (branch) => branch }, (branch) =>
            Text(branch).font(9).color("tertiary").lineLimit(1)),
        ]).frame({ maxWidth: "infinity" }).layoutPriority(1),
        VStack({ spacing: 2 }, [
          HStack({ spacing: 4 }, [
            ForEach({ items: () => highlighted(r()) ? ["attention"] : [], key: (key) => key }, () =>
              Circle({ size: 7 }).fill("#73B5FF").padding(3).background("#73B5FF24").cornerRadius(7).fixedSize()),
            Text(() => shortcut(r())).font(9).monospaced().color("tertiary").fixedSize(),
          ]),
          Text(() => elapsed(r())).font(9).monospaced().color("secondary").fixedSize(),
        ]).fixedSize().layoutPriority(2),
      ]),
      ForEach({ items: () => actions(r()).length ? [r().key] : [], key: (key) => key }, () =>
        HStack({ spacing: 6 }, [
          ForEach({ items: () => actions(r()), key: (item) => item.id }, (item) =>
            Button(() => item().label, () => perform(r().key, item().id)).font(10).color("accent")),
        ])),
    ])
      .paddingHorizontal(7).paddingVertical(() => compact() ? 4 : 7)
      .cornerRadius(5)
      .background(() => rowBackground(r()))
      .hoverBackground("#7f7f7f1c")
      .frame({ maxWidth: "infinity" })
      .onTap(() => jump(r().key))
      .contextMenu([
        Button("Open terminal", () => jump(r().key)),
        Button(() => r().lane === "snoozed" ? "Unsnooze" : "Snooze", () => perform(r().key, r().lane === "snoozed" ? "unsnooze" : "snooze")),
        Button("Mark for review", () => perform(r().key, "review")),
        Button("Mark reviewed", () => perform(r().key, "accept")),
      ]);
  }
  function stat(label, value, count) {
    return HStack({ spacing: 4 }, [
      Text(count).font(11).weight("semibold").color(value === "need" ? meta.need.color : "primary").fixedSize(),
      Text(label).font(10).color("secondary").fixedSize(),
    ]).paddingHorizontal(6).paddingVertical(4).cornerRadius(4).fixedSize()
      .background(() => filter() === value ? "#78A78C22" : null)
      .hoverBackground("#7f7f7f1c")
      .onTap(() => setFilter(filter() === value && value !== "all" ? "all" : value));
  }
  sidebar(() => VStack({ spacing: 5 }, [
    HStack({ spacing: 8 }, [
      Text("Attention").font(14).weight("semibold").lineLimit(1).fixedSize().layoutPriority(2),
      Spacer({ minLength: 0 }),
      Menu("Options", [
        Button(() => grouped() ? "Use keyboard order" : "Group by status", () => setGrouped(!grouped())),
        Button(() => includeReviews() ? "Exclude reviews from Needs you" : "Include reviews in Needs you", () => setIncludeReviews(!includeReviews())),
        Button(() => compact() ? "Comfortable rows" : "Compact rows", () => setCompact(!compact())),
        Button(() => context() ? "Hide branch details" : "Show branch details", () => setContext(!context())),
        Button("Expand all sections", () => setCollapsed([])),
        Button("Collapse quiet sections", () => setCollapsed(["idle", "snoozed", "done"])),
      ]).font(10).color("secondary").fixedSize().layoutPriority(2),
    ]).paddingHorizontal(7),
    HStack({ spacing: 2 }, [
      stat("Needs you", "need", () => String(rows().filter(needsYou).length)),
      stat("Run", "working", () => String(rows().filter((r) => r.lane === "working").length)),
      stat("All", "all", () => String(rows().length)),
    ]),
    TextField("", { placeholder: "Search…", autofocus: false, onEdit: setQuery, onCancel: () => setQuery("") }).font(11).paddingHorizontal(7),
    Divider(),
    ForEach({ items: () => grouped() ? [] : orderedRows().filter((r) => r.lane !== "snoozed").slice(0, 100), key: (r) => r.key }, sessionRow),
    ForEach({ items: () => (grouped() ? order : ["snoozed"]).filter((lane) => sectionRows(lane).length), key: (lane) => lane }, (lane) =>
      VStack({ spacing: 1 }, [
        HStack({ spacing: 6 }, [
          Image(() => collapsed().includes(lane()) ? "chevron.right" : "chevron.down").font(8).color("secondary"),
          Text(() => meta[lane()].label).font(9).weight("semibold").color(() => meta[lane()].color).lineLimit(1),
          Spacer({ minLength: 0 }),
          Text(() => String(sectionRows(lane()).length)).font(9).monospaced().color("secondary").fixedSize(),
        ]).paddingHorizontal(7).paddingVertical(4).onTap(() => {
          const key = lane();
          setCollapsed(collapsed().includes(key) ? collapsed().filter((v) => v !== key) : [...collapsed(), key]);
        }),
        ForEach({ items: () => collapsed().includes(lane()) ? [] : sectionRows(lane()).slice(0, 100), key: (r) => r.key }, sessionRow),
      ])
    ),
    ForEach({ items: () => visible().length ? [] : ["empty"], key: (key) => key }, () =>
      Text(() => query().trim() ? "No matching sessions." : filter() === "need" ? "Nothing needs you right now." : "No sessions in this view.")
        .font(11).color("secondary").paddingHorizontal(7)),
    ForEach({ items: () => message() ? ["message"] : [], key: (key) => key }, () =>
      Text(message).font(10).color("secondary").lineLimit(3).paddingHorizontal(7)),
    Text("Local marks reset on reload").font(9).color("tertiary").paddingHorizontal(7).paddingVertical(3),
  ]).paddingHorizontal(5).paddingVertical(4), { surface: "glass" });
}

if (typeof sidebar === "function") installAttentionSidebar();
if (typeof module !== "undefined") module.exports = { createAttentionModel };
