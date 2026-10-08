#include "TgBlock.h"

#include <WiFi.h>
#include <esp_random.h>

#include "../../net/Push.h"

namespace {

// "/read@renqian_bot ai3" -> cmd "read", args "ai3"
void split(const String& text, String& cmd, String& args) {
  String t = text;
  t.trim();
  int sp = t.indexOf(' ');
  cmd = sp < 0 ? t : t.substring(0, sp);
  args = sp < 0 ? "" : t.substring(sp + 1);
  args.trim();
  if (cmd.startsWith("/")) cmd.remove(0, 1);
  const int at = cmd.indexOf('@');
  if (at >= 0) cmd.remove(at);
  cmd.toLowerCase();
}

String fmt(float v, int decimals) { return String(v, decimals); }

const char* rangeLabel(int code) {
  switch (code) {
    case 0: return "+-10 V";
    case 1: return "+-5 V";
    case 2: return "+-2.5 V";
    case 5: return "0-10 V";
    case 6: return "0-5 V";
    default: return "?";
  }
}

// ">" -> "gt" and so on; nullptr if it is not an operator.
const char* opName(const String& s) {
  if (s == ">") return "gt";
  if (s == "<") return "lt";
  if (s == ">=") return "ge";
  if (s == "<=") return "le";
  if (s == "=" || s == "==") return "eq";
  if (s == "!=") return "ne";
  return nullptr;
}

const char* opSymbol(const char* op) {
  if (!strcmp(op, "gt")) return ">";
  if (!strcmp(op, "lt")) return "<";
  if (!strcmp(op, "ge")) return ">=";
  if (!strcmp(op, "le")) return "<=";
  if (!strcmp(op, "eq")) return "=";
  if (!strcmp(op, "ne")) return "!=";
  return op;
}

}  // namespace

void TgBlock::begin() {
  tg::begin();
  newCode();
}

void TgBlock::newCode() {
  snprintf(code_, sizeof code_, "%06u", static_cast<unsigned>(esp_random() % 1000000u));
}

void TgBlock::loop() {
  tg::Inbound m;
  while (tg::nextInbound(m)) onMessage(m);
}

void TgBlock::onMessage(const tg::Inbound& m) {
  String cmd, args;
  split(String(m.text), cmd, args);
  const int64_t paired = tg::pairedChat();

  if (!paired) {
    if (cmd != "start") {
      tg::send(m.chat, "This instrument is not paired yet. Open its Telegram tab and send /start followed by the code shown there.");
      return;
    }
    if (static_cast<int32_t>(millis() - lockedUntil_) < 0) {
      tg::send(m.chat, "Too many wrong codes - try again in a minute.");
      return;
    }
    if (args != code_) {
      if (++wrong_ >= kMaxWrongCodes) {           // a new code, and a pause
        wrong_ = 0;
        newCode();
        lockedUntil_ = millis() + kLockoutMs;
      }
      tg::send(m.chat, "Wrong code.");
      return;
    }
    wrong_ = 0;
    tg::pair(m.chat);
    pointPushHere(m.chat);
    newCode();
    tg::send(m.chat, String("Paired. Hello ") + m.from + "!\n\n" + help());
    return;
  }

  if (m.chat != paired) {
    tg::send(m.chat, "This instrument is paired with someone else.");
    return;
  }
  tg::send(m.chat, run(cmd, args));
}

// Alarm rules with action "push" go through net/Push.h; aim it at this chat.
void TgBlock::pointPushHere(int64_t chat) {
  const String url = String("https://api.telegram.org/bot") + tg::tokenForPush() + "/sendMessage";
  const String body = String("{\"chat_id\":") + String(static_cast<long long>(chat)) + ",\"text\":\"{msg}\"}";
  push::configure(url, "", body);
}

String TgBlock::run(const String& cmd, const String& args) {
  if (cmd == "start" || cmd == "help") return help();
  if (cmd == "status") return summary();
  if (cmd == "read") return read(args);
  if (cmd == "module") return module(args);
  if (cmd == "led") return led(args);
  if (cmd == "alarms") return alarms();
  if (cmd == "alarm") return addAlarm(args);
  if (cmd == "unalarm") return removeAlarm(args);
  if (cmd == "unpair") {
    tg::unpair();
    if (push::host() == "api.telegram.org") push::clear();
    return "Unpaired. The instrument ignores this chat until someone pairs again with a new code.";
  }
  return "Unknown command - /help lists them.";
}

String TgBlock::help() const {
  return "/status - the instrument at a glance\n"
         "/read - all eight inputs;  /read AI3 - one\n"
         "/module 1 on  (or off) - a module output\n"
         "/led red|green|blue|white|off\n"
         "/alarms - the alarm rules\n"
         "/alarm ai1 > 3.5 - message me here when it happens\n"
         "/unalarm 2 - delete rule 2\n"
         "/unpair - stop obeying this chat";
}

