// Panel for b4_switching: four relay toggles, two opto counters.
let els = {};

export default {
  id: 'b4',
  title: 'B4 Relays',

  render(el, api) {
    el.innerHTML = `
      <h2>B4 Isolated switching</h2>
      <p class="help">4 relays (≤ 30 V DC, 1 A) and 2 isolated fast inputs.</p>
      <h3>Relays</h3>
      <div class="grid" id="relays"></div>
      <div class="row"><button class="btn" id="all-off">All off</button></div>
      <h3>Opto inputs</h3>
      <div class="kv" id="opto"></div>
      <div class="row"><button class="btn" id="opto-reset">Reset counts</button></div>`;

    els.relays = el.querySelector('#relays');
    els.opto = el.querySelector('#opto');
    els.relays.innerHTML = [1, 2, 3, 4].map(n => `<button class="btn" data-n="${n}">Relay ${n}</button>`).join('');
    for (const btn of els.relays.children) {
      btn.onclick = () => api.send('b4', 'relay', { n: Number(btn.dataset.n), on: !btn.classList.contains('on') })
        .catch(e => api.toast(e.message));
    }
    el.querySelector('#all-off').onclick = () => api.send('b4', 'relay_all', { on: false });
    el.querySelector('#opto-reset').onclick = () => api.send('b4', 'opto_reset');
  },

  onStatus(st) {
    for (const btn of els.relays.children) btn.classList.toggle('on', !!st['relay' + btn.dataset.n]);
    els.opto.innerHTML = `
      <span>opto 1 <i class="led ${st.opto1_level ? '' : 'on'}"></i></span><span>${st.opto1 ?? 0} edges</span>
      <span>opto 2 <i class="led ${st.opto2_level ? '' : 'on'}"></i></span><span>${st.opto2 ?? 0} edges</span>`;
  },
};
