// Panel for b3_outputs: DC or sine on AO1 / AO2.
let els = {};

export default {
  id: 'b3',
  title: 'B3 Outputs',

  render(el, api) {
    el.innerHTML = `
      <h2>B3 Signal generation</h2>
      <p class="help">DAC8563 + OPA2192: two ±10 V outputs. Pick <code>b3.ao1</code> in the chart.</p>
      <div class="row">
        <label>channel</label>
        <select id="ch"><option value="1">AO1</option><option value="2">AO2</option></select>
        <span class="value" id="now">-</span>
      </div>
      <h3>DC</h3>
      <div class="row">
        <input type="number" id="dc" value="2.5" step="0.1" min="-10" max="10"> V
        <button class="btn primary" id="set-dc">Set DC</button>
      </div>
      <h3>Sine</h3>
      <div class="row">
        <label>freq</label><input type="number" id="freq" value="0.5" step="0.1" min="0.01"> Hz
      </div>
      <div class="row">
        <label>amp</label><input type="number" id="amp" value="5" step="0.5" min="0" max="10"> V
      </div>
      <div class="row">
        <label>offset</label><input type="number" id="off" value="0" step="0.5" min="-10" max="10"> V
      </div>
      <div class="row">
        <button class="btn primary" id="sine">Start sine</button>
        <button class="btn" id="stop">Off</button>
      </div>`;

    const v = (id) => Number(el.querySelector('#' + id).value);
    const ch = () => v('ch');
    els.now = el.querySelector('#now');
    els.ch = el.querySelector('#ch');
    const err = (e) => api.toast(e.message);

    el.querySelector('#set-dc').onclick = () => api.send('b3', 'set_dc', { ch: ch(), volts: v('dc') }).catch(err);
    el.querySelector('#sine').onclick = () =>
      api.send('b3', 'sine', { ch: ch(), freq: v('freq'), amp: v('amp'), offset: v('off') }).catch(err);
    el.querySelector('#stop').onclick = () => api.send('b3', 'off', { ch: ch() }).catch(err);
  },

  onStatus(st) {
    const c = els.ch.value;
    els.now.textContent = `${(st['ao' + c] ?? 0).toFixed(3)} V · ${st['mode' + c] ?? ''}`;
  },
};
