// watch: drift and excursion monitor on one analog input.
//
// The alarm section is deliberately a chooser rather than a fixed button. E11
// wants the alarm rule to be the student's, and which of these values is worth
// alarming on depends entirely on what is plugged into the input:
//   dev        the reading has moved - the usual one
//   drift      it is walking, caught long before dev crosses anything
//   rms        the noise itself went up, which is an instrument fault, not a
//              measurement; a connector going intermittent shows here first
//   excursions a burst of spikes the mean hides
let els = {};

const FMT = { v: 4, mean: 4, rms: 5, pp: 4, dev: 4, drift: 4, baseline: 4 };

export default {
  id: 'watch',
  title: 'Watch',

  render(el, api) {
    el.innerHTML = `
      <h2>Input watch</h2>
      <p class="help">Watches one analog input over a window and publishes values
      that are worth alarming on. A rule on the raw voltage fires on the first
      noise peak; a rule on <code>dev</code> or <code>drift</code> fires when the
      signal has actually moved.</p>

      <h3>What to watch</h3>
      <div class="row">
        <label>input</label>
        <select id="w-ch">
          ${[1,2,3,4,5,6,7,8].map(n => `<option value="${n}">AI${n}</option>`).join('')}
        </select>
        <button class="btn" id="w-ch-set">Select</button>
      </div>
      <div class="row">
        <label>window</label>
        <input type="number" id="w-win" value="10" min="1" max="30" step="1">
        <span class="help">s</span>
        <button class="btn" id="w-win-set">Set</button>
      </div>
      <div class="row">
        <label>excursion</label>
        <input type="number" id="w-sigma" value="3" min="1" max="10" step="0.5">
        <span class="help">&sigma;</span>
        <button class="btn" id="w-sigma-set">Set</button>
      </div>
      <div class="row">
        <button class="btn primary" id="w-zero">Zero here</button>
        <button class="btn" id="w-reset">Reset window</button>
      </div>

      <h3>Reading</h3>
      <div class="kv">
        <span>v</span><span id="w-v">-</span>
        <span>mean</span><span id="w-mean">-</span>
        <span>dev from baseline</span><span id="w-dev">-</span>
        <span>drift (V/min)</span><span id="w-drift">-</span>
        <span>rms noise</span><span id="w-rms">-</span>
        <span>peak-peak</span><span id="w-pp">-</span>
        <span>excursions</span><span id="w-exc">-</span>
        <span>samples</span><span id="w-n">-</span>
      </div>

      <h3>Alarm</h3>
      <p class="help">Pick the value and the threshold yourself - which one matters
      depends on what is on the input.</p>
      <div class="row">
        <select id="w-key">
          <option value="dev">dev</option>
          <option value="drift">drift</option>
          <option value="rms">rms</option>
          <option value="excursions">excursions</option>
        </select>
        <select id="w-op">
          <option value="gt">&gt;</option>
          <option value="lt">&lt;</option>
        </select>
        <input type="number" id="w-thr" value="0.05" step="0.01">
        <button class="btn" id="w-alarm">Add rule</button>
      </div>`;

    els = {
      v:     el.querySelector('#w-v'),
      mean:  el.querySelector('#w-mean'),
      dev:   el.querySelector('#w-dev'),
      drift: el.querySelector('#w-drift'),
      rms:   el.querySelector('#w-rms'),
      pp:    el.querySelector('#w-pp'),
      exc:   el.querySelector('#w-exc'),
      n:     el.querySelector('#w-n'),
      ch:    el.querySelector('#w-ch'),
    };

    const send = (cmd, args) => api.send('watch', cmd, args).catch(e => api.toast(e.message));

    el.querySelector('#w-ch-set').onclick =
      () => send('set_input', { ch: Number(el.querySelector('#w-ch').value) });
    el.querySelector('#w-win-set').onclick =
      () => send('set_window', { s: Number(el.querySelector('#w-win').value) });
    el.querySelector('#w-sigma-set').onclick =
      () => send('set_sigma', { k: Number(el.querySelector('#w-sigma').value) });
    el.querySelector('#w-zero').onclick  = () => send('zero');
    el.querySelector('#w-reset').onclick = () => send('reset');

    el.querySelector('#w-alarm').onclick = () =>
      api.addAlarm({
        block: 'watch',
        key: el.querySelector('#w-key').value,
        op: el.querySelector('#w-op').value,
        threshold: Number(el.querySelector('#w-thr').value),
        action: 'notify',
      })
        .then(r => api.toast(`alarm rule ${r.id} added`, 'info'))
        .catch(e => api.toast(e.message));
  },

  onStatus(st) {
    const put = (node, key) =>
      node.textContent = st[key] == null ? '-' : st[key].toFixed(FMT[key] ?? 3);
    put(els.v, 'v');
    put(els.mean, 'mean');
    put(els.dev, 'dev');
    put(els.drift, 'drift');
    put(els.rms, 'rms');
    put(els.pp, 'pp');
    els.exc.textContent = st.excursions ?? '-';
    els.n.textContent   = st.n ?? '-';
    if (st.ch != null) els.ch.value = String(st.ch);
  },
};
