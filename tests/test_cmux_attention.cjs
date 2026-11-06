const assert = require('node:assert/strict');
const { test } = require('node:test');
const { createAttentionModel } = require('../cmux/sidebars/attention-first.js');

const session = (status, extra = {}) => ({
  id: 'agent-1', kind: 'codex', status, sinceEpoch: 1000, lastActivityAt: 1000,
  panelId: 'panel-1', surfaceId: 'surface-1', ...extra,
});
const workspace = (agents, extra = {}) => ({
  id: 'workspace-1', title: 'My project', index: 0, selected: true, agents,
  tabs: [{ id: 'panel-1', surfaceId: 'surface-1', focused: true, hasUnread: true }], ...extra,
});
const update = (model, agent, now = 1100, wsExtra = {}) => model.update([workspace([agent], wsExtra)], now)[0];
const key = 'workspace-1:terminal:panel-1';

test('a cold idle session and an unread message do not imply a pending task', () => {
  const model = createAttentionModel();
  const row = update(model, session('idle'), 1100, {
    status: 'review', unread: 4, pr: { status: 'open' },
    tabs: [{ id: 'panel-1', surfaceId: 'surface-1', focused: true, hasUnread: false }],
  });
  assert.equal(row.lane, 'idle');
  assert.equal(row.unread, true);
  assert.equal(row.unresolved, false);
});

test('selection and read receipts do not dismiss a request, even if the host becomes idle', () => {
  const model = createAttentionModel();
  update(model, session('needs_input'));
  const row = update(model, session('idle'), 1200, {
    selected: false, tabs: [{ id: 'panel-1', surfaceId: 'surface-1', focused: false, hasUnread: false }],
  });
  assert.equal(row.lane, 'need');
  assert.equal(row.at, 1000);
  assert.equal(row.unread, false);
});

test('a real resumed turn clears a pending request', () => {
  const model = createAttentionModel();
  update(model, session('needs_input'));
  const row = update(model, session('working', { sinceEpoch: 1200 }), 1200);
  assert.equal(row.lane, 'working');
  assert.equal(row.unresolved, false);
});

test('a background child alone cannot clear a previous input request', () => {
  const model = createAttentionModel();
  update(model, session('needs_input'));
  const row = update(model, session('idle', { children: [{ running: true }] }), 1200);
  assert.equal(row.lane, 'need');
  assert.equal(row.unresolved, true);
  assert.equal(update(model, session('idle', { children: [{ running: false }] }), 1300).lane, 'need');
});

test('background work prevents a premature review, including an ended parent', () => {
  const model = createAttentionModel();
  update(model, session('working'));
  assert.equal(update(model, session('idle', { children: [{ running: true }] }), 1200).lane, 'working');
  assert.equal(update(model, session('ended', { children: [{ running: true }] }), 1250).lane, 'working');
  const row = update(model, session('ended', { children: [{ running: false }] }), 1300);
  assert.equal(row.lane, 'review');
  assert.match(row.reason, /check the outcome/);
});

test('snooze has no timer and stays saved until restored', () => {
  const model = createAttentionModel();
  update(model, session('needs_input'));
  model.act(key, 'snooze', 1100);
  assert.equal(update(model, session('needs_input'), 1999).lane, 'snoozed');
  assert.equal(update(model, session('needs_input'), 2000).lane, 'snoozed');
  assert.equal(update(model, session('needs_input'), 1100 + 30 * 86400).lane, 'snoozed');
  model.act(key, 'unsnooze', 1100 + 30 * 86400);
  assert.equal(update(model, session('needs_input'), 1101 + 30 * 86400).lane, 'need');
});

test('a new needs-input event immediately wakes a snoozed session', () => {
  const model = createAttentionModel();
  update(model, session('needs_input'));
  model.act(key, 'snooze', 1100);
  const row = update(model, session('needs_input', { sinceEpoch: 1200 }), 1201);
  assert.equal(row.lane, 'need');
  assert.equal(row.at, 1200);
});

