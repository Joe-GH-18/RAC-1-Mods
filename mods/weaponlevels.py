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
"""
import struct

from .game import *  # noqa: F401,F403

NAME = "weaponlevels"
TITLE = "Weapon levels"
ABOUT = ("Weapons collect experience from the enemies they kill and reach a second level once: the game's gold version "
         "where it has one, three rockets a shot for the R.Y.N.O., twice the damage for the Visibomb Gun, Walloper and "
         "Drone Device, a twice as large blast for the Visibomb, twice as many gold drones for the Drone Device and a longer reach and lunge with red sparks for the "
         "Walloper. The Taunter collects what its lured enemies are worth, and at level 2 they stand stunned when they reach "
         "Ratchet. A level 2 weapon draws bolts in; a bar in the HUD and the pause menu shows the experience, and at "
         "the second level the weapon, its icon and its name are gold.")

GOLD = 0x969CA8                # byte per item id: the gold version is owned (save block 0x1e, 0x28 bytes)
AMMO = 0x96C0AC                # int per item id (save block 9, 0x94 bytes)
HAND_ITEM = 0x10B8             # hero: the item in the hand slot
LAST_ITEM = 0x24
DAMAGE_RING = 0xA14C00         # 64 entries of 0x40 bytes: +0x24 flags, +0x2c damage, +0x34 target; moby +0xa4 = its entry
WRENCH_DAMAGE = 0x10000        # damage flag
KILL_HOOK = 0xFD8E0            # lhz r7, 0xb4(r3) in 0xfd8d0, behind its saving of the return address
KILL_HOOK_WORD = 0xA0E300B4
# The Decoy Glove kills nothing itself, so it is given what dies while one of its decoys stands:
# 0x2e7140 makes a decoy (class 0xcb, the gold one 0x76c) and 0x2e8af8 is its update, which notes
# the frame here. That function runs for other mobys too (in game it ran every frame for a player
# who does not own the glove), so the class is looked at.
DECOY_GLOVE = 0x19
DECOY_CLASS, GOLD_DECOY_CLASS = 0xCB, 0x76C
DECOY_HOOK = 0x2E8B18          # ori r31, r3, 0
DECOY_HOOK_WORD = 0x607F0000
DECOY_FRAMES = 3               # a decoy seen this many frames ago at most is standing
# The Drone Device's drones (class 0x1df, made by its fire function 0x39ac10, update 0x39b390)
# kill while Ratchet holds the wrench again (seen in game: item 8 in his hand), so the device is
# given what dies while drones are out, in the same way (DRONE_HOOK notes the frame in state
# +0x190); r4 is in use where the hook is.
DRONE_DEVICE, DRONE_CLASS = 0x18, 0x1DF
# The Drone Device at level 2 (the user's wish, 2026-10-14): gold drones, and twice as many. Its
# fire function launches drones until hero +0x1ff6 (the count, raised by the spawner 0x39a708 and
# lowered by a drone that goes) reaches 6, compared at the three DRONE_CAP_HOOKS; a level 2 device
# compares with DRONE_CAP_L2. Nothing keeps one slot per drone (the nine words at hero +0x1ffc
# are their targets), so more drones fit. The gold is the hand weapons' WEAPON_TINT (state
# +0x158), given to each drone at the top of its update (drone_seen).
DRONE_CAP_HOOKS = ((0x39AC74, 0x2C030006, "drone_cap3"), (0x39AE54, 0x2C1F0006, "drone_cap31"),
                   (0x39AE88, 0x2C1F0006, "drone_cap31"))
DRONE_CAP, DRONE_CAP_L2 = 6, 12
# Bosses (the user's pick, 2026-10-14) are worth half of what the weapon still needs for level 2,
# whatever their bolt value: the Blargian Snagglebeast on Umbris (level 7: bolt value 0) and the
# mutant on Blarg Station (level 6: 193). Both die through the bolt drop (the Snagglebeast at
# 0x1c7d40); their classes were picked out of the levels' gameplay files as the one large class of
# a single instance there (moby records of 0x78 bytes: +0x10 bolts, +0x18 class). Qwark and Drek
# were left out at the user's wish (neither dies through the bolt drop).
BOSS_SNAGGLEBEAST, BOSS_MUTANT = 0x452, 0x41B
DRONE_HOOK = 0x39B3C4          # ori r31, r3, 0
DRONE_HOOK_WORD = 0x607F0000
# The Taunter (the user's wish, 2026-10-18) kills nothing itself either; it gets what dies of the
# enemies it lured. Its moby (class 0xaf, update 0x2b1300) calls the lure 0x2b06f0(f1 radius,
# r4 its moby) as it whistles: for every moby of the list 0xa49344 with an AI record (moby +0x78
# -> +0, as 0xfcccc reads it) in reach and in front of it, the record's +0x18 becomes the
# Taunter's moby (stored at the two LURE_HOOKS, r27 the enemy). (Before that it breaks the crates
# within 12 units.) Who reads +0x18 differs by enemy, so the mod keeps its own table of the lured
# (state +LURES): a lured enemy that dies within LURE_FRAMES counts for the Taunter.
# Level 2, the user's pick: a lured enemy that comes within STUN_ARRIVE of Ratchet stands stunned
# for STUN_FRAMES. The moby loop 0xfc238 runs each moby's animation (MOBY_ANIM, unless moby +0x34
# has 0x40) and its update (the descriptor at +0x74); a stunned enemy gets neither, so it stands
# in its pose, with gold puffs above it (DAZE). An enemy only takes its damage in its own update,
# so a hit ends the stun: DEAL_DAMAGE writes the ring entry's index into moby +0xa4. It can be
# stunned again by a lure STUN_COOLDOWN after a stun ends.
TAUNTER = 0x0E
LURE_HOOKS = (0x2B0D64, 0x2B0D70)      # stw r31, 0x18(r26)
LURE_HOOK_WORD = 0x93FA0018
MOBY_UPDATE_HOOK = 0xFC2E0     # lwz r3, 0x74(r31) in the moby loop (r31 = the moby)
MOBY_UPDATE_HOOK_WORD = 0x807F0074
MOBY_ANIM_HOOK = 0xFC2D8       # bl MOBY_ANIM (r3 = the moby)
MOBY_ANIM = 0xF98D8
# The table: LURE_COUNT entries of LURE_SIZE bytes, {+0 moby (0 = free), +4 its class (u16), +6
# its moby +0xa4 when the stun began (byte), +8 the frame it was last lured in, +0xc the frame its
# stun ends in (0 = not stunned since it was lured)}.
LURES, LURE_COUNT, LURE_SIZE = 0x1A0, 16, 16
LURE_FRAMES = 900              # 15 s
STUN_FRAMES = 180
STUN_ARRIVE = 14.0             # lured enemies stop short of him (a robot at 11, seen in game); 5 never stunned
STUN_COOLDOWN = 120
DAZE = ((0.0, 0.0, 1.5), (0.0, 0.0, 0.03), 400000.0, 0.08, (0x0820C8FF, 0x0520B8FF), (20, 25), 1)
FX_DAZE, FX_STUN_FRAMES, FX_ARRIVE, FX_STUN_COOLDOWN, FX_LURE_FRAMES = 0xB0, 0xE8, 0xEC, 0xF0, 0xF4
# Both writers of the damage ring are leaf functions that never save their return address, so
# these two hooks are jumps: each routine stores the damage itself and jumps back.
DAMAGE_HOOK = 0x105C78         # stfs f1, 0x2c(r4) in DEAL_DAMAGE (r3 target, r12 flags)
DAMAGE_HOOK_WORD = 0xD024002C
DAMAGE_BACK = DAMAGE_HOOK + 4
SWEEP_DAMAGE_HOOK = 0x105BD4   # stfs f1, 0x2c(r8) in 0x105ab4 (r3 target, r6 flags)
SWEEP_DAMAGE_HOOK_WORD = 0xD028002C
SWEEP_DAMAGE_BACK = SWEEP_DAMAGE_HOOK + 4

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
BOOST = 2.0
XP_ITEMS = (0, 2, 3, 4, 5, 6, 7, 1)    # the items whose ammunition ints hold the experience, two weapons each
# Weapons added after the first release take the places behind the others' (item 1, the Clank on
# his back, is no more held, sold or picked up than 2 to 7), so a save keeps every weapon's experience.
XP_LATER = (0x0E,)
NO_WEAPON = 0xFF
# Of those, the weapons whose second level is BOOST times the damage. The R.Y.N.O. has a second
# level of its own instead: its update 0x3892e8 launches each rocket with ROCKET(weapon moby,
# position, target, f1, f2 = yaw, f3 = pitch), which makes a moby of class 0x1c9 with that
# rotation; at level 2 every launch sends two more rockets at the same target, RYNO_FAN to either
# side.
DAMAGE_BOOSTED = (0x0D, 0x12, 0x18)
RYNO = 0x17
ROCKET = 0x38C8A0
RYNO_HOOK = 0x389E30           # bl ROCKET
RYNO_FAN = 0.4                 # rad

# The message. Text table: 16-byte entries {string, id, ..}, the pointer to it at TEXT_TABLE, their
# number at TEXT_COUNT. SHOW_MESSAGE(text id, message index) puts a help message up in place of the
# one showing; the index is that of its 8-byte record in the saved block 0xa1000c (+0 how often it
# was shown; 0xffff there keeps it from showing), 0x94 of them.
SHOW_MESSAGE = 0x7B4F0
MESSAGE_INDEX = 0x93           # the last record; taken to be unused
TEXT_TABLE = 0xA1A800
TEXT_COUNT = 0x7208B0
GOLD_TEXT = {0x0A: 0x53CB, 0x10: 0x53CC, 0x0F: 0x53CD, 0x14: 0x53CE, 0x11: 0x53CF,     # "You got the Gold Bomb Glove!" ...
             0x0B: 0x53D0, 0x19: 0x53D1, 0x13: 0x53D2, 0x09: 0x53D3, 0x15: 0x53D4}
BORROWED_TEXT = 0x5302
BOOST_TEXT = "Your \x0c{}\x08 reached level 2!"       # \x0c..\x08 highlights
BOOST_TEXT_SIZE = 48

# The bar. FILL_RECT(x0, y0, x1, y1, colour, 0); colours as the game's slider has them (0x803030f0
# for its filling, 0x80ffffff for its frame).
HUD_BAR_HOOK = 0xCECCC         # extsw r5, r3 in the QuickSelect's draw function 0xce170
HUD_BAR_HOOK_WORD = 0x7C6507B4
HUD_X, HUD_Y = 0x723938, 0x72393C
FILL_RECT = 0xCA72C
BAR_BELOW = 30                 # from the place of the HUD entry (the ammunition count is at +12)
BAR_WIDTH, BAR_HEIGHT = 60, 2
# The filling has the colour of the HUD's ammunition count (0x7244f8), on a faint dark strip.
BAR_FILL, BAR_FULL, BAR_BACK = 0x80E08060, 0x8020D0FF, 0x38000000
FADE = 0x5027BC                # (r3 colour, r4 colour, f1) -> the colour that far from the first to the second
# The HUD in play: 0xd56d8 updates and draws its 13 widgets (0x90 bytes each from 0x723b10; +0x14
# the draw function's descriptor). The ammunition count is the widget made with icon ICON_BASE +
# item; its draw function 0xd4838 writes "%d/%d" at AMMO_X + r30 + r27, AMMO_Y + r21 and is not
# run while the widget is hidden.
AMMO_BAR_HOOK = 0xD4DAC        # lwz r3, 0x58(r31) behind the count
AMMO_BAR_HOOK_WORD = 0x807F0058
AMMO_X, AMMO_Y = 0x724504, 0x724508
# The count is written with its right end at r27 (70, or 95 when the weapon holds 100 rounds or
# more: 0x7244ec, 0x7244f0) from the widget's x, which is about the right edge of the icon; the
# dark pill behind both ends 11 further on. The bar runs inside the pill from the icon to the
# end of the count, under it (placed with the user from screenshots).
AMMO_BAR_BELOW = 18
AMMO_BAR_LEFT, AMMO_BAR_SHORTER = 10, 7
ICON_BASE = 0xEA60
# The level-up itself, besides the message: a flash of the whole screen that fades out (drawn
# behind the HUD's widget loop, which runs every frame), the camera's own shake channel 0
# (CAMERA_STATE +0x160: strength, value, frames left, frames in all), and bolts that burst from
# the enemy and fly to Ratchet.
HUD_FLASH_HOOK = 0xD5A68       # ori r3, r30, 0
HUD_FLASH_HOOK_WORD = 0x63C30000
FLASH_FRAMES, FLASH_ALPHA, FLASH_COLOUR = 30, 0x50, 0x20D0FF     # an alpha of 0x80 hides the picture altogether
# The HUD's x = 0 is not the left edge of a wide screen: drawn from 0, the flash left a strip on
# the left uncovered.
FLASH_LEFT, FLASH_TOP, FLASH_RIGHT, FLASH_BOTTOM = -200, -40, 900, 640
# What tells a level 2 weapon from the others in the HUD: its icon is drawn in gold. The HUD's
# icons are textured quads from DRAW_QUAD (0xcbe60), which gives every one the colour 0x808080
# with its alpha at TINT_HOOK; ICON(widget, sprite, x, y, flags, alpha) draws an item's icon
# through it, and ICON_HOOK is the call for the ammunition widget's.
ICON = 0xCDEB8
ICON_HOOK = 0xD4C9C            # bl ICON in the ammunition widget's draw function
TINT_HOOK = 0xCBEF0            # or r4, r5, r8
# The QuickSelect draws its icons in a loop over its entries, 0x1c bytes each with the item at
# +0x18: the entry is at the pointer QUICK_LISTS[QUICK_LIST] plus r23 where it calls ICON.
QUICK_ICON_HOOK = 0xCEA9C      # bl ICON
QUICK_LISTS, QUICK_LIST = 0xA1C190, 0xA1C084
# The pause menu draws its tiles in several places (the grids' 0x144ec0, 0x13fd08, the ring of
# the QuickSelect page 0x149f88, ...), each with ICON_SPRITE(icon id, version) -> sprite and then
# either ICON_DRAW, which sets the colour itself, or 0xcc0f0, which goes through DRAW_QUAD. So
# the lookup notes whether the icon is one to tint, and the next quad of either kind is.
ICON_SPRITE_WORD = 0x3CA000A2  # lis r5, 0xa2, its first instruction
ICON_SPRITE_BACK = ICON_SPRITE + 4
MENU_TINT_HOOK = 0xCA1B8       # or r6, r6, r7
MENU_TINT_HOOK_WORD = 0x7CC63B78
TINT_HOOK_WORD = 0x7CA44378
TINT = 0x44C6FF                # tuned with the user until a blue tile came out as the game's gold tiles (0x44d8ff was too green, 2026-10-14)
# What a level 2 weapon does that the others do not, whichever kind it is, while it is in his hand:
#   * the bolts of whatever drops some fly to Ratchet at once (the flag BOLT_FLY, at BOLTS_HOOK)
# (Its ammunition coming back by itself was tried and taken out at the user's wish on 2026-10-09: a
# second level is to make the weapon do more, not to refill it. For the record: what an item holds
# is the u16 at 0x737d30 + 24 * item + 0xe.)
# The weapon in his hand is the moby at hero +0x1090. Its colour (moby +0x38, 00BBGGRR; what the
# level gives its mobys is about 0x29 a channel) is set to the hero moby's again in every frame
# (seen in a running game with the R.Y.N.O. and the Devastator; the code that does it was not
# found), so a level 2 weapon without a gold version gets its gold from the HUD's update, which
# is the last thing in the frame's update 0x166fb0, behind the hero and the mobys. Not every
# weapon gets it back: the gold Blaster, left at another colour by the level-up's flash, kept
# it, so the flash puts back what it found.
HAND_MOBY = 0x1090
WEAPON_TINT = 0x0C64B0           # picked from screenshots of the R.Y.N.O. in a running game
# The Walloper at level 2 (the user's wish, 2026-10-14): a larger reach and red sparks.
#   * Its punch is hero state 0x20 (handler 0xb0d60): three spheres of COLLECT, straight ahead and
#     50 degrees to either side, each with the radius r26 +0x248 (0.8, the hero's float table
#     0xaaafc) at that distance from him. WALLOPER_REACH_HOOK is where it is loaded into f29 for
#     all three; a level 2 Walloper multiplies it by WALLOPER_REACH (so the spheres are larger
#     and further out).
#   * The sparks are the trails drawn by 0x2bab98 (the glove's draw callback) in a colour picked
#     at random from two words, 0x7f7f4040 and 0x307f4040 (alpha, then 00BBGGRR: blue).
#     WALLOPER_COLOUR_HOOK is behind that pick, with the colour in r31: its alpha stays and the
#     colour becomes WALLOPER_RED (state +0x17c for tuning). The lightning around the glove is
#     drawn by 0x2baf48 with a white core (0x7b7c10) in a glow of the colour WALLOPER_GLOW, a
#     word of writable data that the same hook sets to that red or back to the game's blue.
# The Visibomb at level 2 (the user's choice, 2026-10-14, besides its doubled damage): a larger
# blast. The missile (class 0xac, update 0x2af360) explodes at VISIBOMB_BLAST_HOOK, which loads
# the radius 4.0 (its constants 0x2af2e8 +0x5c) into f30 for both the explosion's look (0x10e030,
# its size) and the COLLECT that finds what it hits; a level 2 Visibomb multiplies it by
# VISIBOMB_BLAST (state +0x18c as a float for tuning). r3 and r11 are still in use there.
VISIBOMB = 0x0D
VISIBOMB_BLAST_HOOK = 0x2B0450 # lfs f30, 0x5c(r3)
VISIBOMB_BLAST_HOOK_WORD = 0xC3C3005C
VISIBOMB_BLAST = 2.0
WALLOPER = 0x12
WALLOPER_REACH_HOOK = 0xB1110  # lfs f29, 0x248(r26)
WALLOPER_REACH_HOOK_WORD = 0xC3BA0248
WALLOPER_REACH = 1.75
#   * The punch also thrusts him forward: from the 10th to the 18th frame of the state (scaled
#     to the frame rate) his target ground speed (hero +0x190) is r26 +0x290 (18 units/s), which
#     his speed (+0x194) approaches by r26 +0x29c (190 units/s a second) and leaves again by
#     +0x210 (90). A level 2 Walloper multiplies all three by WALLOPER_THRUST, which multiplies
#     the whole run of his speed and so the distance (the hooks are where the state loads them).
WALLOPER_SPEED_HOOK, WALLOPER_SPEED_HOOK_WORD = 0xB0E60, 0xC03A0290    # lfs f1, 0x290(r26)
WALLOPER_ACCEL_HOOK, WALLOPER_ACCEL_HOOK_WORD = 0xB0FCC, 0xC03A029C    # lfs f1, 0x29c(r26)
WALLOPER_DECEL_HOOK, WALLOPER_DECEL_HOOK_WORD = 0xB0FD4, 0xC05A0210    # lfs f2, 0x210(r26)
WALLOPER_THRUST = 2.0
WALLOPER_COLOUR_HOOK = 0x2BACDC   # srawi r3, r31, 24
WALLOPER_COLOUR_HOOK_WORD = 0x7fe3c670
WALLOPER_RED = 0x20207F
WALLOPER_GLOW, WALLOPER_GLOW_BLUE = 0x7B7C14, 0x7F2020
# The pause menu's Weapons page shows the weapon under the cursor in a box of its own (0x145d28)
# and Ratchet holding the one in his hand slot (0x14f828). Both make a moby for it when the item
# changes, give it the colour 0x202020 and, for an owned gold version, the game's gold look
# (0x8d7e8); the colour stays as set while the moby lives (seen in a running game). So the four
# without a gold version get WEAPON_TINT right there, as in his hand (r29 the item, r24 or r28
# the moby).
PREVIEW_GOLD_HOOK = 0x1460AC   # lis r3, 0x95 behind the gold look in 0x145d28
FIGURE_GOLD_HOOK = 0x14FA5C    # lis r3, 0x70 behind the gold look in 0x14f828
PREVIEW_GOLD_HOOK_WORD = 0x3C600095
FIGURE_GOLD_HOOK_WORD = 0x3C600070
# The experience in the menu: the Weapons page's box with the ammunition count (widget 0x72a620,
# draw function 0x147334: +0x20/+0x24 its width and height, r25 = 24 * the item under the cursor,
# nothing drawn for one not owned) writes the count centred in the box with 0x6a510 and then
# calls the empty 0x6d708; there the bar goes under the count, centred.
MENU_BAR_HOOK = 0x1475F0       # bl 0x6d708
MENU_TEXT_DONE = 0x6D708
MENU_BAR_WIDTH = 120
# The ammunition box is made MENU_BOX_GROW taller (in the units of the frame's pose: about 47.6
# a unit of the menu) and the count kept in its top MENU_COUNT_H; under it the bar (MENU_BAR_Y
# from the top) and the experience in words ("XP 340/1500", or "Level 2" in the full bar's
# colour), drawn as the count is: DRAW_TEXT(r3 the box as halfwords {top, bottom, left, right,
# centre x, centre y, 0, 0, 0x10, 3}, r4 colour, r5 the string, r6 -1), in the widget's
# coordinates. (Drawn in another box's place it does not show.) A box's size is that of its frame:
# the frame's update writes it into the widget (+0x20/+0x24) in every frame from the last pose of
# the frame's animation, joints 1 to 3 against joint 0 (see FOOT_BOX in mods/chargeboots.py; the
# pose's fourth corner, joint 4 at +0x58, is the bottom left one and has to move with them);
# the ammunition box's is animation MENU_BOX_ANIM. The numbers were placed in a running game
# (state +0x170 to +0x188).
SPRINTF = 0x5CD2A8
DRAW_TEXT = 0x6A510
MENU_TEXT_COLOUR = 0x80FEA888  # the count's
XP_TEXT, XP_TEXT_MAX_TEXT = b"XP %d/%d", b"Level 2"
XP_TEXT_MAX = len(XP_TEXT) + 1
MENU_COUNT_HOOK = 0x147598     # lwz r3, 0x24(r31)
MENU_COUNT_HOOK_WORD = 0x807F0024
MENU_FRAME_CLASS = 0x472
MODEL_SLOTS = 0xE0
MENU_BOX_ANIM = 0x20
MENU_BOX_ANIM_OFF = 0x48 + 4 * MENU_BOX_ANIM
MENU_BOX_X, MENU_BOX_Y, MENU_BOX_HALF_W, MENU_BOX_HALF_H = 6233, -7790, 5261, 762   # the game's pose
MENU_BOX_GROW = 952            # 20 units
MENU_COUNT_H = 32              # the box's own height
MENU_BAR_Y = 28
MENU_XP_Y, MENU_XP_X, MENU_XP_HEIGHT = 33, 0, 16
MENU_XP_HEIGHT_HALF = MENU_XP_HEIGHT // 2
# The level-up. Its numbers are one block of writable data (FX, see data()), so they can be
# changed in a running game with tools/peek.py; the constants cannot, it does not get through
# to them. The block: two sets of puffs of 0x38 bytes each, the smoke and the burst (+0 where
# from the weapon's origin, +0xc velocity, +0x1c f1, +0x20 scatter, +0x24 the two colours, +0x2c
# the two frame counts, +0x34 how many: a frame for the smoke, in all for the burst), then
#   +0x70 frames the level-up runs (smoke for all of them; counted down in the state block)
#   +0x74 frames the weapon takes from +0x78, the colour it starts with, to its own
#   +0x7c the colour Ratchet's moby is given for the first +0x80 frames (it eases back by itself)
#   +0x84/+0x88 the two sounds, as Ratchet's sound definition + 1 (0 = none; which of his 64
#   a level's sound bank holds differs), +0x8c the frame the second one plays in
#   +0x90 write a sound definition + 1 here to hear it, +0x94 write 1 to see the level-up again
#   +0x98 frames and +0x9c strength of the camera shake
#   +0xa0 frames and +0xa4 alpha at the start of the flash of the whole screen
#   +0xa8/+0xac kept while it runs: the weapon whose colour is not the mod's, and that colour
#   +0xb0 a third set, DAZE, above every enemy the Taunter has stunned (a frame each), then
#   +0xe8 STUN_FRAMES, +0xec STUN_ARRIVE (float), +0xf0 STUN_COOLDOWN, +0xf4 LURE_FRAMES
# The puffs are the game's own, the ones a breaking crate gives off:
# PUFF(position, velocity, colour AABBGGRR, second colour, -, frames, second frame count, -, 0, 0;
# f1, f2 = how far the velocity is scattered) makes one particle (type 0xb), or none in a frame
# that took long. What the numbers do, from screenshots of a running game: the puff is a soft
# ball of glow that is added to the picture and grows; the second colour is the one that shows
# most, and with an alpha of 0x18 and more a puff a frame is a solid yellow ball, with a darker
# tail above; f1 is the square of the distance it is drawn up to (at 40 nothing showed); the
# velocity is in units a frame.
PUFF = 0x123390
PUFFS = ">3f4f2f2I2iI"         # the layout of a set
SMOKE = ((0.0, 0.0, 0.5), (0.0, 0.0, 0.12), 400000.0, 0.05, (0x0820C8FF, 0x0520B8FF), (34, 35), 1)
BURST = ((0.0, 0.0, 0.3), (0.0, 0.0, 0.0), 400000.0, 0.18, (0x3060E0FF, 0x2840D0FF), (30, 35), 24)
LEVELUP_FRAMES = 100
WEAPON_FLASH = (40, 0xFFFFFF)          # frames, colour 00BBGGRR
HERO_GLOW = (0x40B0FF, 20)             # colour, frames
# The sound is Ratchet's sound definition 24, the user's choice by ear (tools/levels.py sound 24)
# after RC2's own were tried (see NOTES.md). All 19 levels' banks hold it.
SOUNDS = (24 + 1, 0, 12)
PLAY_MODEL_SOUND = 0x15D12C            # (r3 definition, r4 flags, r5 moby)
SHAKE = (40, 0.3)
ITEM_AMMO = 0x737D30                   # 24 bytes per item: +0xe what it holds
# The names. TEXT_LOOKUP(text id) -> string is what the QuickSelect, the menus and the vendor get
# an item's name with (191 callers); the game's gold versions have a text of their own (item
# table +4), these four have not, so their name is put together: "Gold " and the game's name in
# the language it runs in, in a buffer for each.
TEXT_LOOKUP = 0x7B740
TEXT_LOOKUP_WORD = 0x3CA00097  # lis r5, 0x97, its first instruction
TEXT_LOOKUP_BACK = TEXT_LOOKUP + 4
NAME_TEXT = {0x0D: 0x4E50, 0x0E: 0x4E51, 0x12: 0x4E45, 0x17: 0x4E4E, 0x18: 0x4E42}   # item table +0
NAME_PREFIX = b"Gold "
NAME_SIZE = 48
BOLT_FLY = 2                   # spawn_bolts flag: the bolts fly to Ratchet at once

# xp_kill: replaces lhz r7, 0xb4(r3) at the top of the bolt drop 0xfd8d0 (r3 = the moby, r4, r5 and
#   the vector register v2 are still to be used by it); r30 = item, r11 -> its experience, r12 = the
#   experience.
LEVELS = """
xp_kill:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0xc0(1)
    std 3, 0x70(1)
    std 4, 0x78(1)
    std 5, 0x80(1)
    std 31, 0x98(1)
    std 30, 0xa0(1)
    li 9, 0xb0
    stvx 2, 1, 9
    mr 31, 3
    bl {IS_CRATE}
    cmpwi 3, 0
    bne xp_out
    lis 9, {HERO_HA}
    addi 9, 9, {HERO_LO}
    lbz 8, 0x20a4(9)                # Ratchet only
    cmpwi 8, 0
    bne xp_out
    lwz 30, {HAND_ITEM}(9)
    lbz 8, 0xa4(31)                 # the last damage it took: nothing for the weapon in his hand
    cmpwi 8, 0xff                   # when that was the wrench's
    beq xp_held
    lis 9, {DAMAGE_RING_HA}
    addi 9, 9, {DAMAGE_RING_LO}
    slwi 8, 8, 6
    add 9, 9, 8
    lwz 8, 0x34(9)
    cmpw 8, 31
    bne xp_held
    lwz 8, 0x24(9)
    andis. 8, 8, {WRENCH_HI}
    bne xp_decoy
