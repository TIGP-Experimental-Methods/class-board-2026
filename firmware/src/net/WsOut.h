// One way for a block to push a binary frame at every connected client.
//
// main.cpp owns the WebSocket, and that is deliberate: blocks do not know about
// the network. But the capture and NMR frames (PROTOCOL.md sections 6 and 7) are
// far too big for the JSON status broadcast, so there has to be one door in the
// wall. This is it - a single free function, defined in main.cpp next to the
// socket it uses.
//
// Call it from the main task only (from a block's loop() or handle()). The
// async-TCP queue is not ours to touch from another task; a worker task that has
// data ready sets a flag and lets loop() do the sending.
#pragma once
#include <stddef.h>
#include <stdint.h>

void wsBinaryAll(const uint8_t* data, size_t len);
