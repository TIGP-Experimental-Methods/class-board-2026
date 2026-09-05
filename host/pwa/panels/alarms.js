// Alarms panel: list rules, add a rule, remove a rule.
// Rules are {block, key, op, threshold, action}; see firmware/PROTOCOL.md.
let els = {};
let apiRef;
let lastBlocks = {};
let timer = null;

async function refresh() {
  // Stop polling once the user has switched to another tab (the table is gone).
  if (!els.table || !els.table.isConnected) { clearInterval(timer); timer = null; return; }
  try {
    const r = await apiRef.send('alarms', 'list');
    els.table.innerHTML = r.rules.length ? r.rules.map(x => `
      <tr>
        <td>${x.id}</td><td>${x.block}.${x.key} ${x.op} ${x.threshold}</td><td>${x.action}</td>
        <td>${x.active ? '<i class="led on"></i>' : '<i class="led"></i>'} ${x.fired}</td>
        <td><button class="btn" data-id="${x.id}">✕</button></td>
      </tr>`).join('') : '<tr><td colspan="5" class="muted">no rules</td></tr>';
    for (const btn of els.table.querySelectorAll('[data-id]'))
      btn.onclick = () => apiRef.send('alarms', 'remove', { id: Number(btn.dataset.id) }).then(refresh);
  } catch (e) { apiRef.toast(e.message); }
}

export default {
  id: 'alarms',
  title: 'Alarms',

  render(el, api) {
    apiRef = api;
    el.innerHTML = `
      <h2>Alarms</h2>
      <p class="help">When <em>block.key op threshold</em> becomes true, do the action once.</p>
      <div class="row">
        <select id="key"></select>
        <select id="op">
          <option>gt</option><option>lt</option><option>ge</option><option>le</option><option>eq</option><option>ne</option>
        </select>
        <input type="number" id="thr" value="0" step="any">
      </div>
      <div class="row">
        <select id="action">
          <option value="notify">notify</option>
          <option value="relay:1:on">relay 1 on</option><option value="relay:1:off">relay 1 off</option>
          <option value="relay:2:on">relay 2 on</option><option value="relay:2:off">relay 2 off</option>
          <option value="relay:3:on">relay 3 on</option><option value="relay:3:off">relay 3 off</option>
          <option value="relay:4:on">relay 4 on</option><option value="relay:4:off">relay 4 off</option>
        </select>
        <button class="btn primary" id="add">Add rule</button>
        <button class="btn" id="notif">Allow notifications</button>
      </div>
      <table><thead><tr><th>#</th><th>rule</th><th>action</th><th>fired</th><th></th></tr></thead>
        <tbody id="table"></tbody></table>`;

    els = { key: el.querySelector('#key'), table: el.querySelector('#table') };
    fillKeys();

    el.querySelector('#add').onclick = () => {
      const [block, key] = els.key.value.split('.');
      api.addAlarm({ block, key, op: el.querySelector('#op').value, threshold: Number(el.querySelector('#thr').value),
        action: el.querySelector('#action').value })
        .then(refresh).catch(e => api.toast(e.message));
    };
    el.querySelector('#notif').onclick = () => { if (typeof Notification !== 'undefined') Notification.requestPermission(); };
    refresh();
    clearInterval(timer);
    timer = setInterval(refresh, 2000);
  },

  onStatus(_st, msg) {
    lastBlocks = msg.blocks;
    if (els.key && els.key.children.length === 0) fillKeys();
  },
};

function fillKeys() {
  const keys = [];
  for (const [b, st] of Object.entries(lastBlocks))
    for (const [k, v] of Object.entries(st)) if (typeof v === 'number' || typeof v === 'boolean') keys.push(`${b}.${k}`);
  els.key.innerHTML = keys.map(k => `<option>${k}</option>`).join('');
}