xp_held:
    bl xp_award
xp_decoy:                           # a decoy is standing: the Decoy Glove gets the same, whatever killed it
    cmpwi 30, {DECOY_GLOVE}
    beq xp_taunt
    lis 9, {STATE_HA}
    addi 9, 9, {STATE_LO}
    lwz 8, 0x134(9)
    cmpwi 8, 0
    beq xp_taunt
    lis 10, {FRAME_COUNTER_HA}
    lwz 10, {FRAME_COUNTER_LO}(10)
    subf 10, 8, 10
    cmplwi 10, {DECOY_FRAMES}
    bgt xp_taunt
    li 30, {DECOY_GLOVE}
    bl xp_award
xp_taunt:                           # it was lured: the Taunter gets the same, unless it is in his hand
    mr 3, 31
    bl lure_find
    cmpwi 12, 0
    beq xp_drone
    lwz 8, 8(12)
    li 9, 0                         # the entry is free again
    stw 9, 0(12)
    stw 9, 8(12)
    stw 9, 0xc(12)
    lis 10, {FRAME_COUNTER_HA}
    lwz 10, {FRAME_COUNTER_LO}(10)
    subf 10, 8, 10
    lis 9, {FX_HA}
    addi 9, 9, {FX_LO}
    lwz 9, {FX_LURE_FRAMES}(9)
    cmplw 10, 9
    bgt xp_drone
    lis 9, {HERO_HA}
    addi 9, 9, {HERO_LO}
    lwz 8, {HAND_ITEM}(9)
    cmpwi 8, {TAUNTER}
    beq xp_drone
    li 30, {TAUNTER}
    bl xp_award
