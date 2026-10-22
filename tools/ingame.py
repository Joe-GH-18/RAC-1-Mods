#!/usr/bin/env python3
"""ingame.py [--restart] [--no-mode] [--log FILE]: into the game without anyone at the pad.

--restart closes RPCS3 and starts it again under tools/trace.py (unsaved progress is lost).
Then, from the title: Start, Load Game, the newest save, Yes; it waits for the level and, if
Golden Clank is bought, switches Giant Clank mode on (L3 + R3). The screens are told apart by
small grey thumbnails of the window against build/ingame/{title,menu,saves,confirm}.png (shots
of this machine's game, made once by hand); the buttons go into the controller's evdev node, so
RPCS3 takes them for the pad's. With the controller away (it sleeps) --restart starts
tools/vpad.py first, a virtual pad of its name that RPCS3 binds at boot, and the presses go to it.
Prints one line per step and exits 0 once in the level.
"""
import argparse
import os
import signal
import struct
import subprocess
import sys
import time

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
REFS = os.path.join(ROOT, "build", "ingame")
SHOT = os.path.join(REFS, "now.png")
PAD = "/dev/input/by-id/usb-8BitDo_8BitDo_Ultimate_2C_Wireless_Controller_49CD7200C8-event-joystick"
PAD_NAME = b"8BitDo Ultimate 2C Wireless Controller"   # what RPCS3's input config (Player 1, Evdev) names
KEYS = {"cross": 0x130, "circle": 0x131, "square": 0x133, "triangle": 0x134, "l1": 0x136, "r1": 0x137,
        "select": 0x13A, "start": 0x13B, "l3": 0x13D, "r3": 0x13E}
HAT_DOWN = (3, 0x11, 1)
MATCH = 0.025                      # RMSE of the thumbnails: the same screen < 0.01, another > 0.1 (black 0.04)
HERO_MOBY, HERO_STATE, FRAME_COUNTER, OWNED, MODE = 0x969CE0 + 0x2080, 0x969CE0 + 0x2084, 0xA10710, 0x96C0B2, 0x1606320 + 0x2C0


def say(text):
    print(time.strftime("%H:%M:%S"), text, flush=True)


def window():
    ids = subprocess.run(["xdotool", "search", "--name", "NPEA00385"], capture_output=True, text=True).stdout.split()
    return ids[-1] if ids else None


def screen():
    """The reference the window looks like now, or None."""
    win = window()
    if not win:
        return None
    if subprocess.run(["import", "-window", win, "-resize", "160x90!", "-colorspace", "gray", SHOT],
                      capture_output=True).returncode:
        return None
    best, name = 1.0, None
    for ref in ("title", "menu", "saves", "confirm"):
        out = subprocess.run(["compare", "-metric", "RMSE", os.path.join(REFS, ref + ".png"), SHOT, "null:"],
                             capture_output=True, text=True).stderr
        try:
            score = float(out.split("(")[1].split(")")[0])
        except (IndexError, ValueError):
            continue
        if score < best:
            best, name = score, ref
    return name if best < MATCH else None


FIFO = os.path.join(ROOT, "build", "vpad.fifo")


class Fifo:
    """tools/vpad.py's pipe, written as its lines."""

    def __init__(self):
        # non-blocking: a pipe left behind by a vpad.py that ended would otherwise wait forever
        try:
            fd = os.open(FIFO, os.O_WRONLY | os.O_NONBLOCK)
        except OSError:
            sys.exit("the virtual pad has ended (tools/ingame.py --restart starts a new one)")
        os.set_blocking(fd, True)
        self.file = os.fdopen(fd, "w", buffering=1)

    def write(self, data):
        _, _, kind, code, value = struct.unpack("llHHi", data)
        self.file.write(f"{kind} {code} {value}\n")

    def close(self):
        self.file.close()


def pad_node():
    """Where presses go: the controller's node, or tools/vpad.py's virtual pad."""
    if os.path.exists(PAD):
        return open(PAD, "wb", buffering=0)
    if os.path.exists(FIFO):
        return Fifo()
    sys.exit("no controller and no virtual pad (tools/ingame.py --restart starts one)")


