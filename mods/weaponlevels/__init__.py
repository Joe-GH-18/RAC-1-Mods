"""Weapon levels: a weapon that is used enough reaches a second level, once (after RC2's upgrades).

RC1 has no experience. What stands in for it here is the value in bolts of what is killed:
everything that drops bolts goes through 0xfd8d0(moby), which takes the value from moby +0xb4,
lowers it for enemies that have been killed before (down to dropping nothing at all) and calls
SPAWN_BOLTS. KILL_HOOK is at its top: unless the moby is a crate or the last damage it took was
the wrench's, the full value is added to the experience of the weapon in Ratchet's hand,
whatever the enemy still drops. (A first version counted the bolts actually dropped; in game an
area's enemies soon dropped none, and the weapon stopped collecting.) A weapon
that reaches its threshold (XP_NEEDED) is at level 2 for good:
  * The ten weapons the game has a gold version of get that version: the byte GOLD + item id is
    set, which is all the gold weapon vendor does. The item table's second name (+4) tells which
    weapons these are. A weapon that is gold already collects nothing.
  * The R.Y.N.O. launches three rockets for every one (RYNO_HOOK).
  * The other three weapons that deal damage (Visibomb Gun, Walloper, Drone Device) deal BOOST
    times their damage from then on, while they are in his hand: both functions that
    write the damage ring (DEAL_DAMAGE and 0x105ab4, which COLLECT uses with a damage
    descriptor) are hooked where they store the damage.
The weapon is taken to be the one in his hand, so a kill by something left behind (a mine, an
agent of doom, a drone) counts for whatever he holds when it happens. The Decoy Glove, which
kills nothing, also gets every kill made while one of its decoys stands (DECOY_HOOK), and the Drone
Device every kill made while its drones are out (DRONE_HOOK), since he holds the wrench then.
The Taunter gets every kill of an enemy it lured; its second level stuns them when they reach
Ratchet (see TAUNTER).

Where it is kept: the game's save is the table of memory blocks at 0x726690 {address, size,
id}, and a save whose sizes do not add up to the table's is refused (0xe6fe4), so the table is
left alone. The experience is 16 bits per weapon in the saved ammunition array (AMMO, one int
per item id), in the ints of the items that are never in his hand and have no ammunition:
items 0 and 1 (Clank) and the back packs and helmets 2 to 7. 0xffff there is level 2 for the five weapons
without a gold version. A new game clears the array, and with it the levels; the gold versions
are the game's own and are saved by it.

What shows it:
  * A bar under the ammunition count, in the HUD in play (AMMO_BAR_HOOK) and in the QuickSelect
    (0xce170 draws the count and the name of the item in the word at +0x18 of its entry;
    HUD_BAR_HOOK is where it has that item in r3, with the place of the entry in r18/r28 and
    the globals HUD_X/HUD_Y), and in the pause menu's box with the ammunition count
    (MENU_BAR_HOOK). The bar is two
    rectangles drawn with the game's FILL_RECT, as its own slider 0xd1df4 does: a background
    and the experience as a share of what is needed, or all of it in another colour at level 2.
  * A message when a weapon gets there, through the game's help message SHOW_MESSAGE: for a
    gold version the game's own text "You got the Gold ...!", for the other five a text of this
    mod. The message code takes its text from the text table by id, so for those the string of
    one table entry (BORROWED_TEXT, "Gold Weapon purchase", which appears twice in the table)
    is pointed at the mod's text first.
  * With the message comes the level-up itself (see FX below): the screen flashes, the camera
    shakes, bolts burst out of the enemy, the weapon in his hand is white-hot for a moment and
    Ratchet glows, a burst of gold puffs goes off around the weapon and gold smoke rises from
    it, a sound plays, and the weapon is filled up, as RC2 does at an upgrade.
  * The icon of a level 2 weapon is gold: in the HUD in play for all of them, and on the tiles
    of the QuickSelect and of the pause menu's grids for the five without a gold version, where
    the game has gold tiles of its own for the others (TINT_HOOK, MENU_TINT_HOOK).
  * The five weapons without a gold version are gold in his hand and in the menus' models (WEAPON_TINT) and
    are called "Gold ..." wherever the game writes their name (GOLD_NAME_HOOK), as the game's
    gold versions are.

And what it changes besides the weapon's own second version: while a level 2 weapon is in his
hand, bolts fly to Ratchet as they drop.

The files: common.py (where the experience is kept, the template macros), experience.py (kills,
experience, reaching level 2), taunter.py, perks.py (what level 2 does), display.py (bars, gold
icons, names and models, the flash), fx.py (the rest of the level-up). This file has the mod's
interface for build.py; the routines are assembled in the order of parts().
"""
import struct

from ..game import *  # noqa: F401,F403
from .common import *  # noqa: F401,F403
from .experience import *  # noqa: F401,F403
from .taunter import *  # noqa: F401,F403
from .perks import *  # noqa: F401,F403
from .display import *  # noqa: F401,F403
from .fx import *  # noqa: F401,F403

