// TEMPLATE PANEL - copy to panels/b<N>.js, then:
//   1. id: 'b<N>', title: your block's name
//   2. replace the example control (set_value) with your block's commands
//   3. replace the example status value; every status key you show must be
//      one your block's status() emits
//   4. add the import + PANELS entry in app.js
// The "Alarm" button shows how a block offers its one alarm rule (E11).
let els = {};

export default {
  id: 'template',
  title: 'Template',

  render(el, api) {
    el.innerHTML = `
      <h2>Template block</h2>
      <p class="help">Copy me. One command, one status value, one alarm.</p>

      <h3>Example command</h3>
      <div class="row">
        <label>setpoint</label>
        <input type="number" id="tpl-set" value="2.5" step="0.1">
        <button class="btn primary" id="tpl-send">Set</button>
      </div>

      <h3>Example status</h3>
      <div class="kv">
        <span>value</span><span id="tpl-value">-</span>
        <span>setpoint</span><span id="tpl-setpoint">-</span>
      </div>

      <h3>Alarm hook</h3>
      <div class="row">
        <button class="btn" id="tpl-alarm">Notify when value &gt; 5</button>
      </div>`;

    els = { value: el.querySelector('#tpl-value'), setpoint: el.querySelector('#tpl-setpoint') };

    el.querySelector('#tpl-send').onclick = () =>
      api.send('template', 'set_value', { value: Number(el.querySelector('#tpl-set').value) })
        .catch(e => api.toast(e.message));

    // TODO: change block/key/op/threshold/action to something meaningful for your block.
    el.querySelector('#tpl-alarm').onclick = () =>
      api.addAlarm({ block: 'template', key: 'value', op: 'gt', threshold: 5, action: 'notify' })
        .then(r => api.toast(`alarm rule ${r.id} added`, 'info'))
        .catch(e => api.toast(e.message));
  },

  onStatus(st) {
    els.value.textContent = st.value?.toFixed(3) ?? '-';
    els.setpoint.textContent = st.setpoint?.toFixed(2) ?? '-';
  },
};
