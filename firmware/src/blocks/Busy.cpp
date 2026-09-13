#include "Busy.h"

// Idle until the NMR sequencer says otherwise.
volatile bool g_nmrBusy = false;