NAME = "weaponlevels"
TITLE = "Weapon levels"
ABOUT = ("Weapons collect experience from the enemies they kill and reach a second level once: the game's gold version "
         "where it has one, three rockets a shot for the R.Y.N.O., twice the damage for the Visibomb Gun, Walloper and "
         "Drone Device, a twice as large blast for the Visibomb, twice as many gold drones for the Drone Device and a longer reach and lunge with red sparks for the "
         "Walloper. The Taunter collects what its lured enemies are worth, and at level 2 they stand stunned when they reach "
         "Ratchet. A level 2 weapon draws bolts in; a bar in the HUD and the pause menu shows the experience, and at "
         "the second level the weapon, its icon and its name are gold.")


def options(ap):
    ap.add_argument("--xp-scale", type=float, default=1.0, help="multiplies the experience every weapon needs for level 2 (default 1)")
    ap.add_argument("--levelup-bolts", type=int, default=500, help="value of the bolts that burst out at a level-up (default 500, 0 for none)")
    ap.add_argument("--boost", type=float, default=BOOST, help=f"damage factor of a level 2 weapon without a gold version (default {BOOST:g})")


def hooks(args):
    return [Hook(KILL_HOOK, "xp_kill", KILL_HOOK_WORD), Hook(DECOY_HOOK, "decoy_seen", DECOY_HOOK_WORD),
            Hook(DRONE_HOOK, "drone_seen", DRONE_HOOK_WORD),
            *(Hook(site, "taunt_lure", LURE_HOOK_WORD) for site in LURE_HOOKS),
            *(Hook(site + 8, "moby_update", MOBY_UPDATE_HOOK_WORD) for site in MOBY_LOOP_HOOKS),
            *(Hook(site, "moby_anim", MOBY_ANIM) for site in MOBY_LOOP_HOOKS),
            *(Hook(site, label, word) for site, word, label in DRONE_CAP_HOOKS),
            Hook(DAMAGE_HOOK, "damage", DAMAGE_HOOK_WORD, jump=True),
            Hook(SWEEP_DAMAGE_HOOK, "sweep_damage", SWEEP_DAMAGE_HOOK_WORD, jump=True),
            Hook(HUD_BAR_HOOK, "hud_bar", HUD_BAR_HOOK_WORD), Hook(AMMO_BAR_HOOK, "ammo_bar", AMMO_BAR_HOOK_WORD),
            Hook(HUD_FLASH_HOOK, "hud_flash", HUD_FLASH_HOOK_WORD),
            Hook(ICON_HOOK, "icon_gold", ICON), Hook(TINT_HOOK, "tint", TINT_HOOK_WORD),
            Hook(QUICK_ICON_HOOK, "quick_icon", ICON), Hook(ICON_SPRITE, "icon_lookup", ICON_SPRITE_WORD, jump=True),
            Hook(MENU_TINT_HOOK, "menu_tint", MENU_TINT_HOOK_WORD),
            Hook(WALLOPER_REACH_HOOK, "wall_reach", WALLOPER_REACH_HOOK_WORD),
            Hook(VISIBOMB_BLAST_HOOK, "visi_blast", VISIBOMB_BLAST_HOOK_WORD),
            Hook(WALLOPER_SPEED_HOOK, "wall_speed", WALLOPER_SPEED_HOOK_WORD),
            Hook(WALLOPER_ACCEL_HOOK, "wall_accel", WALLOPER_ACCEL_HOOK_WORD),
            Hook(WALLOPER_DECEL_HOOK, "wall_decel", WALLOPER_DECEL_HOOK_WORD),
            Hook(WALLOPER_COLOUR_HOOK, "wall_colour", WALLOPER_COLOUR_HOOK_WORD),
            Hook(PREVIEW_GOLD_HOOK, "preview_gold", PREVIEW_GOLD_HOOK_WORD),
            Hook(FIGURE_GOLD_HOOK, "figure_gold", FIGURE_GOLD_HOOK_WORD), Hook(MENU_BAR_HOOK, "menu_bar", MENU_TEXT_DONE),
            Hook(MENU_COUNT_HOOK, "menu_count", MENU_COUNT_HOOK_WORD),
Hook(RYNO_HOOK, "ryno_fan", ROCKET), Hook(BOLTS_HOOK, "magnet", SPAWN_BOLTS, chain=True),
            *(Hook(site, "levelup_frame", HERO_MAIN, chain=True) for site in FRAME_HOOKS),
            Hook(TEXT_LOOKUP, "gold_name", TEXT_LOOKUP_WORD, jump=True)]