xp_drone:                           # drones are out: the Drone Device gets it, unless it is in his hand
    lis 9, {HERO_HA}
    addi 9, 9, {HERO_LO}
    lwz 8, {HAND_ITEM}(9)
    cmpwi 8, {DRONE_DEVICE}
    beq xp_out
    lis 9, {STATE_HA}
    addi 9, 9, {STATE_LO}
    lwz 8, 0x190(9)
    cmpwi 8, 0
    beq xp_out
    lis 10, {FRAME_COUNTER_HA}
    lwz 10, {FRAME_COUNTER_LO}(10)
    subf 10, 8, 10
    cmplwi 10, {DECOY_FRAMES}
    bgt xp_out
    li 30, {DRONE_DEVICE}
    bl xp_award
xp_out:
    li 9, 0xb0
    lvx 2, 1, 9
    ld 30, 0xa0(1)
    ld 31, 0x98(1)
    ld 5, 0x80(1)
    ld 4, 0x78(1)
    ld 3, 0x70(1)
    addi 1, 1, 0xc0
    ld 0, 0x10(1)
    mtlr 0
    lhz 7, 0xb4(3)                  # the displaced instruction
    blr

decoy_seen:                         # replaces ori r31, r3, 0 at the top of the update (r3 = the moby)
    lhz 11, 0xa6(3)
    cmpwi 11, {DECOY_CLASS}
    beq decoy_stamp
    cmpwi 11, {GOLD_DECOY_CLASS}
    bne decoy_out
