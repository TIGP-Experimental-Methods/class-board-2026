// Panel for the "nmr" block: the NMR console.
//
// What it does: you set the transmit and local-oscillator frequencies and the
// pulse, press Start, and the board runs a scan set. After every scan the board
// sends the averaged free induction decay (FID) as a binary frame (kind 3, see
// firmware/PROTOCOL.md section 7). This panel draws the FID in time and its
// spectrum, which it computes here in the browser with a small FFT.
//
// The record is a complex signal z = I + jQ at the intermediate frequency
// (IF = f_tx - f_lo), so a positive peak in the spectrum means the line sits
// above the local oscillator. The Larmor frequency is f_lo + peak.
//
// A panel is a plain object: { id, title, render(container, api), onStatus(st) }.
let els = {};
let api = null;

// The newest record from the board, and what we worked out from it.
let record = null; // { rate_hz, n, if_hz, scans, i: Float32Array, q: Float32Array }
let spectrum = null; // { freq: Float32Array, mag: Float32Array, peak, peakHz, noise, snrDb }
let fLoStatus = null; // f_lo_hz from the status broadcast, when the board reports it

// These are wired once for the life of the page: the binary frames keep coming
// while another tab is open, and the canvases must survive a phone rotation.
let wired = false;

const DEFAULTS = {
  f_tx_hz: 89400,
  f_lo_hz: 84000,
  sequence: 'fid',
  t90_us: 417,
  t_acq_ms: 2000,
  n_avg: 1,
  cyclops: true,
  polarize_ms: 0,
};

const MAX_FFT = 16384; // the longest transform we are willing to do on a phone

