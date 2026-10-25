#!/usr/bin/env python3
"""stage.py <command> ...: set up the scenes of the Golden Clank video in the running game.

Needs the game started under tools/trace.py (tools/ingame.py --restart does that).

  mark NAME            remember where Ratchet stands now (level, place, facing) as a spot
  go NAME              put him there again (travels to the spot's level first if needed)
  spots                list the spots
  travel LEVEL         fly to a level (0..18, Novalis 1, Batalia 8, Gemlik 13) as the ship menu does
  purchase             the purchase scene from the start: saves backed up, 40 gold bolts,
                       Golden Clank not bought, the mode off; then walk him to the gold display
  restore              after the purchase takes: the saves, gold bolts and purchase as before
  mode on|off          Giant Clank mode (presses L3 + R3)
  bomb                 the golden bomb ready again (no cooldown)
  view side|left|behind|front|top|off [DISTANCE]
                       the mod's debug camera (VIEW) around him, or the game's camera back
  rec NAME [SECONDS]   film the game window at 60 fps with the game's sound to
                       build/video/raw/NAME-NN.mkv; Ctrl+C (or SECONDS) stops
  where                level, place and state now

The spots are kept in build/stage/spots.json, the saves' backup in build/stage/savedata.
"""
import json
import math
import os
import shutil
import signal
import struct
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)

from ingame import OWNED, MODE, HERO_STATE, press, window          # noqa: E402
from live import peek                                             # noqa: E402

STAGE = os.path.join(ROOT, "build", "stage")
SPOTS = os.path.join(STAGE, "spots.json")
BOLTS_KEPT = os.path.join(STAGE, "gold_bolts.json")
SAVES_KEPT = os.path.join(STAGE, "savedata")
RAW = os.path.join(ROOT, "build", "video", "raw")
SAVEDATA = os.path.expanduser("~/.config/rpcs3/dev_hdd0/home/00000001/savedata")

HERO = 0x969CE0
PLACE, FACING = HERO + 0x80, HERO + 0x90         # 3 floats each: place, euler angles (+0x98 the yaw)
PLANET = 0x969C70
GOLD_BOLTS, GOLD_BOLT_BYTES = 0xA0CA34, 80       # flag bytes, 4 per planet; the count takes all 80
TRAVEL_LEVEL, TRAVEL_GO, TRAVEL_ARM = 0xA10704, 0xA1071C, 0xA10700
BOMB_WAIT = 0x1606320 + 0x330
LEVELS = ["Veldin", "Novalis", "Aridia", "Kerwan", "Eudora", "Rilgar", "Blarg Station", "Umbris",
          "Batalia", "Gaspar", "Orxon", "Pokitaru", "Hoven", "Gemlik Base", "Oltanis", "Quartu",
          "Kalebo III", "Drek's Fleet", "Veldin (2)"]
VIEWS = {"behind": 0.0, "side": math.pi / 2, "left": -math.pi / 2, "front": math.pi}   # VIEW turn 0 = behind him


def write(addr, data):
    out = subprocess.run([sys.executable, os.path.join(HERE, "peek.py"), f"w {addr:x} {data.hex()}"],
                         capture_output=True, text=True).stdout
    if "written" not in out:
        sys.exit(f"write at {addr:#x} failed: is tools/trace.py attached? ({out.strip()})")


def read(addr, n):
    got = peek(f"r {addr:x} {n}")
    if addr not in got:
        sys.exit("no answer: start the game with tools/ingame.py --restart (it attaches tools/trace.py)")
    return got[addr]


def u32(addr):
    return struct.unpack(">I", read(addr, 4))[0]


def owned():
    return struct.unpack(">H", read(OWNED, 2))[0]


