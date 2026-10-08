"""Exact check of the NMR frequency lattice (NMR-FIRMWARE.md section 3.9).

Mirrors the arithmetic of drivers/Si5351.cpp (setClk0, setClk1, setClk2Exact),
drivers/Ad9834.cpp (the frequency word) and Sequencer::programClocks, and checks
in exact rational arithmetic that

    CLK2 = f_tx - f_lo          (the reference tone is exactly the IF)

for the register values the firmware writes. Run it on a PC:

    python firmware/scripts/lattice_check.py [f_tx_hz f_lo_hz] ...

With no arguments it checks the proton demonstration (89 400 / 84 000 Hz) and
an Earth's-field case (2 100 / 1 900 Hz).
"""

import sys
from fractions import Fraction
from math import floor, gcd

XTAL = 25_000_000
VCO_MIN, VCO_MAX = 600_000_000, 900_000_000
MS_MAX = 1800  # Si5351::kMsMax: AN619 allows 2048, 1800..2048 is unmeasured
DENOM_CLK1 = 1 << 19  # PLLB fractional denominator: makes the LO lattice exact
STEP = Fraction(XTAL, 1 << 27)  # the common lattice: 0.186 Hz


def encode(a: int, b: int, c: int) -> tuple[int, int, int]:
    """AN619 section 3.2: P1, P2, P3 of a divider a + b/c."""
    q = (128 * b) // c
    return 128 * a + q - 512, 128 * b - c * q, c