export default {
  id: 'nmr',
  title: 'NMR',

  render(el, a) {
    api = a;
    el.innerHTML = `
      <style>
        .nmr-form { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 8px 12px; }
        .nmr-form label { display: flex; flex-direction: column; gap: 4px; color: var(--muted); font-size: 13px; }
        .nmr-form input, .nmr-form select { width: 100%; min-height: 44px; }
        .nmr-form .check { flex-direction: row; align-items: center; gap: 8px; min-height: 44px; }
        .nmr-form .check input { width: 22px; height: 22px; min-height: 22px; }
        .nmr-actions .btn { min-height: 44px; flex: 1 1 auto; min-width: 96px; }
        .nmr-prog { font-size: 13px; font-variant-numeric: tabular-nums; margin: 8px 0 2px; }
        .nmr-prog .bad { color: var(--bad); }
        .nmr-prog .warn { color: var(--warn); }
        .nmr-legend { display: flex; gap: 14px; font-size: 12px; color: var(--muted); margin-top: 2px; }
        .nmr-legend i { display: inline-block; width: 12px; height: 3px; vertical-align: middle; margin-right: 4px; }
        canvas.nmr-plot { height: 190px; }
        @media (max-width: 400px) {
          .nmr-form { grid-template-columns: 1fr 1fr; }
          .nmr-actions { flex-direction: column; align-items: stretch; }
          canvas.nmr-plot { height: 165px; }
        }
      </style>

      <h2>NMR console</h2>
      <p class="help">Pulse the coil, catch the free induction decay, average scans.
        The spectrum is computed here from the record the board sends.</p>

      <h3>Settings</h3>
      <div class="nmr-form">
        <label>transmit f_tx (Hz)<input type="number" id="f-tx" step="1"></label>
        <label>local osc. f_lo (Hz)<input type="number" id="f-lo" step="1"></label>
        <label>sequence<select id="seq"><option value="fid">FID</option><option value="echo">echo</option></select></label>
        <label>90&deg; pulse t90 (&micro;s)<input type="number" id="t90" step="1" min="1"></label>
        <label>record length (ms)<input type="number" id="t-acq" step="10" min="10" max="4000"></label>
        <label>scans to average<input type="number" id="n-avg" step="1" min="1" max="256"></label>
        <label>polarize (ms)<input type="number" id="polarize" step="10" min="0"></label>
        <label class="check"><input type="checkbox" id="cyclops"> CYCLOPS phase cycling</label>
      </div>
      <div class="row">
        <button class="btn" id="apply">Apply settings</button>
        <span class="value" id="if-now">-</span>
      </div>

      <h3>Run</h3>
      <div class="row nmr-actions">
        <button class="btn primary" id="start">Start</button>
        <button class="btn" id="abort">Abort</button>
        <button class="btn" id="pulse">Pulse</button>
        <label class="muted">t (&micro;s)<input type="number" id="pulse-us" value="417" min="1" max="5000" step="1"></label>
      </div>
      <p class="nmr-prog" id="prog">idle</p>

      <h3>FID</h3>
      <canvas id="fid" class="nmr-plot"></canvas>
      <div class="nmr-legend">
        <span><i style="background:#e6e8ee"></i>|z|</span>
        <span><i style="background:#4fa3ff"></i>I</span>
        <span><i style="background:#ffb020"></i>Q</span>
        <span id="fid-info"></span>
      </div>

      <h3>Spectrum</h3>
      <canvas id="spec" class="nmr-plot"></canvas>
      <div class="nmr-legend"><span id="spec-info">no record yet</span></div>`;

    els = {
      fTx: el.querySelector('#f-tx'),
      fLo: el.querySelector('#f-lo'),
      seq: el.querySelector('#seq'),
      t90: el.querySelector('#t90'),
      tAcq: el.querySelector('#t-acq'),
      nAvg: el.querySelector('#n-avg'),
      polarize: el.querySelector('#polarize'),
      cyclops: el.querySelector('#cyclops'),
      ifNow: el.querySelector('#if-now'),
      prog: el.querySelector('#prog'),
      pulseUs: el.querySelector('#pulse-us'),
      fid: el.querySelector('#fid'),
      fidInfo: el.querySelector('#fid-info'),
      spec: el.querySelector('#spec'),
      specInfo: el.querySelector('#spec-info'),
    };

    // Start from the last settings this phone used, else the defaults.
    const saved = loadSettings();
    els.fTx.value = saved.f_tx_hz;
    els.fLo.value = saved.f_lo_hz;
    els.seq.value = saved.sequence;
    els.t90.value = saved.t90_us;
    els.tAcq.value = saved.t_acq_ms;
    els.nAvg.value = saved.n_avg;
    els.polarize.value = saved.polarize_ms;
    els.cyclops.checked = !!saved.cyclops;
    els.pulseUs.value = saved.t90_us;
    showIf();

    const err = (e) => api.toast(e.message);
    for (const input of [els.fTx, els.fLo]) input.oninput = showIf;

    el.querySelector('#apply').onclick = () => sendConfig().catch(err);
    el.querySelector('#start').onclick = () =>
      sendConfig()
        .then(() => api.send('nmr', 'start'))
        .then(() => api.toast('scan set started', 'info'))
        .catch(err);
    el.querySelector('#abort').onclick = () => api.send('nmr', 'abort').catch(err);
    el.querySelector('#pulse').onclick = () =>
      api.send('nmr', 'pulse', { t_us: Number(els.pulseUs.value) }).catch(err);

    if (!wired) {
      wired = true;
      // Binary frames arrive on the same WebSocket; app.js parses the header
      // and hands us the fields plus the payload as a DataView.
      api.on('binary', (f) => {
        if (f.kind !== 3) return;
        takeRecord(f);
        redraw();
      });
      // A phone rotation changes the canvas width, so draw again.
      window.addEventListener('resize', redraw);
      window.addEventListener('orientationchange', redraw);
    }

    redraw();
  },

  onStatus(st) {
    if (typeof st.f_lo_hz === 'number') fLoStatus = st.f_lo_hz;

    const state = st.state ?? 'idle';
    const parts = [`state: <b>${state}</b>`];
    if (st.n_avg) parts.push(`scan ${st.scan ?? 0} / ${st.n_avg}`);
    if (st.rate_hz) parts.push(`${(st.rate_hz / 1000).toFixed(1)} kS/s`);
    if (typeof st.snr_db === 'number' && isFinite(st.snr_db)) parts.push(`SNR ${st.snr_db.toFixed(1)} dB (board)`);
    if (st.i_flag) parts.push('<span class="bad">CURRENT LIMIT</span>');
    if (st.t_flag) parts.push('<span class="bad">THERMAL</span>');
    if (st.sim) parts.push('<span class="warn">SIM</span>');
    if (st.error) parts.push(`<span class="bad">${escapeHtml(String(st.error))}</span>`);
    els.prog.innerHTML = parts.join(' &middot; ');
  },
};

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------
function formSettings() {
  return {
    f_tx_hz: Number(els.fTx.value),
    f_lo_hz: Number(els.fLo.value),
    sequence: els.seq.value,
    t90_us: Number(els.t90.value),
    t_acq_ms: Number(els.tAcq.value),
    n_avg: Number(els.nAvg.value),
    polarize_ms: Number(els.polarize.value),
    cyclops: els.cyclops.checked,
  };
}

