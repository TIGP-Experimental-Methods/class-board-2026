// Panel for b1_inputs: an eight-channel voltmeter and a two-channel oscilloscope
// with a spectrum view.
//
// Voltmeter: the 20 Hz status values ai1..ai8, each with its own range.
// Scope: the fast path (firmware/PROTOCOL.md section 6). The board samples one
// input at kHz rates and sends binary frames on the same WebSocket:
//   Roll    `stream`  - a frame (kind 1) every ~50 ms, drawn as a rolling trace.
//                      The board drops a stream 10 s after the last `stream`
//                      command, so this panel renews it while it is on screen.
//   Single  `capture` - one triggered frame (kind 2), then stop.
//   Normal  `capture` again after every frame, waiting for the trigger.
//   Auto    the same, but the board sends an untriggered frame if nothing
//           crosses the level in time - so a flat line still shows.
// Tap the trace to put the trigger level there.
// A second input (`ch2`) is sampled in the same ADC scans as the first, so the
// two traces line up to within microseconds; the board sends one frame per
// input with the same t_ms, and this panel pairs them. With two inputs the
// panel also gives the phase and gain of the second relative to the first at
// the first one's main frequency - one point of a Bode plot.
// Spectrum: a Hann-windowed FFT of what is on screen, in dBV (dB relative to
// 1 V rms), the mean removed. A sine of amplitude A reads 20 log10(A / sqrt 2).
//
// A panel is a plain object: { id, title, render(container, api), onStatus(st) }.
let els = {};
let api = null;
let wired = false;          // the binary listener is added once for the life of the page

const RANGES = [
  { code: 0, label: '±10 V', fs: 10.24 },
  { code: 1, label: '±5 V', fs: 5.12 },
  { code: 2, label: '±2.5 V', fs: 2.56 },
  { code: 5, label: '0–10 V', fs: 10.24 },
  { code: 6, label: '0–5 V', fs: 5.12 },
];
const ROLL_RATES = [100, 500, 1000, 2000, 5000, 10000, 20000];
const CAPTURE_RATES = [1000, 5000, 10000, 20000, 50000, 100000, 250000];
const CAPTURE_N = [500, 1000, 2000, 4000, 5000, 10000];
const ROLL_N = 2000;               // samples shown in roll mode
const MAX_CAPTURE_S = 1;           // the board refuses n / rate above this
const MAX_N_DUAL = 5000;           // ...and n above this with two inputs
const MAX_ROLL_DUAL = 10000;       // ...and a stream above this with two inputs
const MAX_FFT = 16384;
const COLOR_A = '#4fa3ff', COLOR_B = '#3ddc84';
const LEASE_RENEW_MS = 4000;       // the board's lease is 10 s
const AUTO_TIMEOUT_MS = 150;

// What the scope is set to. Kept across tab switches and reloads.
const cfg = Object.assign({
  ch: 3, ch2: 0, mode: 'auto', view: 'time', rollRate: 1000, rate: 50000, n: 500,
  level: 0.5, edge: 'rising', prePct: 25,
}, load());

let running = false;               // the user pressed Run (roll / normal / auto)
let renewTimer = null;
let trace = null;                  // { v, v2 (or null), rate, trig, ch, ch2, kind, t_ms, lsb }
let pending = null;                // first input's capture frame, waiting for the second's
const roll = { buf: new Float32Array(ROLL_N), buf2: new Float32Array(ROLL_N), head: 0, filled: 0,
  rate: 0, ch: 0, ch2: 0, pendingN: 0 };
let boardScope = {};               // b1.scope from the status broadcast

function load() {
  try { return JSON.parse(localStorage.getItem('b1scope') || '{}'); } catch { return {}; }
}
function save() {
  try { localStorage.setItem('b1scope', JSON.stringify(cfg)); } catch { /* private mode */ }
}