decoy_stamp:
    lis 11, {FRAME_COUNTER_HA}
    lwz 11, {FRAME_COUNTER_LO}(11)
    lis 12, {STATE_HA}
    addi 12, 12, {STATE_LO}
    stw 11, 0x134(12)
decoy_out:
    ori 31, 3, 0                    # the displaced instruction
    blr

drone_seen:                         # replaces ori r31, r3, 0 in the drones' update (r3 = the moby; r4 in use)
    lhz 11, 0xa6(3)
    cmpwi 11, {DRONE_CLASS}
    bne drone_out
    lis 11, {FRAME_COUNTER_HA}
    lwz 11, {FRAME_COUNTER_LO}(11)
    lis 12, {STATE_HA}
    addi 12, 12, {STATE_LO}
    stw 11, 0x190(12)
    li 10, {DRONE_DEVICE}
@LEVEL2 drone_out@
    lis 12, {STATE_HA}
    addi 12, 12, {STATE_LO}
    lwz 12, 0x158(12)
    cmpwi 12, 0
    bne drone_gold
    lis 12, {WEAPON_TINT_HI}
    ori 12, 12, {WEAPON_TINT_LO}
drone_gold:
    stw 12, 0x38(3)
drone_out:
    ori 31, 3, 0                    # the displaced instruction
    blr

drone_cap3:                         # replace cmpwi r3/r31, 6 in the fire function (r0, r9 to r12 free)
    mflr 0
    bl drone_limit
    mtlr 0
    cmpw 3, 12
    blr
drone_cap31:
    mflr 0
    bl drone_limit
    mtlr 0
    cmpw 31, 12
    blr
drone_limit:                        # r12 = how many drones the device keeps out
    li 12, {DRONE_CAP}
    li 10, {DRONE_DEVICE}
@LEVEL2 dl_out@
    li 12, {DRONE_CAP_L2}
dl_out:
    blr

xp_award:                           # (r30 item, r31 the moby killed)
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    cmplwi 30, {LAST_ITEM}
    bgt xa_out
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    addi 10, 9, {P_XP_AT}
    lbzx 10, 10, 30
    cmpwi 10, {NO_WEAPON}
    beq xa_out
    lis 11, {AMMO_HA}
    addi 11, 11, {AMMO_LO}
    add 11, 11, 10
    lhz 12, 0(11)
    cmplwi 12, 0xffff               # at level 2 already
    beq xa_out
    lis 10, {GOLD_HA}
    addi 10, 10, {GOLD_LO}
    lbzx 8, 10, 30
    cmpwi 8, 0                      # gold already
    bne xa_out
    lhz 8, 0xa6(31)                 # a boss: half of what the weapon still needs
    cmpwi 8, {BOSS_SNAGGLEBEAST}
    beq xa_boss
    cmpwi 8, {BOSS_MUTANT}
    beq xa_boss
    lha 8, 0xb4(31)                 # what it is worth in bolts
    b xa_worth
xa_boss:
    addi 8, 9, {P_XP_NEEDED}
    slwi 7, 30, 1
    lhzx 8, 8, 7
    subf 8, 12, 8
    srawi 8, 8, 1
    cmpwi 8, 1
    bge xa_worth
    li 8, 1
xa_worth:
    cmpwi 8, 0
    ble xa_out
    add 12, 12, 8
    addi 8, 9, {P_XP_NEEDED}
    slwi 7, 30, 1
    lhzx 8, 8, 7
    cmplw 12, 8
    bge xp_level
    sth 12, 0(11)
    b xa_out
xp_level:
    mulli 8, 30, 0x4c               # the item has a second name: there is a gold version of it
    lis 7, {ITEM_TABLE_HA}
    addi 7, 7, {ITEM_TABLE_LO}
    add 7, 7, 8
    lwz 7, 4(7)
    cmpwi 7, 0
    beq xp_boost
    li 7, 1
    stbx 7, 10, 30
    li 12, 0
    sth 12, 0(11)
    addi 8, 9, {P_GOLD_TEXT}        # the game's own message for the gold version
    slwi 7, 30, 1
    lhzx 3, 8, 7
    b xp_tell
xp_boost:
    li 12, -1
    sth 12, 0(11)
    addi 8, 9, {P_BOOST_TEXT_AT}    # the borrowed text entry gets this weapon's text
    lbzx 8, 8, 30
    add 8, 8, 9
    addi 8, 8, {P_BOOST_TEXTS}
    lis 10, {TEXT_TABLE_HA}
    lwz 10, {TEXT_TABLE_LO}(10)
    lis 11, {TEXT_COUNT_HA}
    lwz 11, {TEXT_COUNT_LO}(11)
    cmpwi 11, 0
    ble xa_out
    mtctr 11
xp_find:
    lwz 12, 4(10)
    cmpwi 12, {BORROWED_TEXT}
    beq xp_found
    addi 10, 10, 16
    bdnz xp_find
    b xa_out
xp_found:
    stw 8, 0(10)
    li 3, {BORROWED_TEXT}
xp_tell:
    mulli 8, 30, 24                 # the weapon is filled up
    lis 7, {ITEM_AMMO_HA}
    addi 7, 7, {ITEM_AMMO_LO}
    add 7, 7, 8
    lhz 7, 0xe(7)
    cmpwi 7, 0
    beq xp_filled
    lis 9, {AMMO_HA}
    addi 9, 9, {AMMO_LO}
    slwi 8, 30, 2
    stwx 7, 9, 8
xp_filled:
    lis 4, {STATE_HA}
    addi 4, 4, {STATE_LO}
    lwz 4, 0x11c(4)
    cmpwi 4, 0
    bne xp_show
    li 4, {MESSAGE_INDEX}
xp_show:
    bl {SHOW_MESSAGE}
    bl celebrate
{BOLT_BURST}
xa_out:
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr
"""

# The damage of a boosted weapon at level 2, once per ring writer: replaces the store of the damage
# (f1; r3 = target, @FLAGS@ = flags). r9 and r10 are kept below the stack pointer; f2 is free at
# both sites.
DAMAGE = """
@NAME@:
    std 9, -8(1)
    std 10, -16(1)
    andis. 9, @FLAGS@, {WRENCH_HI}
    bne @NAME@_out
    lis 9, {HERO_HA}
    addi 9, 9, {HERO_LO}
    lwz 10, 0x2080(9)               # not what Ratchet takes himself
    cmpw 10, 3
    beq @NAME@_out
    lbz 10, 0x20a4(9)
    cmpwi 10, 0
    bne @NAME@_out
    lwz 10, {HAND_ITEM}(9)
    cmplwi 10, {LAST_ITEM}
    bgt @NAME@_out
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    lfs 2, {P_BOOST}(9)
    addi 9, 9, {P_BOOSTED_AT}
    lbzx 10, 9, 10
    cmpwi 10, {NO_WEAPON}
    beq @NAME@_out
    lis 9, {AMMO_HA}
    addi 9, 9, {AMMO_LO}
    lhzx 10, 9, 10
    cmplwi 10, 0xffff
    bne @NAME@_out
    fmuls 1, 1, 2
@NAME@_out:
    ld 10, -16(1)
    ld 9, -8(1)
    stfs 1, 0x2c(@ENTRY@)           # the displaced instruction
    b {@BACK@}
"""


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

# ryno_fan: replaces bl ROCKET in the R.Y.N.O.'s update.
# icon_gold: replaces bl ICON for the ammunition widget (r3): a level 2 weapon's icon is tinted.
# quick_icon: the same for an entry of the QuickSelect.
# icon_lookup: jumped to from the top of ICON_SPRITE (r3 = icon id); menu_tint: replaces
#   or r6, r6, r7 in ICON_DRAW, its own place for the colour (r7 and r9 are free there).
# tint: replaces or r4, r5, r8 in DRAW_QUAD, where r5 is the alpha and r8 the grey.
# magnet: replaces bl SPAWN_BOLTS (r6 = flags).
PERKS = """
ryno_fan:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0xa0(1)
    std 3, 0x70(1)
    std 4, 0x78(1)
    std 5, 0x80(1)
    stfd 1, 0x88(1)
    stfd 2, 0x90(1)
    stfd 3, 0x98(1)
    bl {ROCKET}
    li 10, {RYNO}