test('routine activity updates do not replace a request when its sinceEpoch is unchanged', () => {
  const model = createAttentionModel();
  update(model, session('needs_input'));
  model.act(key, 'snooze', 1100);
  assert.equal(update(model, session('needs_input', { lastActivityAt: 1250 }), 1250).lane, 'snoozed');
});

test('manual review acceptance is per terminal, and new work clears it', () => {
  const model = createAttentionModel();
  const second = session('needs_input', { id: 'agent-2', panelId: 'panel-2', surfaceId: 'surface-2' });
  model.update([workspace([session('working'), second])], 1100);
  model.update([workspace([session('idle'), second])], 1200);
  model.act(key, 'accept', 1200);
  const rows = model.update([workspace([session('idle'), second])], 1201);
  assert.equal(rows[0].lane, 'done');
  assert.equal(rows[1].lane, 'need');
  assert.equal(update(model, session('working', { sinceEpoch: 1300 }), 1300).lane, 'working');
});

test('a running agent or live input request cannot be marked reviewed', () => {
  const model = createAttentionModel();
  update(model, session('working'));
  assert.match(model.act(key, 'accept', 1100), /Only an idle response/);
  assert.match(model.act(key, 'review', 1100), /Wait/);
  update(model, session('needs_input'));
  assert.match(model.act(key, 'resolve', 1100), /terminal/);
  assert.equal(update(model, session('needs_input')).lane, 'need');
});

test('unknown signals and connection loss are visible, even during a snooze', () => {
  const model = createAttentionModel();
  assert.equal(update(model, session('unrecognized')).lane, 'unknown');
  update(model, session('needs_input'));
  model.act(key, 'snooze', 1100);
  const row = update(model, session('needs_input'), 1200, { remote: { target: 'my-host', connected: false } });
  assert.equal(row.lane, 'need');
  assert.match(row.reason, /unknown/);
});

test('a missed snapshot does not permanently lose the pending request', () => {
  const model = createAttentionModel();
  update(model, session('needs_input'));
  model.update([], 1110);
  assert.match(model.act(key, 'snooze', 1110), /no longer available/);
  assert.equal(update(model, session('idle'), 1120).lane, 'need');
});

test('workspaces without agents remain reachable and do not manufacture reviews', () => {
  const model = createAttentionModel();
  const row = model.update([workspace([], { status: 'review' })], 1100)[0];
  assert.equal(row.workspaceId, 'workspace-1');
  assert.equal(row.lane, 'unknown');
  assert.equal(row.hasAgent, false);
});

test('an ended session is hidden when another agent owns the same terminal', () => {
  const model = createAttentionModel();
  const rows = model.update([workspace([
    session('ended', { id: 'previous-agent', kind: 'claude' }), session('working'),
  ])], 1100);
  assert.equal(rows.length, 1);
  assert.equal(rows[0].agent, 'Codex');
  assert.equal(rows[0].multi, false);
});

test('idle helper records on the same terminal do not create a second review row', () => {
  const model = createAttentionModel();
  const helper = (status) => session(status, { id: 'helper', kind: 'claude', lastActivityAt: 1200 });
  model.update([workspace([session('working'), helper('working')])], 1100);
  const rows = model.update([workspace([session('working'), helper('idle')])], 1200);
  assert.equal(rows.length, 1);
  assert.equal(rows[0].lane, 'working');
  assert.equal(rows[0].agent, 'Codex');
  assert.equal(rows[0].unresolved, false);
});

