"""instrument - command-line client for the class-board instrument.

Mirrors the WebSocket protocol in firmware/PROTOCOL.md one-to-one:

    instrument status
    instrument send base led --args '{"r":0,"g":255,"b":0}'
    instrument stream base.counter --seconds 5 --csv out.csv
    instrument alarms list
    instrument alarms add --block b1 --key ai1 --op gt --threshold 9 --action module:1:off
    instrument alarms remove 3
    instrument alarms clear
    instrument nmr --n-avg 8 --csv fid.csv

numpy is imported inside the NMR functions only, so every other command still
works on a machine without numpy installed.

Without --host the client talks to 192.168.4.1, the board on its own access point.
When the board has joined a shared network, pass --host instrument-XXXX.local, where XXXX
is the last four hex digits of its MAC address (the same four as in its access-point name
and the boot log); mDNS resolves that name on the local network.
"""

from __future__ import annotations

import asyncio
import csv
import json
import socket
import struct
import sys
import time
from collections import deque
from typing import Any

import typer
import websockets

app = typer.Typer(help=__doc__, no_args_is_help=True)
alarms_app = typer.Typer(help="Manage alarm rules on the board.")
app.add_typer(alarms_app, name="alarms")

DEFAULT_HOST = "192.168.4.1"  # the board's own access point

# Binary frame header, little-endian, PROTOCOL.md section 6 (and section 7 for the
# NMR record): kind, block_id, ch, bits, t_ms, rate_hz, n, trig_index,
# volts_per_lsb, offset_v.
FRAME_HEADER = "<4BIIIiff"
FRAME_HEADER_BYTES = struct.calcsize(FRAME_HEADER)  # 28
FRAME_KIND_NMR = 3


def parse_frame_header(data: bytes) -> dict | None:
    """Unpack the 28-byte header of a binary frame; None if the frame is too short."""
    if len(data) < FRAME_HEADER_BYTES:
        return None
    fields = struct.unpack_from(FRAME_HEADER, data, 0)
    keys = ("kind", "block_id", "ch", "bits", "t_ms", "rate_hz", "n", "trig_index", "volts_per_lsb", "offset_v")
    return dict(zip(keys, fields, strict=True))


