// Panel for the "base" block: LED colour + brightness, counter, chip info.
// Exercise E1 adds one more control here (and its handler in BaseBlock.cpp).
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
      <!-- TODO(E1): add your control here, e.g. a text field that sends {"cmd":"hello","args":{"text":...}} -->

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
