"""What the parts of the weapon levels share: where the game keeps the weapons' state, the
experience needed per weapon and where it is kept, and the template macros (tuned)."""
import importlib

from ..game import *  # noqa: F401,F403

GOLD = 0x969CA8                # byte per item id: the gold version is owned (save block 0x1e, 0x28 bytes)
AMMO = 0x96C0AC                # int per item id (save block 9, 0x94 bytes)
HAND_ITEM = 0x10B8             # hero: the item in the hand slot
LAST_ITEM = 0x24

# Item id -> experience for level 2, in bolts dropped by its kills. Not from RC2, whose amounts
# are for its own enemies: half of what the weapon costs in RC1, 1500 at least.
XP_NEEDED = {
    0x09: 1500,     # Suck Cannon
    0x0A: 1500,     # Bomb Glove
    0x0B: 5000,     # Devastator
    0x0D: 7500,     # Visibomb Gun
    0x0E: 1500,     # Taunter
    0x0F: 1500,     # Blaster
    0x10: 1500,     # Pyrocitor
    0x11: 3750,     # Mine Glove
    0x12: 3750,     # Walloper
    0x13: 20000,    # Tesla Claw
    0x14: 3750,     # Glove of Doom
    0x15: 10000,    # Morph-o-Ray
    0x17: 30000,    # R.Y.N.O.
    0x18: 3750,     # Drone Device
    0x19: 6250,     # Decoy Glove
}
BOOSTED = {0x0D: "Visibomb Gun", 0x0E: "Taunter", 0x12: "Walloper", 0x17: "R.Y.N.O.", 0x18: "Drone Device"}   # the weapons without a gold version
XP_ITEMS = (0, 2, 3, 4, 5, 6, 7, 1)    # the items whose ammunition ints hold the experience, two weapons each
# Weapons added after the first release take the places behind the others' (item 1, the Clank on
# his back, is no more held, sold or picked up than 2 to 7), so a save keeps every weapon's experience.
XP_LATER = (0x0E,)
NO_WEAPON = 0xFF


# @LEVEL2 no@: goes on when the item in r10 is at level 2, to the label otherwise; uses r9 and r11.
LEVEL2 = """
    lis 9, {GOLD_HA}
    addi 9, 9, {GOLD_LO}
    lbzx 11, 9, 10
    cmpwi 11, 0
    bne @YES@
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    addi 9, 9, {P_XP_AT}
    lbzx 11, 9, 10
    cmpwi 11, {NO_WEAPON}
    beq @NO@
    lis 9, {AMMO_HA}
    addi 9, 9, {AMMO_LO}
    lhzx 11, 9, 11
    cmplwi 11, 0xffff
    bne @NO@
@YES@:
"""


# @NOGOLD2 no@: the same for a level 2 weapon that has no gold version; those with one have gold
# icons of the game's own on the tiles of the QuickSelect and the menus.
NOGOLD2 = """
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    addi 9, 9, {P_XP_AT}
    lbzx 11, 9, 10
    cmpwi 11, {NO_WEAPON}
    beq @NO@
    lis 9, {AMMO_HA}
    addi 9, 9, {AMMO_LO}
    lhzx 11, 9, 11
    cmplwi 11, 0xffff
    bne @NO@
"""


_tuned = 0

def tuned(template):
    """@TUNE register offset NAME@: the word at that offset of the state block (r29), or the
    constant NAME (of the package) when it is 0. @LEVEL2 label@: see LEVEL2."""
    global _tuned
    names = vars(importlib.import_module(__package__))
    out = []
    for line in template.splitlines():
        if line.startswith("@TUNE"):
            reg, offset, name = line.strip("@").split()[1:]
            value, _tuned = names[name], _tuned + 1
            count = _tuned
            out += [f"    lwz {reg}, {offset}(29)", f"    cmpwi {reg}, 0", f"    bne hb_tuned{count}",
                    f"    lis {reg}, {(value >> 16) & 0xFFFF}", f"    ori {reg}, {reg}, {value & 0xFFFF}", f"hb_tuned{count}:"]
        elif line.startswith(("@LEVEL2", "@NOGOLD2")):
            _tuned += 1
            test = LEVEL2 if line.startswith("@LEVEL2") else NOGOLD2
            out.append(test.strip("\n").replace("@YES@", f"level2_{_tuned}").replace("@NO@", line.strip("@").split()[1]))
        else:
            out.append(line)
    return "\n".join(out) + "\n"


def xp_offsets():
    """Item id -> offset of the weapon's experience from AMMO."""
    places = [4 * item + half for item in XP_ITEMS for half in (0, 2)]
    if len(places) < len(XP_NEEDED):
        raise SystemExit("weaponlevels: more weapons than places for their experience")
    return dict(zip(sorted(XP_NEEDED, key=lambda item: (item in XP_LATER, item)), places))