@LEVEL2 rf_out@
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    lfs 0, {P_RYNO_FAN}(9)
    ld 3, 0x70(1)
    ld 4, 0x78(1)
    ld 5, 0x80(1)
    lfd 1, 0x88(1)
    lfd 2, 0x90(1)
    lfd 3, 0x98(1)
    fadds 2, 2, 0
    bl {ROCKET}
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    lfs 0, {P_RYNO_FAN}(9)
    ld 3, 0x70(1)
    ld 4, 0x78(1)
    ld 5, 0x80(1)
    lfd 1, 0x88(1)
    lfd 2, 0x90(1)
    lfd 3, 0x98(1)
    fsubs 2, 2, 0
    bl {ROCKET}
rf_out:
    addi 1, 1, 0xa0
    ld 0, 0x10(1)
    mtlr 0
    blr

quick_icon:
    lis 10, {QUICK_LISTS_HA}
    lwz 10, {QUICK_LISTS_LO}(10)
    lis 11, {QUICK_LIST_HA}
    lwz 11, {QUICK_LIST_LO}(11)
    slwi 11, 11, 2
    lwzx 10, 10, 11
    add 10, 10, 23
    lwz 10, 0x18(10)
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    cmplwi 10, {LAST_ITEM}
    bgt qi_draw
@NOGOLD2 qi_draw@
    lis 12, {STATE_HA}
    addi 12, 12, {STATE_LO}
    li 11, 1
    stw 11, 0x138(12)
qi_draw:
    bl {ICON}
    lis 12, {STATE_HA}
    addi 12, 12, {STATE_LO}
    li 11, 0
    stw 11, 0x138(12)
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

icon_gold:
    lwz 10, 0(3)
    lis 11, {ICON_BASE_HI}
    ori 11, 11, {ICON_BASE_LO}
    subf 10, 11, 10
icon_item:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    cmplwi 10, {LAST_ITEM}
    bgt ig_draw
@LEVEL2 ig_draw@
    lis 12, {STATE_HA}
    addi 12, 12, {STATE_LO}
    li 11, 1
    stw 11, 0x138(12)
ig_draw:
    bl {ICON}
    lis 12, {STATE_HA}
    addi 12, 12, {STATE_LO}
    li 11, 0
    stw 11, 0x138(12)
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

icon_lookup:
    lis 12, {STATE_HA}
    addi 12, 12, {STATE_LO}
    li 11, 0
    stw 11, 0x154(12)
    lis 11, {ICON_BASE_HI}
    ori 11, 11, {ICON_BASE_LO}
    subf 10, 11, 3
    cmplwi 10, {LAST_ITEM}
    bgt il_out
@NOGOLD2 il_out@
    li 11, 1
    stw 11, 0x154(12)
il_out:
    lis 5, 0xa2                     # the displaced instruction
    b {ICON_SPRITE_BACK}

menu_tint:
    or 6, 6, 7                      # the displaced instruction
    lis 7, {STATE_HA}
    addi 7, 7, {STATE_LO}
    lwz 9, 0x154(7)
    cmpwi 9, 0
    beqlr
    li 9, 0
    stw 9, 0x154(7)
    lwz 9, 0x13c(7)
    cmpwi 9, 0
    bne menu_tint_set
    lis 9, {TINT_HI}
    ori 9, 9, {TINT_LO}
menu_tint_set:
    rlwinm 6, 6, 0, 0, 7
    or 6, 6, 9
    blr

preview_gold:
    lis 3, 0x95                     # the displaced instruction
    mr 12, 24
    b model_gold
figure_gold:
    lis 3, 0x70                     # the displaced instruction
    mr 12, 28
model_gold:
    mr 10, 29
    cmplwi 10, {LAST_ITEM}
    bgtlr
@NOGOLD2 mg_out@
    lis 11, {WEAPON_TINT_HI}
    ori 11, 11, {WEAPON_TINT_LO}
    stw 11, 0x38(12)
mg_out:
    blr

wall_reach:
    lfs 29, 0x248(26)               # the displaced instruction
    li 10, {WALLOPER}
@LEVEL2 wr_out@
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    lfs 0, {P_WALLOPER_REACH}(9)
    fmuls 29, 29, 0
wr_out:
    blr

visi_blast:
    lfs 30, 0x5c(3)                 # the displaced instruction
    mr 12, 11
    li 10, {VISIBOMB}
@LEVEL2 vb_out@
    lis 9, {STATE_HA}
    addi 9, 9, {STATE_LO}
    lfs 0, 0x18c(9)
    lwz 10, 0x18c(9)
    cmpwi 10, 0
    bne vb_scale
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    lfs 0, {P_VISIBOMB_BLAST}(9)
vb_scale:
    fmuls 30, 30, 0
vb_out:
    mr 11, 12
    blr

wall_speed:
    lfs 1, 0x290(26)                # the displaced instruction
    b wall_thrust
wall_accel:
    lfs 1, 0x29c(26)                # the displaced instruction
wall_thrust:
    li 10, {WALLOPER}
@LEVEL2 wt_out@
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    lfs 0, {P_WALLOPER_THRUST}(9)
    fmuls 1, 1, 0
wt_out:
    blr

wall_decel:
    lfs 2, 0x210(26)                # the displaced instruction
    li 10, {WALLOPER}
@LEVEL2 wd_out@
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    lfs 0, {P_WALLOPER_THRUST}(9)
    fmuls 2, 2, 0
wd_out:
    blr

wall_colour:
    li 10, {WALLOPER}
@LEVEL2 wc_blue@
    lis 9, {STATE_HA}
    addi 9, 9, {STATE_LO}
    lwz 12, 0x17c(9)
    cmpwi 12, 0
    bne wc_set
    lis 12, {WALLOPER_RED_HI}
    ori 12, 12, {WALLOPER_RED_LO}
wc_set:
    rlwinm 31, 31, 0, 0, 7
    or 31, 31, 12
    b wc_glow
wc_blue:
    lis 12, {WALLOPER_GLOW_BLUE_HI}
    ori 12, 12, {WALLOPER_GLOW_BLUE_LO}
wc_glow:
    lis 9, {WALLOPER_GLOW_HA}
    stw 12, {WALLOPER_GLOW_LO}(9)
    srawi 3, 31, 24                 # the displaced instruction
    blr

tint:
    or 4, 5, 8                      # the displaced instruction
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x138(11)
    cmpwi 12, 0
    bne tint_do
    lwz 12, 0x154(11)               # or the icon a menu looked up last
    cmpwi 12, 0
    beqlr
    li 12, 0
    stw 12, 0x154(11)
tint_do:
    lwz 12, 0x13c(11)
    cmpwi 12, 0
    bne tint_set
    lis 12, {TINT_HI}
    ori 12, 12, {TINT_LO}
tint_set:
    rlwinm 4, 4, 0, 0, 7            # the alpha stays
    or 4, 4, 12
    blr

magnet:
    lis 12, {HERO_HA}
    addi 12, 12, {HERO_LO}
    lbz 10, 0x20a4(12)
    cmpwi 10, 0
    bne magnet_next
    lwz 10, {HAND_ITEM}(12)
    cmplwi 10, {LAST_ITEM}
    bgt magnet_next
@LEVEL2 magnet_next@
    ori 6, 6, {BOLT_FLY}
magnet_next:
    {CHAIN}
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