export default {
  id: 'b1',
  title: 'B1 Inputs',

  render(el, a) {
    api = a;
    const opts = (list, sel, fmt) => list.map(v => `<option value="${v}" ${v === sel ? 'selected' : ''}>${fmt(v)}</option>`).join('');
    const hz = v => v >= 1000 ? `${v / 1000} kS/s` : `${v} S/s`;
    el.innerHTML = `
      <style>
        .b1-tiles { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; }
        .b1-tile { border: 1px solid var(--line); border-radius: 10px; padding: 8px 10px; }
        .b1-tile .top { display: flex; justify-content: space-between; color: var(--muted); font-size: 13px; }
        .b1-tile .v { font-size: 22px; font-variant-numeric: tabular-nums; color: var(--accent); margin: 2px 0 6px; }
        .b1-tile .v.clip { color: var(--warn); }
        .b1-tile select { width: 100%; min-height: 36px; padding: 4px 8px; }
        .b1-form { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 8px 12px; }
        .b1-form label { display: flex; flex-direction: column; gap: 4px; color: var(--muted); font-size: 13px; }
        .b1-form input, .b1-form select { width: 100%; min-height: 44px; }
        .b1-modes { display: flex; gap: 6px; flex-wrap: wrap; }
        .b1-modes .btn { flex: 1 1 70px; min-height: 44px; }
        .b1-modes .btn.sel { border-color: var(--accent); color: var(--accent); }
        canvas.b1-scope { height: 220px; touch-action: manipulation; }
        .b1-meas { display: grid; grid-template-columns: repeat(auto-fill, minmax(96px, 1fr)); gap: 6px; font-size: 13px; }
        .b1-meas div { display: flex; flex-direction: column; }
        .b1-meas b { font-weight: normal; color: var(--accent); font-variant-numeric: tabular-nums; font-size: 15px; }
        .b1-state { font-size: 13px; color: var(--muted); font-variant-numeric: tabular-nums; min-height: 1.4em; }
        .b1-state .warn { color: var(--warn); }
        .b1-meas .b { color: ${COLOR_B}; }
        .b1-meas .wide { grid-column: 1 / -1; }
      </style>
      <h2>B1 Precision inputs</h2>
      <p class="help">ADS8688, 8 × 16 bit. Each input has its own range; a reading in amber is at the end of its range.
        Pick <code>b1.aiN</code> in the chart above for a 20 Hz trend, or use the scope below for kHz signals.</p>
      <div class="b1-tiles" id="tiles"></div>

      <h3>Scope</h3>
      <div class="b1-modes" id="modes">
        <button class="btn" data-m="roll">Roll</button>
        <button class="btn" data-m="auto">Auto</button>
        <button class="btn" data-m="normal">Normal</button>
        <button class="btn" data-m="single">Single</button>
      </div>
      <div class="b1-form" style="margin-top:8px">
        <label>input<select id="ch">${opts([1, 2, 3, 4, 5, 6, 7, 8], cfg.ch, v => 'AI' + v)}</select></label>
        <label>second input<select id="ch2">${opts([0, 1, 2, 3, 4, 5, 6, 7, 8], cfg.ch2, v => v ? 'AI' + v : '—')}</select></label>
        <label class="roll-only">sample rate<select id="rollRate">${opts(ROLL_RATES, cfg.rollRate, hz)}</select></label>
        <label class="cap-only">sample rate<select id="rate">${opts(CAPTURE_RATES, cfg.rate, hz)}</select></label>
        <label class="cap-only">samples<select id="n">${opts(CAPTURE_N, cfg.n, v => String(v))}</select></label>
        <label class="cap-only">trigger level (V)<input id="level" type="number" step="0.05" value="${cfg.level}"></label>
        <label class="cap-only">edge<select id="edge">${opts(['rising', 'falling'], cfg.edge, v => v)}</select></label>
        <label class="cap-only">before trigger (%)<input id="pre" type="number" min="0" max="90" step="5" value="${cfg.prePct}"></label>
      </div>
      <div class="row">
        <button class="btn primary" id="run">Run</button>
        <button class="btn" id="csv">CSV</button>
        <span class="b1-state" id="state"></span>
      </div>
      <div class="b1-modes" id="views">
        <button class="btn" data-v="time">Time</button>
        <button class="btn" data-v="spectrum">Spectrum</button>
      </div>
      <canvas id="scope" class="b1-scope"></canvas>
      <div class="b1-meas" id="meas"></div>

      <h3>Alarm</h3>
      <div class="row"><button class="btn" id="alarm">ai1 &gt; 3.5 V → module 1 on</button></div>`;

    els = {
      tiles: el.querySelector('#tiles'), modes: el.querySelector('#modes'),
      ch: el.querySelector('#ch'), ch2: el.querySelector('#ch2'), views: el.querySelector('#views'), rollRate: el.querySelector('#rollRate'), rate: el.querySelector('#rate'),
      n: el.querySelector('#n'), level: el.querySelector('#level'), edge: el.querySelector('#edge'),
      pre: el.querySelector('#pre'), run: el.querySelector('#run'), state: el.querySelector('#state'),
      scope: el.querySelector('#scope'), meas: el.querySelector('#meas'), root: el,
    };

    els.tiles.innerHTML = Array.from({ length: 8 }, (_, i) => `
      <div class="b1-tile">
        <div class="top"><span>AI${i + 1}</span><span id="fs${i + 1}"></span></div>
        <div class="v" id="ai${i + 1}">–</div>
        <select data-ch="${i + 1}">${RANGES.map(r => `<option value="${r.code}">${r.label}</option>`).join('')}</select>
      </div>`).join('');
    for (const s of els.tiles.querySelectorAll('select')) {
      s.onchange = () => api.send('b1', 'set_range', { ch: Number(s.dataset.ch), range: Number(s.value) })
        .then(() => { if (running) restart(); })
        .catch(e => api.toast(e.message));
    }

    for (const b of els.modes.querySelectorAll('button')) {
      b.onclick = () => {
        const wasRunning = running;
        if (running) stopScope();
        cfg.mode = b.dataset.m; save(); showMode();
        if (wasRunning && cfg.mode !== 'single') startScope();
      };
    }
    const num = (input, key, lo, hi) => {
      input.onchange = () => {
        let v = Number(input.value);
        if (!Number.isFinite(v)) v = cfg[key];
        cfg[key] = Math.min(hi, Math.max(lo, v)); input.value = cfg[key]; save();
        if (running) restart(); else draw();
      };
    };
    for (const b of els.views.querySelectorAll('button')) {
      b.onclick = () => { cfg.view = b.dataset.v; save(); showMode(); draw(); };
    }
    for (const k of ['ch', 'ch2', 'rollRate', 'rate', 'n']) {
      els[k].onchange = () => {
        cfg[k] = Number(els[k].value); fitLength(); save();
        if (running) restart();
      };
    }
    els.edge.onchange = () => { cfg.edge = els.edge.value; save(); if (running) restart(); };
    num(els.level, 'level', -10.24, 10.24);
    num(els.pre, 'prePct', 0, 90);

    els.run.onclick = () => (running || boardScope.mode === 'armed') ? stopScope() : startScope();
    el.querySelector('#csv').onclick = exportCsv;
    els.scope.onclick = tapLevel;
    el.querySelector('#alarm').onclick = () =>
      api.addAlarm({ block: 'b1', key: 'ai1', op: 'gt', threshold: 3.5, action: 'module:1:on' })
        .then(r => api.toast(`alarm rule ${r.id} added`, 'info')).catch(e => api.toast(e.message));

    if (!wired) {
      wired = true;
      api.on('binary', onFrame);
      api.on('close', () => { if (running) { running = false; clearInterval(renewTimer); showRun(); } });
      window.addEventListener('resize', draw);
    }
    showMode();
    showRun();
    draw();
  },

  onStatus(st) {
    const ranges = Array.isArray(st.ranges) ? st.ranges : null;
    for (let i = 1; i <= 8; i++) {
      const v = st['ai' + i];
      const code = ranges ? ranges[i - 1] : (i === 1 ? st.range : undefined);
      const r = RANGES.find(x => x.code === code);
      const vEl = els.tiles?.isConnected && els.tiles.querySelector(`#ai${i}`);
      if (!vEl) continue;
      const fsEl = els.tiles.querySelector(`#fs${i}`);
      if (fsEl && r) fsEl.textContent = r.label;
      if (typeof v === 'number') {
        vEl.textContent = v.toFixed(3) + ' V';
        // Amber within 0.5 % of full scale. A unipolar range reads 0 V both for
        // 0 V and for anything below it, so only its top end can be flagged.
        const fs = r?.fs ?? 10.24;
        const near = fs * 0.005;
        const bipolar = !r || r.code < 5;
        vEl.classList.toggle('clip', v >= fs - near || (bipolar && v <= -fs + near));
      }
      const sel = els.tiles.querySelector(`select[data-ch="${i}"]`);
      if (sel && r && document.activeElement !== sel && Number(sel.value) !== r.code) sel.value = String(r.code);
    }
    boardScope = st.scope || {};
    showState();
  },
};

