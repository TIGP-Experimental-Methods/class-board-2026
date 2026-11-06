// push: set up the chat webhook that the alarm action "push" sends to.
//
// The three presets fill in the shape of each service; you still paste your own
// token. Nothing typed here is echoed back by the board - status reports only
// whether something is configured and which host, so a screenshot of this panel
// cannot leak the token.
let els = {};

const PRESETS = {
  telegram: {
    url:  'https://api.telegram.org/bot<TOKEN>/sendMessage',
    auth: '',
    body: '{"chat_id":"<CHAT_ID>","text":"{msg}"}',
    help: 'Make a bot with @BotFather, then message it once and read your chat id from ' +
          'https://api.telegram.org/bot&lt;TOKEN&gt;/getUpdates',
  },
  line: {
    url:  'https://api.line.me/v2/bot/message/push',
    auth: 'Bearer <CHANNEL_ACCESS_TOKEN>',
    body: '{"to":"<USER_ID>","messages":[{"type":"text","text":"{msg}"}]}',
    help: 'LINE Notify was withdrawn in March 2025, so this is the Messaging API: ' +
          'a channel in the LINE Developers console gives you the token, and your own ' +
          'user id comes from the channel&rsquo;s Basic settings.',
  },
  discord: {
    url:  'https://discord.com/api/webhooks/<ID>/<TOKEN>',
    auth: '',
    body: '{"content":"{msg}"}',
    help: 'Channel &rarr; Edit Channel &rarr; Integrations &rarr; Webhooks &rarr; New Webhook, then Copy Webhook URL.',
  },
};

export default {
  id: 'push',
  title: 'Push',

  render(el, api) {
    el.innerHTML = `
      <h2>Chat webhook</h2>
      <p class="help">An alarm rule whose action is <code>push</code> sends one line here.
      Only works when the board joined your WiFi &mdash; on its own access point there is
      no route out.</p>

      <div class="row">
        <label>service</label>
        <select id="p-preset">
          <option value="telegram">Telegram</option>
          <option value="line">LINE</option>
          <option value="discord">Discord</option>
        </select>
      </div>
      <p class="help" id="p-help"></p>

      <div class="row"><label>url</label><input type="text" id="p-url" style="flex:1"></div>
      <div class="row"><label>auth</label><input type="text" id="p-auth" style="flex:1"
        placeholder="Authorization header, blank if the token is in the url"></div>
      <div class="row"><label>body</label><input type="text" id="p-body" style="flex:1"></div>
      <p class="help"><code>{msg}</code> is replaced with the alarm line, JSON-escaped.</p>

      <div class="row">
        <button class="btn primary" id="p-save">Save</button>
        <button class="btn" id="p-test">Send a test</button>
        <button class="btn" id="p-clear">Forget</button>
      </div>

      <h3>State</h3>
      <div class="kv">
        <span>configured</span><span id="p-cfg">-</span>
        <span>host</span><span id="p-host">-</span>
        <span>sent</span><span id="p-sent">-</span>
        <span>failed</span><span id="p-failed">-</span>
        <span>last code</span><span id="p-code">-</span>
        <span>last error</span><span id="p-err">-</span>
      </div>

      <p class="help"><strong>The token is a secret.</strong> It is stored only on the board&rsquo;s
      own filesystem, never in the repository, and the board never sends it back &mdash; which is
      also why this form comes up blank after a reload. The connection does not check the
      server&rsquo;s certificate, so treat the token as something a determined listener on the
      network could take.</p>`;

    const $ = id => el.querySelector(id);
    els = { cfg: $('#p-cfg'), host: $('#p-host'), sent: $('#p-sent'),
            failed: $('#p-failed'), code: $('#p-code'), err: $('#p-err') };

    const applyPreset = () => {
      const p = PRESETS[$('#p-preset').value];
      $('#p-url').value = p.url;
      $('#p-auth').value = p.auth;
      $('#p-body').value = p.body;
      $('#p-help').innerHTML = p.help;
    };
    $('#p-preset').onchange = applyPreset;
    applyPreset();

    $('#p-save').onclick = () =>
      api.send('push', 'set', {
        url: $('#p-url').value.trim(),
        auth: $('#p-auth').value.trim(),
        body: $('#p-body').value.trim(),
      }).then(r => api.toast(`saved: ${r.host}`, 'info'))
        .catch(e => api.toast(e.message));

    $('#p-test').onclick = () =>
      api.send('push', 'test', { text: 'test from the instrument' })
        .then(() => api.toast('queued - watch sent / failed below', 'info'))
        .catch(e => api.toast(e.message));

    $('#p-clear').onclick = () =>
      api.send('push', 'clear').then(() => api.toast('forgotten', 'info'))
        .catch(e => api.toast(e.message));
  },

  onStatus(st) {
    els.cfg.textContent    = st.configured ? 'yes' : 'no';
    els.host.textContent   = st.host || '-';
    els.sent.textContent   = st.sent ?? '-';
    els.failed.textContent = st.failed ?? '-';
    els.code.textContent   = st.code ?? '-';
    els.err.textContent    = st.error || '-';
  },
};
