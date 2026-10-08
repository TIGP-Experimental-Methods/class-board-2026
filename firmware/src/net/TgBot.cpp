#include "TgBot.h"

#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <Preferences.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>

namespace tg {
namespace {

const char* kNamespace = "tg";
const char* kApi = "https://api.telegram.org/bot";
constexpr int kInQueue = 6;
constexpr int kOutQueue = 6;
constexpr int kOutMax = 640;              // characters in one reply
constexpr uint16_t kPollSeconds = 20;     // long-poll length
constexpr uint32_t kReplyWaitMs = 2000;   // after a message, how long to wait for its reply

struct Outbound {
  int64_t chat;
  char text[kOutMax];
};

QueueHandle_t in_ = nullptr, out_ = nullptr;
portMUX_TYPE mux_ = portMUX_INITIALIZER_UNLOCKED;

// Shared between the main task and the bot task; copied under mux_.
char token_[64] = "";
int64_t chat_ = 0;
volatile bool tokenChanged_ = true;       // the task re-runs getMe and the boot skip

String bot_, lastError_;
const char* volatile state_ = "no token";
volatile uint32_t received_ = 0, sent_ = 0, errors_ = 0;

String tokenCopy() {
  char t[sizeof token_];
  portENTER_CRITICAL(&mux_);
  memcpy(t, token_, sizeof t);
  portEXIT_CRITICAL(&mux_);
  return String(t);
}

void fail(const String& why) {
  errors_ = errors_ + 1;
  lastError_ = why;
  state_ = "error";
}

void saveNvs() {
  Preferences p;
  if (!p.begin(kNamespace, false)) return;
  portENTER_CRITICAL(&mux_);
  const String t(token_);
  const int64_t c = chat_;
  portEXIT_CRITICAL(&mux_);
  p.putString("token", t);
  p.putLong64("chat", c);
  p.end();
}

void loadNvs() {
  Preferences p;
  if (!p.begin(kNamespace, true)) return;   // absent on a fresh board
  const String t = p.getString("token", "");
  const int64_t c = p.getLong64("chat", 0);
  p.end();
  portENTER_CRITICAL(&mux_);
  strlcpy(token_, t.c_str(), sizeof token_);
  chat_ = c;
  portEXIT_CRITICAL(&mux_);
}

// ---- HTTPS -----------------------------------------------------------------
// One TLS connection, kept alive between requests: a handshake costs about a
// second, a long poll every 20 s would otherwise pay it every time.
WiFiClientSecure client_;

// GET or POST `method` with an optional JSON body; the parsed reply in `doc`.
// Returns the HTTP code (negative for a client error).
int call(const String& token, const String& method, const String& body, JsonDocument& doc,
         const JsonDocument* filter, uint16_t timeout_ms) {
  HTTPClient http;
  http.setReuse(true);
  http.setTimeout(timeout_ms);
  http.setConnectTimeout(8000);
  if (!http.begin(client_, String(kApi) + token + "/" + method)) return -100;
  int code;
  if (body.length()) {
    http.addHeader("Content-Type", "application/json");
    code = http.POST(body);
  } else {
    code = http.GET();
  }
  if (code > 0) {
    const String payload = http.getString();
    DeserializationError e = filter ? deserializeJson(doc, payload, DeserializationOption::Filter(*filter))
                                    : deserializeJson(doc, payload);
    if (e) doc.clear();
  } else {
    client_.stop();                       // a broken connection: start clean next time
  }
  http.end();
  return code;
}

String describe(int code, const JsonDocument& doc) {
  if (code == 401 || code == 404) return "token rejected by Telegram - make a new one with @BotFather";
  if (code == 409) return "another program is reading this bot's messages (two boards with one token?)";
  if (code < 0) return String("network: ") + HTTPClient::errorToString(code);
  const char* d = doc["description"] | "";
  return String("HTTP ") + code + (*d ? String(": ") + d : String(""));
}

bool getMe(const String& token) {
  JsonDocument doc;
  const int code = call(token, "getMe", "", doc, nullptr, 10000);
  if (code != 200 || !(doc["ok"] | false)) { fail(describe(code, doc)); return false; }
  bot_ = doc["result"]["username"] | "";
  return true;
}

bool sendOne(const String& token, const Outbound& m) {
  JsonDocument req;
  req["chat_id"] = m.chat;
  req["text"] = m.text;
  req["disable_web_page_preview"] = true;
  String body;
  serializeJson(req, body);
  JsonDocument doc;
  const int code = call(token, "sendMessage", body, doc, nullptr, 10000);
  if (code == 200 && (doc["ok"] | false)) { sent_ = sent_ + 1; return true; }
  fail(describe(code, doc));
  return false;
}

void drainOutbox(const String& token, uint32_t wait_ms) {
  Outbound m;
  // The first message may take up to wait_ms to appear; the rest are already there.
  while (xQueueReceive(out_, &m, pdMS_TO_TICKS(wait_ms)) == pdTRUE) {
    sendOne(token, m);
    wait_ms = 0;
  }
}

// Long poll. Fills the inbound queue; returns how many messages it queued, or
// -1 on an error.
int64_t offset_ = 0;
int poll(const String& token, uint16_t seconds) {
  JsonDocument filter;
  filter["ok"] = true;
  filter["description"] = true;
  JsonObject u = filter["result"].add<JsonObject>();
  u["update_id"] = true;
  u["message"]["chat"]["id"] = true;
  u["message"]["text"] = true;
  u["message"]["from"]["first_name"] = true;

  String q = String("getUpdates?timeout=") + seconds + "&limit=5&allowed_updates=%5B%22message%22%5D";
  if (offset_) q += String("&offset=") + String(static_cast<long long>(offset_));
  JsonDocument doc;
  const int code = call(token, q, "", doc, &filter, (seconds + 10) * 1000);
  if (code != 200 || !(doc["ok"] | false)) { fail(describe(code, doc)); return -1; }

  int n = 0;
  for (JsonObject upd : doc["result"].as<JsonArray>()) {
    const int64_t id = upd["update_id"] | 0LL;
    if (id >= offset_) offset_ = id + 1;     // confirm it, whatever it was
    JsonObject msg = upd["message"];
    const char* text = msg["text"] | "";
    if (!*text) continue;                    // a photo, a sticker: nothing to do
    Inbound in;
    in.chat = msg["chat"]["id"] | 0LL;
    strlcpy(in.text, text, sizeof in.text);
    strlcpy(in.from, msg["from"]["first_name"] | "", sizeof in.from);
    if (xQueueSend(in_, &in, 0) == pdTRUE) { received_ = received_ + 1; n++; }
  }
  return n;
}

// After a boot (or a new token), confirm everything already waiting, unread:
// a "/module 1 on" typed while the board was off must not switch anything
// minutes or hours later. offset = -1 returns only the newest update; confirming
// past it drops the lot.
bool skipBacklog(const String& token) {
  JsonDocument filter;
  filter["ok"] = true;
  filter["result"][0]["update_id"] = true;
  JsonDocument doc;
  const int code = call(token, "getUpdates?offset=-1&timeout=0", "", doc, &filter, 10000);
  if (code != 200 || !(doc["ok"] | false)) { fail(describe(code, doc)); return false; }
  JsonArray r = doc["result"].as<JsonArray>();
  offset_ = r.size() ? (r[0]["update_id"] | 0LL) + 1 : 0;
  return true;
}

void task(void*) {
  // No certificate check, as in net/Push.cpp and for the same reason: pinning
  // Telegram's root would mean shipping and updating a CA bundle. The price is
  // that someone on the path could read the token; say so in the write-up.
  client_.setInsecure();
  bool ready = false;                       // getMe done and the backlog skipped
  for (;;) {
    const String token = tokenCopy();
    if (token.isEmpty()) { state_ = "no token"; ready = false; vTaskDelay(pdMS_TO_TICKS(1000)); continue; }
    if (WiFi.status() != WL_CONNECTED) { state_ = "no internet"; ready = false; vTaskDelay(pdMS_TO_TICKS(2000)); continue; }
    if (tokenChanged_) { tokenChanged_ = false; ready = false; client_.stop(); bot_ = ""; }

    if (!ready) {
      state_ = "connecting";
      if (!getMe(token) || !skipBacklog(token)) {
        // A rejected token will not get better by asking again every second.
        vTaskDelay(pdMS_TO_TICKS(lastError_.startsWith("token rejected") ? 30000 : 5000));
        continue;
      }
      ready = true;
      lastError_ = "";
      int64_t chat;
      portENTER_CRITICAL(&mux_);
      chat = chat_;
      portEXIT_CRITICAL(&mux_);
      if (chat) {
        send(chat, String("Instrument online - http://") + WiFi.localIP().toString() +
                       "/  (commands sent while it was off were ignored; /help for the list)");
      }
    }
    state_ = "online";

    drainOutbox(token, 0);
    const int got = poll(token, kPollSeconds);
    if (got < 0) { vTaskDelay(pdMS_TO_TICKS(3000)); continue; }
    if (got > 0) drainOutbox(token, kReplyWaitMs);
  }
}

}  // namespace

void begin() {
  loadNvs();
  in_ = xQueueCreate(kInQueue, sizeof(Inbound));
  out_ = xQueueCreate(kOutQueue, sizeof(Outbound));
  // 12 kB: TLS needs most of it. Priority 1 keeps it below the Arduino loop.
  xTaskCreatePinnedToCore(task, "tgbot", 12288, nullptr, 1, nullptr, 0);
}

bool nextInbound(Inbound& out) { return in_ && xQueueReceive(in_, &out, 0) == pdTRUE; }

bool send(int64_t chat, const String& text) {
  if (!out_ || !chat) return false;
  Outbound m;
  m.chat = chat;
  strlcpy(m.text, text.c_str(), sizeof m.text);
  return xQueueSend(out_, &m, 0) == pdTRUE;
}

bool setToken(const String& token) {
  // "<bot id>:<35 characters of A-Z a-z 0-9 _ ->"
  const int colon = token.indexOf(':');
  if (colon < 5 || token.length() - colon - 1 < 30 || token.length() >= sizeof token_) return false;
  for (int i = 0; i < colon; i++) if (!isdigit(static_cast<unsigned char>(token[i]))) return false;
  for (size_t i = colon + 1; i < token.length(); i++) {
    const char c = token[i];
    if (!isalnum(static_cast<unsigned char>(c)) && c != '_' && c != '-') return false;
  }
  portENTER_CRITICAL(&mux_);
  strlcpy(token_, token.c_str(), sizeof token_);
  chat_ = 0;                                 // a new bot has no paired chat yet
  portEXIT_CRITICAL(&mux_);
  tokenChanged_ = true;
  saveNvs();
  return true;
}

void clearToken() {
  portENTER_CRITICAL(&mux_);
  token_[0] = '\0';
  chat_ = 0;
  portEXIT_CRITICAL(&mux_);
  tokenChanged_ = true;
  Preferences p;
  if (p.begin(kNamespace, false)) { p.clear(); p.end(); }
}

void pair(int64_t chat) {
  portENTER_CRITICAL(&mux_);
  chat_ = chat;
  portEXIT_CRITICAL(&mux_);
  saveNvs();
}

void unpair() { pair(0); }

bool hasToken() { return token_[0] != '\0'; }
int64_t pairedChat() {
  portENTER_CRITICAL(&mux_);
  const int64_t c = chat_;
  portEXIT_CRITICAL(&mux_);
  return c;
}
const String& botName() { return bot_; }
const char* state() { return state_; }
uint32_t received() { return received_; }
uint32_t sent() { return sent_; }
uint32_t errors() { return errors_; }
const String& lastError() { return lastError_; }
String tokenForPush() { return tokenCopy(); }

}  // namespace tg