function sendConfig() {
  const s = formSettings();
  try {
    localStorage.setItem('nmrSettings', JSON.stringify(s));
  } catch {
    // A private window may refuse to store anything; the settings still apply.
  }
  return api.send('nmr', 'config', s).then((r) => {
    // The board replies with what it really programmed; show that.
    if (typeof r.f_tx_actual_hz === 'number') els.fTx.value = Math.round(r.f_tx_actual_hz);
    if (typeof r.f_lo_actual_hz === 'number') els.fLo.value = Math.round(r.f_lo_actual_hz);
    showIf();
    return r;
  });
}

function loadSettings() {
  try {
    return { ...DEFAULTS, ...JSON.parse(localStorage.getItem('nmrSettings') || '{}') };
  } catch {
    return { ...DEFAULTS };
  }
}

function showIf() {
  const hz = Number(els.fTx.value) - Number(els.fLo.value);
  els.ifNow.textContent = `IF = ${(hz / 1000).toFixed(3)} kHz`;
}

// The local oscillator the axis labels are relative to: what the board reports,
// else what the form says (the form is what we asked the board for).
function loFrequency() {
  if (typeof fLoStatus === 'number' && fLoStatus > 0) return fLoStatus;
  const v = Number(els.fLo?.value);
  return isFinite(v) && v > 0 ? v : DEFAULTS.f_lo_hz;
}

function escapeHtml(s) {
  return s.replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' })[c]);
}

// ---------------------------------------------------------------------------
// The record and its spectrum
// ---------------------------------------------------------------------------
// One kind-3 frame: n complex samples as float32 pairs (I, Q) in volts.
function takeRecord(f) {
  const n = Math.min(f.n, Math.floor(f.payload.byteLength / 8));
  const i = new Float32Array(n);
  const q = new Float32Array(n);
  for (let k = 0; k < n; k++) {
    i[k] = f.payload.getFloat32(k * 8, true);
    q[k] = f.payload.getFloat32(k * 8 + 4, true);
  }
  record = {
    rate_hz: f.rate_hz || 1,
    n,
    if_hz: f.offset_v, // the IF the board programmed, f_tx - f_lo
    scans: f.trig_index, // scans averaged so far
    i,
    q,
  };
  spectrum = computeSpectrum(record);
}

// Radix-2 complex FFT, in place, length a power of two.
function fft(re, im) {
  const n = re.length;
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) {
      let t = re[i];
      re[i] = re[j];
      re[j] = t;
      t = im[i];
      im[i] = im[j];
      im[j] = t;
    }
  }
  for (let len = 2; len <= n; len <<= 1) {
    const ang = (-2 * Math.PI) / len;
    const wr = Math.cos(ang);
    const wi = Math.sin(ang);
    const half = len >> 1;
    for (let i = 0; i < n; i += len) {
      let cr = 1;
      let ci = 0;
      for (let k = 0; k < half; k++) {
        const ur = re[i + k];
        const ui = im[i + k];
        const xr = re[i + k + half];
        const xi = im[i + k + half];
        const vr = xr * cr - xi * ci;
        const vi = xr * ci + xi * cr;
        re[i + k] = ur + vr;
        im[i + k] = ui + vi;
        re[i + k + half] = ur - vr;
        im[i + k + half] = ui - vi;
        const ncr = cr * wr - ci * wi;
        ci = cr * wi + ci * wr;
        cr = ncr;
      }
    }
  }
}

