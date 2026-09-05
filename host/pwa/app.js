// The app shell: WebSocket client, tabs (one per block), the live chart,
// and loading of the panel modules. Panels live in panels/<block>.js.
//
// Adding a block = write panels/b<N>.js and add it to PANELS below.
import base from './panels/base.js';
import b1 from './panels/b1.js';
import b2 from './panels/b2.js';
import b3 from './panels/b3.js';
import b4 from './panels/b4.js';
import b5 from './panels/b5.js';
import template from './panels/template.js';
import alarms from './panels/alarms.js';

const PANELS = [base, b1, b2, b3, b4, b5, template, alarms];

// ---------------------------------------------------------------------------
// WebSocket client with reconnect. api.send(block, cmd, args) -> Promise(result)
// ---------------------------------------------------------------------------
const api = (() => {
  let ws = null;
  let nextId = 1;
  const waiting = new Map();      // id -> {resolve, reject, timer}
  const listeners = { status: [], hello: [], alarm: [], open: [], close: [] };
  let backoff = 500;

  function emit(kind, data) { for (const fn of listeners[kind]) fn(data); }

  function connect() {
    const url = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws';
    ws = new WebSocket(url);
    ws.onopen = () => { backoff = 500; emit('open'); };
    ws.onclose = () => {
      emit('close');
      for (const [, w] of waiting) { clearTimeout(w.timer); w.reject(new Error('disconnected')); }
      waiting.clear();
      setTimeout(connect, backoff);
      backoff = Math.min(backoff * 2, 5000);
    };
    ws.onerror = () => ws.close();
    ws.onmessage = (ev) => {
      let msg;
      try { msg = JSON.parse(ev.data); } catch { return; }
      if (msg.type) { emit(msg.type, msg); return; }          // broadcast
      const w = waiting.get(msg.id);                          // reply
      if (!w) return;
      waiting.delete(msg.id);
      clearTimeout(w.timer);
      msg.ok ? w.resolve(msg.result ?? {}) : w.reject(new Error(msg.error || 'error'));
    };
  }

  function send(block, cmd, args = {}) {
    return new Promise((resolve, reject) => {
      if (!ws || ws.readyState !== WebSocket.OPEN) return reject(new Error('not connected'));
      const id = nextId++;
      const timer = setTimeout(() => { waiting.delete(id); reject(new Error('timeout')); }, 3000);
      waiting.set(id, { resolve, reject, timer });
      ws.send(JSON.stringify({ id, block, cmd, args }));
    });
  }

  function on(kind, fn) { listeners[kind].push(fn); }

  // Convenience for panels: add an alarm rule on this block.
  function addAlarm(rule) { return send('alarms', 'add', rule); }

  connect();
  return { send, on, addAlarm, toast };
})();

// ---------------------------------------------------------------------------
// Toasts (alarms, errors)
// ---------------------------------------------------------------------------
function toast(text, kind = 'alarm') {
  const el = document.createElement('div');
  el.className = 'toast' + (kind === 'info' ? ' info' : '');
  el.textContent = text;
  document.getElementById('toasts').appendChild(el);
  setTimeout(() => el.remove(), 5000);
}

// ---------------------------------------------------------------------------
// Live chart: a ring buffer of the chosen key, drawn on a canvas.
// ---------------------------------------------------------------------------
const chart = (() => {
  const canvas = document.getElementById('chart');
  const ctx = canvas.getContext('2d');
  const select = document.getElementById('chart-key');
  const valueEl = document.getElementById('chart-value');
  const N = 400;                        // 20 s at 20 Hz
  const buf = new Float32Array(N);
  let head = 0, filled = 0;
  let key = localStorage.getItem('chartKey') || 'base.counter';
  let knownKeys = [];

  select.onchange = () => { key = select.value; localStorage.setItem('chartKey', key); filled = 0; };

  function refreshKeys(blocks) {
    // Collect "block.key" for every numeric top-level status value.
    const keys = [];
    for (const [b, st] of Object.entries(blocks))
      for (const [k, v] of Object.entries(st))
        if (typeof v === 'number') keys.push(`${b}.${k}`);
    if (keys.join() === knownKeys.join()) return;
    knownKeys = keys;
    select.innerHTML = keys.map(k => `<option ${k === key ? 'selected' : ''}>${k}</option>`).join('');
  }

  function push(blocks) {
    const [b, k] = key.split('.');
    const v = blocks[b]?.[k];
    if (typeof v !== 'number') return;
    buf[head] = v; head = (head + 1) % N; filled = Math.min(filled + 1, N);
    valueEl.textContent = Number.isInteger(v) ? v : v.toFixed(3);
    draw();
  }

  function draw() {
    const w = canvas.width = canvas.clientWidth * devicePixelRatio;
    const h = canvas.height = 140 * devicePixelRatio;
    ctx.clearRect(0, 0, w, h);
    if (filled < 2) return;
    let min = Infinity, max = -Infinity;
    for (let i = 0; i < filled; i++) { const v = buf[(head - 1 - i + N) % N]; if (v < min) min = v; if (v > max) max = v; }
    if (max - min < 1e-6) { max += 0.5; min -= 0.5; }
    const pad = 6 * devicePixelRatio;
    const y = v => h - pad - (v - min) / (max - min) * (h - 2 * pad);
    ctx.strokeStyle = '#2a2f3a'; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(0, y(0)); ctx.lineTo(w, y(0)); ctx.stroke();   // zero line
    ctx.strokeStyle = '#4fa3ff'; ctx.lineWidth = 2 * devicePixelRatio;
    ctx.beginPath();
    for (let i = 0; i < filled; i++) {
      const v = buf[(head - filled + i + N) % N];
      const x = (i / (N - 1)) * w;
      i ? ctx.lineTo(x, y(v)) : ctx.moveTo(x, y(v));
    }
    ctx.stroke();
    ctx.fillStyle = '#8b93a7'; ctx.font = `${11 * devicePixelRatio}px system-ui`;
    ctx.fillText(max.toPrecision(4), pad, pad + 10 * devicePixelRatio);
    ctx.fillText(min.toPrecision(4), pad, h - pad - 2);
  }

  return { refreshKeys, push };
})();