# The bar. bar(r3 item, r4 x, r5 y, r6 = x is the bar's centre, not its left end, r7 = width or 0
#   for BAR_WIDTH, f1 = how far the HUD element is faded in): r31 = the filled width, r30 = pool, r29 = state block, f31 = fade; on
#   the stack: 0x98 colour, 0xa0 width, 0xa8 x0, 0xb0 y0, 0xb8 y1, 0xc8 r6.
# hud_bar: replaces extsw r5, r3 in the QuickSelect (r3 = the item of the entry, r18/r28 = its place).
# ammo_bar: replaces lwz r3, 0x58(r31) behind the ammunition count of the HUD in play (r31 = the
#   widget, +0 its icon, ICON_BASE + item; r30/r27 and r21 = where the count is; f30 = fade).
# hud_flash: replaces ori r3, r30, 0 behind the HUD's loop over its widgets (r31 = they are drawn):
#   it counts the flash's frames. A rectangle drawn there did not show in game, so the flash is
#   drawn from ammo_bar, with the ammunition widget, which is on screen when a weapon is used.
BAR = """
bar:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0xe0(1)
    std 31, 0x80(1)
    std 30, 0x88(1)
    std 29, 0x90(1)
    stfd 31, 0xd0(1)
    fmr 31, 1
    std 4, 0xa8(1)
    std 5, 0xb0(1)
    std 6, 0xc8(1)
    std 7, 0xa0(1)
    cmplwi 3, {LAST_ITEM}
    bgt hb_out
    lis 30, {POOL_HA}
    addi 30, 30, {POOL_LO}
    addi 10, 30, {P_XP_AT}
    lbzx 10, 10, 3
    cmpwi 10, {NO_WEAPON}
    beq hb_out
    lis 11, {AMMO_HA}
    addi 11, 11, {AMMO_LO}
    lhzx 31, 11, 10                 # the experience
    slwi 12, 3, 1
    addi 11, 30, {P_XP_NEEDED}
    lhzx 12, 11, 12                 # what level 2 takes
    lis 11, {GOLD_HA}
    addi 11, 11, {GOLD_LO}
    lbzx 11, 11, 3
    lis 29, {STATE_HA}
    addi 29, 29, {STATE_LO}
    ld 9, 0xa0(1)
    cmpwi 9, 0
    bgt hb_width
@TUNE 9 0x108 BAR_WIDTH@
hb_width:
    cmpwi 11, 0
    bne hb_full
    cmplwi 31, 0xffff
    beq hb_full
    mullw 31, 31, 9
    divwu 31, 31, 12
@TUNE 11 0x110 BAR_FILL@
    b hb_place
hb_full:
    mr 31, 9
@TUNE 11 0x114 BAR_FULL@
hb_place:
    std 11, 0x98(1)
    std 9, 0xa0(1)
    ld 10, 0xa8(1)
    ld 6, 0xc8(1)
    cmpwi 6, 0
    beq hb_left
    srawi 8, 9, 1
    subf 10, 8, 10
hb_left:
    ld 8, 0xb0(1)
@TUNE 7 0x10c BAR_HEIGHT@
    add 7, 8, 7
    std 10, 0xa8(1)
    std 7, 0xb8(1)
@TUNE 4 0x118 BAR_BACK@
    extsw 4, 4                      # the background, faded as the HUD is
    clrlwi 3, 4, 8
    fmr 1, 31
    bl {FADE}
    mr 7, 3
    ld 3, 0xa8(1)
    ld 4, 0xb0(1)
    ld 9, 0xa0(1)
    add 5, 3, 9
    ld 6, 0xb8(1)
    extsw 3, 3
    extsw 4, 4
    extsw 5, 5
    extsw 6, 6
    clrldi 7, 7, 32
    li 8, 0
    bl {FILL_RECT}
    cmpwi 31, 0
    ble hb_out
    ld 4, 0x98(1)
    extsw 4, 4
    clrlwi 3, 4, 8
    fmr 1, 31
    bl {FADE}
    mr 7, 3
    ld 3, 0xa8(1)
    ld 4, 0xb0(1)
    add 5, 3, 31
    ld 6, 0xb8(1)
    extsw 3, 3
    extsw 4, 4
    extsw 5, 5
    extsw 6, 6
    clrldi 7, 7, 32
    li 8, 0
    bl {FILL_RECT}
hb_out:
    lfd 31, 0xd0(1)
    ld 29, 0x90(1)
    ld 30, 0x88(1)
    ld 31, 0x80(1)
    addi 1, 1, 0xe0
    ld 0, 0x10(1)
    mtlr 0
    blr

hud_bar:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 3, 0x70(1)
    std 4, 0x78(1)
    lis 9, {STATE_HA}
    addi 9, 9, {STATE_LO}
    lis 4, {HUD_X_HA}
    lwz 4, {HUD_X_LO}(4)
    add 4, 4, 18
    lwz 8, 0x100(9)
    add 4, 4, 8
    lis 5, {HUD_Y_HA}
    lwz 5, {HUD_Y_LO}(5)
    add 5, 5, 28
    addi 5, 5, {BAR_BELOW}
    lwz 8, 0x104(9)
    add 5, 5, 8
    li 6, 1                         # centred as the count is
    li 7, 0
    lis 8, {POOL_HA}
    addi 8, 8, {POOL_LO}
    lfs 1, {P_ONE}(8)
    bl bar
    ld 4, 0x78(1)
    ld 3, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    extsw 5, 3                      # the displaced instruction
    blr

menu_bar:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 30, 0x70(1)
    bl box_grow
    li 9, 24
    divwu 30, 25, 9                 # the item
    mr 3, 30
    lis 9, {STATE_HA}
    addi 9, 9, {STATE_LO}
    lwz 4, 0x20(31)
    srawi 4, 4, 1
    lwz 8, 0x170(9)
    add 4, 4, 8
    li 5, {MENU_BAR_Y}
    lwz 8, 0x174(9)
    add 5, 5, 8
    li 6, 1
    li 7, {MENU_BAR_WIDTH}
    lis 8, {POOL_HA}
    addi 8, 8, {POOL_LO}
    lfs 1, {P_ONE}(8)
    bl bar
    mr 4, 30
    bl xp_words
    bl {MENU_TEXT_DONE}
    ld 30, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

# box_grow: the ammunition box's frame MENU_BOX_GROW taller at its bottom (the last pose of
#   animation MENU_BOX_ANIM of the menu frames' model, recognised by its width and x).
box_grow:
    lis 3, {CLASS_SLOT_MAP_HA}
    addi 3, 3, {CLASS_SLOT_MAP_LO}
    lbz 4, {MENU_FRAME_CLASS}(3)
    cmplwi 4, {MODEL_SLOTS}
    bgelr
    slwi 4, 4, 2
    lis 5, {MODEL_TABLE_HA}
    addi 5, 5, {MODEL_TABLE_LO}
    lwzx 5, 5, 4
    cmpwi 5, 0
    beqlr
    lwz 5, {MENU_BOX_ANIM_OFF}(5)
    cmpwi 5, 0
    beqlr
    lbz 4, 0x10(5)                  # frames
    slwi 4, 4, 2
    add 4, 4, 5
    lwz 4, 0x18(4)                  # the last pose
    lha 6, 0x3a(4)
    cmpwi 6, {MENU_BOX_X}
    bnelr
    lha 6, 0x42(4)
    cmpwi 6, {MENU_BOX_HALF_W}
    bnelr
    lis 9, {STATE_HA}
    addi 9, 9, {STATE_LO}
    lwz 6, 0x184(9)
    cmpwi 6, 0
    bne bg_set
    li 6, {MENU_BOX_GROW}
bg_set:
    srawi 6, 6, 1                   # half of it to the half height, as much down for the centre
    addi 7, 6, {MENU_BOX_HALF_H}
    sth 7, 0x44(4)
    sth 7, 0x4c(4)
    neg 7, 7
    sth 7, 0x54(4)
    sth 7, 0x5c(4)
    neg 6, 6
    addi 6, 6, {MENU_BOX_Y}
    sth 6, 0x3c(4)
    blr

# menu_count: replaces lwz r3, 0x24(r31) where the count's box is set up: the count stays in
#   the top MENU_COUNT_H of the taller box.
menu_count:
    lwz 3, 0x24(31)                 # the displaced instruction
    lis 9, {STATE_HA}
    addi 9, 9, {STATE_LO}
    lwz 10, 0x188(9)
    cmpwi 10, 0
    bne mc_set
    li 10, {MENU_COUNT_H}
mc_set:
    cmpw 10, 3
    bgelr
    mr 3, 10
    blr

xp_words:                           # (r4 item, r31 the box's widget)
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0xe0(1)
    std 29, 0xc8(1)
    std 30, 0xd0(1)
    mr 30, 4
    cmplwi 30, {LAST_ITEM}
    bgt mx_done
    lis 8, {POOL_HA}
    addi 8, 8, {POOL_LO}
    addi 9, 8, {P_XP_AT}
    lbzx 10, 9, 30
    cmpwi 10, {NO_WEAPON}
    beq mx_done
    lis 9, {AMMO_HA}
    addi 9, 9, {AMMO_LO}
    lhzx 5, 9, 10
    lis 9, {GOLD_HA}
    addi 9, 9, {GOLD_LO}
    lbzx 11, 9, 30
    cmpwi 11, 0
    bne mx_max
    cmplwi 5, 0xffff
    beq mx_max
    slwi 12, 30, 1
    addi 9, 8, {P_XP_NEEDED}
    lhzx 6, 9, 12
    addi 4, 8, {P_XP_TEXTS}
    lis 29, {MENU_TEXT_COLOUR_HI}
    ori 29, 29, {MENU_TEXT_COLOUR_LO}
    b mx_print
mx_max:
    addi 4, 8, {P_XP_TEXTS}
    addi 4, 4, {XP_TEXT_MAX}
    lis 29, {BAR_FULL_HI}
    ori 29, 29, {BAR_FULL_LO}
mx_print:
    addi 3, 1, 0x70
    bl {SPRINTF}
    li 0, 0                         # where: see MENU_XP_X/MENU_XP_Y
    std 0, 0xa0(1)
    std 0, 0xa8(1)
    std 0, 0xb0(1)
    lis 9, {STATE_HA}
    addi 9, 9, {STATE_LO}
    lwz 5, 0x178(9)
    addi 5, 5, {MENU_XP_Y}
    sth 5, 0xa0(1)
    addi 6, 5, {MENU_XP_HEIGHT}
    sth 6, 0xa2(1)
    lwz 7, 0x180(9)
    addi 7, 7, {MENU_XP_X}
    sth 7, 0xa4(1)
    lwz 4, 0x20(31)
    add 8, 4, 7
    sth 8, 0xa6(1)
    srawi 4, 4, 1
    add 4, 4, 7
    sth 4, 0xa8(1)
    addi 6, 5, {MENU_XP_HEIGHT_HALF}
    sth 6, 0xaa(1)
    li 4, 0x10
    sth 4, 0xb0(1)
    li 4, 3
    sth 4, 0xb2(1)
    addi 3, 1, 0xa0
    clrldi 4, 29, 32
    addi 5, 1, 0x70
    li 6, -1
    bl {DRAW_TEXT}
mx_done:
    ld 29, 0xc8(1)
    ld 30, 0xd0(1)
    addi 1, 1, 0xe0
    ld 0, 0x10(1)
    mtlr 0
    blr

ammo_bar:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lwz 3, 0(31)
    lis 8, {ICON_BASE_HI}
    ori 8, 8, {ICON_BASE_LO}
    subf 3, 8, 3
    lis 9, {STATE_HA}
    addi 9, 9, {STATE_LO}
    lis 4, {AMMO_X_HA}
    lwz 4, {AMMO_X_LO}(4)
    add 4, 4, 30
    addi 4, 4, {AMMO_BAR_LEFT}
    lwz 8, 0x120(9)
    add 4, 4, 8
    lis 5, {AMMO_Y_HA}
    lwz 5, {AMMO_Y_LO}(5)
    add 5, 5, 21
    addi 5, 5, {AMMO_BAR_BELOW}
    lwz 8, 0x124(9)
    add 5, 5, 8
    li 6, 0
    addi 7, 27, -{AMMO_BAR_SHORTER}
    fmr 1, 30
    bl bar
    bl flash
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    lwz 3, 0x58(31)                 # the displaced instruction
    blr

hud_flash:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    cmpwi 31, 0
    beq hf_out
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x130(11)               # frames of the flash left: it fades with them
    cmpwi 12, 0
    ble hf_out
    addi 12, 12, -1
    stw 12, 0x130(11)
hf_out:
    bl weapon_gold
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    ori 3, 30, 0                    # the displaced instruction
    blr

weapon_gold:                        # r31 = the weapon, r30 = its colour, r29 = it is to be set, r28 = FX
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x90(1)
    std 31, 0x70(1)
    std 30, 0x78(1)
    std 29, 0x80(1)
    std 28, 0x88(1)
    lis 28, {FX_HA}
    addi 28, 28, {FX_LO}
    lis 12, {HERO_HA}
    addi 12, 12, {HERO_LO}
    lbz 10, 0x20a4(12)
    cmpwi 10, 0
    bne wg_out
    lis 9, {STATE_HA}
    addi 9, 9, {STATE_LO}
    lwz 8, 0x15c(9)                 # frames of a level-up left (r8)
    lwz 7, 0x70(28)
    subf 7, 8, 7                   # r7 = frames into it
    cmpwi 8, 0
    ble wg_weapon
    lwz 10, 0x80(28)                # Ratchet glows
    cmpw 7, 10
    bge wg_weapon
    lwz 9, 0x2080(12)
    lwz 10, 0x7c(28)
    stw 10, 0x38(9)
wg_weapon:
    lwz 31, {HAND_MOBY}(12)
    cmpwi 31, 0
    beq wg_out
    lwz 10, {HAND_ITEM}(12)
    cmplwi 10, {LAST_ITEM}
    bgt wg_out
    li 29, 0
@NOGOLD2 wg_other@
    li 29, 1                        # a level 2 weapon without a gold version: gold
    lis 9, {STATE_HA}
    addi 9, 9, {STATE_LO}
    lwz 30, 0x158(9)
    cmpwi 30, 0
    bne wg_flash
    lis 30, {WEAPON_TINT_HI}
    ori 30, 30, {WEAPON_TINT_LO}
    b wg_flash
wg_other:                           # any other weapon has its own colour, which is kept through a level-up
    cmpwi 8, 0
    bgt wg_keep
    li 0, 0
    stw 0, 0xa8(28)
    b wg_out
wg_keep:
    lwz 9, 0xa8(28)
    cmpw 9, 31
    beq wg_kept
    stw 31, 0xa8(28)
    lwz 9, 0x38(31)
    stw 9, 0xac(28)
wg_kept:
    lwz 30, 0xac(28)
    li 29, 1
wg_flash:                           # in the first frames of a level-up: on its way there from the flash's colour
    cmpwi 8, 0
    ble wg_set
    lwz 6, 0x74(28)
    cmpw 7, 6
    bge wg_set
    subf 7, 7, 6                    # frames of it to go
    lwz 3, 0x78(28)
    li 5, 0
    li 12, 0
wg_mix:                             # byte by byte
    srw 9, 3, 5
    andi. 9, 9, 0xff
    srw 10, 30, 5
    andi. 10, 10, 0xff
    subf 9, 10, 9
    mullw 9, 9, 7
    divw 9, 9, 6
    add 9, 9, 10
    slw 9, 9, 5
    or 12, 12, 9
    addi 5, 5, 8
    cmpwi 5, 24
    blt wg_mix
    mr 30, 12
wg_set:
    cmpwi 29, 0
    beq wg_out
    stw 30, 0x38(31)
wg_out:
    ld 28, 0x88(1)
    ld 29, 0x80(1)
    ld 30, 0x78(1)
    ld 31, 0x70(1)
    addi 1, 1, 0x90
    ld 0, 0x10(1)
    mtlr 0
    blr

flash:                              # the level-up flash, while its frames run
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 29, 0x70(1)
    lis 29, {STATE_HA}
    addi 29, 29, {STATE_LO}
    lwz 9, 0x130(29)
    cmpwi 9, 0
    ble flash_out
    lis 8, {FX_HA}
    addi 8, 8, {FX_LO}
    lwz 10, 0xa4(8)
    mullw 9, 9, 10
    lwz 10, 0xa0(8)
    divw 9, 9, 10
    slwi 9, 9, 24
@TUNE 7 0x128 FLASH_COLOUR@
    clrlwi 7, 7, 8
    or 7, 7, 9
    clrldi 7, 7, 32
@TUNE 3 0x14c FLASH_LEFT@
@TUNE 4 0x150 FLASH_TOP@
    extsw 3, 3
    extsw 4, 4
@TUNE 5 0x144 FLASH_RIGHT@
@TUNE 6 0x148 FLASH_BOTTOM@
    li 8, 0
    bl {FILL_RECT}
flash_out:
    ld 29, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr
"""

