// Panel for the "base" block: LED colour + brightness, counter, chip info.
// Exercise E2 adds one control + readouts here (and its handler + status keys in BaseBlock.cpp):
// default = an N input (1..1024) for set_avg and live adc_v (mean of the newest N samples, V) /
// adc_sd (the noise of one N-sample average, V) readouts (workbook ch. 1 A.4).
//
// A panel is a plain object: { id, title, render(container, api), onStatus(status) }.
//   render    builds the DOM once, when the tab is opened
//   onStatus  is called 20x per second with this block's status object
let els = {};

export default {
  id: 'base',
  title: 'Base',

  render(el, api) {
    el.innerHTML = `
      <h2>Base</h2>
      <p class="help">The dev board itself: RGB LED, a counter, chip temperature.</p>

      <h3>LED</h3>
      <div class="row">
        <button class="btn" data-rgb="255,0,0">Red</button>
        <button class="btn" data-rgb="0,255,0">Green</button>
        <button class="btn" data-rgb="0,0,255">Blue</button>
        <button class="btn" data-rgb="0,0,0">Off</button>
        <input type="color" id="led-color" value="#0000ff" title="pick a colour">
      </div>
      <div class="row">
        <label>brightness</label>
        <input type="range" id="led-bri" min="0" max="255" value="40">
        <span class="value" id="led-bri-val">40</span>
      </div>

      <h3>Signal</h3>
      <div class="row">
        <label>counter</label><span class="value" id="counter">-</span>
        <button class="btn" id="counter-reset">Reset</button>
      </div>
      <!-- TODO(E2): add your control + readouts here (workbook ch. 1 A.4). Default:
           <div class="row"><label>N</label><input type="number" id="avg-n" value="16" min="1" max="1024">
                <button class="btn primary" id="avg-set">Set</button></div>
           <div class="kv"><span>mean</span><span id="adc-v">-</span><span>sd</span><span id="adc-sd">-</span></div>
           then add to els below: adcV: el.querySelector('#adc-v'), adcSd: el.querySelector('#adc-sd'),
           then: el.querySelector('#avg-set').onclick = () => api.send('base', 'set_avg', { n: Number(el.querySelector('#avg-n').value) });
           and in onStatus(st): els.adcV.textContent = st.adc_v?.toFixed(3) + ' V'; els.adcSd.textContent = (st.adc_sd * 1000)?.toFixed(2) + ' mV'; -->

      <h3>Board</h3>
      <div class="kv" id="kv"></div>`;

    els = {
      counter: el.querySelector('#counter'),
      kv: el.querySelector('#kv'),
      bri: el.querySelector('#led-bri'),
      briVal: el.querySelector('#led-bri-val'),
    };

    for (const btn of el.querySelectorAll('[data-rgb]')) {
      const [r, g, b] = btn.dataset.rgb.split(',').map(Number);
      btn.onclick = () => api.send('base', 'led', { r, g, b }).catch(e => api.toast(e.message));
    }
    el.querySelector('#led-color').oninput = (ev) => {
      const hex = ev.target.value;
      api.send('base', 'led', { r: parseInt(hex.slice(1, 3), 16), g: parseInt(hex.slice(3, 5), 16), b: parseInt(hex.slice(5, 7), 16) });
    };
    els.bri.oninput = () => { els.briVal.textContent = els.bri.value; api.send('base', 'brightness', { value: Number(els.bri.value) }); };
    el.querySelector('#counter-reset').onclick = () => api.send('base', 'counter_reset');
  },

  onStatus(st) {
    els.counter.textContent = st.counter ?? '-';
    els.kv.innerHTML = `
      <span>temperature</span><span>${st.temp_c?.toFixed(1)} °C</span>
      <span>uptime</span><span>${st.uptime_s} s</span>
      <span>RSSI</span><span>${st.rssi} dBm</span>
      <span>free heap</span><span>${((st.heap_free ?? 0) / 1024).toFixed(0)} kB</span>
      <span>AP clients</span><span>${st.clients}</span>`;
  },
};
