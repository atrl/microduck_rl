#!/usr/bin/env python3
"""CyberBrick X11 USB-CDC receiver -> upstream MicroDuck netpadd (DKPD v1).

Requires pyserial only when executing main(). The encoder and safety guards
are standard-library-only so tests can run without any robot hardware.
"""

from __future__ import annotations

import argparse
import secrets
import socket
import struct
import time
from dataclasses import dataclass

DEFAULT_CENTERS = (2080, 1960, 1960, 1920)  # X12 L2/L3/R2/R3; calibrate!
TICK_MODULUS = 1 << 30  # ESP32 MicroPython ticks_ms() period
START = 1 << 6


@dataclass(frozen=True)
class RemoteFrame:
    tick_ms: int
    channels: tuple[int, ...]


def parse_line(line: bytes | str) -> RemoteFrame | None:
    """Accept *only* timestamped 'CB,tick,L1,...,K4' receiver frames."""
    try:
        if isinstance(line, bytes):
            line = line.decode("ascii")
        parts = line.strip().split(",")
        if len(parts) != 12 or parts[0] != "CB":
            return None
        nums = tuple(int(part) for part in parts[1:])
        tick, channels = nums[0], nums[1:]
        if not 0 <= tick < TICK_MODULUS:
            return None
        if not all(0 <= value <= 4095 for value in channels[:6]):
            return None
        if not all(value in (0, 1) for value in channels[6:]):
            return None
        return RemoteFrame(tick, channels)
    except (UnicodeError, ValueError):
        return None


def axis(raw: int, center: int) -> int:
    """Positive is right/up; leave deadzone to MicroDuck pad-map."""
    if not (0 < center < 4095):
        raise ValueError("ADC centers must be between 1 and 4094")
    span = center if raw <= center else 4095 - center
    normalized = (center - raw) / span
    return max(-32767, min(32767, round(normalized * 32767)))


def pad_state(frame: RemoteFrame, centers=DEFAULT_CENTERS, extra_buttons=False):
    l1, l2, l3, r1, r2, r3, k1, k2, k3, k4 = frame.channels
    del l1, r1  # Trimmer and 3-way switch are intentionally unmapped.
    axes = (
        axis(l2, centers[0]), axis(l3, centers[1]),
        axis(r2, centers[2]), axis(r3, centers[3]),
        0, 0,  # LT/RT
    )
    # CyberBrick switches are active low. K2-K4 absent on stock remote.
    buttons = START if k1 == 0 else 0
    if extra_buttons:
        if k2 == 0:
            buttons |= 1 << 0   # A
        if k3 == 0:
            buttons |= 1 << 2   # X
        if k4 == 0:
            buttons |= 1 << 9   # D-pad Down
    return axes, buttons


def encode_packet(sequence: int, tick_ms: int, axes=(0,) * 6, buttons=0) -> bytes:
    """Matches https://github.com/pollen-robotics/microduck/.../udp-pad.md."""
    if len(axes) != 6:
        raise ValueError("need six pad axes")
    return b"DKPD" + struct.pack(
        "<BBII6hH", 1, 0, sequence & 0xFFFFFFFF, tick_ms & 0xFFFFFFFF,
        *axes, buttons,
    )


class FreshnessGuard:
    """Drop buffered USB-CDC frames using their *receiver* monotonic clock.

    Tracks the best (minimum) arrival-time offset, rejecting frames whose
    excess queue delay exceeds max_lag_ms. reset() after a gap/reconnect.
    """

    def __init__(self, max_lag_ms=150):
        self.max_lag_ms = max_lag_ms
        self.reset()

    def reset(self):
        self.last_tick = None
        self.best_offset = None
        self.unwrapped_tick = None

    def accept(self, tick_ms: int, received_ms: int) -> bool:
        if self.last_tick is None:
            unwrapped = tick_ms
        else:
            delta = (tick_ms - self.last_tick) % TICK_MODULUS
            # A reset, reversed clock or long backlog is not a new input.
            if delta == 0 or delta > 1000:
                return False
            unwrapped = self.unwrapped_tick + delta
        offset = received_ms - unwrapped
        if self.best_offset is None or offset < self.best_offset:
            self.best_offset = offset
        self.last_tick, self.unwrapped_tick = tick_ms, unwrapped
        return offset - self.best_offset <= self.max_lag_ms


def _parse_centers(raw: str) -> tuple[int, int, int, int]:
    try:
        vals = tuple(int(v.strip()) for v in raw.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("centers must be four integers") from exc
    if len(vals) != 4 or any(v <= 0 or v >= 4095 for v in vals):
        raise argparse.ArgumentTypeError("centers must be four values in 1..4094")
    return vals


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="/dev/ttyACM0", help="X11 USB CDC device")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--target", default="127.0.0.1", help="host running MicroDuck netpadd")
    parser.add_argument("--udp-port", type=int, default=4210)
    parser.add_argument("--centers", type=_parse_centers, default=DEFAULT_CENTERS,
                        help="L2,L3,R2,R3 ADC centers, read from --dry-run")
    parser.add_argument("--extra-buttons", action="store_true", help="enable optional K2/K3/K4")
    parser.add_argument("--dry-run", action="store_true", help="never send UDP commands")
    args = parser.parse_args()

    try:
        import serial
    except ImportError as exc:
        parser.error("install receiver dependency: python3 -m pip install pyserial")
        raise AssertionError from exc

    seq = secrets.randbits(32)
    guard = FreshnessGuard()
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Standard DSCP EF as recommended by netpadd; harmless on unmanaged Wi-Fi.
    try:
        udp.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, 0xB8)
    except OSError:
        pass
    address = (args.target, args.udp_port)
    last_frame_s = None
    last_dry_print_s = 0.0
    active = False

    def send(axes=(0,) * 6, buttons=0):
        nonlocal seq
        seq = (seq + 1) & 0xFFFFFFFF
        if not args.dry_run:
            udp.sendto(encode_packet(seq, int(time.monotonic() * 1000), axes, buttons), address)

    try:
        with serial.Serial(args.port, args.baud, timeout=0.04) as receiver:
            # Flush bytes from the stock firmware or the previous run.
            receiver.reset_input_buffer()
            print("CyberBrick", args.port, "DRY RUN" if args.dry_run else f"-> {address}")
            while True:
                now = time.monotonic()
                # On remote/serial loss, send neutral ONCE, then stop. Continuous
                # zero packets would prevent upstream netpadd timeout/sitdown.
                if active and last_frame_s is not None and now - last_frame_s > 0.20:
                    send()
                    active = False
                    guard.reset()
                # If host was starved, never replay a backlog of old actions.
                if receiver.in_waiting > 512:
                    receiver.reset_input_buffer()
                    if active:
                        send()
                        active = False
                    guard.reset()
                    continue
                raw = receiver.readline()
                frame = parse_line(raw)
                if frame is None:
                    continue
                now = time.monotonic()
                if not guard.accept(frame.tick_ms, int(now * 1000)):
                    continue
                axes, buttons = pad_state(frame, args.centers, args.extra_buttons)
                send(axes, buttons)
                last_frame_s = now
                active = True
                if args.dry_run and now - last_dry_print_s > 0.25:
                    print("axes=", axes[:4], "buttons=", hex(buttons), "raw=", frame.channels)
                    last_dry_print_s = now
    except KeyboardInterrupt:
        print("Stopping")
    finally:
        if active:
            try:
                send()  # Explicit neutral, then let netpadd time out.
            except OSError:
                pass
        udp.close()


if __name__ == "__main__":
    main()