// Hann window, zero pad to a power of two, transform, shift so the frequency
// axis runs from -rate/2 to +rate/2 with 0 Hz (the local oscillator) in the middle.
function computeSpectrum(rec) {
  const nUse = Math.min(rec.n, MAX_FFT);
  if (nUse < 8) return null;
  let nfft = 1;
  while (nfft < nUse) nfft <<= 1;
  if (nfft > MAX_FFT) nfft = MAX_FFT;

  const re = new Float64Array(nfft);
  const im = new Float64Array(nfft);
  let wsum = 0;
  for (let k = 0; k < nUse; k++) {
    const w = 0.5 - 0.5 * Math.cos((2 * Math.PI * k) / (nUse - 1));
    wsum += w;
    re[k] = rec.i[k] * w;
    im[k] = rec.q[k] * w;
  }
  fft(re, im);

  // Amplitude scaling: a sine of amplitude A gives a bin of A after this.
  const scale = wsum > 0 ? 2 / wsum : 1;
  const df = rec.rate_hz / nfft;
  const freq = new Float32Array(nfft);
  const mag = new Float32Array(nfft);
  const halfN = nfft >> 1;
  for (let k = 0; k < nfft; k++) {
    const src = (k + halfN) % nfft; // fftshift: negative frequencies first
    const binF = src < halfN ? src : src - nfft;
    freq[k] = binF * df;
    mag[k] = Math.hypot(re[src], im[src]) * scale;
  }

  // Peak, ignoring the few bins around 0 Hz where any leftover DC sits.
  const guard = Math.max(2, Math.round(2 / df));
  let peak = 0;
  let peakK = -1;
  for (let k = 0; k < nfft; k++) {
    if (Math.abs(freq[k]) < guard * df) continue;
    if (mag[k] > peak) {
      peak = mag[k];
      peakK = k;
    }
  }
  if (peakK < 0) return null;

  // Noise: the median magnitude away from the peak, which a stray line cannot drag up.
  const away = [];
  const skip = Math.max(4, Math.round(nfft / 100));
  for (let k = 0; k < nfft; k++) if (Math.abs(k - peakK) > skip) away.push(mag[k]);
  away.sort((a, b) => a - b);
  const median = away.length ? away[away.length >> 1] : 0;
  // A median of magnitudes of complex Gaussian noise is about 1.18 sigma.
  const noise = median / 1.177;
  const snrDb = noise > 0 ? 20 * Math.log10(peak / noise) : Infinity;

  return { freq, mag, nfft, df, peak, peakHz: freq[peakK], peakK, noise, snrDb };
}

// ---------------------------------------------------------------------------
// Drawing
// ---------------------------------------------------------------------------
function prepare(canvas) {
  // Match the canvas pixels to the screen pixels so lines and text stay sharp.
  const dpr = window.devicePixelRatio || 1;
  const w = Math.max(1, Math.round(canvas.clientWidth * dpr));
  const h = Math.max(1, Math.round(canvas.clientHeight * dpr));
  if (canvas.width !== w || canvas.height !== h) {
    canvas.width = w;
    canvas.height = h;
  }
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, w, h);
  ctx.font = `${11 * dpr}px system-ui, sans-serif`;
  return { ctx, w, h, dpr };
}

function emptyPlot(ctx, w, h, dpr, text) {
  ctx.fillStyle = '#8b93a7';
  ctx.textAlign = 'center';
  ctx.fillText(text, w / 2, h / 2);
  ctx.textAlign = 'left';
  ctx.strokeStyle = '#2a2f3a';
  ctx.lineWidth = dpr;
  ctx.strokeRect(0.5, 0.5, w - 1, h - 1);
}

function redraw() {
  if (!els.fid || !els.fid.isConnected) return;
  drawFid();
  drawSpectrum();
}