# levelup_frame: replaces bl HERO_MAIN; fx_tick(): the level-up's frame (r31 = state block, r30 =
#   the weapon, r29 = hero, r28 = FX, r26 = frames into it); puffs(r3 = a set): its puffs from
#   the weapon r30 (the position is at 0x80 on the stack); celebrate(): start a level-up.
# gold_name: jumped to from the top of TEXT_LOOKUP (r3 = text id; a leaf function, so everything
#   volatile is free).
FX = """
levelup_frame:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    bl fx_tick
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
levelup_frame_next:
    {CHAIN}

fx_tick:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0xa0(1)
    std 31, 0x70(1)
    std 30, 0x78(1)
    std 29, 0x80(1)
    std 28, 0x88(1)
    std 26, 0x90(1)
    lis 31, {STATE_HA}
    addi 31, 31, {STATE_LO}
    lis 29, {HERO_HA}
    addi 29, 29, {HERO_LO}
    lis 28, {FX_HA}
    addi 28, 28, {FX_LO}
    lwz 3, 0x90(28)                 # a sound to hear
    li 0, 0
    stw 0, 0x90(28)
    bl fx_sound
    lwz 3, 0x94(28)                 # the level-up again
    cmpwi 3, 0
    beq fx_run
    li 0, 0
    stw 0, 0x94(28)
    bl celebrate
fx_run:
    bl daze_tick
    lwz 9, 0x15c(31)
    cmpwi 9, 0
    ble fx_out
    lwz 26, 0x70(28)
    subf 26, 9, 26
    addi 9, 9, -1
    stw 9, 0x15c(31)
    lbz 10, 0x20a4(29)
    cmpwi 10, 0
    bne fx_out
    cmpwi 26, 0
    bne fx_second
    lwz 3, 0x84(28)
    bl fx_sound
    b fx_glow
fx_second:
    lwz 10, 0x8c(28)
    cmpw 26, 10
    bne fx_glow
    lwz 3, 0x88(28)
    bl fx_sound
fx_glow:
    lwz 30, {HAND_MOBY}(29)
    cmpwi 30, 0
    beq fx_out
    cmpwi 26, 0
    bne fx_smoke
    addi 3, 28, 0x38
    bl puffs
fx_smoke:
    mr 3, 28
    bl puffs
fx_out:
    ld 26, 0x90(1)
    ld 28, 0x88(1)
    ld 29, 0x80(1)
    ld 30, 0x78(1)
    ld 31, 0x70(1)
    addi 1, 1, 0xa0
    ld 0, 0x10(1)
    mtlr 0
    blr

fx_sound:                           # (r3 = one of Ratchet's sound definitions + 1, or 0)
    cmpwi 3, 0
    beqlr
    addi 3, 3, -1
    li 4, 0
    lwz 5, 0x2080(29)
    b {PLAY_MODEL_SOUND}

celebrate:
    lis 9, {STATE_HA}
    addi 9, 9, {STATE_LO}
    lis 10, {FX_HA}
    addi 10, 10, {FX_LO}
    lwz 8, 0xa0(10)
    stw 8, 0x130(9)
    lwz 8, 0x70(10)
    stw 8, 0x15c(9)
    lis 9, {CAMERA_STATE_HA}
    addi 9, 9, {CAMERA_STATE_LO}
    lfs 0, 0x9c(10)
    stfs 0, 0x160(9)
    lwz 8, 0x98(10)
    stw 8, 0x168(9)
    stw 8, 0x16c(9)
    blr

puffs:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0xb0(1)
    std 28, 0x98(1)
    std 27, 0xa0(1)
    mr 28, 3
    lwz 27, 0x34(28)
pf_next:
    cmpwi 27, 0
    ble pf_out
    lfs 0, 0x10(30)
    lfs 1, 0(28)
    fadds 0, 0, 1
    stfs 0, 0x80(1)
    lfs 0, 0x14(30)
    lfs 1, 4(28)
    fadds 0, 0, 1
    stfs 0, 0x84(1)
    lfs 0, 0x18(30)
    lfs 1, 8(28)
    fadds 0, 0, 1
    stfs 0, 0x88(1)
    lfs 0, 0x1c(30)
    stfs 0, 0x8c(1)
    addi 3, 1, 0x80
    addi 4, 28, 0xc
    lwz 5, 0x24(28)
    lwz 6, 0x28(28)
    li 7, 0
    lwz 8, 0x2c(28)
    lwz 9, 0x30(28)
    li 10, 0
    li 0, 0
    std 0, 0x70(1)
    std 0, 0x78(1)
    lfs 1, 0x1c(28)
    lfs 2, 0x20(28)
    bl {PUFF}
    addi 27, 27, -1
    b pf_next
pf_out:
    ld 27, 0xa0(1)
    ld 28, 0x98(1)
    addi 1, 1, 0xb0
    ld 0, 0x10(1)
    mtlr 0
    blr

gold_name:
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    addi 10, 9, {P_NAMES}           # for each of the four: u16 text id, u8 place of its experience, u8 number
    li 11, {NAME_COUNT}
    mtctr 11
gn_next:
    lhz 12, 0(10)
    cmpw 12, 3
    beq gn_found
    addi 10, 10, 4
    bdnz gn_next
gn_plain:
    lis 5, 0x97                     # the displaced instruction
    b {TEXT_LOOKUP_BACK}
gn_found:
    lbz 11, 2(10)
    lis 12, {AMMO_HA}
    addi 12, 12, {AMMO_LO}
    lhzx 11, 12, 11
    cmplwi 11, 0xffff
    bne gn_plain
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    lbz 11, 3(10)
    std 11, 0x70(1)
    lis 5, 0x97
    bl {TEXT_LOOKUP_BACK}           # the game's name
    ld 11, 0x70(1)
    mulli 11, 11, {NAME_SIZE}
    lis 12, {NAME_BUFFERS_HA}
    addi 12, 12, {NAME_BUFFERS_LO}
    add 12, 12, 11
    addi 10, 12, {NAME_PREFIX_END}  # behind the prefix
    addi 3, 3, -1
    li 11, {NAME_ROOM}
    mtctr 11
gn_copy:
    lbzu 9, 1(3)
    stbu 9, 1(10)
    cmpwi 9, 0
    beq gn_done
    bdnz gn_copy
    li 9, 0
    stb 9, 1(10)
gn_done:
    mr 3, 12
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr
"""

