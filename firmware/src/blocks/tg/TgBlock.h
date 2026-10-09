// tg: talk to the instrument from Telegram - the block half (net/TgBot.h is the
// network half).
//
// Every message from Telegram arrives here, in loop(), on the main task, and is
// turned into ordinary block commands through the registry - the same door the
// alarm engine uses to switch a module output. So /module 1 on does exactly
// what the b4 panel's button does, and is refused for the same reasons.
//
// Pairing: the panel shows a six-digit code; sending "/start <code>" to the bot
// makes that chat the only one the instrument obeys. Five wrong codes and the
// code changes and pairing pauses for a minute. Pairing also points the alarm
// action "push" (net/Push.h) at the same chat, so an alarm rule with action
// "push" - or one made with /alarm - messages you there.
//
// Telegram commands: /help /status /read [AIn] /module N on|off
//                    /led red|green|blue|white|off /alarms /alarm KEY OP VALUE
//                    /unalarm ID /unpair
// Block commands:    set_token {token}, clear, unpair, test {text}
// Status:            token, paired, bot, state, code (until paired), received,
//                    sent, errors, error
#pragma once
#include "../Block.h"
#include "../Registry.h"
#include "../../net/TgBot.h"

class TgBlock : public Block {
 public:
  explicit TgBlock(Registry& reg) : reg_(reg) {}

  const char* name() const override { return "tg"; }
  void begin() override;
  void loop() override;
  bool handle(JsonObjectConst cmd, JsonObject reply) override;
  void status(JsonObject out) override;

 private:
  static constexpr int kMaxWrongCodes = 5;
  static constexpr uint32_t kLockoutMs = 60000;

  void onMessage(const tg::Inbound& m);
  String run(const String& cmd, const String& args);   // one command -> the reply text
  bool call(const char* block, const char* cmd, JsonDocument& args, JsonDocument& result, String& err);

  String help() const;
  String summary();
  String read(const String& arg);
  String module(const String& args);
  String led(const String& arg);
  String alarms();
  String addAlarm(const String& args);
  String removeAlarm(const String& arg);

  void newCode();
  void pointPushHere(int64_t chat);

  Registry& reg_;
  char code_[7] = "";
  int wrong_ = 0;
  uint32_t lockedUntil_ = 0;
};
