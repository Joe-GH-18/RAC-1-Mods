#!/usr/bin/env python3
"""coop_align.py: place Co-op Clank's Thruster-Pack (wings and jets) on him in the running game.

Run it in a terminal of its own while the game runs under tools/trace.py (tools/ingame.py) with
Clank out (Player 2 joined). Each key moves or turns the pack at once; nothing else may use
tools/peek.py meanwhile. Player 2's test input is switched off, so your own pad flies him.

  w / s    up / down             q / e    ahead / back          a / d    to his left / right
  i / k    pitch                 j / l    yaw                   u / o    roll
  z / x    smaller / bigger (0 = the pack's own size)
  1 2 3    fine / normal / coarse steps
  v        turn Clank a quarter round and hold him there (views from the side, behind, ...)
  b        let him turn by himself again
  r        back to the values at the start
  p        print the values
  Enter    keep them and quit: written to build/coop_wings.txt and printed as the lines for
           mods/coop/layout.py (the game keeps them until it restarts)
  Esc, Ctrl+C   quit and put the start values back
"""
import math
import os
import struct
import sys
import termios
import tty

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

from coop import block                    # noqa: E402
from live import read, write              # noqa: E402
from mods.coop import layout as L          # noqa: E402

FIELDS = ("T_WINGS_AHEAD", "T_WINGS_LEFT", "T_WINGS_UP", "T_WINGS_ROLL", "T_WINGS_PITCH", "T_WINGS_YAW", "T_WINGS_SCALE")
KEYS = {"w": ("T_WINGS_UP", 1), "s": ("T_WINGS_UP", -1), "q": ("T_WINGS_AHEAD", 1), "e": ("T_WINGS_AHEAD", -1),
        "a": ("T_WINGS_LEFT", 1), "d": ("T_WINGS_LEFT", -1), "i": ("T_WINGS_PITCH", 1), "k": ("T_WINGS_PITCH", -1),
        "j": ("T_WINGS_YAW", 1), "l": ("T_WINGS_YAW", -1), "u": ("T_WINGS_ROLL", 1), "o": ("T_WINGS_ROLL", -1),
        "x": ("T_WINGS_SCALE", 1), "z": ("T_WINGS_SCALE", -1)}
STEPS = {"1": (0.005, 0.01), "2": (0.02, 0.05), "3": (0.08, 0.2)}      # (units, radians)
ANGLES = {"T_WINGS_ROLL", "T_WINGS_PITCH", "T_WINGS_YAW"}


def get(at, name, fmt=">f"):
    return struct.unpack(fmt, read(at + getattr(L, name), 4))[0]


def put(at, name, value, fmt=">f"):
    write(at + getattr(L, name), struct.pack(fmt, value))


def wrap(angle):
    return (angle + math.pi) % (2 * math.pi) - math.pi


def show(values, step):
    text = "  ".join(f"{name[8:].lower()} {values[name]:+.3f}" for name in FIELDS)
    print(f"\r{text}   step {step[0]:g}/{step[1]:g}   ", end="", flush=True)


def lines(values):
    return [f'    ("T_WINGS_AHEAD", "f", {values["T_WINGS_AHEAD"]:.3f}), ("T_WINGS_LEFT", "f", {values["T_WINGS_LEFT"]:.3f}), '
            f'("T_WINGS_UP", "f", {values["T_WINGS_UP"]:.3f}), ("T_WINGS_SCALE", "f", {values["T_WINGS_SCALE"]:.3f}),',
            f'    ("T_WINGS_ROLL", "f", {values["T_WINGS_ROLL"]:.3f}), ("T_WINGS_PITCH", "f", {values["T_WINGS_PITCH"]:.3f}), '
            f'("T_WINGS_YAW", "f", {values["T_WINGS_YAW"]:.3f}),']


def main():
    at = block()
    if get(at, "C_MODE", ">i") != L.MODE_FLY:
        print("Clank is not out: join with Player 2 (Start or Cross) first")
    put(at, "C_TEST", 0, ">i")                              # your pad, not the test input
    start = {name: get(at, name) for name in FIELDS}
    turn = get(at, "T_TURN")
    if start["T_WINGS_SCALE"] == 0.0:                       # 0 leaves the pack's own size: start from it
        wings = struct.unpack(">I", read(at + L.C_WINGS, 4))[0]
        own = struct.unpack(">f", read(wings + 0x2c, 4))[0] if wings else 0.0
    else:
        own = start["T_WINGS_SCALE"]
    values, step = dict(start), STEPS["2"]
    print(__doc__.split("\n\n", 1)[1].split("\n\n")[1])
    show(values, step)
    old = termios.tcgetattr(sys.stdin)
    keep = False
    try:
        tty.setcbreak(sys.stdin.fileno())
        while True:
            key = sys.stdin.read(1)
            if key in ("\x1b", "\x03"):
                break
            if key in ("\n", "\r"):
                keep = True
                break
            if key in KEYS:
                name, sign = KEYS[key]
                if name == "T_WINGS_SCALE":
                    base = values[name] if values[name] else own
                    values[name] = max(0.01, base + sign * step[0])
                elif name in ANGLES:
                    values[name] = wrap(values[name] + sign * step[1])
                else:
                    values[name] += sign * step[0]
                put(at, name, values[name])
            elif key in STEPS:
                step = STEPS[key]
            elif key == "v":
                put(at, "T_TURN", 0.0)
                put(at, "C_YAW", wrap(get(at, "C_YAW") + math.pi / 2))
            elif key == "b":
                put(at, "T_TURN", turn)
            elif key == "r":
                values = dict(start)
                for name in FIELDS:
                    put(at, name, values[name])
            elif key == "p":
                print("\n" + "\n".join(lines(values)))
            show(values, step)
    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old)
        put(at, "T_TURN", turn)
    print()
    if keep:
        text = "\n".join(lines(values))
        with open(os.path.join(ROOT, "build", "coop_wings.txt"), "w") as out:
            out.write(text + "\n")
        print("kept (build/coop_wings.txt; for mods/coop/layout.py):\n" + text)
    else:
        for name in FIELDS:
            put(at, name, start[name])
        print("put back as they were")


if __name__ == "__main__":
    main()
