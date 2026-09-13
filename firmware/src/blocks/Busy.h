// One flag that says an NMR scan is in progress.
//
// The sequencer owns the transmit gate, the receiver blanking, the polarizer FET
// and the H-bridge while it is running. If b4 flipped the polarizer or reversed
// the field halfway through a scan the data would be quietly wrong, so b4 refuses
// those commands while the flag is set.
//
// It lives in its own tiny header, not in NmrBlock.h, so the blocks that have to
// check it do not have to include the NMR block - and so they compile before that
// block exists at all.
//
// Written only by the sequencer task, read by block code on the main task. A
// single bool is atomic on this core; volatile is enough to stop the compiler
// caching it across the read.
#pragma once

extern volatile bool g_nmrBusy;

inline bool nmr_busy() { return g_nmrBusy; }