function drawFid() {
  const { ctx, w, h, dpr } = prepare(els.fid);
  if (!record) {
    emptyPlot(ctx, w, h, dpr, 'no record yet - press Start');
    els.fidInfo.textContent = '';
    return;
  }
  const { i, q, n, rate_hz } = record;
  const padL = 42 * dpr;
  const padR = 6 * dpr;
  const padT = 8 * dpr;
  const padB = 18 * dpr;
  const plotW = w - padL - padR;
  const plotH = h - padT - padB;

  let amax = 1e-9;
  for (let k = 0; k < n; k++) {
    const a = Math.hypot(i[k], q[k]);
    if (a > amax) amax = a;
  }
  const tEndMs = (n / rate_hz) * 1000;
  const x = (k) => padL + (k / Math.max(1, n - 1)) * plotW;
  const y = (v) => padT + plotH / 2 - (v / amax) * (plotH / 2 - 2 * dpr);

  // Frame and the zero line.
  ctx.strokeStyle = '#2a2f3a';
  ctx.lineWidth = dpr;
  ctx.strokeRect(padL, padT, plotW, plotH);
  ctx.beginPath();
  ctx.moveTo(padL, y(0));
  ctx.lineTo(padL + plotW, y(0));
  ctx.stroke();

  // One pixel column can hold many samples on a phone, so draw the min and max
  // of each column instead of every point.
  const trace = (get, colour, width) => {
    ctx.strokeStyle = colour;
    ctx.lineWidth = width * dpr;
    ctx.beginPath();
    const cols = Math.max(2, Math.round(plotW));
    for (let c = 0; c < cols; c++) {
      const k0 = Math.floor((c / cols) * n);
      const k1 = Math.max(k0 + 1, Math.floor(((c + 1) / cols) * n));
      let lo = Infinity;
      let hi = -Infinity;
      for (let k = k0; k < k1 && k < n; k++) {
        const v = get(k);
        if (v < lo) lo = v;
        if (v > hi) hi = v;
      }
      if (lo === Infinity) continue;
      const px = padL + (c / cols) * plotW;
      ctx.moveTo(px, y(lo));
      ctx.lineTo(px, y(hi));
    }
    ctx.stroke();
  };
  trace((k) => i[k], '#4fa3ff', 1);
  trace((k) => q[k], '#ffb020', 1);
  trace((k) => Math.hypot(i[k], q[k]), '#e6e8ee', 1.5);

  // Labels: amplitude in mV on the left, time in ms along the bottom.
  ctx.fillStyle = '#8b93a7';
  ctx.fillText(`${(amax * 1000).toPrecision(3)} mV`, 2 * dpr, padT + 10 * dpr);
  ctx.fillText('0', 2 * dpr, y(0) + 4 * dpr);
  for (let f = 0; f <= 1.0001; f += 0.25) {
    const ms = tEndMs * f;
    const px = padL + f * plotW;
    ctx.textAlign = f === 0 ? 'left' : f > 0.99 ? 'right' : 'center';
    ctx.fillText(`${ms.toFixed(ms < 10 ? 1 : 0)} ms`, px, h - 5 * dpr);
  }
  ctx.textAlign = 'left';

  const scans = record.scans > 0 ? record.scans : 1;
  els.fidInfo.textContent = `${n} pts @ ${(record.rate_hz / 1000).toFixed(2)} kS/s · ${scans} scan${scans === 1 ? '' : 's'} averaged`;
}