def set_clk0(hz: int) -> tuple[int, int]:
    """Integer PLLA multiplier and output divider (the search of Si5351::setClk0)."""
    best = None
    for d in range(6, MS_MAX + 1, 2):
        pll = hz * d
        if pll < VCO_MIN:
            continue
        if pll > VCO_MAX:
            break
        if pll % XTAL == 0:
            best = (pll // XTAL, d)
    if best is None:
        raise ValueError("no integer CLK0 solution")
    return best


def dds_word(f_tx: float, mclk: int) -> int:
    """Ad9834::setFrequency: word = round(hz * 2^28 / MCLK)."""
    return floor(f_tx * (1 << 28) / mclk + 0.5)  # llround for a positive value


def lo_word(f_lo: float) -> int:
    """Sequencer::programClocks: the nearest even lattice word."""
    return 2 * floor(f_lo / (2 * float(STEP)) + 0.5)


def set_clk1(hz: Fraction) -> dict:
    """Si5351::setClk1: R so the multisynth runs at >= 1 MHz, MS even and a multiple of
    32 / R where the VCO window allows it, PLLB = a + b / 2^19."""
    r_exp = 0
    fms = hz
    while fms < 1_000_000 and r_exp < 7:
        r_exp += 1
        fms *= 2
    gran = max(2, 32 >> r_exp)
    d = int(VCO_MAX / fms) // gran * gran
    if d > MS_MAX:
        d = MS_MAX // gran * gran
    if d < 8 or fms * d < VCO_MIN:
        d = int(VCO_MAX / fms) & ~1  # off the lattice: any even divider
        d = min(max(d, 8), MS_MAX)
    pll = fms * d
    if not (VCO_MIN <= pll <= VCO_MAX):
        raise ValueError("CLK1 out of range")
    fb = pll / XTAL
    a = int(fb)
    b = round((fb - a) * DENOM_CLK1)
    return {
        "r_exp": r_exp,
        "ms": d,
        "a": a,
        "b": b,
        "c": DENOM_CLK1,
        "vco": XTAL * (a + Fraction(b, DENOM_CLK1)),
        "f": XTAL * (a + Fraction(b, DENOM_CLK1)) / (d << r_exp),
    }


def set_clk2_exact(beat_word: int, plla_mul: int) -> dict:
    """Si5351::setClk2Exact: CLK2 = beat_word * xtal / 2^27 from the integer PLLA."""
    if beat_word <= 0:
        raise ValueError("beat word must be positive")
    num = plla_mul << 27  # PLLA / (xtal / 2^27)
    choice = None
    for r_exp in range(8):
        if Fraction(num, beat_word << r_exp) <= MS_MAX:
            choice = r_exp
            break
    if choice is None:
        raise ValueError(f"CLK2 below {float(Fraction(plla_mul * XTAL, MS_MAX * 128)):.1f} Hz: out of reach")
    if Fraction(num, beat_word << choice) < 8:
        raise ValueError("CLK2 above the multisynth range")
    den = beat_word << choice
    g = gcd(num, den)
    n, dd = num // g, den // g
    a, b, c = n // dd, n % dd, dd
    if b == 0:
        c = 1
    if c > (1 << 20) - 1:
        raise ValueError("CLK2 denominator does not fit in 20 bits")
    return {"r_exp": choice, "a": a, "b": b, "c": c, "f": plla_mul * XTAL / ((a + Fraction(b, c)) * (1 << choice))}


def check(f_tx: float, f_lo: float) -> bool | None:
    """True = exact, False = the arithmetic is wrong, None = no reference possible at this IF."""
    print(f"--- requested f_tx = {f_tx} Hz, f_lo = {f_lo} Hz")
    m, ms0 = set_clk0(50_000_000)
    mclk = Fraction(XTAL * m, ms0)
    print(f"CLK0: PLLA = {m} x 25 MHz = {m * 25} MHz (integer), MS0 = {ms0} -> MCLK = {mclk} Hz")
    w = dds_word(f_tx, int(mclk))
    ftx = w * mclk / (1 << 28)
    print(f"DDS : W = {w} -> f_tx = {float(ftx):.6f} Hz  (= W * 25 MHz / 2^27: {ftx == w * STEP})")
    v = lo_word(f_lo)
    flo = v * STEP
    print(f"LO  : V = {v} (even) -> f_lo = {float(flo):.6f} Hz, lattice step 2 x {float(STEP):.6f} = {float(2 * STEP):.4f} Hz")
    c1 = set_clk1(4 * flo)
    p1 = encode(c1["a"], c1["b"], c1["c"])
    print(
        f"CLK1: R = 2^{c1['r_exp']} = {1 << c1['r_exp']}, MS1 = {c1['ms']} (MS*R = {c1['ms'] << c1['r_exp']}), "
        f"PLLB = {c1['a']} + {c1['b']}/{c1['c']} = {float(c1['vco']) / 1e6:.6f} MHz, P1/P2/P3 = {p1}"
    )
    lo_from_regs = c1["f"] / 4
    print(f"      f_lo from the registers = {float(lo_from_regs):.9f} Hz, exactly V * step: {lo_from_regs == flo}")
    beat = w - v
    f_if = beat * STEP
    print(f"IF  : W - V = {beat} -> {float(f_if):.6f} Hz exactly")
    ok = lo_from_regs == flo
    try:
        c2 = set_clk2_exact(abs(beat), m)
    except ValueError as e:
        print(f"CLK2: {e}; a reference channel is not possible at this IF")
        return None if ok else False
    p2 = encode(c2["a"], c2["b"], c2["c"])
    print(
        f"CLK2: R2 = 2^{c2['r_exp']} = {1 << c2['r_exp']}, MS2 = {c2['a']} + {c2['b']}/{c2['c']} "
        f"= {float(c2['a'] + Fraction(c2['b'], c2['c'])):.6f}, P1/P2/P3 = {p2}"
    )
    diff = c2["f"] - (ftx - lo_from_regs)
    print(f"      CLK2 = {float(c2['f']):.9f} Hz; CLK2 - (f_tx - f_lo) = {diff} (exact rational)")
    ok = ok and diff == 0 and c2["f"] == abs(f_if)
    print("RESULT: exact" if ok else "RESULT: NOT exact")
    return ok


def main() -> int:
    args = [float(x) for x in sys.argv[1:]]
    pairs = list(zip(args[0::2], args[1::2], strict=False)) or [(89400.0, 84000.0), (2100.0, 1900.0)]
    results = [check(a, b) for a, b in pairs]
    return 1 if any(r is False for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
