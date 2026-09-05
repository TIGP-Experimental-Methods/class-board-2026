// Panel for b2_power: the five rails.
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
      <h3>Alarm</h3>
      <div class="row"><button class="btn" id="alarm">v5_raw &lt; 4.9 V → notify</button></div>`;
    kv = el.querySelector('#kv');
    el.querySelector('#alarm').onclick = () =>
      api.addAlarm({ block: 'b2', key: 'v5_raw', op: 'lt', threshold: 4.9, action: 'notify' })
        .then(r => api.toast(`alarm rule ${r.id} added`, 'info')).catch(e => api.toast(e.message));
    el.querySelector('#note').textContent = '';
    this._note = el.querySelector('#note');
  },

  onStatus(st) {
    kv.innerHTML = RAILS.map(([k, label]) => `<span>${label}</span><span>${(st[k] ?? 0).toFixed(3)} V</span>`).join('');
    this._note.textContent = st.measured ? '' : 'Board v0.6 has no rail sensing: these are nominal design values.';
  },
};
