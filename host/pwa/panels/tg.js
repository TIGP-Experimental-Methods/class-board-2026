// Panel for the "tg" block: talk to the instrument from Telegram.
//
// Three steps, shown one at a time:
//   1. the board needs the internet - it must have joined a WiFi (your phone's
//      hotspot works), not be running its own access point;
//   2. paste the bot token from @BotFather (stored on the board, never shown again);
//   3. pair: open the bot from the link below - Telegram sends "/start <code>"
//      for you - and from then on the instrument obeys that chat only.
// Nothing typed here comes back from the board: status says whether a token is
// set, never what it is.
let els = {};
let api = null;

export default {
  id: 'tg',
  title: 'Telegram',

  render(el, a) {
    api = a;
    el.innerHTML = `
      <style>
        .tg-state { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin: 4px 0 10px; font-size: 14px; }
        .tg-badge { border: 1px solid var(--line); border-radius: 12px; padding: 2px 10px; font-size: 13px; }
        .tg-badge.ok { border-color: var(--ok); color: var(--ok); }
        .tg-badge.warn { border-color: var(--warn); color: var(--warn); }
        .tg-badge.bad { border-color: var(--bad); color: var(--bad); }
        .tg-step { border: 1px solid var(--line); border-radius: 10px; padding: 10px 12px; margin: 10px 0; }
        .tg-step h3 { margin-top: 0; }
        .tg-code { font-size: 24px; letter-spacing: .08em; white-space: nowrap; font-variant-numeric: tabular-nums; color: var(--accent); margin: 4px 0 8px; }
        .tg-step input[type=password] { flex: 1; min-width: 180px; }
        a.tg-link { display: inline-flex; align-items: center; min-height: 44px; padding: 8px 16px; border-radius: 8px;
          background: var(--accent); color: #06111f; text-decoration: none; font-weight: 600; }
        .tg-cmds { display: grid; grid-template-columns: auto 1fr; gap: 4px 12px; font-size: 13px; color: var(--muted); }
        .tg-cmds code { color: var(--text); white-space: nowrap; }
      </style>
      <h2>Telegram</h2>
      <div class="tg-state" id="state"></div>

      <div class="tg-step" id="s-wifi">
        <h3>1 · Internet</h3>
        <p class="help">The board is running its own access point, so it cannot reach Telegram. Copy
          <code>firmware/include/secrets.h.example</code> to <code>secrets.h</code>, put your phone hotspot's
          name and password in it (2.4 GHz), flash again, and open this page at the address the board prints.</p>
      </div>

      <div class="tg-step" id="s-token">
        <h3>2 · Bot token</h3>
        <p class="help">From @BotFather (<code>/newbot</code>). It is stored on the board and never shown again;
          a new token forgets the paired chat.</p>
        <div class="row">
          <input id="token" type="password" autocomplete="off" placeholder="123456789:AA…">
          <button class="btn primary" id="save">Save</button>
        </div>
        <div class="row"><button class="btn" id="clear">Forget token</button></div>
      </div>

      <div class="tg-step" id="s-pair">
        <h3>3 · Pair your chat</h3>
        <p class="help">Tap the button: Telegram opens your bot, press <b>Start</b>. Or send it this yourself:</p>
        <div class="tg-code" id="code">––––––</div>
        <div class="row"><a class="tg-link" id="link" target="_blank" rel="noopener">Open in Telegram</a></div>
      </div>

      <div class="tg-step" id="s-done">
        <h3>Paired</h3>
        <p class="help">The instrument answers this chat only. An alarm rule with action <code>push</code>
          (or one made in Telegram with <code>/alarm ai1 &gt; 3.5</code>) messages you there.</p>
        <div class="row">
          <button class="btn" id="test">Send a test message</button>
          <button class="btn" id="unpair">Unpair</button>
        </div>
      </div>

      <h3>Commands</h3>
      <div class="tg-cmds">
        <code>/status</code><span>the instrument at a glance</span>
        <code>/read</code><span>all eight inputs</span>
        <code>/read AI3</code><span>one input</span>
        <code>/module 1 on</code><span>a module output (off too)</span>
        <code>/led blue</code><span>red, green, blue, white, off</span>
        <code>/alarms</code><span>the alarm rules</span>
        <code>/alarm ai1 &gt; 3.5</code><span>message me when it happens</span>
        <code>/unalarm 2</code><span>delete rule 2</span>
        <code>/unpair</code><span>stop obeying this chat</span>
      </div>`;

    els = {
      state: el.querySelector('#state'), wifi: el.querySelector('#s-wifi'), tokenStep: el.querySelector('#s-token'),
      pair: el.querySelector('#s-pair'), done: el.querySelector('#s-done'), code: el.querySelector('#code'),
      link: el.querySelector('#link'), token: el.querySelector('#token'),
    };
    const err = e => api.toast(e.message || String(e));
    el.querySelector('#save').onclick = () => {
      const token = els.token.value.trim();
      if (!token) return;
      api.send('tg', 'set_token', { token })
        .then(() => { els.token.value = ''; api.toast('token saved on the board', 'info'); })
        .catch(err);
    };
    el.querySelector('#clear').onclick = () => {
      if (!confirm('Forget the bot token and the paired chat?')) return;
      api.send('tg', 'clear').then(() => api.toast('token forgotten', 'info')).catch(err);
    };
    el.querySelector('#test').onclick = () =>
      api.send('tg', 'test', { text: 'Test message from the instrument panel.' })
        .then(() => api.toast('sent - check Telegram', 'info')).catch(err);
    el.querySelector('#unpair').onclick = () => {
      if (!confirm('Unpair? The instrument will ignore the chat until you pair again.')) return;
      api.send('tg', 'unpair').then(() => api.toast('unpaired', 'info')).catch(err);
    };
  },

  onStatus(st) {
    if (!els.state?.isConnected) return;
    const badge = (text, cls) => `<span class="tg-badge ${cls}">${text}</span>`;
    const stateCls = { online: 'ok', connecting: 'warn', 'no internet': 'bad', 'no token': '', error: 'bad' }[st.state] ?? '';
    const parts = [badge(st.state ?? '–', stateCls)];
    if (st.bot) parts.push(`@${st.bot}`);
    parts.push(st.paired ? badge('paired', 'ok') : badge('not paired', ''));
    parts.push(`<span class="muted">in ${st.received ?? 0} · out ${st.sent ?? 0}${st.errors ? ' · errors ' + st.errors : ''}</span>`);
    if (st.error) parts.push(`<span class="muted" style="color:var(--bad)">${escapeHtml(st.error)}</span>`);
    els.state.innerHTML = parts.join(' ');

    els.wifi.style.display = st.wifi ? 'none' : '';
    els.tokenStep.style.display = st.paired ? 'none' : '';
    const pairing = st.token && !st.paired;
    els.pair.style.display = pairing ? '' : 'none';
    els.done.style.display = st.paired ? '' : 'none';
    if (pairing) {
      els.code.textContent = st.code ? `/start ${st.code}` : '––––––';
      // t.me/<bot>?start=<code> opens the bot with a Start button that sends
      // "/start <code>" - pairing in one tap.
      if (st.bot && st.code) els.link.href = `https://t.me/${encodeURIComponent(st.bot)}?start=${st.code}`;
      els.link.style.visibility = st.bot && st.code ? 'visible' : 'hidden';
    }
  },
};

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
}
