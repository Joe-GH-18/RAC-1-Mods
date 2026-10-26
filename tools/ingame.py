#!/usr/bin/env python3
"""ingame.py [--restart] [--p2] [--no-mode] [--log FILE]: into the game without anyone at the pad.

--restart closes RPCS3 and starts it again under tools/trace.py (unsaved progress is lost).
Then, from the title: Start, Load Game, the newest save, Yes; it waits for the level and, if
Golden Clank is bought, switches Giant Clank mode on (L3 + R3). The screens are told apart by
small grey thumbnails of the window against build/ingame/{title,menu,saves,confirm}.png (shots
of this machine's game, made once by hand); the buttons go into the controller's evdev node, so
RPCS3 takes them for the pad's. With the controller away (it sleeps) --restart starts
tools/vpad.py first, a virtual pad of its name that RPCS3 binds at boot, and the presses go to it.
With --p2 it also starts the second player's virtual pad (tools/vpad.py --p2, "Backport P2") before
RPCS3, for the co-op mod; RPCS3's Player 2 must be bound to it (tools/coop.py drives it).
Prints one line per step and exits 0 once in the level.
"""
import argparse
import os
import shutil
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


BLIND_PRESSES = 3
SAVES = os.path.expanduser("~/.config/rpcs3/dev_hdd0/home/00000001/savedata")
SAVE_BACKUPS = os.path.join(ROOT, "build", "saves")


def saves_state():
    """{file: (size, mtime)} of the game's saves."""
    state = {}
    for folder in sorted(os.listdir(SAVES)):
        if folder.startswith("NPEA00385"):
            for name in os.listdir(os.path.join(SAVES, folder)):
                path = os.path.join(SAVES, folder, name)
                state[path] = (os.path.getsize(path), os.path.getmtime(path))
    return state


def back_up_saves():
    """A copy of the game's saves in build/saves/<time> (the last 20 kept)."""
    os.makedirs(SAVE_BACKUPS, exist_ok=True)
    target = os.path.join(SAVE_BACKUPS, time.strftime("%Y-%m-%d_%H%M%S"))
    for folder in os.listdir(SAVES):
        if folder.startswith("NPEA00385"):
            shutil.copytree(os.path.join(SAVES, folder), os.path.join(target, folder))
    for old in sorted(os.listdir(SAVE_BACKUPS))[:-20]:
        shutil.rmtree(os.path.join(SAVE_BACKUPS, old))
    say(f"saves backed up to {target}")


def restart(log, p2=False):
    for pid in subprocess.run(["pgrep", "-x", "AppRun.wrapped"], capture_output=True, text=True).stdout.split():
        os.kill(int(pid), signal.SIGTERM)
    for _ in range(80):
        if not subprocess.run(["pgrep", "-x", "AppRun.wrapped"], capture_output=True).stdout:
            break
        time.sleep(0.25)
    else:
        sys.exit("RPCS3 did not close")
    say("RPCS3 closed, starting it under tools/trace.py")
    subprocess.run(["pkill", "-f", r"vpad\.py( --p2)?$"])   # old virtual pads (they would go with that RPCS3 anyway)
    if p2:
        say("tools/vpad.py --p2: Player 2's pad")
        subprocess.Popen([sys.executable, os.path.join(ROOT, "tools", "vpad.py"), "--p2"], cwd=ROOT,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        time.sleep(1)
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
    """Title -> menu -> saves -> confirm -> the level.

    Presses on unknown screens only while no game is loaded (no hero moby) and at most
    BLIND_PRESSES of them: on 2026-10-26 Start and Cross pressed every few seconds on screens it
    did not know reached the pause menu of a loaded (paused, so frames stood still) game and
    saved it over three slots."""
    done, unknown_since, start, blind = set(), time.time(), time.time(), 0
    while time.time() - start < timeout:
        name = screen()
        if name is None:
            if in_level():                      # (also when the last press was made by hand)
                return True
            if peek(HERO_MOBY):                 # a game is loaded (paused, or a scene): hands off
                say("a game is loaded but frames stand still (paused?): no presses")
                time.sleep(2)
                continue
            if blind < BLIND_PRESSES and not done and time.time() - unknown_since > 15:   # the attract demo: Start goes back to the title
                say("no known screen for 15 s: Start")
                press("start")
                blind += 1
                unknown_since = time.time()
            elif blind < BLIND_PRESSES and "menu" in done and time.time() - unknown_since > 6:
                # the saves or the confirm screen not matched (their thumbnails change with the
                # saves): both take Cross; no game is loaded yet, so nothing can be saved
                say("no known screen for 6 s after the menu: Cross")
                press("cross")
                blind += 1
                done.add("confirm")
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
    parser.add_argument("--p2", action="store_true", help="with --restart: start Player 2's virtual pad too")
    parser.add_argument("--log", default=os.path.join(ROOT, "build", "trace.log"))
    parser.add_argument("--timeout", type=float, default=180)
    args = parser.parse_args()
    before = saves_state()
    if args.restart:
        back_up_saves()
        restart(args.log, args.p2)
    try:
        run(args)
    finally:
        changed = [path for path, stat in saves_state().items() if before.get(path) != stat]
        if changed:
            say("WARNING: saves changed while this ran: " + ", ".join(sorted({os.path.basename(os.path.dirname(p)) for p in changed})))


def run(args):
    if not args.restart and not window():
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
