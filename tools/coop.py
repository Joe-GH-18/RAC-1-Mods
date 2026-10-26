#!/usr/bin/env python3
"""coop.py <command> ...: Player 2's virtual pad and the co-op mod's block in a running game.

Needs the game started under tools/trace.py with Player 2's virtual pad
(tools/ingame.py --restart --p2) and RPCS3's Player 2 bound to "Backport P2".

  block                where the mod's block is
  state                the block and Player 2's pad block, decoded
  press BUTTON...      press buttons on Player 2's pad (cross circle square triangle l1 r1 l2 r2
                       select start l3 r3 up down left right), held 0.15 s
  hold SECONDS BUTTON...  the same, held that long
  stick X Y SECONDS    Player 2's left stick (-1..1, y up) for that long, then centred
"""
import os
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)

from live import peek, read           # noqa: E402

FIFO = os.path.join(ROOT, "build", "vpad2.fifo")
TAG = b"COOP-CLANK-BLOCK"
RW, RW_SIZE = 0x1630000, 0x10000      # mods/game.py SEGMENTS["rw"]
STATE = 0x1606320
COOP_OUT, COOP_P2, COOP_PILOT, COOP_PAD = 0x340, 0x344, 0x348, 0x34C
KEYS = {"cross": 0x130, "circle": 0x131, "square": 0x133, "triangle": 0x134, "l1": 0x136, "r1": 0x137,
        "l2": 0x138, "r2": 0x139, "select": 0x13A, "start": 0x13B, "l3": 0x13D, "r3": 0x13E}
HATS = {"up": (0x11, -1), "down": (0x11, 1), "left": (0x10, -1), "right": (0x10, 1)}
TRIGGERS = {"l2": 0x02, "r2": 0x05}   # also as axes, as the real pad sends them
BITS = {0x1: "L2", 0x2: "R2", 0x4: "L1", 0x8: "R1", 0x10: "triangle", 0x20: "circle", 0x40: "cross",
        0x80: "square", 0x100: "select", 0x200: "L3", 0x400: "R3", 0x800: "start", 0x1000: "up",
        0x2000: "right", 0x4000: "down", 0x8000: "left"}


def block():
    """The address of the mod's block (behind its tag in the rw segment), or exit."""
    data = b""
    for at in range(RW, RW + RW_SIZE, 0x800):
        data += read(at, 0x800)
        found = data.find(TAG)
        if found >= 0:
            return RW + found + len(TAG)
    sys.exit("no co-op block: is the mod built in?")


class Pad:
    def __init__(self):
        try:
            fd = os.open(FIFO, os.O_WRONLY | os.O_NONBLOCK)
        except OSError:
            sys.exit("Player 2's virtual pad is not running (tools/ingame.py --restart --p2)")
        os.set_blocking(fd, True)
        self.file = os.fdopen(fd, "w", buffering=1)

    def event(self, kind, code, value):
        self.file.write(f"{kind} {code} {value}\n")

    def sync(self):
        self.event(0, 0, 0)

    def buttons(self, names, down):
        for name in names:
            if name in HATS:
                axis, value = HATS[name]
                self.event(3, axis, value * down)
            else:
                self.event(1, KEYS[name], down)
                if name in TRIGGERS:
                    self.event(3, TRIGGERS[name], 255 * down)
        self.sync()

    def stick(self, x, y):
        self.event(3, 0, int(max(-1, min(1, x)) * 32767))
        self.event(3, 1, int(max(-1, min(1, -y)) * 32767))
        self.sync()


def hold(seconds, names):
    pad = Pad()
    pad.buttons(names, 1)
    time.sleep(seconds)
    pad.buttons(names, 0)
    time.sleep(0.1)


def state():
    at = block()
    words = struct.unpack(">5I", read(at, 20))
    shared = struct.unpack(">4I", read(STATE + COOP_OUT, 16))
    print(f"block {at:#x}: read at frame {words[0]}, {words[1]} reads, port {words[2]}, "
          f"held {words[3]:#x} ({names(words[3])}), pressed {words[4]:#x}")
    print(f"shared: out {shared[0]}, p2 {shared[1]}, pilot {shared[2]}, pad block {shared[3]:#x}")
    if shared[3]:
        pad = read(shared[3], 0xb0)
        lx, ly = struct.unpack(">2f", pad[8:16])
        held, pressed = struct.unpack(">2I", pad[0xa0:0xa8])
        active = struct.unpack(">I", pad[0x9c:0xa0])[0]
        print(f"pad: active {active}, stick {lx:+.2f} {ly:+.2f}, held {held:#x} ({names(held)}), pressed {pressed:#x}")


def names(bits):
    return " ".join(name for bit, name in BITS.items() if bits & bit) or "-"


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    command, rest = sys.argv[1], sys.argv[2:]
    if command == "block":
        print(f"{block():#x}")
    elif command == "state":
        state()
    elif command == "press":
        hold(0.15, rest)
    elif command == "hold":
        hold(float(rest[0]), rest[1:])
    elif command == "stick":
        pad = Pad()
        pad.stick(float(rest[0]), float(rest[1]))
        time.sleep(float(rest[2]))
        pad.stick(0, 0)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