// ---------------------------------------------------------------------------
// Scope control
// ---------------------------------------------------------------------------
function err(e) { api.toast(e.message || String(e)); }

function dual() { return cfg.ch2 > 0 && cfg.ch2 !== cfg.ch; }

function fitLength() {
  // n / rate must stay within a second (and n within 5000 with two inputs);
  // shorten the record rather than refuse. The same for a two-input stream.
  const maxN = dual() ? MAX_N_DUAL : Infinity;
  while ((cfg.n / cfg.rate > MAX_CAPTURE_S || cfg.n > maxN) && cfg.n > CAPTURE_N[0]) {
    cfg.n = CAPTURE_N[Math.max(0, CAPTURE_N.indexOf(cfg.n) - 1)] ?? CAPTURE_N[0];
  }
  if (dual() && cfg.rollRate > MAX_ROLL_DUAL) cfg.rollRate = MAX_ROLL_DUAL;
  if (els.n) els.n.value = String(cfg.n);
  if (els.rollRate) els.rollRate.value = String(cfg.rollRate);
}

function captureArgs() {
  fitLength();
  const args = { ch: cfg.ch, rate_hz: cfg.rate, n: cfg.n };
  if (dual()) args.ch2 = cfg.ch2;
  args.trig = { level: cfg.level, edge: cfg.edge, pre: Math.round(cfg.n * cfg.prePct / 100) };
  if (cfg.mode === 'auto') args.timeout_ms = AUTO_TIMEOUT_MS + Math.round(2000 * cfg.n / cfg.rate);
  return args;
}

function startScope() {
  if (cfg.mode === 'roll') {
    fitLength();
    roll.filled = 0; roll.head = 0; roll.rate = cfg.rollRate; roll.ch = cfg.ch; roll.ch2 = dual() ? cfg.ch2 : 0;
    const args = { ch: cfg.ch, rate_hz: cfg.rollRate };
    if (dual()) args.ch2 = cfg.ch2;
    const ask = () => api.send('b1', 'stream', args);
    ask().then(() => {
      running = true; showRun();
      clearInterval(renewTimer);
      renewTimer = setInterval(() => {
        // Left the tab: let the board stop sampling.
        if (!els.scope?.isConnected) { stopScope(); return; }
        ask().catch(() => {});
      }, LEASE_RENEW_MS);
    }).catch(err);
    return;
  }
  running = cfg.mode !== 'single';
  pending = null;
  api.send('b1', 'capture', captureArgs())
    .then(() => showRun())
    .catch(e => { running = false; showRun(); err(e); });
}

function stopScope() {
  running = false;
  clearInterval(renewTimer);
  showRun();
  return api.send('b1', 'stop').catch(() => {});
}

function restart() {
  stopScope().then(() => startScope());
}