// ---------------------------------------------------------------------------
// Tabs + panels
// ---------------------------------------------------------------------------
const tabsEl = document.getElementById('tabs');
const panelEl = document.getElementById('panel');
let activePanel = null;
let lastStatus = null;

function buildTabs(blockNames) {
  // One tab per block the firmware reports; panels without a module get a
  // generic key/value view so a new block is visible before its panel exists.
  const panels = blockNames.map(name => PANELS.find(p => p.id === name) || genericPanel(name));
  tabsEl.innerHTML = '';
  for (const p of panels) {
    const btn = document.createElement('button');
    btn.textContent = p.title;
    btn.onclick = () => activate(p, btn);
    tabsEl.appendChild(btn);
  }
  const wanted = localStorage.getItem('tab') || 'base';
  const idx = Math.max(0, panels.findIndex(p => p.id === wanted));
  activate(panels[idx], tabsEl.children[idx]);
}

function activate(panel, btn) {
  for (const b of tabsEl.children) b.classList.remove('active');
  btn.classList.add('active');
  localStorage.setItem('tab', panel.id);
  panelEl.innerHTML = '';
  activePanel = panel;
  panel.render(panelEl, api);
  if (lastStatus) panel.onStatus?.(lastStatus.blocks[panel.id] ?? {}, lastStatus);
}

function genericPanel(id) {
  let kv;
  return {
    id, title: id.toUpperCase(),
    render(el) {
      el.innerHTML = `<h2>${id}</h2><p class="help">No panel yet - create host/pwa/panels/${id}.js.</p><div class="kv"></div>`;
      kv = el.querySelector('.kv');
    },
    onStatus(st) {
      kv.innerHTML = Object.entries(st).map(([k, v]) => `<span>${k}</span><span>${JSON.stringify(v)}</span>`).join('');
    },
  };
}

// ---------------------------------------------------------------------------
// Wire it up
// ---------------------------------------------------------------------------
const dot = document.getElementById('conn-dot');
const connText = document.getElementById('conn-text');

api.on('open', () => { dot.classList.add('on'); connText.textContent = location.host; });
api.on('close', () => { dot.classList.remove('on'); connText.textContent = 'reconnecting…'; });
api.on('hello', (msg) => {
  connText.textContent = `${location.host} · fw ${msg.fw}${msg.sim ? ' · SIM' : ''}`;
  buildTabs(msg.blocks);
});
api.on('status', (msg) => {
  lastStatus = msg;
  chart.refreshKeys(msg.blocks);
  chart.push(msg.blocks);
  activePanel?.onStatus?.(msg.blocks[activePanel.id] ?? {}, msg);
});
api.on('alarm', (msg) => {
  toast(`ALARM ${msg.block}.${msg.key} = ${Number(msg.value).toFixed(3)} → ${msg.action}`);
  if (typeof Notification !== 'undefined' && Notification.permission === 'granted') new Notification('Instrument alarm', { body: `${msg.block}.${msg.key} = ${msg.value}` });
});

// Service worker for offline / installable use. Browsers only allow this on
// https or localhost, so on http://192.168.4.1 registration fails quietly.
if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js').catch(() => {});