test('a paused parent and working helper share one row until all terminal work stops', () => {
  const model = createAttentionModel();
  const helper = (status) => session(status, {
    id: 'helper', kind: 'claude', lastActivityAt: 1200, directory: '/work/helper-checkout',
  });
  const ws = (agents) => workspace(agents, {
    tabs: [{ id: 'panel-1', surfaceId: 'surface-1', focused: true, hasUnread: true, directory: '/work/main-project' }],
  });
  model.update([ws([session('working'), helper('idle')])], 1100);
  const rows = model.update([ws([session('idle'), helper('working')])], 1200);
  assert.equal(rows.length, 1);
  assert.equal(rows[0].lane, 'working');
  assert.equal(rows[0].backgroundActive, true);
  assert.equal(rows[0].unread, true);
  assert.equal(rows[0].directoryName, 'helper-checkout');
  const completed = model.update([ws([session('idle'), helper('ended')])], 1300);
  assert.equal(completed.length, 1);
  assert.equal(completed[0].key, rows[0].key);
  assert.equal(completed[0].lane, 'review');
  assert.equal(completed[0].backgroundActive, false);
  model.act(completed[0].key, 'accept', 1300);
  assert.equal(model.update([ws([session('idle'), helper('ended')])], 1301)[0].lane, 'done');
});

test('a helper cannot clear a different agent input request, even with nested children or a missing owner', () => {
  const model = createAttentionModel();
  const helper = session('working', { id: 'helper', lastActivityAt: 1200 });
  model.update([workspace([session('needs_input'), helper])], 1100);
  const paused = session('idle', { children: [{ id: 'nested-child', running: true }] });
  assert.equal(model.update([workspace([paused, helper])], 1200)[0].lane, 'need');
  assert.equal(model.update([workspace([helper])], 1250)[0].lane, 'need');
  assert.equal(model.update([workspace([session('working'), helper])], 1300)[0].lane, 'working');
});

test('a helper input request is visible on its terminal without creating another row', () => {
  const model = createAttentionModel();
  const helper = session('needs_input', { id: 'helper' });
  const rows = model.update([workspace([session('working'), helper])], 1100);
  assert.equal(rows.length, 1);
  assert.equal(rows[0].lane, 'need');
  assert.equal(rows[0].unresolved, true);
});

test('surface identity and workspace identity are both preserved for focus', () => {
  const model = createAttentionModel();
  const row = update(model, session('working', { surfaceId: 'internal-tab-id' }));
  assert.equal(row.workspaceId, 'workspace-1');
  assert.equal(row.surfaceId, 'surface-1');
  assert.equal(row.selected, true);
});

test('reloading clears local dispositions and exposes the live request', () => {
  const original = createAttentionModel();
  update(original, session('needs_input'));
  original.act(key, 'snooze', 1100);
  assert.equal(update(original, session('needs_input'), 1200).lane, 'snoozed');
  assert.equal(update(createAttentionModel(), session('needs_input'), 1200).lane, 'need');
});

test('open actions wait for focus to arrive, then close when it leaves', () => {
  const model = createAttentionModel();
  const a = { id: 'a', title: 'A', index: 0, agents: [session('idle')] };
  const b = { id: 'b', title: 'B', index: 1, agents: [session('idle')] };
  const tab = (focused) => [{ id: 'panel-1', surfaceId: 'surface-1', focused, hasUnread: false }];
  const snapshot = (selected, now = 1100) => model.update([
    { ...a, selected: selected === 'a', tabs: tab(true) },
    { ...b, selected: selected === 'b', tabs: tab(true) },
  ], now);
  const openKeys = (rows) => rows.filter((r) => r.open).map((r) => r.key);
  const keyB = 'b:terminal:panel-1';

  assert.deepEqual(openKeys(snapshot('a')), []);
  model.openActions(keyB);
  assert.deepEqual(openKeys(snapshot('a')), [keyB], 'a click does not close before focus lands');
  assert.deepEqual(openKeys(snapshot('b')), [keyB]);
  assert.deepEqual(openKeys(snapshot('b', 9999)), [keyB], 'staying on the row has no timeout');
  assert.deepEqual(openKeys(snapshot('a')), [], 'switching away closes the actions');
  assert.deepEqual(openKeys(snapshot('b')), [], 'returning does not reopen them');
});

