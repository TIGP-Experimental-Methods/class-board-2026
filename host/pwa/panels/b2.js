// Panel for b2_power: the five rails and +VEXT.
//
// +VEXT is measured on GPIO4 through the sense divider of the 2026-10-08
// rework (B6). The NMR console refuses to transmit outside 6.5..25 V while the
// check is on; a board without the divider reads noise there, so the check can
// be switched off (until the next restart).
let kv;

const RAILS = [['v5_raw', '+5V_RAW'], ['v3v3', '+3V3'], ['v12p', '+12V'], ['v12n', '−12V'], ['v5a', '+5VA']];

export default {
  id: 'b2',
  title: 'B2 Power',

  render(el, api) {
    el.innerHTML = `
      <h2>B2 Power &amp; rails</h2>
      <p class="help">USB-C / 5 V jack → +5V_RAW; AMS1117 → +3V3; two isolated modules → ±12 V; 78L05 → +5VA.</p>
      <div class="kv" id="kv"></div>
      <p class="help" id="note"></p>
      <h3>+VEXT</h3>
      <div class="kv"><span>+VEXT (bench supply)</span><span id="vext">-</span></div>
      <div class="row">
        <label class="muted"><input type="checkbox" id="vext-check"> check +VEXT before the NMR console transmits</label>
      </div>
      <p class="help">Turn the check off on a board without the sense divider: there the reading is noise.</p>
      <h3>Alarm</h3>
      <div class="row"><button class="btn" id="alarm">v5_raw &lt; 4.9 V → notify</button></div>`;
    kv = el.querySelector('#kv');
    el.querySelector('#alarm').onclick = () =>
      api.addAlarm({ block: 'b2', key: 'v5_raw', op: 'lt', threshold: 4.9, action: 'notify' })
        .then(r => api.toast(`alarm rule ${r.id} added`, 'info')).catch(e => api.toast(e.message));
    el.querySelector('#note').textContent = '';
    this._note = el.querySelector('#note');
    this._vext = el.querySelector('#vext');
    this._vextCheck = el.querySelector('#vext-check');
    this._vextCheck.onchange = () =>
      api.send('b2', 'vext_check', { on: this._vextCheck.checked }).catch(e => api.toast(e.message));
  },

  onStatus(st) {
    kv.innerHTML = RAILS.map(([k, label]) => `<span>${label}</span><span>${(st[k] ?? 0).toFixed(3)} V</span>`).join('');
    this._note.textContent = st.measured ? '' : 'Board v0.7 has no rail sensing: these are nominal design values.';
    this._vext.textContent = st.vext_measured && typeof st.vext === 'number' ? `${st.vext.toFixed(1)} V` : 'not measured';
    // Do not fight the user's finger while the command is on its way.
    if (typeof st.vext_check === 'boolean' && document.activeElement !== this._vextCheck) this._vextCheck.checked = st.vext_check;
  },
};
