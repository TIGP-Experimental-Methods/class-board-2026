// push: configure and test the chat webhook that the alarm action "push" uses.
//
// The work is in net/Push.h - this is just the block that lets the phone set it
// up and watch it. Kept as a block so it goes through the same message protocol
// as everything else, and so the panel gets a place to live.
//
// The token never comes back out: status() reports whether something is
// configured and which host it points at, never the URL or the header.
//
// Commands: set {url, auth, body}, test {text}, clear
// Status:   configured, host, sent, failed, code
#pragma once
#include "../Block.h"

class PushBlock : public Block {
 public:
  const char* name() const override { return "push"; }
  void begin() override;
  void loop() override {}
  bool handle(JsonObjectConst cmd, JsonObject reply) override;
  void status(JsonObject out) override;
};
