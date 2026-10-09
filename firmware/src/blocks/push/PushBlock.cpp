#include "PushBlock.h"

#include "../../net/Push.h"

void PushBlock::begin() { push::begin(); }

bool PushBlock::handle(JsonObjectConst cmd, JsonObject reply) {
  const char* c = cmd["cmd"] | "";
  JsonObjectConst a = argsOf(cmd);

  if (strcmp(c, "set") == 0) {
    // {"url":"https://...","auth":"Bearer ...","body":"{\"content\":\"{msg}\"}"}
    String url  = a["url"]  | "";
    String auth = a["auth"] | "";
    String body = a["body"] | "";
    if (!push::configure(url, auth, body)) {
      reply["error"] = "url must be http(s) and body must contain {msg}";
      return false;
    }
    // Deliberately not echoing url or auth back - the reply is broadcast.
    reply["configured"] = true;
    reply["host"] = push::host();
    return true;
  }

  if (strcmp(c, "test") == 0) {
    const char* t = a["text"] | "test from the instrument";
    if (!push::send(String(t))) {
      reply["error"] = push::configured() ? "queue full" : "not configured";
      return false;
    }
    reply["queued"] = true;        // the result shows up in status: sent / failed / code
    return true;
  }

  if (strcmp(c, "clear") == 0) {
    push::clear();
    reply["configured"] = false;
    return true;
  }

  reply["error"] = "unknown cmd";
  return false;
}

void PushBlock::status(JsonObject out) {
  out["configured"] = push::configured() ? 1 : 0;
  out["host"]       = push::host();
  out["sent"]       = push::sent();
  out["failed"]     = push::failed();
  out["code"]       = push::lastCode();
  if (push::lastError().length()) out["error"] = push::lastError();
}
