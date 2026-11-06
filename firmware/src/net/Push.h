// push: send a line of text to a chat service when an alarm fires.
//
// Two things decide the shape of this.
//
// 1. An HTTPS POST takes one to two seconds. fire() is called from the alarm
//    engine, which runs from loop(), and blocking there would stall every
//    block on the board. So send() only drops the message in a queue and
//    returns; a separate FreeRTOS task does the request.
//
// 2. A bot token is a secret. It is never compiled in and never written to the
//    source tree - it lives in NVS, a flash partition of its own. Deliberately
//    not a file: the web server hands out the whole of LittleFS, so a token in
//    a file there could be downloaded straight off the board. configure() below
//    deliberately gives the token back as a bool, not a string, so it cannot
//    leak through the status broadcast either.
//
// The body is a template so one mechanism covers every service. {msg} is
// replaced with the alarm text, JSON-escaped:
//
//   Telegram   url  https://api.telegram.org/bot<TOKEN>/sendMessage
//              body {"chat_id":"<CHAT_ID>","text":"{msg}"}
//              auth (none - the token is in the URL)
//
//   LINE       url  https://api.line.me/v2/bot/message/push
//   Messaging  body {"to":"<USER_ID>","messages":[{"type":"text","text":"{msg}"}]}
//   API        auth Bearer <CHANNEL_ACCESS_TOKEN>
//              (LINE Notify was withdrawn in March 2025; this is the replacement)
//
//   Discord    url  the channel webhook
//              body {"content":"{msg}"}
//
// Only works when the board joined your WiFi. If it fell back to its own
// access point there is no route to the internet and send() will fail - which
// is why status() reports the last HTTP code rather than swallowing it.
#pragma once
#include <Arduino.h>

namespace push {

// Starts the sender task and loads /push.json. Call once from setup().
void begin();

// Queue one message. Returns false if the queue is full or nothing is
// configured. Never blocks.
bool send(const String& text);

// Replace the configuration and persist it. Pass an empty auth to clear it.
bool configure(const String& url, const String& auth, const String& body);

// Forget the configuration, including the token.
void clear();

// --- for the status panel. None of these return the token. ---
bool  configured();
const String& host();      // host part of the URL only, so the panel can show where
uint32_t sent();
uint32_t failed();
int   lastCode();          // last HTTP status, or a negative client error
const String& lastError();

}  // namespace push
