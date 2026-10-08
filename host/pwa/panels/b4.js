// Panel for b4_switching: seven module outputs, two isolated inputs, and the
// two coil switches of the main board (field-cycling H-bridge, polarizer).
let els = {};

const MODULES = [1, 2, 3, 4, 5, 6, 7];
const HB_MODES = ['off', 'fwd', 'rev', 'brake'];
const POLARIZER_MAX_MS = 10000;   // the firmware refuses to keep the coil on longer

export default {
  id: 'b4',
  title: 'B4 Switching',

  render(el, api) {
    el.innerHTML = `
      <h2>B4 Power and switching</h2>
      <p class="help">Seven module outputs (5 V logic on the module header), two isolated inputs, and the coil switches on the main board.</p>
      <h3>Module outputs</h3>
      <div class="grid" id="modules"></div>
      <div class="row">
        <button class="btn" id="all-off">All off</button>
        <button class="btn" id="all-on">All on</button>
      </div>
      <h3>Isolated inputs</h3>
      <div class="kv" id="opto"></div>
      <div class="row"><button class="btn" id="opto-reset">Reset counts</button></div>
      <h3>H-bridge</h3>
      <div class="row" id="hbridge"></div>
      <h3>Polarizer</h3>
      <p class="help">Caution: the coil switch has no hardware limit; only this timer switches the coil off.</p>
      <div class="row">
        <label>time</label>
        <input type="number" id="pol-ms" value="1000" min="1" max="${POLARIZER_MAX_MS}" step="100"> ms
      </div>
      <div class="row">
        <button class="btn primary" id="pol-on">On for this time</button>
        <button class="btn" id="pol-off">Off</button>
        <span class="value" id="pol-now">-</span>
      </div>`;

    const err = (e) => api.toast(e.message);

    els.modules = el.querySelector('#modules');
    els.modules.innerHTML = MODULES.map(n => `<button class="btn" data-n="${n}">Module ${n}</button>`).join('');
    for (const btn of els.modules.children)
      btn.onclick = () => api.send('b4', 'module', { n: Number(btn.dataset.n), on: !btn.classList.contains('on') }).catch(err);
    el.querySelector('#all-off').onclick = () => api.send('b4', 'module_all', { on: false }).catch(err);
    el.querySelector('#all-on').onclick = () => api.send('b4', 'module_all', { on: true }).catch(err);

    els.opto = el.querySelector('#opto');
    el.querySelector('#opto-reset').onclick = () => api.send('b4', 'opto_reset').catch(err);

    els.hbridge = el.querySelector('#hbridge');
    els.hbridge.innerHTML = HB_MODES.map(m => `<button class="btn" data-mode="${m}">${m}</button>`).join('');
    for (const btn of els.hbridge.children)
      btn.onclick = () => api.send('b4', 'hbridge', { mode: btn.dataset.mode }).catch(err);

    const msInput = el.querySelector('#pol-ms');
    els.polNow = el.querySelector('#pol-now');
    el.querySelector('#pol-on').onclick = () => {
      const ms = Math.min(POLARIZER_MAX_MS, Math.max(1, Math.round(Number(msInput.value) || 0)));
      msInput.value = ms;
      api.send('b4', 'polarizer', { on: true, ms })
        .then(r => api.toast(`polarizer on for ${r.ms} ms`, 'info')).catch(err);
    };
    el.querySelector('#pol-off').onclick = () => api.send('b4', 'polarizer', { on: false }).catch(err);
  },

  onStatus(st) {
    for (const btn of els.modules.children) btn.classList.toggle('on', !!st['module' + btn.dataset.n]);
    for (const btn of els.hbridge.children) btn.classList.toggle('on', st.hbridge === btn.dataset.mode);
    // The 6N137 output is active low: a lit LED means current flows in the input.
    els.opto.innerHTML = `
      <span>input 1 <i class="led ${st.opto1_level ? '' : 'on'}"></i></span><span>${st.opto1 ?? 0} falling edges</span>
      <span>input 2 <i class="led ${st.opto2_level ? '' : 'on'}"></i></span><span>${st.opto2 ?? 0} falling edges</span>`;
    els.polNow.textContent = st.polarizer ? 'coil on' : 'coil off';
  },
};