def giant():
    """The address of the mod's GIANT block in the build installed (it moves with the texts)."""
    cache = os.path.join(STAGE, "giant.json")
    eboot = os.path.join(ROOT, "build", "EBOOT.elf")
    stamp = os.path.getmtime(eboot)
    try:
        kept = json.load(open(cache))
        if kept["stamp"] == stamp:
            return kept["giant"]
    except (OSError, ValueError, KeyError):
        pass
    code = ("import sys; sys.argv = ['build.py']; import build; from ppu import Elf; "
            "args = build.parse_args(); units, _ = build.build(args, Elf(args.src)); "
            "print(units['goldenclank'].addr['giant'])")
    py = os.path.join(ROOT, ".venv", "bin", "python")
    out = subprocess.run([py if os.path.exists(py) else sys.executable, "-c", code], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout
    addr = int(out.split()[-1])
    os.makedirs(STAGE, exist_ok=True)
    json.dump({"stamp": stamp, "giant": addr}, open(cache, "w"))
    return addr


def spots():
    try:
        return json.load(open(SPOTS))
    except (OSError, ValueError):
        return {}


def wait_level(level, timeout=120):
    """Until the level is loaded and Ratchet stands (hero state 0)."""
    start = time.time()
    while time.time() - start < timeout:
        if u32(PLANET) == level and u32(HERO + 0x2080) and u32(HERO_STATE) == 0:
            return
        time.sleep(1)
    sys.exit(f"not standing in {LEVELS[level]} after {timeout} s")


def travel(level):
    if u32(PLANET) == level:
        return
    print(f"flying to {LEVELS[level]} ...")
    write(TRAVEL_LEVEL, struct.pack(">I", level))
    write(TRAVEL_GO, struct.pack(">I", 1))
    write(TRAVEL_ARM, struct.pack(">I", 1))
    time.sleep(5)
    wait_level(level)


def place(x, y, z, facing):
    write(PLACE, struct.pack(">3f", x, y, z))
    write(FACING, bytes.fromhex(facing))


def set_mode(on):
    if owned() != 1:
        sys.exit("Golden Clank is not bought in this game")
    for _ in range(3):
        if u32(MODE) == on:
            print(f"Giant Clank mode {'on' if on else 'off'}")
            return
        press("l3", "r3")
        time.sleep(1.5)
    sys.exit("the mode did not switch (is Ratchet standing, not in a menu?)")


def view(how, distance):
    at = giant() + __import__("mods.goldenclank", fromlist=["G_VIEW"]).G_VIEW
    if how == "off":
        write(at, struct.pack(">I", 0))
        return
    pitch = 1.5707963 if how == "top" else 0.12
    turn = VIEWS.get(how, 0.0)
    distance = distance or (9.0 if how == "top" else 6.0)
    write(at + 4, struct.pack(">5f", distance, math.cos(pitch), -math.sin(pitch) if how == "top" else math.sin(pitch), turn, 1.8))
    write(at, struct.pack(">I", 1))


def backup_saves():
    if os.path.exists(SAVES_KEPT):
        print(f"saves already backed up in {SAVES_KEPT} (restore puts them back)")
        return
    os.makedirs(SAVES_KEPT)
    for name in os.listdir(SAVEDATA):
        if name.startswith("NPEA00385"):
            shutil.copytree(os.path.join(SAVEDATA, name), os.path.join(SAVES_KEPT, name))
    print(f"saves backed up to {SAVES_KEPT}")


def purchase():
    backup_saves()
    if not os.path.exists(BOLTS_KEPT):
        json.dump({"bolts": read(GOLD_BOLTS, GOLD_BOLT_BYTES).hex(), "owned": owned()},
                  open(BOLTS_KEPT, "w"))
    if u32(MODE) == 1:
        set_mode(0)
    travel(1)
    bolts = bytearray(bytes.fromhex(json.load(open(BOLTS_KEPT))["bolts"]))   # the count adds up all 80
    for i in range(GOLD_BOLT_BYTES):                                          # bytes: the ones he has and
        if sum(1 for b in bolts if b) >= 40:                                  # more up to 40
            break
        bolts[i] = bolts[i] or 1
    write(GOLD_BOLTS, bytes(bolts))
    write(OWNED, struct.pack(">H", 0))
    print("40 gold bolts, Golden Clank for sale. ", end="")
    if "room" in spots():
        go("room")
        print("Ratchet is at the spot 'room'.")
    else:
        print("Walk Ratchet into the gold weapons room, then 'stage.py mark room' for the next take.")
    print("The scene saves when it ends: run 'stage.py restore' when the takes are done.")


def restore():
    if os.path.exists(BOLTS_KEPT):
        kept = json.load(open(BOLTS_KEPT))
        write(GOLD_BOLTS, bytes.fromhex(kept["bolts"]))
        write(OWNED, struct.pack(">H", kept["owned"]))
        os.remove(BOLTS_KEPT)
        print("gold bolts and the purchase as before (in the running game)")
    if os.path.exists(SAVES_KEPT):
        for name in os.listdir(SAVES_KEPT):
            target = os.path.join(SAVEDATA, name)
            shutil.rmtree(target, ignore_errors=True)
            shutil.copytree(os.path.join(SAVES_KEPT, name), target)
        shutil.rmtree(SAVES_KEPT)
        print("saves put back; do not save again in this session (or restart: tools/ingame.py --restart)")


def go(name):
    spot = spots().get(name)
    if not spot:
        sys.exit(f"no spot '{name}' (spots: {', '.join(spots()) or 'none'})")
    travel(spot["level"])
    place(*spot["place"], spot["facing"])


def mark(name):
    level = u32(PLANET)
    x, y, z = struct.unpack(">3f", read(PLACE, 12))
    all_spots = spots()
    all_spots[name] = {"level": level, "place": [x, y, z], "facing": read(FACING, 16).hex()}
    os.makedirs(STAGE, exist_ok=True)
    json.dump(all_spots, open(SPOTS, "w"), indent=1)
    print(f"{name}: {LEVELS[level]} ({x:.1f}, {y:.1f}, {z:.1f})")


def rec(name, seconds):
    win = window()
    if not win:
        sys.exit("no game window")
    os.makedirs(RAW, exist_ok=True)
    n = 1
    while os.path.exists(os.path.join(RAW, f"{name}-{n:02}.mkv")):
        n += 1
    out = os.path.join(RAW, f"{name}-{n:02}.mkv")
    sink = subprocess.run(["pactl", "get-default-sink"], capture_output=True, text=True).stdout.strip()
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error",
           "-f", "x11grab", "-framerate", "60", "-window_id", win, "-i", os.environ.get("DISPLAY", ":0"),
           "-f", "pulse", "-i", sink + ".monitor",
           "-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "16", "-pix_fmt", "yuv420p",
           "-vf", "crop=trunc(iw/2)*2:trunc(ih/2)*2", "-c:a", "aac", "-b:a", "256k"]
    cmd += (["-t", str(seconds)] if seconds else []) + [out]
    print(f"recording {out}" + (f" for {seconds} s" if seconds else ", Ctrl+C stops"))
    proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL)
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.send_signal(signal.SIGINT)
        proc.wait()
    print(f"saved {out}")


