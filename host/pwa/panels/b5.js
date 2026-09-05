// Panel for b5_dio_trig: 8 TTL outputs, TRIG direction/level, 2 fast outputs.
let els = {};

export default {
  id: 'b5',
  title: 'B5 DIO/TRIG',

  render(el, api) {
    el.innerHTML = `
      <h2>B5 Digital I/O &amp; timing</h2>
      <p class="help">8 × 5 V TTL outputs, 2 fast outputs, one switchable TRIG SMA.</p>
      <h3>TTL outputs</h3>
      <div class="grid" id="dio"></div>
      <h3>TRIG</h3>
      <div class="row">
        <button class="btn" id="trig-dir">direction: input</button>
        <button class="btn" id="trig-level">level</button>
        <span class="value" id="trig-now">-</span>
      </div>
      <h3>Fast outputs</h3>
      <div class="row">
        <select id="fast-n"><option value="1">FAST 1</option><option value="2">FAST 2</option></select>
        <input type="number" id="fast-hz" value="1000" min="0" step="100"> Hz
        <button class="btn primary" id="fast-set">Set</button>
      </div>`;

    const err = (e) => api.toast(e.message);
    els.dio = el.querySelector('#dio');
    els.dio.innerHTML = Array.from({ length: 8 }, (_, i) => `<button class="btn" data-n="${i + 1}">DIO ${i + 1}</button>`).join('');
    for (const btn of els.dio.children)
      btn.onclick = () => api.send('b5', 'dio', { n: Number(btn.dataset.n), level: !btn.classList.contains('on') }).catch(err);

    els.dir = el.querySelector('#trig-dir');
    els.level = el.querySelector('#trig-level');
    els.now = el.querySelector('#trig-now');
    els.dir.onclick = () => api.send('b5', 'trig_dir', { out: !els.dir.classList.contains('on') }).catch(err);
    els.level.onclick = () => api.send('b5', 'trig', { level: !els.level.classList.contains('on') }).catch(err);

    el.querySelector('#fast-set').onclick = () =>
      api.send('b5', 'fast_out', { n: Number(el.querySelector('#fast-n').value), freq_hz: Number(el.querySelector('#fast-hz').value) }).catch(err);
  },

  onStatus(st) {
    for (const btn of els.dio.children) btn.classList.toggle('on', !!st['dio' + btn.dataset.n]);
    els.dir.classList.toggle('on', !!st.trig_dir);
    els.dir.textContent = 'direction: ' + (st.trig_dir ? 'output' : 'input');
    els.level.classList.toggle('on', !!st.trig);
    els.now.textContent = `TRIG=${st.trig ? 1 : 0} · fast ${st.fast1_hz ?? 0} / ${st.fast2_hz ?? 0} Hz`;
  },
};