bool TgBlock::call(const char* block, const char* cmd, JsonDocument& args, JsonDocument& result, String& err) {
  Block* b = reg_.find(block);
  if (!b) { err = String("no block ") + block; return false; }
  JsonDocument req;
  req["cmd"] = cmd;
  req["args"] = args.as<JsonObjectConst>();
  JsonObject out = result.to<JsonObject>();
  const bool ok = b->handle(req.as<JsonObjectConst>(), out);
  if (!ok) err = out["error"] | "refused";
  return ok;
}

String TgBlock::summary() {
  JsonDocument doc;
  reg_.statusAll(doc.to<JsonObject>());
  JsonObject base = doc["base"];
  JsonObject scope = doc["b1"]["scope"];
  const uint32_t up = base["uptime_s"] | 0u;
  String s = String("Instrument ") + WiFi.getHostname();
#ifdef SIM
  s += " (SIM - the inputs are simulated)";
#endif
  s += String("\nup ") + (up / 3600) + " h " + ((up / 60) % 60) + " min";
  s += String("\nWiFi ") + WiFi.RSSI() + " dBm - http://" + WiFi.localIP().toString() + "/";
  s += String("\nboard ") + fmt(base["temp_c"] | 0.0f, 1) + " C, free memory " + ((base["heap_free"] | 0u) / 1024) + " kB";
  const char* mode = scope["mode"] | "idle";
  s += String("\nscope ") + mode;
  s += String("\nalarm rules ") + (doc["alarms"]["rules"] | 0) + ", active " + (doc["alarms"]["active"] | 0);
  return s;
}

String TgBlock::read(const String& arg) {
  JsonDocument doc;
  reg_.statusAll(doc.to<JsonObject>());
  JsonObject b1 = doc["b1"];
  if (b1.isNull()) return "No b1 inputs on this firmware.";
  JsonArray ranges = b1["ranges"];
  String a = arg;
  a.toLowerCase();
  a.replace("ai", "");
  a.trim();
  auto line = [&](int i) {
    char key[4] = "ai1";
    key[2] = '1' + i;
    const int code = ranges.isNull() ? (i == 0 ? (b1["range"] | 0) : 0) : (ranges[i] | 0);
    return String("AI") + (i + 1) + "  " + fmt(b1[key] | 0.0f, 4) + " V  (" + rangeLabel(code) + ")";
  };
  if (a.length()) {
    const int n = a.toInt();
    if (n < 1 || n > 8) return "Which input? /read AI1 ... /read AI8";
    return line(n - 1);
  }
  String s;
  for (int i = 0; i < 8; i++) s += line(i) + (i < 7 ? "\n" : "");
  return s;
}

String TgBlock::module(const String& args) {
  const int sp = args.indexOf(' ');
  const int n = (sp < 0 ? args : args.substring(0, sp)).toInt();
  String state = sp < 0 ? "" : args.substring(sp + 1);
  state.trim();
  state.toLowerCase();
  if (n < 1 || n > 7 || (state != "on" && state != "off")) return "Use: /module 1 on  (modules 1 to 7, on or off)";
  JsonDocument a, r;
  a["n"] = n;
  a["on"] = state == "on";
  String err;
  if (!call("b4", "module", a, r, err)) return String("Refused: ") + err;
  return String("Module ") + n + " is now " + (state == "on" ? "ON" : "OFF");
}

String TgBlock::led(const String& arg) {
  String c = arg;
  c.toLowerCase();
  int r = 0, g = 0, b = 0;
  if (c == "red") r = 60;
  else if (c == "green") g = 60;
  else if (c == "blue") b = 60;
  else if (c == "white") r = g = b = 40;
  else if (c != "off") return "Use: /led red, green, blue, white or off";
  JsonDocument a, res;
  a["r"] = r;
  a["g"] = g;
  a["b"] = b;
  String err;
  if (!call("base", "led", a, res, err)) return String("Refused: ") + err;
  return String("LED ") + c;
}

String TgBlock::alarms() {
  JsonDocument a, r;
  String err;
  if (!call("alarms", "list", a, r, err)) return String("Refused: ") + err;
  JsonArray rules = r["rules"];
  if (rules.isNull() || rules.size() == 0) return "No alarm rules. Make one with /alarm ai1 > 3.5";
  String s;
  for (JsonObject x : rules) {
    s += String("#") + (x["id"] | 0) + "  " + (x["block"] | "") + "." + (x["key"] | "") + " " +
         opSymbol(x["op"] | "gt") + " " + fmt(x["threshold"] | 0.0f, 3) + "  -> " + (x["action"] | "") +
         "  (fired " + (x["fired"] | 0) + "x)\n";
  }
  s.trim();
  return s;
}