function onFrame(f) {
  if (f.block_id !== 1 || (f.kind !== 1 && f.kind !== 2)) return;
  const n = Math.min(f.n, f.payload.byteLength >> 1);
  const v = new Float32Array(n);
  for (let k = 0; k < n; k++) v[k] = f.offset_v + f.volts_per_lsb * f.payload.getInt16(2 * k, true);

  const two = dual();
  if (f.kind === 1) {
    if (cfg.mode !== 'roll') return;
    if (f.rate_hz !== roll.rate || roll.ch !== cfg.ch || roll.ch2 !== (two ? cfg.ch2 : 0)) {
      roll.filled = 0; roll.head = 0; roll.pendingN = 0;
      roll.rate = f.rate_hz; roll.ch = cfg.ch; roll.ch2 = two ? cfg.ch2 : 0;
    }
    // The board sends the first input's chunk, then the second's: write the
    // first, then the second over the same span, and only then move the head.
    if (f.ch === roll.ch) {
      for (let k = 0; k < n; k++) roll.buf[(roll.head + k) % ROLL_N] = v[k];
      if (two) { roll.pendingN = n; return; }
    } else if (two && f.ch === roll.ch2 && roll.pendingN === n) {
      for (let k = 0; k < n; k++) roll.buf2[(roll.head + k) % ROLL_N] = v[k];
      roll.pendingN = 0;
    } else return;
    roll.head = (roll.head + n) % ROLL_N;
    roll.filled = Math.min(ROLL_N, roll.filled + n);
    const lin = (buf) => {
      const o = new Float32Array(roll.filled);
      for (let k = 0; k < roll.filled; k++) o[k] = buf[(roll.head - roll.filled + k + ROLL_N) % ROLL_N];
      return o;
    };
    trace = { v: lin(roll.buf), v2: two ? lin(roll.buf2) : null, rate: f.rate_hz, trig: -1,
      ch: roll.ch, ch2: two ? roll.ch2 : 0, kind: 1, t_ms: f.t_ms, lsb: f.volts_per_lsb };
  } else {
    if (two) {
      if (f.ch === cfg.ch) { pending = { v, f }; return; }          // wait for the second input
      if (f.ch !== cfg.ch2 || !pending || pending.f.t_ms !== f.t_ms) return;
      trace = { v: pending.v, v2: v, rate: f.rate_hz, trig: f.trig_index, ch: cfg.ch, ch2: cfg.ch2,
        kind: 2, t_ms: f.t_ms, lsb: pending.f.volts_per_lsb };
      pending = null;
    } else {
      if (f.ch !== cfg.ch) return;
      trace = { v, v2: null, rate: f.rate_hz, trig: f.trig_index, ch: f.ch, ch2: 0, kind: 2, t_ms: f.t_ms,
        lsb: f.volts_per_lsb };
    }
    if (cfg.mode === 'single') running = false;
    // Normal / auto: arm the next one - unless the user left this tab.
    if (running) {
      if (els.scope?.isConnected) api.send('b1', 'capture', captureArgs()).catch(e => { running = false; showRun(); err(e); });
      else running = false;
    }
    showRun();
  }
  draw();
}

function tapLevel(ev) {
  if (cfg.mode === 'roll' || cfg.view !== 'time' || !trace) return;
  const rect = els.scope.getBoundingClientRect();
  const { lo, hi, padT, plotH } = scaleOf(trace.v, trace.v2, rect.height, 1);
  const y = ev.clientY - rect.top;
  const v = hi - ((y - padT) / plotH) * (hi - lo);
  cfg.level = Math.round(v * 20) / 20;
  els.level.value = cfg.level; save();
  if (running) restart(); else draw();
}

// ---------------------------------------------------------------------------
// Display
// ---------------------------------------------------------------------------
function showMode() {
  if (!els.modes) return;
  for (const b of els.modes.querySelectorAll('button')) b.classList.toggle('sel', b.dataset.m === cfg.mode);
  const isRoll = cfg.mode === 'roll';
  for (const e of els.root.querySelectorAll('.roll-only')) e.style.display = isRoll ? '' : 'none';
  for (const e of els.root.querySelectorAll('.cap-only')) e.style.display = isRoll ? 'none' : '';
  els.run.textContent = cfg.mode === 'single' ? 'Arm' : 'Run';
  for (const b of els.views.querySelectorAll('button')) b.classList.toggle('sel', b.dataset.v === cfg.view);
}

function showRun() {
  if (!els.run) return;
  const active = running || boardScope.mode === 'armed';
  els.run.textContent = active ? 'Stop' : (cfg.mode === 'single' ? 'Arm' : 'Run');
  els.run.classList.toggle('primary', !active);
}

function showState() {
  if (!els.state) return;
  const s = boardScope;
  const parts = [];
  const inputs = s.ch2 ? `AI${s.ch} + AI${s.ch2}` : `AI${s.ch}`;
  if (s.mode === 'stream') parts.push(`streaming ${inputs} · ${fmtHz(s.rate_hz)}`);
  else if (s.mode === 'armed') parts.push(`armed ${inputs} · waiting for trigger`);
  else parts.push('idle');
  if (s.dropped) parts.push(`<span class="warn">${s.dropped} dropped</span>`);
  if (s.mode === 'idle' && s.last && s.last !== 'stopped') parts.push(s.last);
  els.state.innerHTML = parts.join(' · ');
  // The board stopped on its own (lease, NMR scan): follow it.
  if (running && cfg.mode === 'roll' && s.mode === 'idle' && s.last && s.last !== 'stopped') {
    running = false; clearInterval(renewTimer); showRun();
  }
  showRun();
}

function fmtHz(v) { return v >= 1000 ? `${+(v / 1000).toFixed(1)} kS/s` : `${v} S/s`; }

function fmtTime(s) {
  const a = Math.abs(s);
  if (a === 0) return '0';
  if (a < 1e-3) return `${+(s * 1e6).toFixed(1)} µs`;
  if (a < 1) return `${+(s * 1e3).toFixed(a < 1e-2 ? 2 : 1)} ms`;
  return `${+s.toFixed(2)} s`;
}

function niceStep(span, target) {
  const raw = span / target;
  const p = Math.pow(10, Math.floor(Math.log10(raw)));
  const m = raw / p;
  return (m < 1.5 ? 1 : m < 3.5 ? 2 : m < 7.5 ? 5 : 10) * p;
}