def press(*names, hold=0.15):
    pad = pad_node()
    try:
        def event(kind, code, value):
            now = time.time()
            pad.write(struct.pack("llHHi", int(now), int(now % 1 * 1e6), kind, code, value))
        for down in (1, 0):
            for name in names:
                if name == "down":
                    event(HAT_DOWN[0], HAT_DOWN[1], HAT_DOWN[2] * down)
                else:
                    event(1, KEYS[name], down)
            event(0, 0, 0)
            time.sleep(hold if down else 0.15)
    finally:
        pad.close()


def peek(address, size=4):
    """A big-endian word of the running game through tools/trace.py, or None."""
    out = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "peek.py"), f"r {address:x} {size}"],
                         capture_output=True, text=True, cwd=ROOT).stdout.split()
    try:
        return int(out[1], 16)
    except (IndexError, ValueError):
        return None


def restart(log):
    for pid in subprocess.run(["pgrep", "-x", "AppRun.wrapped"], capture_output=True, text=True).stdout.split():
        os.kill(int(pid), signal.SIGTERM)
    for _ in range(80):
        if not subprocess.run(["pgrep", "-x", "AppRun.wrapped"], capture_output=True).stdout:
            break
        time.sleep(0.25)
    else:
        sys.exit("RPCS3 did not close")
    say("RPCS3 closed, starting it under tools/trace.py")
    subprocess.run(["pkill", "-f", r"vpad\.py$"])   # an old virtual pad (it would go with that RPCS3 anyway)
    if not os.path.exists(PAD):              # RPCS3 binds a pad only at boot: the virtual one must be there
        say("no controller: tools/vpad.py stands in for it")
        subprocess.Popen([sys.executable, os.path.join(ROOT, "tools", "vpad.py")], cwd=ROOT,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        for _ in range(20):
            if os.path.exists(FIFO):
                break
            time.sleep(0.25)
        time.sleep(1)
    with open(log, "w") as out:
        subprocess.Popen([sys.executable, os.path.join(ROOT, "tools", "trace.py")], cwd=ROOT,
                         stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
    for _ in range(120):
        if window():
            return
        time.sleep(0.5)
    sys.exit("no game window after 60 s")


def in_level():
    """Ratchet is there and frames go on."""
    if not peek(HERO_MOBY):
        return False
    first = peek(FRAME_COUNTER)
    time.sleep(0.3)
    second = peek(FRAME_COUNTER)
    return first is not None and second is not None and second > first > 60


def load(timeout):
    """Title -> menu -> saves -> confirm -> the level."""
    done, unknown_since, start = set(), time.time(), time.time()
    while time.time() - start < timeout:
        name = screen()
        if name is None:
            if "confirm" in done and in_level():
                return True
            if not done and time.time() - unknown_since > 15:     # the attract demo: Start goes back to the title
                say("no known screen for 15 s: Start")
                press("start")
                unknown_since = time.time()
            time.sleep(1)
            continue
        unknown_since = time.time()
        if name == "title":
            press("start")
        elif name == "menu":
            press("down")
            time.sleep(0.4)
            press("cross")
        elif name in ("saves", "confirm"):
            press("cross")
        if name not in done:
            say(f"{name}: pressed")
        done.add(name)
        time.sleep(2)
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--restart", action="store_true")
    parser.add_argument("--no-mode", action="store_true")
    parser.add_argument("--log", default=os.path.join(ROOT, "build", "trace.log"))
    parser.add_argument("--timeout", type=float, default=180)
    args = parser.parse_args()
    if args.restart:
        restart(args.log)
    elif not window():
        sys.exit("no game window (use --restart)")
    if not in_level():
        if not load(args.timeout):
            sys.exit(f"not in a level after {args.timeout:.0f} s (last screen: {SHOT})")
    say("in the level")
    if args.no_mode or peek(OWNED, 2) != 1:
        return
    for _ in range(60):                # the level's intro (the ship landing) takes no buttons: until he stands
        if peek(HERO_STATE) == 0:
            break
        time.sleep(0.5)
    time.sleep(1)
    for _ in range(3):
        if peek(MODE) == 1:
            say("Giant Clank mode on")
            return
        press("l3", "r3")
        time.sleep(1.5)
    sys.exit("Giant Clank mode did not come on")


if __name__ == "__main__":
    main()
