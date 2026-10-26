#!/usr/bin/env python3
"""vpad.py [--name NAME --fifo PATH]: a virtual pad for RPCS3 while the real controller is away
(it sleeps, and RPCS3 binds a pad only at boot). Makes a uinput device with the controller's name,
buttons and axes (sticks centred), takes input events from the pipe build/vpad.fifo as lines
"type code value" (a line "0 0 0" ends a report), and ends with RPCS3 (or after a minute if RPCS3
never comes). tools/ingame.py starts it before RPCS3 when the controller is missing and writes to it.
--p2 makes the second player's pad instead: "Backport P2" on build/vpad2.fifo, which RPCS3's
Player 2 is bound to for the co-op mod (tools/ingame.py --p2 starts it, tools/coop.py drives it).
"""
import argparse
import fcntl
import os
import select
import struct
import subprocess
import time

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
FIFO = os.path.join(ROOT, "build", "vpad.fifo")
NAME = b"8BitDo Ultimate 2C Wireless Controller"   # what RPCS3's input config (Player 1, Evdev) names
P2_NAME, P2_FIFO = b"Backport P2", os.path.join(ROOT, "build", "vpad2.fifo")   # (Player 2)
UI_SET_EVBIT, UI_SET_KEYBIT, UI_SET_ABSBIT, UI_DEV_CREATE, UI_DEV_DESTROY = 0x40045564, 0x40045565, 0x40045567, 0x5501, 0x5502
BUTTONS = range(0x130, 0x13F)
AXES = {0x00: (-32768, 32767), 0x01: (-32768, 32767), 0x02: (0, 255), 0x03: (-32768, 32767),
        0x04: (-32768, 32767), 0x05: (0, 255), 0x10: (-1, 1), 0x11: (-1, 1)}


def rpcs3_running():
    return bool(subprocess.run(["pgrep", "-x", "AppRun.wrapped"], capture_output=True).stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--p2", action="store_true", help="the second player's pad")
    parser.add_argument("--name", help="the device's name")
    parser.add_argument("--fifo", help="the pipe it reads")
    args = parser.parse_args()
    name = (args.name.encode() if args.name else P2_NAME if args.p2 else NAME)
    fifo = args.fifo or (P2_FIFO if args.p2 else FIFO)
    product = 0x3106 if name == NAME else 0x3107
    device = open("/dev/uinput", "wb", buffering=0)
    for kind in (1, 3):
        fcntl.ioctl(device, UI_SET_EVBIT, kind)
    for key in BUTTONS:
        fcntl.ioctl(device, UI_SET_KEYBIT, key)
    absmax, absmin = [0] * 64, [0] * 64
    for axis, (low, high) in AXES.items():
        fcntl.ioctl(device, UI_SET_ABSBIT, axis)
        absmin[axis], absmax[axis] = low, high
    setup = name.ljust(80, b"\0") + struct.pack("<4HI", 3, 0x2DC8, product, 0x111, 0)
    setup += struct.pack("<64i", *absmax) + struct.pack("<64i", *absmin) + bytes(4 * 64 * 2)
    device.write(setup)
    fcntl.ioctl(device, UI_DEV_CREATE)
    if os.path.exists(fifo):
        os.remove(fifo)
    os.mkfifo(fifo)
    pipe = os.open(fifo, os.O_RDWR | os.O_NONBLOCK)    # (read-write: no EOF when a writer goes)
    mine = os.fstat(pipe).st_ino
    seen, start, buffer = False, time.time(), b""
    try:
        while True:
            if select.select([pipe], [], [], 2.0)[0]:
                buffer += os.read(pipe, 4096)
                *lines, buffer = buffer.split(b"\n")
                for line in lines:
                    kind, code, value = (int(v) for v in line.split())
                    now = time.time()
                    device.write(struct.pack("llHHi", int(now), int(now % 1 * 1e6), kind, code, value))
            running = rpcs3_running()
            seen = seen or running
            if (seen and not running) or (not seen and time.time() - start > 60):
                break
    finally:
        fcntl.ioctl(device, UI_DEV_DESTROY)
        os.close(pipe)
        try:
            if os.stat(fifo).st_ino == mine:            # (not a newer vpad.py's)
                os.remove(fifo)
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    main()