def where():
    level = u32(PLANET)
    x, y, z = struct.unpack(">3f", read(PLACE, 12))
    print(f"{LEVELS[level]} (level {level}), ({x:.1f}, {y:.1f}, {z:.1f}), hero state {u32(HERO_STATE):#x}, "
          f"mode {'on' if u32(MODE) == 1 else 'off'}, gold bolts {sum(1 for b in read(GOLD_BOLTS, GOLD_BOLT_BYTES) if b)}")


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        sys.exit(__doc__)
    cmd, rest = args[0], args[1:]
    if cmd == "mark":
        mark(rest[0])
    elif cmd == "go":
        go(rest[0])
    elif cmd == "spots":
        for name, spot in spots().items():
            print(f"{name}: {LEVELS[spot['level']]} ({', '.join(f'{v:.1f}' for v in spot['place'])})")
    elif cmd == "travel":
        travel(int(rest[0]))
    elif cmd == "purchase":
        purchase()
    elif cmd == "restore":
        restore()
    elif cmd == "mode":
        set_mode(1 if rest[0] == "on" else 0)
    elif cmd == "bomb":
        write(BOMB_WAIT, struct.pack(">I", 0))
    elif cmd == "view":
        view(rest[0], float(rest[1]) if len(rest) > 1 else None)
    elif cmd == "rec":
        rec(rest[0], float(rest[1]) if len(rest) > 1 else None)
    elif cmd == "where":
        where()
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
