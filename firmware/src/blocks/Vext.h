// +VEXT, the bench supply of the transmitter and the coil drivers, as b2 reads it.
//
// The sense divider is rework B6 of 2026-10-08 (pins.h PIN_VEXT_SENSE). b2
// measures it at 2 Hz and writes it here; the NMR sequencer reads it before a
// scan set and before a single pulse and refuses to transmit outside the
// OPA564's range. Same pattern as Busy.h: a header of its own, so neither block
// includes the other.
//
// Written on the main task only (b2 loop and its vext_check command), read on
// the main task by the nmr block. A 32-bit float and a bool are atomic on this
// core; volatile stops the compiler caching them.
#pragma once

extern volatile float g_vextVolts;   // NAN until b2 has measured (b2 not registered: no check)
extern volatile bool g_vextCheck;    // `b2 vext_check {on}`; RAM only, on at every start