// "/alarm ai1 > 3.5" or "/alarm base.temp_c >= 50": a rule whose action is
// "push", which pairing pointed at this chat.
String TgBlock::addAlarm(const String& args) {
  String t = args;
  t.trim();
  const int s1 = t.indexOf(' ');
  const int s2 = s1 < 0 ? -1 : t.indexOf(' ', s1 + 1);
  if (s1 < 0 || s2 < 0) return "Use: /alarm ai1 > 3.5   (operators > < >= <= = !=)";
  String key = t.substring(0, s1);
  const String op = t.substring(s1 + 1, s2);
  String val = t.substring(s2 + 1);
  val.trim();
  key.toLowerCase();
  const char* o = opName(op);
  if (!o) return "Operator must be one of > < >= <= = !=";
  char* end = nullptr;
  const float th = strtof(val.c_str(), &end);
  if (end == val.c_str()) return "The threshold must be a number, e.g. /alarm ai1 > 3.5";
  String block = "b1";
  const int dot = key.indexOf('.');
  if (dot > 0) { block = key.substring(0, dot); key = key.substring(dot + 1); }
  else if (!key.startsWith("ai")) return "Name an input (ai1..ai8) or block.key, e.g. base.temp_c";

  JsonDocument a, r;
  a["block"] = block;
  a["key"] = key;
  a["op"] = o;
  a["threshold"] = th;
  a["action"] = "push";
  String err;
  if (!call("alarms", "add", a, r, err)) return String("Refused: ") + err;
  return String("Alarm #") + (r["id"] | 0) + ": " + block + "." + key + " " + opSymbol(o) + " " + fmt(th, 3) +
         " - I will message you here when it happens.";
}

String TgBlock::removeAlarm(const String& arg) {
  const int id = arg.toInt();
  if (id <= 0) return "Use: /unalarm 2   (/alarms lists the numbers)";
  JsonDocument a, r;
  a["id"] = id;
  String err;
  if (!call("alarms", "remove", a, r, err)) return String("Refused: ") + err;
  return String("Alarm #") + id + " deleted.";
}

bool TgBlock::handle(JsonObjectConst cmd, JsonObject reply) {
  const char* c = cmd["cmd"] | "";
  JsonObjectConst a = argsOf(cmd);

  if (strcmp(c, "set_token") == 0) {
    String token = a["token"] | "";
    token.trim();
    if (!tg::setToken(token)) {
      reply["error"] = "that does not look like a bot token (digits, a colon, then about 35 characters)";
      return false;
    }
    newCode();
    reply["token"] = true;           // deliberately not echoing it - the reply is not private
    return true;
  }
  if (strcmp(c, "clear") == 0) {
    tg::clearToken();
    if (push::host() == "api.telegram.org") push::clear();
    reply["token"] = false;
    return true;
  }
  if (strcmp(c, "unpair") == 0) {
    const int64_t chat = tg::pairedChat();
    if (chat) tg::send(chat, "Unpaired from the instrument's panel.");
    tg::unpair();
    if (push::host() == "api.telegram.org") push::clear();
    newCode();
    reply["paired"] = false;
    return true;
  }
  if (strcmp(c, "test") == 0) {
    const int64_t chat = tg::pairedChat();
    if (!chat) { reply["error"] = "not paired yet"; return false; }
    // Through net/Push.h, which pairing pointed at this chat: it sends at once,
    // where tg::send would wait for the bot task's long poll to come back.
    const String text = a["text"] | "Test message from the instrument.";
    const bool ok = push::host() == "api.telegram.org" ? push::send(text) : tg::send(chat, text);
    if (!ok) { reply["error"] = "queue full"; return false; }
    reply["queued"] = true;
    return true;
  }
  reply["error"] = "unknown cmd";
  return false;
}

void TgBlock::status(JsonObject out) {
  const bool token = tg::hasToken();
  const bool paired = tg::pairedChat() != 0;
  out["token"] = token ? 1 : 0;
  out["paired"] = paired ? 1 : 0;
  out["bot"] = tg::botName();
  out["state"] = tg::state();
  out["wifi"] = WiFi.isConnected() ? 1 : 0;
  // The code only means something to whoever can see this panel - the local
  // network - and changes after every pairing and every five wrong guesses.
  if (token && !paired) out["code"] = code_;
  out["received"] = tg::received();
  out["sent"] = tg::sent();
  out["errors"] = tg::errors();
  if (tg::lastError().length()) out["error"] = tg::lastError();
}