function scaleOf(v, v2, cssH, dpr) {
  let lo = Infinity, hi = -Infinity;
  for (const arr of v2 ? [v, v2] : [v]) {
    for (let k = 0; k < arr.length; k++) { if (arr[k] < lo) lo = arr[k]; if (arr[k] > hi) hi = arr[k]; }
  }
  if (cfg.mode !== 'roll') { lo = Math.min(lo, cfg.level); hi = Math.max(hi, cfg.level); }
  if (!Number.isFinite(lo)) { lo = -1; hi = 1; }
  if (hi - lo < 0.02) { const c = (hi + lo) / 2; lo = c - 0.01; hi = c + 0.01; }
  const m = (hi - lo) * 0.08; lo -= m; hi += m;
  const padT = 8 * dpr, padB = 20 * dpr;
  return { lo, hi, padT, padB, plotH: cssH * dpr - padT - padB };
}

// Vpp, mean, RMS, and the frequency from mean crossings (with 10 % hysteresis).
function measure(v, rate) {
  const n = v.length;
  if (n < 2) return null;
  let lo = Infinity, hi = -Infinity, sum = 0, sq = 0;
  for (let k = 0; k < n; k++) { const x = v[k]; if (x < lo) lo = x; if (x > hi) hi = x; sum += x; sq += x * x; }
  const mean = sum / n;
  const rms = Math.sqrt(sq / n);
  const acRms = Math.sqrt(Math.max(0, sq / n - mean * mean));
  const h = (hi - lo) * 0.1;
  let armed = false, first = -1, last = -1, count = 0;
  for (let k = 0; k < n; k++) {
    if (v[k] < mean - h) armed = true;
    else if (armed && v[k] >= mean + h) {
      armed = false;
      if (first < 0) first = k; else { last = k; count++; }
    }
  }
  const freq = count > 0 && hi - lo > 0.02 ? count * rate / (last - first) : NaN;
  return { lo, hi, pp: hi - lo, mean, rms, acRms, freq };
}

// ---------------------------------------------------------------------------
// Spectrum: Hann window, radix-2 FFT, magnitude in dBV
// ---------------------------------------------------------------------------
function fft(re, im) {
  const n = re.length;
  for (let i = 1, j = 0; i < n; i++) {               // bit-reversal permutation
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) { [re[i], re[j]] = [re[j], re[i]]; [im[i], im[j]] = [im[j], im[i]]; }
  }
  for (let len = 2; len <= n; len <<= 1) {
    const ang = -2 * Math.PI / len, wr = Math.cos(ang), wi = Math.sin(ang);
    for (let i = 0; i < n; i += len) {
      let cr = 1, ci = 0;
      for (let k = 0; k < len / 2; k++) {
        const a = i + k, b = a + len / 2;
        const tr = re[b] * cr - im[b] * ci, ti = re[b] * ci + im[b] * cr;
        re[b] = re[a] - tr; im[b] = im[a] - ti;
        re[a] += tr; im[a] += ti;
        const nr = cr * wr - ci * wi; ci = cr * wi + ci * wr; cr = nr;
      }
    }
  }
}

function hann(n) {
  const w = new Float64Array(n);
  for (let k = 0; k < n; k++) w[k] = 0.5 - 0.5 * Math.cos(2 * Math.PI * k / Math.max(1, n - 1));
  return w;
}

// { db: Float64Array (bins 0..N/2), binHz, peaks: [{hz, db}] } - the mean removed,
// zero-padded to a power of two. A sine of amplitude A reads 20 log10(A / sqrt 2).
function spectrum(v, rate) {
  const n = Math.min(v.length, MAX_FFT);
  if (n < 16) return null;
  let N = 1; while (N < n) N <<= 1;
  const w = hann(n);
  let mean = 0; for (let k = 0; k < n; k++) mean += v[k]; mean /= n;
  let sumW = 0; for (let k = 0; k < n; k++) sumW += w[k];
  const re = new Float64Array(N), im = new Float64Array(N);
  for (let k = 0; k < n; k++) re[k] = (v[k] - mean) * w[k];
  fft(re, im);
  const half = N / 2;
  const db = new Float64Array(half + 1);
  for (let k = 0; k <= half; k++) {
    const amp = 2 * Math.hypot(re[k], im[k]) / sumW;      // sine amplitude, volts
    db[k] = 20 * Math.log10(Math.max(amp / Math.SQRT2, 1e-9));
  }
  const binHz = rate / N;
  // Local maxima, strongest first, at least 4 bins apart (a Hann main lobe is 4
  // bins wide at this padding or less); the lowest bins are what is left of DC.
  const skip = Math.max(3, Math.ceil(2 * N / n));
  // A peak has to stand 10 dB clear of the median bin - the noise floor - or
  // every wiggle in the noise would be listed.
  const floor = Float64Array.from(db.subarray(skip)).sort()[Math.floor((half - skip) / 2)];
  const cand = [];
  for (let k = skip; k < half; k++) if (db[k] > db[k - 1] && db[k] >= db[k + 1] && db[k] > floor + 10) cand.push(k);
  cand.sort((a, b) => db[b] - db[a]);
  const peaks = [];
  for (const k of cand) {
    if (peaks.some(p => Math.abs(p.k - k) < 4 * N / n)) continue;
    const a = db[k - 1], b = db[k], c = db[k + 1];       // parabolic interpolation
    const d = a - 2 * b + c;
    const delta = d !== 0 ? 0.5 * (a - c) / d : 0;
    peaks.push({ k, hz: (k + delta) * binHz, db: b - 0.25 * (a - c) * delta });
    if (peaks.length === 3) break;
  }
  return { db, binHz, peaks };
}