test('focus passing through a sibling terminal does not close a clicked row', () => {
  const model = createAttentionModel();
  const agents = [session('idle'), session('idle', { id: 'agent-2', panelId: 'panel-2', surfaceId: 'surface-2' })];
  const snapshot = (focused) => model.update([workspace(agents, { tabs: ['panel-1', 'panel-2'].map((id, i) => (
    { id, surfaceId: 'surface-' + (i + 1), focused: id === focused, hasUnread: false }
  )) })], 1100);
  const second = 'workspace-1:terminal:panel-2';
  snapshot('panel-1');
  model.openActions(second);
  assert.equal(snapshot('panel-1')[1].open, true);
  assert.equal(snapshot('panel-2')[1].open, true);
  assert.equal(snapshot('panel-1')[1].open, false);
});

test('snoozing closes the row actions', () => {
  const model = createAttentionModel();
  update(model, session('needs_input'));
  model.openActions(key);
  assert.equal(update(model, session('needs_input')).open, true);
  model.act(key, 'snooze', 1100);
  assert.equal(update(model, session('needs_input')).open, false);
});

test('native rows follow keyboard order, focus the matching terminal, and mirror native unread state', () => {
  const fs = require('node:fs');
  const vm = require('node:vm');
  const calls = [];
  let render;
  let nativeUnread = true;
  let helperWorking = true;
  let splitTerminal = false;
  const node = (type, value, children = []) => {
    const target = { type, value, children, modifiers: {} };
    const proxy = new Proxy(target, { get(object, key) {
      if (key in object) return object[key];
      return (...args) => { object.modifiers[key] = args; return proxy; };
    } });
    return proxy;
  };
  const sandbox = {
    signal: (initial) => { let value = initial; return [() => value, (next) => { value = next; }]; },
    computed: (fn) => fn,
    sidebar: (fn) => { render = fn; },
    data: { clock: () => ({ epoch: 1100 }), workspaces: () => [
      workspace([
        session('needs_input'),
        ...(splitTerminal ? [session('needs_input', { id: 'other-terminal', panelId: 'panel-2', surfaceId: 'surface-2' })] : []),
      ], { id: 'workspace-2', index: 1, title: 'Second' }),
      workspace([session('idle'), session(helperWorking ? 'working' : 'idle', { id: 'helper' })], {
        id: 'workspace-1', index: 0, title: 'First', unread: nativeUnread ? 1 : 0,
        tabs: [{ id: 'panel-1', surfaceId: 'surface-1', focused: true, hasUnread: nativeUnread }],
      }),
    ] },
    cmux: (method, args) => calls.push({ method, args: { ...args } }),
    ForEach: (options, fn) => node('ForEach', { options, fn }),
  };
  for (const name of ['VStack', 'HStack']) sandbox[name] = (options, children) => node(name, options, children);
  for (const name of ['Text', 'Image', 'Circle', 'Spacer', 'Divider', 'TextField', 'Button', 'Menu']) {
    sandbox[name] = (value, extra) => {
      const item = node(name, value, Array.isArray(extra) ? extra : []);
      if (name === 'Button') item.action = extra;
      return item;
    };
  }
  vm.runInNewContext(fs.readFileSync(require.resolve('../cmux/sidebars/attention-first.js'), 'utf8'), sandbox);
  const renderedRows = [];
  const renderedNodes = [];
  function visit(item) {
    renderedNodes.push(item);
    if (item.modifiers.contextMenu) renderedRows.push(item);
    if (item.type === 'ForEach') {
      for (const value of item.value.options.items()) visit(item.value.fn(() => value));
    } else for (const child of item.children) visit(child);
  }
  visit(render());
  assert.equal(renderedRows.length, 2);
  function countDots(item) {
    if (item.type === 'Circle') return 1;
    const children = item.type === 'ForEach'
      ? Array.from(item.value.options.items(), (value) => item.value.fn(() => value)) : item.children;
    return children.reduce((sum, child) => sum + countDots(child), 0);
  }
  assert.equal(countDots(renderedRows[0]), 1, 'background work cannot hide a native unread notification');
  assert.equal(countDots(renderedRows[1]), 1, 'other unread notifications remain visible');
  renderedRows[0].modifiers.onTap[0]();
  renderedRows[1].modifiers.onTap[0]();
  assert.deepEqual(calls, [
    { method: 'workspace.select', args: { workspace_id: 'workspace-1' } },
    { method: 'surface.focus', args: { workspace_id: 'workspace-1', surface_id: 'surface-1' } },
    { method: 'workspace.select', args: { workspace_id: 'workspace-2' } },
    { method: 'surface.focus', args: { workspace_id: 'workspace-2', surface_id: 'surface-1' } },
  ]);
  helperWorking = false;
  nativeUnread = false;
  renderedRows.length = 0;
  visit(render());
  assert.equal(countDots(renderedRows[0]), 0, 'a pending local review cannot retain a dot after native read');
  assert.notEqual(renderedRows[0].modifiers.background[0](), '#5BA7F738');
  assert.equal(countDots(renderedRows[1]), 1, 'reading one workspace leaves other notifications intact');
  nativeUnread = true;
  renderedRows.length = 0;
  visit(render());
  assert.equal(countDots(renderedRows[0]), 1, 'native mark-unread restores the indicator');
  assert.equal(renderedRows[0].modifiers.background[0](), '#5BA7F738');

  const snooze = renderedRows[1].modifiers.contextMenu[0][1];
  assert.equal(snooze.value(), 'Snooze');
  snooze.action();
  assert.deepEqual(calls.at(-1), { method: 'notification.mark_read', args: { tab_id: 'workspace-2' } });
  renderedRows.length = 0;
  renderedNodes.length = 0;
  visit(render());
  assert.equal(renderedRows.length, 1, 'Snooze removes the row from the main list');
  const snoozedHeader = renderedNodes.find((item) => item.type === 'HStack'
    && item.children.some((child) => child.type === 'Text' && typeof child.value === 'function' && child.value() === 'SNOOZED'));
  assert.ok(snoozedHeader, 'a collapsed Snoozed section keeps the saved row reachable');
  snoozedHeader.modifiers.onTap[0]();
  renderedRows.length = 0;
  visit(render());
  assert.equal(renderedRows.length, 2);
  const unsnooze = renderedRows[1].modifiers.contextMenu[0][1];
  assert.equal(unsnooze.value(), 'Unsnooze');
  const callsBeforeRestore = calls.length;
  unsnooze.action();
  assert.equal(calls.length, callsBeforeRestore, 'restoring does not manufacture a native notification');
  renderedRows.length = 0;
  renderedNodes.length = 0;
  visit(render());
  assert.equal(renderedRows.length, 2, 'Unsnooze restores the row to the main list');
  assert.ok(!renderedNodes.some((item) => item.type === 'Text'
    && typeof item.value === 'function' && item.value() === 'SNOOZED'));

  splitTerminal = true;
  helperWorking = true;
  renderedRows.length = 0;
  visit(render());
  assert.equal(renderedRows.length, 3);
  const beforeInvalidSnooze = calls.length;
  renderedRows[0].modifiers.contextMenu[0][1].action();
  assert.equal(calls.length, beforeInvalidSnooze, 'a rejected snooze must not mark notifications read');
  renderedRows[1].modifiers.contextMenu[0][1].action();
  assert.deepEqual(calls.at(-1), {
    method: 'notification.mark_read', args: { tab_id: 'workspace-2', surface_id: 'surface-1' },
  }, 'snoozing one of several terminals does not read the other terminal notifications');
});
