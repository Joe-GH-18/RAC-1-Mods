#!/usr/bin/env python3
"""Show or set the weapon levels of a running game (through tools/trace.py; see mods/weaponlevels/).

levels.py                  every weapon: owned, experience / what level 2 takes, gold
levels.py near <item>      leave the weapon one kill short of level 2
levels.py set <item> <xp>  set its experience (0 also takes a level 2 back, and the gold version)
levels.py give <item>      set the item's byte in the unlock block and fill its ammunition (not tried for every weapon)
levels.py give all         the same for every weapon with levels
levels.py again            show the level-up (flash, shake, puffs, sounds) once more, without levelling anything
levels.py sound <n>        play Ratchet's sound definition n (0 to 63; some are not in a level's bank)
levels.py fx [<offset> <value>]   print the level-up's block of numbers, or set one of its words
                           (hex offset; the value as hex 0x..., an integer, or a float with a point)
<item> is an item id in hex (0x17) or part of a name ("ryno", "visi"). The amounts are those of a
build with the default --xp-scale.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from live import read, write                                        # noqa: E402
from mods.weaponlevels import AMMO, GOLD, XP_NEEDED, xp_offsets     # noqa: E402

UNLOCKED = 0x96C140            # byte per item id (save block of 0x25 bytes)
ITEM_AMMO = 0x737D30           # rows of 24 bytes per item id: +0xe the u16 an item holds
NAMES = {0x09: "Suck Cannon", 0x0A: "Bomb Glove", 0x0B: "Devastator", 0x0D: "Visibomb Gun", 0x0E: "Taunter", 0x0F: "Blaster",
         0x10: "Pyrocitor", 0x11: "Mine Glove", 0x12: "Walloper", 0x13: "Tesla Claw", 0x14: "Glove of Doom",
         0x15: "Morph-o-Ray", 0x17: "R.Y.N.O.", 0x18: "Drone Device", 0x19: "Decoy Glove"}
AT = xp_offsets()


def item_of(text):
    try:
        item = int(text, 16)
    except ValueError:
        key = "".join(c for c in text.lower() if c.isalnum())
        found = [i for i, name in NAMES.items() if key in "".join(c for c in name.lower() if c.isalnum())]
        if len(found) != 1:
            sys.exit(f"{text}: {'no' if not found else 'more than one'} weapon of that name")
        item = found[0]
    if item not in NAMES:
        sys.exit(f"{item:#x} is not a weapon with levels")
    return item


def set_xp(item, xp):
    write(AMMO + AT[item], struct.pack(">H", xp))
    if not xp:
        write(GOLD + item, b"\0")


def give(item):
    write(UNLOCKED + item, b"\x01")
    full = struct.unpack(">H", read(ITEM_AMMO + 24 * item + 0xE, 2))[0]
    if full:
        write(AMMO + 4 * item, struct.pack(">I", full))


def fx_block():
    """The address of the level-up's numbers (FX in mods/weaponlevels/fx.py): found by the smoke's f1 in the mods' writable data."""
    from mods.game import SEGMENTS
    start, mark = SEGMENTS["rw"][1], struct.pack(">f", 400000.0)
    for base in range(start, start + 0x10000, 0x2000):
        try:
            at = read(base, 0x2000).find(mark)
        except KeyError:
            break
        if at >= 0:
            return base + at - 0x1c
    sys.exit("the level-up's numbers were not found: is this build running?")


def show():
    ammo, gold, owned = read(AMMO, 0x20), read(GOLD, 0x28), read(UNLOCKED, 0x25)
    for item, name in NAMES.items():
        xp = struct.unpack_from(">H", ammo, AT[item])[0]
        level = "level 2 (gold)" if gold[item] else "level 2" if xp == 0xFFFF else f"{xp} / {XP_NEEDED[item]}"
        print(f"{item:#04x} {name:14s} {'owned' if owned[item] else '-':6s} {level}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        show()
    elif args[0] == "near" and len(args) == 2:
        set_xp(item_of(args[1]), XP_NEEDED[item_of(args[1])] - 1)
        show()
    elif args[0] == "set" and len(args) == 3 and 0 <= int(args[2]) < 0xFFFF:
        set_xp(item_of(args[1]), int(args[2]))
        show()
    elif args[0] == "give" and len(args) == 2:
        for item in NAMES if args[1] == "all" else [item_of(args[1])]:
            give(item)
        show()
    elif args[0] == "again":
        write(fx_block() + 0x94, struct.pack(">I", 1))
    elif args[0] == "sound" and len(args) == 2:
        write(fx_block() + 0x90, struct.pack(">I", int(args[1]) + 1))
    elif args[0] == "fx" and len(args) in (1, 3):
        at = fx_block()
        if len(args) == 3:
            value = args[2]
            write(at + int(args[1], 16), struct.pack(">f", float(value)) if "." in value else struct.pack(">I", int(value, 0) & 0xFFFFFFFF))
        block = read(at, 0xA0)
        for off in range(0, 0xA0, 16):
            print(f"{at + off:x} +{off:02x}: {block[off:off + 16].hex(' ', 4)}")
    else:
        sys.exit(__doc__)
