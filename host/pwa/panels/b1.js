// Panel for b1_inputs: eight input voltages and the range selector.
let els = {};

export default {
  id: 'b1',
  title: 'B1 Inputs',

  render(el, api) {
    el.innerHTML = `
      <h2>B1 Precision inputs</h2>
      <p class="help">ADS8688, 8 × ±10 V, 16 bit. Pick <code>b1.ai1</code> in the chart to see the waveform.</p>
      <div class="grid" id="ai"></div>
      <h3>Range (ch 1)</h3>
      <div class="row">
        <select id="range">
          <option value="0">±10 V</option><option value="1">±5 V</option><option value="2">±2.5 V</option>
          <option value="5">0–10 V</option><option value="6">0–5 V</option>
        </select>
        <button class="btn" id="read">read_all</button>
      </div>
      <h3>Alarm</h3>
      <div class="row"><button class="btn" id="alarm">ai1 &gt; 3.5 V → relay 1 on</button></div>`;

    els.ai = el.querySelector('#ai');
    els.ai.innerHTML = Array.from({ length: 8 }, (_, i) =>
      `<div class="kv"><span>AI${i + 1}</span><span id="ai${i + 1}">-</span></div>`).join('');

    el.querySelector('#range').onchange = (ev) =>
      api.send('b1', 'set_range', { ch: 1, range: Number(ev.target.value) }).catch(e => api.toast(e.message));
    el.querySelector('#read').onclick = () =>
      api.send('b1', 'read_all').then(r => api.toast('ai = ' + r.ai.map(v => v.toFixed(2)).join(', '), 'info'));
    el.querySelector('#alarm').onclick = () =>
      api.addAlarm({ block: 'b1', key: 'ai1', op: 'gt', threshold: 3.5, action: 'relay:1:on' })
        .then(r => api.toast(`alarm rule ${r.id} added`, 'info')).catch(e => api.toast(e.message));
  },

  onStatus(st) {
    for (let i = 1; i <= 8; i++) {
      const s = els.ai.querySelector(`#ai${i}`);
      if (s) s.textContent = (st['ai' + i] ?? 0).toFixed(3) + ' V';
    }
  },
};
