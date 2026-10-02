#include "Push.h"

#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <Preferences.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>

namespace push {
namespace {

// NOT a file. main.cpp does serveStatic("/", LittleFS, "/"), which hands out the
// whole filesystem - /alarms.json and anything beside it - so a token kept in a
// file there could simply be downloaded off the board at /push.json. NVS is a
// separate flash partition that the web server has no route to.
const char* kNamespace = "push";
constexpr int kQueueLen = 8;
constexpr int kMsgMax   = 192;

struct Msg { char text[kMsgMax]; };

QueueHandle_t q_ = nullptr;
String url_, auth_, body_ = "{\"content\":\"{msg}\"}";
String host_, lastError_;
volatile uint32_t sent_ = 0, failed_ = 0;
volatile int lastCode_ = 0;

String hostOf(const String& url) {
  int a = url.indexOf("://");
  if (a < 0) return "";
  a += 3;
  int b = url.indexOf('/', a);
  return b < 0 ? url.substring(a) : url.substring(a, b);
}

// Minimal JSON string escaping, so an alarm message can never break the body
// template or inject extra fields.
String escape(const String& s) {
  String o;
  o.reserve(s.length() + 8);
  for (size_t i = 0; i < s.length(); i++) {
    char c = s[i];
    switch (c) {
      case '"':  o += "\\\""; break;
      case '\\': o += "\\\\"; break;
      case '\n': o += "\\n";  break;
      case '\r': o += "\\r";  break;
      case '\t': o += "\\t";  break;
      default:
        if ((uint8_t)c < 0x20) { char b[7]; snprintf(b, sizeof b, "\\u%04x", c); o += b; }
        else o += c;
    }
  }
  return o;
}

void save() {
  Preferences p;
  if (!p.begin(kNamespace, false)) { Serial.println("[push] cannot open nvs"); return; }
  p.putString("url", url_);
  p.putString("auth", auth_);
  p.putString("body", body_);
  p.end();
}

void load() {
  Preferences p;
  if (!p.begin(kNamespace, true)) return;    // read-only; absent on a fresh board
  url_  = p.getString("url", "");
  auth_ = p.getString("auth", "");
  body_ = p.getString("body", body_);
  p.end();
  host_ = hostOf(url_);
  Serial.printf("[push] %s\n", url_.length() ? "configured" : "not configured");
}

void post(const char* text) {
  if (WiFi.status() != WL_CONNECTED) {
    failed_++; lastCode_ = -1;
    lastError_ = "no network (the board is on its own access point)";
    return;
  }

  WiFiClientSecure client;
  // No certificate check. Pinning a root CA per service would be better, and
  // this is the one place in the firmware where that matters: without it, a
  // machine on the path could read the token. It is left insecure because the
  // alternative is shipping and maintaining a CA bundle, and the consequence
  // is a chat message, not control of the instrument. Say so in the write-up
  // rather than quietly pretending it is fine.
  client.setInsecure();

  HTTPClient http;
  if (!http.begin(client, url_)) {
    failed_++; lastCode_ = -2; lastError_ = "bad url";
    return;
  }
  http.addHeader("Content-Type", "application/json");
  if (auth_.length()) http.addHeader("Authorization", auth_);

  String payload = body_;
  payload.replace("{msg}", escape(String(text)));

  int code = http.POST(payload);
  lastCode_ = code;
  if (code >= 200 && code < 300) {
    sent_++;
    lastError_ = "";
  } else {
    failed_++;
    lastError_ = code > 0 ? http.getString().substring(0, 120) : http.errorToString(code);
  }
  http.end();
}

void task(void*) {
  Msg m;
  for (;;) {
    if (xQueueReceive(q_, &m, portMAX_DELAY) == pdTRUE) post(m.text);
  }
}

}  // namespace

void begin() {
  load();
  q_ = xQueueCreate(kQueueLen, sizeof(Msg));
  // 8 kB: TLS needs most of it. Priority 1 keeps it below the Arduino loop.
  xTaskCreatePinnedToCore(task, "push", 8192, nullptr, 1, nullptr, 0);
}

bool send(const String& text) {
  if (!q_ || url_.isEmpty()) return false;
  Msg m;
  strlcpy(m.text, text.c_str(), sizeof m.text);
  return xQueueSend(q_, &m, 0) == pdTRUE;   // 0 ticks: never block the caller
}

bool configure(const String& url, const String& auth, const String& body) {
  if (!url.startsWith("https://") && !url.startsWith("http://")) return false;
  if (body.indexOf("{msg}") < 0) return false;    // nothing would be sent
  url_ = url; auth_ = auth; body_ = body;
  host_ = hostOf(url_);
  save();
  return true;
}

void clear() {
  url_ = ""; auth_ = ""; host_ = "";
  Preferences p;
  if (p.begin(kNamespace, false)) { p.clear(); p.end(); }
}

bool configured()          { return url_.length() > 0; }
const String& host()       { return host_; }
uint32_t sent()            { return sent_; }
uint32_t failed()          { return failed_; }
int lastCode()             { return lastCode_; }
const String& lastError()  { return lastError_; }

}  // namespace push