function drawSpectrum() {
  const { ctx, w, h, dpr } = prepare(els.spec);
  if (!spectrum) {
    emptyPlot(ctx, w, h, dpr, 'no spectrum yet');
    els.specInfo.textContent = 'no record yet';
    return;
  }
  const { freq, mag, nfft, peak, peakHz, peakK, noise, snrDb } = spectrum;
  const padL = 42 * dpr;
  const padR = 6 * dpr;
  const padT = 8 * dpr;
  const padB = 30 * dpr; // two label rows: Hz from the LO, then Larmor Hz
  const plotW = w - padL - padR;
  const plotH = h - padT - padB;

  // Show a window around the peak so the line is easy to see, but never less
  // than a few hundred Hz and never more than the whole spectrum.
  const span = Math.min(freq[nfft - 1] - freq[0], Math.max(400, Math.abs(peakHz) * 4));
  const centre = Math.abs(peakHz) < span / 2 ? 0 : peakHz;
  const f0 = centre - span / 2;
  const f1 = centre + span / 2;
  const x = (f) => padL + ((f - f0) / (f1 - f0)) * plotW;
  const y = (v) => padT + plotH - (v / (peak * 1.1)) * plotH;

  ctx.strokeStyle = '#2a2f3a';
  ctx.lineWidth = dpr;
  ctx.strokeRect(padL, padT, plotW, plotH);

  ctx.strokeStyle = '#4fa3ff';
  ctx.lineWidth = 1.2 * dpr;
  ctx.beginPath();
  let started = false;
  for (let k = 0; k < nfft; k++) {
    if (freq[k] < f0 || freq[k] > f1) continue;
    const px = x(freq[k]);
    const py = y(mag[k]);
    if (started) ctx.lineTo(px, py);
    else {
      ctx.moveTo(px, py);
      started = true;
    }
  }
  ctx.stroke();

  // Where the board said the line should be (the programmed IF), dashed.
  const ifHz = record?.if_hz;
  if (typeof ifHz === 'number' && isFinite(ifHz) && ifHz >= f0 && ifHz <= f1) {
    ctx.save();
    ctx.setLineDash([4 * dpr, 4 * dpr]);
    ctx.strokeStyle = '#8b93a7';
    ctx.beginPath();
    ctx.moveTo(x(ifHz), padT);
    ctx.lineTo(x(ifHz), padT + plotH);
    ctx.stroke();
    ctx.restore();
  }

  // The peak marker.
  if (peakK >= 0 && peakHz >= f0 && peakHz <= f1) {
    const px = x(peakHz);
    const py = y(peak);
    ctx.strokeStyle = '#3ddc84';
    ctx.lineWidth = 1.5 * dpr;
    ctx.beginPath();
    ctx.arc(px, py, 4 * dpr, 0, 2 * Math.PI);
    ctx.stroke();
    ctx.fillStyle = '#3ddc84';
    ctx.textAlign = px > padL + plotW * 0.7 ? 'right' : 'left';
    ctx.fillText(`${peakHz.toFixed(1)} Hz`, px + (ctx.textAlign === 'right' ? -6 * dpr : 6 * dpr), py - 6 * dpr);
    ctx.textAlign = 'left';
  }

  // Two rows of x labels: Hz from the local oscillator, then absolute Larmor Hz.
  const fLo = loFrequency();
  ctx.fillStyle = '#8b93a7';
  for (let n = 0; n <= 4; n++) {
    const f = f0 + ((f1 - f0) * n) / 4;
    const px = x(f);
    ctx.textAlign = n === 0 ? 'left' : n === 4 ? 'right' : 'center';
    ctx.fillText(fmtHz(f), px, h - 17 * dpr);
    ctx.fillText(((fLo + f) / 1000).toFixed(2), px, h - 4 * dpr);
  }
  ctx.textAlign = 'left';
  ctx.fillText('kHz Larmor', 2 * dpr, h - 4 * dpr);
  ctx.fillText('Hz - LO', 2 * dpr, h - 17 * dpr);
  ctx.fillText(`${(peak * 1e6).toPrecision(3)} µV`, 2 * dpr, padT + 10 * dpr);

  // SNR in the corner.
  ctx.fillStyle = '#e6e8ee';
  ctx.textAlign = 'right';
  ctx.fillText(`SNR ${isFinite(snrDb) ? snrDb.toFixed(1) : '--'} dB`, w - 8 * dpr, padT + 10 * dpr);
  ctx.textAlign = 'left';

  const larmor = fLo + peakHz;
  els.specInfo.textContent =
    `peak ${peakHz.toFixed(1)} Hz from the LO · Larmor ${(larmor / 1000).toFixed(3)} kHz · ` +
    `amplitude ${(peak * 1e6).toPrecision(3)} µV · noise ${(noise * 1e6).toPrecision(3)} µV · ` +
    `SNR ${isFinite(snrDb) ? snrDb.toFixed(1) : '--'} dB`;
}

function fmtHz(f) {
  const a = Math.abs(f);
  if (a >= 1000) return `${(f / 1000).toFixed(1)}k`;
  return f.toFixed(a < 10 ? 1 : 0);
}