def data(args):
    def fx(vaddr):
        def puffs(at, rise, f1, scatter, colours, life, count):
            return struct.pack(PUFFS, *at, *rise, 0.0, f1, scatter, *colours, *life, count)

        block = (puffs(*SMOKE) + puffs(*BURST)
                 + struct.pack(">2i2I4i2Iif2i2I", LEVELUP_FRAMES, *WEAPON_FLASH, *HERO_GLOW, *SOUNDS, 0, 0, *SHAKE,
                               FLASH_FRAMES, FLASH_ALPHA, 0, 0))
        assert len(block) == FX_DAZE
        block += puffs(*DAZE)
        assert len(block) == FX_STUN_FRAMES
        return block + struct.pack(">ifii", STUN_FRAMES, STUN_ARRIVE, STUN_COOLDOWN, LURE_FRAMES)

    return [("rw", "names", lambda vaddr: NAME_PREFIX.ljust(NAME_SIZE, b"\0") * len(NAME_TEXT)), ("rw", "fx", fx)]


def pool(args):
    at = xp_offsets()
    needed = {item: min(max(round(xp * args.xp_scale), 1), 0xFFFE) for item, xp in XP_NEEDED.items()}
    items = range(LAST_ITEM + 1)
    texts = [BOOST_TEXT.format(name).encode() for _, name in sorted(BOOSTED.items())]
    if max(map(len, texts)) >= BOOST_TEXT_SIZE:
        raise SystemExit("weaponlevels: a level-up text is too long")
    text_at = {item: BOOST_TEXT_SIZE * index for index, item in enumerate(sorted(BOOSTED))}
    return dict(
        BOOST=args.boost, ONE=1.0, RYNO_FAN=RYNO_FAN, WALLOPER_REACH=WALLOPER_REACH, WALLOPER_THRUST=WALLOPER_THRUST, VISIBOMB_BLAST=VISIBOMB_BLAST,
        NAMES=b"".join(struct.pack(">HBB", text, at[item], index) for index, (item, text) in enumerate(sorted(NAME_TEXT.items()))),
        GOLD_TEXT=struct.pack(f">{len(items)}H", *(GOLD_TEXT.get(item, 0) for item in items)) + bytes(2),
        BOOST_TEXT_AT=bytes(text_at.get(item, 0) for item in items) + bytes(3),
        BOOST_TEXTS=b"".join(text.ljust(BOOST_TEXT_SIZE, b"\0") for text in texts),
        XP_NEEDED=struct.pack(f">{len(items)}H", *(needed.get(item, 0) for item in items)) + bytes(2),
        XP_AT=bytes(at.get(item, NO_WEAPON) for item in items) + bytes(3),
        BOOSTED_AT=bytes(at[item] if item in DAMAGE_BOOSTED else NO_WEAPON for item in items) + bytes(3),
        XP_TEXTS=(XP_TEXT + b"\0" + XP_TEXT_MAX_TEXT + b"\0").ljust(32, b"\0"))


def parts(args):
    # (the order is that of the code in the game; the pieces of a file are not kept together)
    return [tuned(LEVELS), damage_part("damage", "12", "4", "DAMAGE_BACK"), damage_part("sweep_damage", "6", "8", "SWEEP_DAMAGE_BACK"),
            tuned(BAR), tuned(RYNO_PERK), tuned(ICONS), tuned(WALLOPER_VISIBOMB), tuned(TINT_QUADS), tuned(MAGNET),
            FX, GOLD_NAME, tuned(TAUNT)]


def fields(args, addr):
    if not 0 <= args.levelup_bolts < 0x8000:
        raise SystemExit("weaponlevels: --levelup-bolts has to be between 0 and 32767")
    burst = BOLT_BURST.format(LEVELUP_BOLTS=args.levelup_bolts, BOLT_FLY=BOLT_FLY, SPAWN_BOLTS=SPAWN_BOLTS) if args.levelup_bolts else ""
    return dict(TINT_HI=TINT >> 16, TINT_LO=TINT & 0xFFFF, WALLOPER_RED_HI=WALLOPER_RED >> 16, WALLOPER_RED_LO=WALLOPER_RED & 0xFFFF,
                WALLOPER_GLOW_BLUE_HI=WALLOPER_GLOW_BLUE >> 16, WALLOPER_GLOW_BLUE_LO=WALLOPER_GLOW_BLUE & 0xFFFF,
                MENU_TEXT_COLOUR_HI=MENU_TEXT_COLOUR >> 16, MENU_TEXT_COLOUR_LO=MENU_TEXT_COLOUR & 0xFFFF,
                BAR_FULL_HI=BAR_FULL >> 16, BAR_FULL_LO=BAR_FULL & 0xFFFF, WEAPON_TINT_HI=WEAPON_TINT >> 16, WEAPON_TINT_LO=WEAPON_TINT & 0xFFFF,
                NAME_COUNT=len(NAME_TEXT), NAME_PREFIX_END=len(NAME_PREFIX) - 1, NAME_ROOM=NAME_SIZE - len(NAME_PREFIX) - 1,
                **pair("NAME_BUFFERS", addr["names"]), **pair("FX", addr["fx"]),
                WRENCH_HI=WRENCH_DAMAGE >> 16, ICON_BASE_HI=ICON_BASE >> 16, ICON_BASE_LO=ICON_BASE & 0xFFFF, BOLT_BURST=burst)