// Phase (degrees) and gain (dB) of v2 relative to v at frequency hz: one DFT
// bin of each, Hann-windowed, the means removed.
function phaseGain(v, v2, rate, hz) {
  const n = Math.min(v.length, v2.length);
  const w = hann(n);
  let m1 = 0, m2 = 0; for (let k = 0; k < n; k++) { m1 += v[k]; m2 += v2[k]; } m1 /= n; m2 /= n;
  let r1 = 0, i1 = 0, r2 = 0, i2 = 0;
  for (let k = 0; k < n; k++) {
    const a = -2 * Math.PI * hz * k / rate, c = Math.cos(a) * w[k], s = Math.sin(a) * w[k];
    r1 += (v[k] - m1) * c; i1 += (v[k] - m1) * s;
    r2 += (v2[k] - m2) * c; i2 += (v2[k] - m2) * s;
  }
  let ph = (Math.atan2(i2, r2) - Math.atan2(i1, r1)) * 180 / Math.PI;
  while (ph > 180) ph -= 360;
  while (ph <= -180) ph += 360;
  return { phase: ph, gain: 20 * Math.log10(Math.hypot(r2, i2) / Math.max(Math.hypot(r1, i1), 1e-12)) };
}

function fmtFreq(hz) {
  return hz >= 1000 ? `${(hz / 1000).toFixed(3)} kHz` : `${hz.toFixed(hz < 100 ? 2 : 1)} Hz`;
}

// ---------------------------------------------------------------------------
// Drawing
// ---------------------------------------------------------------------------
function draw() {
  const c = els.scope;
  if (!c || !c.isConnected) return;
  const dpr = window.devicePixelRatio || 1;
  const w = Math.max(1, Math.round(c.clientWidth * dpr));
  const h = Math.max(1, Math.round(c.clientHeight * dpr));
  if (c.width !== w || c.height !== h) { c.width = w; c.height = h; }
  const ctx = c.getContext('2d');
  ctx.clearRect(0, 0, w, h);
  ctx.font = `${11 * dpr}px system-ui, sans-serif`;

  const show = trace && !(cfg.mode === 'roll' && trace.kind !== 1) && !(cfg.mode !== 'roll' && trace.kind !== 2);
  if (!show) {
    ctx.fillStyle = '#8b93a7'; ctx.textAlign = 'center';
    ctx.fillText(cfg.mode === 'roll' ? 'press Run to stream' : 'press Run (or Arm) to capture', w / 2, h / 2);
    ctx.textAlign = 'left';
    ctx.strokeStyle = '#2a2f3a'; ctx.lineWidth = dpr; ctx.strokeRect(0.5, 0.5, w - 1, h - 1);
    els.meas.innerHTML = '';
    return;
  }
  if (cfg.view === 'spectrum') drawSpectrum(ctx, w, h, dpr);
  else drawTime(ctx, w, h, dpr);
}