# --------------------------------------------------------------------------
# Connection
# --------------------------------------------------------------------------
def discover(host: str | None) -> str:
    """Return the host to talk to: --host if given (it must resolve), else the access-point address."""
    h = host or DEFAULT_HOST
    try:
        socket.getaddrinfo(h, 80, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        typer.echo(f"cannot resolve {h}; check the name (instrument-XXXX.local) or use the IP address", err=True)
        raise typer.Exit(2) from None
    return h


class Client:
    """Tiny request/reply client. One WebSocket, ids matched to replies."""

    def __init__(self, host: str):
        self.url = f"ws://{host}/ws"
        self.ws = None
        self.next_id = 1
        self.binary: deque[bytes] = deque(maxlen=8)  # binary frames seen while waiting for JSON

    async def __aenter__(self):
        self.ws = await websockets.connect(self.url, open_timeout=5)
        return self

    async def __aexit__(self, *exc):
        await self.ws.close()

    async def recv_any(self) -> dict | bytes:
        """Return one frame: a parsed dict for JSON text, raw bytes for a binary frame."""
        data = await self.ws.recv()
        return json.loads(data) if isinstance(data, str) else bytes(data)

    async def recv(self) -> dict:
        """Return the next JSON message; binary frames are parked in self.binary."""
        while True:
            msg = await self.recv_any()
            if isinstance(msg, dict):
                return msg
            self.binary.append(msg)

    async def next_binary(self, kind: int | None = None, timeout: float = 10.0) -> tuple[dict, bytes]:
        """Wait for a binary frame (of this kind, if given); return (header, payload)."""
        deadline = time.monotonic() + timeout
        pending = list(self.binary)
        self.binary.clear()
        while True:
            for data in pending:
                head = parse_frame_header(data)
                if head and (kind is None or head["kind"] == kind):
                    return head, data[FRAME_HEADER_BYTES:]
            left = deadline - time.monotonic()
            if left <= 0:
                raise RuntimeError("no binary frame from the board")
            msg = await asyncio.wait_for(self.recv_any(), timeout=left)
            pending = [msg] if isinstance(msg, bytes) else []

    async def send(self, block: str, cmd: str, args: dict | None = None) -> Any:
        """Send one command; return result or raise RuntimeError(error)."""
        msg_id = self.next_id
        self.next_id += 1
        await self.ws.send(json.dumps({"id": msg_id, "block": block, "cmd": cmd, "args": args or {}}))
        # Broadcasts (status/hello/alarm) interleave with the reply; skip them.
        while True:
            msg = await asyncio.wait_for(self.recv(), timeout=5)
            if msg.get("id") == msg_id:
                if msg.get("ok"):
                    return msg.get("result", {})
                raise RuntimeError(msg.get("error", "error"))

    async def next_status(self) -> dict:
        while True:
            msg = await asyncio.wait_for(self.recv(), timeout=5)
            if msg.get("type") == "status":
                return msg


def run(coro):
    try:
        return asyncio.run(coro)
    except (TimeoutError, OSError, websockets.WebSocketException) as e:
        typer.echo(f"connection failed: {e}", err=True)
        raise typer.Exit(1) from None
    except typer.Exit:  # a deliberate exit (e.g. from discover); typer.Exit is a RuntimeError
        raise
    except RuntimeError as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(1) from None


HostOpt = typer.Option(
    None,
    "--host",
    "-H",
    help="board hostname or IP address: instrument-XXXX.local on a shared network (XXXX = the last four hex digits "
    "of the MAC, as in the access-point name), default 192.168.4.1 (the board's own access point)",
)


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------
@app.command()
def status(host: str | None = HostOpt, block: str | None = typer.Argument(None, help="only this block")):
    """Print one status broadcast as JSON."""

    async def go():
        async with Client(discover(host)) as c:
            msg = await c.next_status()
            data = msg["blocks"].get(block, {}) if block else msg["blocks"]
            typer.echo(json.dumps(data, indent=2))

    run(go())


@app.command()
def send(block: str, cmd: str, args: str = typer.Option("{}", help="JSON object"), host: str | None = HostOpt):
    """Send one command and print the result."""
    try:
        parsed = json.loads(args)
    except json.JSONDecodeError as e:
        typer.echo(f"--args is not valid JSON: {e}", err=True)
        raise typer.Exit(2) from None

    async def go():
        async with Client(discover(host)) as c:
            typer.echo(json.dumps(await c.send(block, cmd, parsed), indent=2))

    run(go())


@app.command()
def stream(
    key: str = typer.Argument(..., help="block.key, e.g. base.counter"),
    seconds: float = typer.Option(5.0, help="how long to record"),
    csv_path: str | None = typer.Option(None, "--csv", help="write t_ms,value rows here"),
    host: str | None = HostOpt,
):
    """Print (and optionally save) one status value at 20 Hz."""
    if "." not in key:
        typer.echo("key must be block.key (e.g. base.counter)", err=True)
        raise typer.Exit(2)
    blk, k = key.split(".", 1)

    async def go():
        rows = []
        async with Client(discover(host)) as c:
            t_end = time.monotonic() + seconds
            while time.monotonic() < t_end:
                msg = await c.next_status()
                v = msg["blocks"].get(blk, {}).get(k)
                rows.append((msg["t"], v))
                typer.echo(f"{msg['t']}\t{v}")
        if csv_path:
            with open(csv_path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["t_ms", key])
                w.writerows(rows)
            typer.echo(f"wrote {len(rows)} rows to {csv_path}", err=True)

    run(go())


# --------------------------------------------------------------------------
# NMR console (PROTOCOL.md section 7)
#
# numpy is imported inside these functions, so importing this module and using
# every other command works on a machine that has no numpy.
# --------------------------------------------------------------------------
NMR_DEFAULTS = {"f_tx_hz": 89400.0, "f_lo_hz": 84000.0, "sequence": "fid", "n_avg": 1}


async def nmr_config(client: Client, **settings: Any) -> dict:
    """Set any subset of the NMR settings; returns the full effective settings."""
    return await client.send("nmr", "config", settings)


async def nmr_start(client: Client) -> dict:
    """Start the scan set; the board runs it in the background."""
    return await client.send("nmr", "start")


async def nmr_abort(client: Client) -> dict:
    """Stop the scan set now."""
    return await client.send("nmr", "abort")


async def nmr_wait(client: Client, timeout_s: float = 600.0, progress: bool = False) -> dict:
    """Watch the status broadcast until the scan set finishes; return the last nmr status.

    Raises RuntimeError if the board reports an error (current limit, thermal).
    """
    deadline = time.monotonic() + timeout_s
    last: dict = {}
    while True:
        if time.monotonic() > deadline:
            raise RuntimeError("timed out waiting for the scan set")
        msg = await client.next_status()
        last = msg["blocks"].get("nmr", {})
        state = last.get("state", "idle")
        if progress:
            typer.echo(f"  {state}: scan {last.get('scan', 0)} / {last.get('n_avg', 0)}", err=True)
        if state == "error":
            raise RuntimeError(last.get("error", "nmr error"))
        if state in ("done", "idle") and last.get("scan"):
            return last


async def nmr_record(client: Client, timeout_s: float = 20.0) -> tuple[int, Any, int]:
    """Ask for the last averaged record; return (rate_hz, complex numpy array, n_avg).

    The array is the decimated complex record z = I + jQ in volts at the ADC input,
    sampled at rate_hz. Imports numpy.
    """
    import numpy as np

    await client.send("nmr", "get_record")
    head, payload = await client.next_binary(kind=FRAME_KIND_NMR, timeout=timeout_s)
    n = min(int(head["n"]), len(payload) // 8)
    if n <= 0:
        raise RuntimeError("the board sent an empty record")
    pairs = np.frombuffer(payload[: n * 8], dtype="<f4").reshape(-1, 2).astype(np.float64)
    z = pairs[:, 0] + 1j * pairs[:, 1]
    return int(head["rate_hz"]), z, max(1, int(head["trig_index"]))


def nmr_spectrum(z: Any, rate_hz: float) -> tuple[Any, Any]:
    """Return (freq_hz, amplitude) for a complex record: Hann window, FFT, fftshift.

    freq_hz is relative to the local oscillator, so the Larmor frequency of a line
    at f is f_lo + f. Imports numpy.
    """
    import numpy as np

    z = np.asarray(z)
    n = z.size
    if n < 8:
        raise ValueError("the record is too short for a spectrum")
    w = np.hanning(n)
    spec = np.fft.fftshift(np.fft.fft(z * w)) * (2.0 / w.sum())
    freq = np.fft.fftshift(np.fft.fftfreq(n, d=1.0 / rate_hz))
    return freq, np.abs(spec)


def nmr_peak(freq: Any, amp: Any, guard_hz: float = 2.0) -> tuple[float, float, float, float]:
    """Return (peak_hz, peak_amp, noise_rms, snr_db), ignoring the bins around 0 Hz.

    The noise is the median magnitude away from the peak, divided by 1.177 (the
    median of the magnitude of complex Gaussian noise is 1.177 sigma). Imports numpy.
    """
    import numpy as np

    ok = np.abs(freq) > guard_hz
    idx = int(np.argmax(np.where(ok, amp, 0.0)))
    peak_hz, peak_amp = float(freq[idx]), float(amp[idx])
    skip = max(4, amp.size // 100)
    mask = np.abs(np.arange(amp.size) - idx) > skip
    noise = float(np.median(amp[mask])) / 1.177 if mask.any() else 0.0
    snr_db = 20.0 * float(np.log10(peak_amp / noise)) if noise > 0 else float("inf")
    return peak_hz, peak_amp, noise, snr_db


@app.command()
def nmr(
    n_avg: int = typer.Option(1, "--n-avg", min=1, max=256, help="scans to average"),
    f_tx: float = typer.Option(NMR_DEFAULTS["f_tx_hz"], "--f-tx", help="transmit frequency, Hz"),
    f_lo: float = typer.Option(NMR_DEFAULTS["f_lo_hz"], "--f-lo", help="local-oscillator frequency, Hz"),
    sequence: str = typer.Option("fid", help="fid or echo"),
    ref_ch: int = typer.Option(1, "--ref-ch", min=0, max=6, help="panel input carrying the Si5351 CLK2 phase reference (0 = none)"),
    csv_path: str | None = typer.Option(None, "--csv", help="write t_ms,I,Q rows of the averaged record here"),
    timeout: float = typer.Option(600.0, help="seconds to wait for the scan set"),
    host: str | None = HostOpt,
):
    """Run one NMR scan set and print the peak, the Larmor frequency and the SNR."""

    async def go():
        async with Client(discover(host)) as c:
            cfg = await nmr_config(c, f_tx_hz=f_tx, f_lo_hz=f_lo, sequence=sequence, n_avg=n_avg, ref_ch=ref_ch)
            lo = float(cfg.get("f_lo_actual_hz", cfg.get("f_lo_hz", f_lo)))
            if_hz = float(cfg.get("if_hz", float(cfg.get("f_tx_actual_hz", f_tx)) - lo))
            typer.echo(f"IF = {if_hz:.2f} Hz, {n_avg} scan(s)", err=True)
            await nmr_start(c)
            st = await nmr_wait(c, timeout_s=timeout, progress=True)
            rate_hz, z, scans = await nmr_record(c)
            freq, amp = nmr_spectrum(z, rate_hz)
            peak_hz, peak_amp, noise, snr_db = nmr_peak(freq, amp)
            typer.echo(
                json.dumps(
                    {
                        "scans": scans,
                        "rate_hz": rate_hz,
                        "n": int(z.size),
                        "peak_hz": round(peak_hz, 2),
                        "larmor_hz": round(lo + peak_hz, 2),
                        "peak_amp_v": peak_amp,
                        "noise_rms_v": noise,
                        "snr_db": round(snr_db, 2),
                        "board_snr_db": st.get("snr_db"),
                        "ref_phase_deg": st.get("ref_phase_deg"),
                        "ref_amp_v": st.get("ref_amp"),
                    },
                    indent=2,
                )
            )
            if csv_path:
                with open(csv_path, "w", newline="") as f:
                    w = csv.writer(f)
                    w.writerow(["t_ms", "I_V", "Q_V"])
                    for k, v in enumerate(z):
                        w.writerow([k * 1000.0 / rate_hz, v.real, v.imag])
                typer.echo(f"wrote {z.size} rows to {csv_path}", err=True)

    run(go())


@alarms_app.command("list")
def alarms_list(host: str | None = HostOpt):
    """List alarm rules."""

    async def go():
        async with Client(discover(host)) as c:
            r = await c.send("alarms", "list")
            for x in r["rules"]:
                flag = "*" if x["active"] else " "
                rule = f"{x['block']}.{x['key']} {x['op']} {x['threshold']}"
                typer.echo(f"{flag} #{x['id']:<3} {rule}  ->  {x['action']}  (fired {x['fired']})")
            if not r["rules"]:
                typer.echo("no rules")

    run(go())


@alarms_app.command("add")
def alarms_add(
    block: str = typer.Option(...),
    key: str = typer.Option(...),
    op: str = typer.Option("gt", help="gt lt ge le eq ne (a true/false key compares as 1/0)"),
    threshold: float = typer.Option(...),
    action: str = typer.Option("notify", help="notify | module:<n>:on | module:<n>:off (n = 1..7)"),
    host: str | None = HostOpt,
):
    """Add an alarm rule."""

    async def go():
        async with Client(discover(host)) as c:
            r = await c.send("alarms", "add", {"block": block, "key": key, "op": op, "threshold": threshold, "action": action})
            typer.echo(f"added rule #{r['id']}")

    run(go())


@alarms_app.command("remove")
def alarms_remove(rule_id: int = typer.Argument(..., help="rule id from `alarms list`"), host: str | None = HostOpt):
    """Remove an alarm rule by id."""

    async def go():
        async with Client(discover(host)) as c:
            await c.send("alarms", "remove", {"id": rule_id})
            typer.echo(f"removed rule #{rule_id}")

    run(go())


@alarms_app.command("clear")
def alarms_clear(host: str | None = HostOpt):
    """Remove every alarm rule."""

    async def go():
        async with Client(discover(host)) as c:
            await c.send("alarms", "clear")
            typer.echo("removed all rules")

    run(go())


def main():
    app()


if __name__ == "__main__":
    sys.exit(main())