_tuned = 0


def tuned(template):
    """@TUNE register offset NAME@: the word at that offset of the state block (r29), or the
    constant NAME when it is 0. @LEVEL2 label@: see LEVEL2."""
    global _tuned
    out = []
    for line in template.splitlines():
        if line.startswith("@TUNE"):
            reg, offset, name = line.strip("@").split()[1:]
            value, _tuned = globals()[name], _tuned + 1
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


# Bolts worth {LEVELUP_BOLTS} from the enemy (r31), with the last argument its own drop passes on.
BOLT_BURST = """
    mr 3, 31
    li 4, {LEVELUP_BOLTS}
    li 5, {LEVELUP_BOLTS}
    li 6, {BOLT_FLY}
    ld 7, 0xf0(1)                   # r5 as xp_kill kept it
    bl {SPAWN_BOLTS}
"""


# The Taunter. lure_find(r3 a moby) -> r12 its entry in the lure table or 0 (uses r9 to r11 and the
#   CTR). taunt_lure: replaces stw r31, 0x18(r26) in the lure (r27 = the enemy; r3 to r12 are free).
# stun_check(r3 a moby) -> r12 = 1 while it is stunned, and starts the stun of a lured enemy that
#   has come close (uses r7 to r11, f0 to f2 and the CTR, not r0 or r3). moby_update: replaces lwz
#   r3, 0x74(r31) in the moby loop (r31 = the moby; 0 there skips the update); moby_anim: replaces
#   bl MOBY_ANIM (r3 = the moby).
# daze_tick: from fx_tick (r28 = FX, r31 = state): gold puffs above the stunned, and the entries
#   of enemies lured long ago are freed.
TAUNT = """
lure_find:
    lis 12, {STATE_HA}
    addi 12, 12, {STATE_LO}
    addi 12, 12, {LURES}
    li 11, {LURE_COUNT}
    mtctr 11
    lhz 10, 0xa6(3)
lf_next:
    lwz 9, 0(12)
    cmpw 9, 3
    bne lf_skip
    lhz 9, 4(12)
    cmpw 9, 10
    beqlr
lf_skip:
    addi 12, 12, {LURE_SIZE}
    bdnz lf_next
    li 12, 0
    blr

taunt_lure:
    stw 31, 0x18(26)                # the displaced instruction
    mflr 0
    mr 3, 27
    bl lure_find
    mtlr 0
    lis 11, {FRAME_COUNTER_HA}
    lwz 11, {FRAME_COUNTER_LO}(11)
    cmpwi 12, 0
    bne tl_known
    lis 10, {STATE_HA}              # a new one takes the entry lured longest ago (a free one: never)
    addi 10, 10, {STATE_LO}
    addi 10, 10, {LURES}
    mr 12, 10
    li 7, 0
    li 9, {LURE_COUNT}
    mtctr 9
tl_oldest:
    lwz 9, 8(10)
    subf 9, 9, 11
    cmplw 9, 7
    ble tl_older
    mr 7, 9
    mr 12, 10
tl_older:
    addi 10, 10, {LURE_SIZE}
    bdnz tl_oldest
    stw 27, 0(12)
    lhz 9, 0xa6(27)
    sth 9, 4(12)
    li 9, 0
    stw 9, 0xc(12)
    b tl_stamp
tl_known:                           # stunned before: again once STUN_COOLDOWN has passed since
    lwz 9, 0xc(12)
    cmpwi 9, 0
    beq tl_stamp
    subf 9, 9, 11
    lis 10, {FX_HA}
    addi 10, 10, {FX_LO}
    lwz 10, {FX_STUN_COOLDOWN}(10)
    cmpw 9, 10
    blt tl_stamp
    li 9, 0
    stw 9, 0xc(12)
tl_stamp:
    stw 11, 8(12)
    blr

stun_check:
    mflr 8
    bl lure_find
    mtlr 8
    cmpwi 12, 0
    beqlr
    mr 7, 12
    lis 11, {FRAME_COUNTER_HA}
    lwz 11, {FRAME_COUNTER_LO}(11)
    lwz 9, 0xc(7)
    cmpwi 9, 0
    beq sc_arrive
    subf 9, 11, 9                   # frames of the stun left
    cmpwi 9, 0
    ble sc_no
    lbz 9, 0xa4(3)                  # a hit ends it
    lbz 10, 6(7)
    cmpw 9, 10
    beq sc_yes
    stw 11, 0xc(7)
    b sc_no
sc_arrive:
    lwz 9, 8(7)
    subf 9, 9, 11
    lis 10, {FX_HA}
    addi 10, 10, {FX_LO}
    lwz 10, {FX_LURE_FRAMES}(10)
    cmplw 9, 10
    bgt sc_no
    li 10, {TAUNTER}
@LEVEL2 sc_no@
    lis 9, {HERO_HA}
    addi 9, 9, {HERO_LO}
    lfs 0, 0x80(9)
    lfs 1, 0x10(3)
    fsubs 0, 0, 1
    fmuls 0, 0, 0
    lfs 1, 0x84(9)
    lfs 2, 0x14(3)
    fsubs 1, 1, 2
    fmadds 0, 1, 1, 0
    lfs 1, 0x88(9)
    lfs 2, 0x18(3)
    fsubs 1, 1, 2
    fmadds 0, 1, 1, 0
    lis 10, {FX_HA}
    addi 10, 10, {FX_LO}
    lfs 1, {FX_ARRIVE}(10)
    fmuls 1, 1, 1
    fcmpu 0, 0, 1
    bge sc_no
    lwz 9, {FX_STUN_FRAMES}(10)
    lis 11, {FRAME_COUNTER_HA}
    lwz 11, {FRAME_COUNTER_LO}(11)
    add 9, 11, 9
    stw 9, 0xc(7)
    lbz 9, 0xa4(3)
    stb 9, 6(7)
sc_yes:
    li 12, 1
    blr
sc_no:
    li 12, 0
    blr

moby_update:
    mflr 0
    mr 3, 31
    bl stun_check
    mtlr 0
    li 3, 0
    cmpwi 12, 0
    bnelr
    lwz 3, 0x74(31)                 # the displaced instruction
    blr

moby_anim:
    mflr 0
    bl stun_check
    mtlr 0
    cmpwi 12, 0
    bnelr
    b {MOBY_ANIM}

daze_tick:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x90(1)
    std 30, 0x70(1)
    std 27, 0x78(1)
    std 26, 0x80(1)
    addi 26, 31, {LURES}
    li 27, {LURE_COUNT}
dz_next:
    lwz 30, 0(26)
    cmpwi 30, 0
    beq dz_skip
    lis 11, {FRAME_COUNTER_HA}
    lwz 11, {FRAME_COUNTER_LO}(11)
    lwz 9, 8(26)                    # lured in the future: the level's frame count started again
    subf 9, 9, 11
    cmpwi 9, 0
    blt dz_free
    lwz 9, 0xc(26)
    cmpwi 9, 0
    beq dz_old
    subf 10, 11, 9
    cmpwi 10, 0
    ble dz_old
    lhz 9, 0xa6(30)                 # its moby went to another
    lhz 10, 4(26)
    cmpw 9, 10
    bne dz_free
    addi 3, 28, {FX_DAZE}
    bl puffs
    b dz_skip
dz_old:                             # lured long ago, and not stunned: the entry is free again
    lwz 9, 8(26)
    subf 9, 9, 11
    lwz 10, {FX_LURE_FRAMES}(28)
    lwz 8, {FX_STUN_COOLDOWN}(28)
    add 10, 10, 8
    cmplw 9, 10
    ble dz_skip
dz_free:
    li 9, 0
    stw 9, 0(26)
    stw 9, 8(26)
    stw 9, 0xc(26)
dz_skip:
    addi 26, 26, {LURE_SIZE}
    addi 27, 27, -1
    cmpwi 27, 0
    bgt dz_next
    ld 26, 0x80(1)
    ld 27, 0x78(1)
    ld 30, 0x70(1)
    addi 1, 1, 0x90
    ld 0, 0x10(1)
    mtlr 0
    blr
"""


def damage_part(name, flags, entry, back):
    return DAMAGE.replace("@NAME@", name).replace("@FLAGS@", flags).replace("@ENTRY@", entry).replace("@BACK@", back)


def options(ap):
    ap.add_argument("--xp-scale", type=float, default=1.0, help="multiplies the experience every weapon needs for level 2 (default 1)")
    ap.add_argument("--levelup-bolts", type=int, default=500, help="value of the bolts that burst out at a level-up (default 500, 0 for none)")
    ap.add_argument("--boost", type=float, default=BOOST, help=f"damage factor of a level 2 weapon without a gold version (default {BOOST:g})")


def hooks(args):
    return [Hook(KILL_HOOK, "xp_kill", KILL_HOOK_WORD), Hook(DECOY_HOOK, "decoy_seen", DECOY_HOOK_WORD),
            Hook(DRONE_HOOK, "drone_seen", DRONE_HOOK_WORD),
            *(Hook(site, "taunt_lure", LURE_HOOK_WORD) for site in LURE_HOOKS),
            Hook(MOBY_UPDATE_HOOK, "moby_update", MOBY_UPDATE_HOOK_WORD), Hook(MOBY_ANIM_HOOK, "moby_anim", MOBY_ANIM),
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


def xp_offsets():
    """Item id -> offset of the weapon's experience from AMMO."""
    places = [4 * item + half for item in XP_ITEMS for half in (0, 2)]
    if len(places) < len(XP_NEEDED):
        raise SystemExit("weaponlevels: more weapons than places for their experience")
    return dict(zip(sorted(XP_NEEDED, key=lambda item: (item in XP_LATER, item)), places))


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
    return [tuned(LEVELS), damage_part("damage", "12", "4", "DAMAGE_BACK"), damage_part("sweep_damage", "6", "8", "SWEEP_DAMAGE_BACK"),
            tuned(BAR), tuned(PERKS), FX, tuned(TAUNT)]


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