function drawTime(ctx, w, h, dpr) {
  const { v, v2, rate } = trace;
  const n = v.length;
  const nAxis = trace.kind === 1 ? ROLL_N : n;          // roll: fixed window, fills from the right
  const t0 = trace.kind === 2 && trace.trig >= 0 ? -trace.trig / rate : (trace.kind === 1 ? -(nAxis - 1) / rate : 0);
  const t1 = t0 + (nAxis - 1) / rate;
  const { lo, hi, padT, plotH } = scaleOf(v, v2, h / dpr, dpr);
  const padL = 44 * dpr, padR = 6 * dpr;
  const plotW = w - padL - padR;
  const x = t => padL + ((t - t0) / (t1 - t0 || 1)) * plotW;
  const y = val => padT + ((hi - val) / (hi - lo)) * plotH;

  // Grid with labelled steps.
  ctx.strokeStyle = '#2a2f3a'; ctx.lineWidth = dpr; ctx.fillStyle = '#8b93a7';
  const vs = niceStep(hi - lo, 5);
  ctx.textAlign = 'right';
  for (let g = Math.ceil(lo / vs) * vs; g <= hi; g += vs) {
    ctx.beginPath(); ctx.moveTo(padL, y(g)); ctx.lineTo(w - padR, y(g)); ctx.stroke();
    ctx.fillText(`${+g.toFixed(3)}`, padL - 4 * dpr, y(g) + 4 * dpr);
  }
  const ts = niceStep(t1 - t0, 5);
  ctx.textAlign = 'center';
  for (let g = Math.ceil(t0 / ts) * ts; g <= t1 + ts * 1e-6; g += ts) {
    ctx.beginPath(); ctx.moveTo(x(g), padT); ctx.lineTo(x(g), padT + plotH); ctx.stroke();
    ctx.fillText(fmtTime(Math.abs(g) < ts * 1e-6 ? 0 : g), x(g), h - 5 * dpr);
  }
  ctx.textAlign = 'left';
  ctx.fillText('V', 4 * dpr, padT + 10 * dpr);

  // Trigger level and position.
  if (trace.kind === 2) {
    ctx.strokeStyle = '#ffb020'; ctx.setLineDash([4 * dpr, 4 * dpr]);
    ctx.beginPath(); ctx.moveTo(padL, y(cfg.level)); ctx.lineTo(w - padR, y(cfg.level)); ctx.stroke();
    if (trace.trig >= 0) { ctx.beginPath(); ctx.moveTo(x(0), padT); ctx.lineTo(x(0), padT + plotH); ctx.stroke(); }
    ctx.setLineDash([]);
  }

  // The traces: at most one min/max pair per pixel column, so 10 000 samples
  // draw as fast as 500 and a narrow spike still shows.
  const offset = nAxis - n;                               // roll: empty on the left
  const cols = Math.max(1, Math.floor(plotW));
  const per = (nAxis - 1) / cols;
  const line = (arr, color) => {
    ctx.strokeStyle = color; ctx.lineWidth = 1.5 * dpr;
    ctx.beginPath();
    if (per <= 1) {
      for (let k = 0; k < n; k++) {
        const px = x(t0 + (k + offset) / rate);
        k ? ctx.lineTo(px, y(arr[k])) : ctx.moveTo(px, y(arr[k]));
      }
    } else {
      let started = false;
      for (let col = 0; col < cols; col++) {
        const a = Math.floor(col * per) - offset, b = Math.floor((col + 1) * per) - offset;
        if (b < 0 || a >= n) continue;
        let mn = Infinity, mx = -Infinity;
        for (let k = Math.max(0, a); k <= Math.min(n - 1, b); k++) { if (arr[k] < mn) mn = arr[k]; if (arr[k] > mx) mx = arr[k]; }
        const px = padL + col;
        if (!started) { ctx.moveTo(px, y(mn)); started = true; } else ctx.lineTo(px, y(mn));
        ctx.lineTo(px, y(mx));
      }
    }
    ctx.stroke();
  };
  if (v2) line(v2, COLOR_B);
  line(v, COLOR_A);

  ctx.textAlign = 'right';
  if (trace.kind === 2 && trace.trig < 0) {
    ctx.fillStyle = '#ffb020';
    ctx.fillText('untriggered', w - padR - 4 * dpr, padT + 12 * dpr);
  }
  if (v2) legend(ctx, w, padR, padT, dpr);
  ctx.textAlign = 'left';

  // Measurements, one block per input.
  const V = x => `${(Math.abs(x) < 5e-4 ? 0 : x).toFixed(3)} V`;   // no "-0.000"
  const cells = [['rate', fmtHz(rate)], ['samples', n]];
  const block = (arr, ch, cls) => {
    const m = measure(arr, rate);
    if (!m) return;
    const f = Number.isFinite(m.freq) ? fmtFreq(m.freq) : '–';
    cells.push(
      [`AI${ch} Vpp`, V(m.pp), cls], [`AI${ch} min`, V(m.lo), cls], [`AI${ch} max`, V(m.hi), cls],
      [`AI${ch} mean`, V(m.mean), cls], [`AI${ch} RMS (AC)`, V(m.acRms), cls], [`AI${ch} frequency`, f, cls],
    );
    // Section A's number: with the SMA shorted this is the noise floor (capture
    // 4000 in Auto); with a signal on the input it is just the signal's RMS.
    if (!cls) cells.push([`AI${ch} AC RMS in LSB`, trace.lsb > 0 ? `${(m.acRms / trace.lsb).toFixed(1)} LSB` : '–']);
  };
  block(v, trace.ch, '');
  if (v2) {
    block(v2, trace.ch2, 'b');
    const sp = spectrum(v, rate);
    if (sp && sp.peaks.length) {
      const f0 = sp.peaks[0].hz;
      const pg = phaseGain(v, v2, rate, f0);
      cells.push([`AI${trace.ch2} vs AI${trace.ch} at ${fmtFreq(f0)}`,
        `${pg.phase >= 0 ? '+' : ''}${pg.phase.toFixed(1)}° · ${pg.gain >= 0 ? '+' : ''}${pg.gain.toFixed(2)} dB`, 'wide']);
    }
  }
  showCells(cells);
}

function legend(ctx, w, padR, padT, dpr) {
  const y0 = padT + 26 * dpr;
  const bw = 34 * dpr;
  ctx.fillStyle = 'rgba(15, 17, 21, 0.85)';
  ctx.fillRect(w - padR - bw - 8 * dpr, y0 - 12 * dpr, bw + 6 * dpr, 30 * dpr);
  ctx.fillStyle = COLOR_A; ctx.fillText(`AI${trace.ch}`, w - padR - 4 * dpr, y0);
  ctx.fillStyle = COLOR_B; ctx.fillText(`AI${trace.ch2}`, w - padR - 4 * dpr, y0 + 14 * dpr);
}

