// tg: talk to the instrument from Telegram - the network half.
//
// Why Telegram and not LINE: a Telegram bot can *fetch* its messages
// (getUpdates, "long polling"), so the board needs nothing but a way out to the
// internet. LINE only *delivers* messages, to a public HTTPS address of yours,
// and a board on a phone hotspot has no such address - two-way LINE needs a
// relay server in between.
//
// Shape, the same as net/Push.h for the same reasons:
//   * HTTPS takes a second or two, so a FreeRTOS task (core 0, below the
//     Arduino loop) does every request. Block code never waits on the network.
//   * Commands are NOT executed here. The task queues each incoming message;
//     the tg block pops it in loop() on the main task - the one task that may
//     touch blocks - and queues a reply, which the task then sends.
//   * The bot token is a secret: kept in NVS (not LittleFS, which the web server
//     hands out), never sent back to a client, never logged.
//   * Only one chat - the one that paired with /start <code> - may command the
//     instrument. The chat id is kept in NVS too.
//
// The task, round and round:
//   send whatever replies are queued -> getUpdates (long poll, up to 20 s; it
//   returns at once when a message arrives) -> queue the messages -> wait up to
//   2 s for their replies -> send them -> poll again.
#pragma once
#include <Arduino.h>

namespace tg {

struct Inbound {
  int64_t chat = 0;
  char text[160] = "";
  char from[32] = "";
};

// Starts the task and loads the token and the paired chat from NVS.
void begin();

// Main task: the next message to act on, if there is one.
bool nextInbound(Inbound& out);
// Main task: queue a message to `chat`. Returns false if the queue is full.
bool send(int64_t chat, const String& text);

// Store a new token (checked for the "<digits>:<35 chars>" shape, never echoed)
// and forget any paired chat. Returns false if it does not look like a token.
bool setToken(const String& token);
void clearToken();
// The chat that may command the instrument; 0 = nobody yet.
void pair(int64_t chat);
void unpair();

// For status. None of these returns the token.
bool hasToken();
int64_t pairedChat();
const String& botName();      // "renqian_instrument_bot" once getMe has answered
const char* state();          // "no token", "no internet", "connecting", "online", "error"
uint32_t received();
uint32_t sent();
uint32_t errors();
const String& lastError();

// The token, for net/Push.h's Telegram preset only (so alarm "push" messages
// reach the paired chat). Never put it in a reply or a status.
String tokenForPush();

}  // namespace tg