function drawSpectrum(ctx, w, h, dpr) {
  const { v, v2, rate } = trace;
  const sa = spectrum(v, rate);
  const sb = v2 ? spectrum(v2, rate) : null;
  if (!sa) return;
  const half = sa.db.length - 1;
  const fMax = half * sa.binHz;
  let top = -Infinity;
  for (const s of sb ? [sa, sb] : [sa]) for (let k = 3; k <= half; k++) if (s.db[k] > top) top = s.db[k];
  top = Math.ceil((top + 5) / 20) * 20;
  const bottom = top - 120;                               // a 16-bit converter spans ~96 dB
  const padL = 44 * dpr, padR = 6 * dpr, padT = 8 * dpr, padB = 20 * dpr;
  const plotW = w - padL - padR, plotH = h - padT - padB;
  const x = hz => padL + (hz / fMax) * plotW;
  const y = db => padT + ((top - Math.max(bottom, Math.min(top, db))) / (top - bottom)) * plotH;

  ctx.strokeStyle = '#2a2f3a'; ctx.lineWidth = dpr; ctx.fillStyle = '#8b93a7';
  ctx.textAlign = 'right';
  for (let g = top; g >= bottom; g -= 20) {
    ctx.beginPath(); ctx.moveTo(padL, y(g)); ctx.lineTo(w - padR, y(g)); ctx.stroke();
    ctx.fillText(`${g}`, padL - 4 * dpr, y(g) + 4 * dpr);
  }
  const fs = niceStep(fMax, 5);
  ctx.textAlign = 'center';
  for (let g = 0; g <= fMax + fs * 1e-6; g += fs) {
    ctx.beginPath(); ctx.moveTo(x(g), padT); ctx.lineTo(x(g), padT + plotH); ctx.stroke();
    ctx.textAlign = x(g) > w - padR - 14 * dpr ? 'right' : 'center';     // keep the last label on the canvas
    ctx.fillText(g === 0 ? '0' : (g >= 1000 ? `${+(g / 1000).toFixed(2)}k` : `${+g.toFixed(1)}`), x(g), h - 5 * dpr);
  }
  ctx.textAlign = 'left';
  ctx.fillText('dBV', 4 * dpr, padT + 10 * dpr);

  const curve = (s, color) => {
    ctx.strokeStyle = color; ctx.lineWidth = 1.2 * dpr;
    ctx.beginPath();
    const cols = Math.max(1, Math.floor(plotW));
    const per = half / cols;
    if (per <= 1) {
      for (let k = 0; k <= half; k++) { const px = x(k * s.binHz); k ? ctx.lineTo(px, y(s.db[k])) : ctx.moveTo(px, y(s.db[k])); }
    } else {
      for (let col = 0; col < cols; col++) {                // the loudest bin per column: peaks never vanish
        let mx = -Infinity;
        for (let k = Math.floor(col * per); k <= Math.min(half, Math.floor((col + 1) * per)); k++) if (s.db[k] > mx) mx = s.db[k];
        col ? ctx.lineTo(padL + col, y(mx)) : ctx.moveTo(padL + col, y(mx));
      }
    }
    ctx.stroke();
  };
  if (sb) curve(sb, COLOR_B);
  curve(sa, COLOR_A);

  // Mark the strongest peak of the first input.
  const p = sa.peaks[0];
  if (p) {
    ctx.fillStyle = '#ffb020';
    ctx.beginPath(); ctx.arc(x(p.hz), y(p.db), 3.5 * dpr, 0, 2 * Math.PI); ctx.fill();
    ctx.textAlign = x(p.hz) > w * 0.7 ? 'right' : 'left';
    ctx.fillText(`${fmtFreq(p.hz)}  ${p.db.toFixed(1)} dBV`, x(p.hz) + (ctx.textAlign === 'left' ? 6 : -6) * dpr, y(p.db) - 6 * dpr);
  }
  ctx.textAlign = 'right';
  if (v2) legend(ctx, w, padR, padT, dpr);
  ctx.textAlign = 'left';

  const cells = [['rate', fmtHz(rate)], ['resolution', `${sa.binHz < 10 ? sa.binHz.toFixed(2) : sa.binHz.toFixed(1)} Hz/bin`],
    ['span', `0 – ${fmtFreq(fMax)}`]];
  sa.peaks.forEach((q, i) => cells.push([`AI${trace.ch} peak ${i + 1}`, `${fmtFreq(q.hz)} · ${q.db.toFixed(1)} dBV`]));
  if (sb) sb.peaks.slice(0, 2).forEach((q, i) => cells.push([`AI${trace.ch2} peak ${i + 1}`, `${fmtFreq(q.hz)} · ${q.db.toFixed(1)} dBV`, 'b']));
  showCells(cells);
}

function showCells(cells) {
  els.meas.innerHTML = cells.map(([k, val, cls]) =>
    `<div class="${cls === 'wide' ? 'wide' : ''}"><span class="muted">${k}</span><b class="${cls === 'b' ? 'b' : ''}">${val}</b></div>`).join('');
}

// What is on screen as CSV - the samples, or in the spectrum view the spectrum.
// Share sheet on a phone, a download elsewhere.
function exportCsv() {
  if (!trace || !trace.v.length) { api.toast('nothing to export yet', 'info'); return; }
  const { v, v2, rate } = trace;
  const names = v2 ? `AI${trace.ch} + AI${trace.ch2}` : `AI${trace.ch}`;
  let lines;
  if (cfg.view === 'spectrum') {
    const sa = spectrum(v, rate), sb = v2 ? spectrum(v2, rate) : null;
    if (!sa) { api.toast('too few samples for a spectrum', 'info'); return; }
    lines = [`# b1 ${names}, ${rate} S/s, spectrum (Hann, mean removed), dBV`,
      v2 ? `f_hz,ai${trace.ch}_dbv,ai${trace.ch2}_dbv` : `f_hz,ai${trace.ch}_dbv`];
    for (let k = 0; k < sa.db.length; k++) {
      lines.push(`${(k * sa.binHz).toPrecision(8)},${sa.db[k].toFixed(2)}${sb ? ',' + sb.db[k].toFixed(2) : ''}`);
    }
  } else {
    const t0 = trace.kind === 2 && trace.trig >= 0 ? -trace.trig / rate : 0;
    lines = [`# b1 ${names}, ${rate} S/s, ${trace.kind === 1 ? 'roll' : 'capture'}${trace.trig >= 0 ? ', t = 0 at the trigger' : ''}`,
      v2 ? `t_s,ai${trace.ch}_volts,ai${trace.ch2}_volts` : 't_s,volts'];
    for (let k = 0; k < v.length; k++) {
      lines.push(`${(t0 + k / rate).toPrecision(8)},${v[k].toFixed(5)}${v2 ? ',' + v2[k].toFixed(5) : ''}`);
    }
  }
  const tag = v2 ? `ai${trace.ch}-ai${trace.ch2}` : `ai${trace.ch}`;
  const name = `${tag}${cfg.view === 'spectrum' ? '-spectrum' : ''}-${new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)}.csv`;
  const blob = new Blob([lines.join('\n') + '\n'], { type: 'text/csv' });
  const file = typeof File === 'function' ? new File([blob], name, { type: 'text/csv' }) : null;
  if (file && navigator.canShare?.({ files: [file] })) {
    navigator.share({ files: [file], title: name }).catch(() => {});
    return;
  }
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = name;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
