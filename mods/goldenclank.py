"""Golden Clank: bought with all 40 gold bolts in the gold weapons room, and gold from then on.

With the weapon levels, the gold weapons come from experience, so the gold weapons rooms (Novalis,
level 1, and the Gemlik Base, level 13) sell Golden Clank instead: under the dome where the Gold
Devastator stood, Clank turns slowly, in gold; standing in front of it, Ratchet is told the price,
all 40 gold bolts, and with all of them Circle buys him. From then on Clank on Ratchet's back and
his Heli-, Thruster- and Hydro-Pack are gold, and L3 + R3 switch Giant Clank mode on and off:
Clank grows on Ratchet's back and Square, Circle and Triangle are his (the moves come next).

The room. Each gold weapon is a moby of its own above a pedestal, classes 0x5b0..0x5b9 (one per
weapon, in the order of the item ids at 0x811cb0; 0x5b2 is the Devastator's), with the update
0x339b70, which also runs the pedestals (class 0x130): it shows the prompt and sells the weapon
(the price, 4 gold bolts, is the prompt system's: 0x4d3870 with the level's prompt records). A
display whose gold version is owned goes to state 0xfd, which the moby loop neither updates nor
draws. The mod skips the update of the displays (PEDESTAL_HOOK) and runs them itself from the
frame hook: all of them in state 0xfd, but the Devastator's, which gets the model of Clank on
Ratchet's back (class 0x259, in every level), turns and is gold, until Golden Clank is bought.
Nothing animates it (its update is skipped), so it is held in a pose of that model (POSE); without
one the model is drawn in its bind pose, the head apart from the body.

Gold bolts are 80 flag bytes at 0xa0ca34 (4 per planet); GOLD_BOLT_COUNT counts the set ones (the
pause menu's "%d of 40"). Collecting is all there is to them: the game takes 4 off the count for
each gold weapon owned. Golden Clank wants all 40 and takes them all the same way; the purchase is
a word of the save (OWNED, beside the Taunter's experience in item 1's ammunition int, which no
weapon uses).

A moby's colour (+0x38) is set again every frame by the level's lighting, so the gold goes on at
the HUD's hook, the last thing in the frame's update.

L3 and R3 are the game's: pressed, L3 shows the HUD (0x16754c) and R3 the map (0x1673ec, with
Select: the mask 0x500); held, L3 aims finer on the guns Ratchet mans (classes 0x45, 0x2b1,
0x4da, 0x563, hero state 0x32). Both are read in the frame's update (GAMEPLAY_FRAME) before the
hero, so the chord is taken there, at its two calls (PAD_HOOKS), right after the pad is copied
in (0x11e2d4 copies the whole pad struct every frame, so clearing bits in it lasts one frame):
a first L3 or R3 is held back from the game for a few frames; if the other comes in that time
the mode is switched and the game sees neither, else it gets the press late. Not on a gun nor
in the states the game keeps the map from (0x1d, 0x72), and not before Golden Clank is bought.
While the mode is on, Square, Circle and Triangle are taken from every button word of the pad
and from its history of presses (PAD_WORDS, PAD_HISTORY) and kept in the state block for the moves.

Backpack Clank's scale (+0x2c) is set by the game only when he is created, so the mod sets it
every frame while he grows, is big or shrinks back. Its numbers are a block of writable data
(GIANT, see giant()), for tuning in a running game with tools/peek.py.

Giant Clank himself (class 0x1a3) is only in levels 15 and 18, so his model and textures are
embedded (from the player's RC1 data, rc2data.py) and installed once per boot as the Charge
Boots' are (mods/chargeboots/boots.py): memory from the top of the main heap (the model, then
its texture entries) and of the graphics heap (the pixels), the game's model fix-up, and the
mesh groups pointed at the entries. A moby shows him by being created as a backpack Clank
(class 0x259, in every level, no update of its own) and given his model; the moby loop animates
it (0xf98d8) and keeps its bounds (0xf31a8). For now one such moby stands next to Ratchet while
GIANT +0x94 is set (a test of the model, its textures and animations).
"""
import functools
import struct

from .game import *  # noqa: F401,F403
from .rc2 import Extract

NAME = "goldenclank"
TITLE = "Golden Clank"
ABOUT = ("The gold weapons rooms sell Golden Clank for all 40 gold bolts (the gold weapons come from the weapon levels); "
         "Clank and his packs are gold from then on.")

ROOMS = (1, 13)                    # Novalis, Gemlik Base: PLANET
PEDESTAL_HOOK = 0x339B70           # stdu r1, -0x80(r1): the top of the displays' and pedestals' update
PEDESTAL_HOOK_WORD = 0xF821FF81
PEDESTAL_BACK = PEDESTAL_HOOK + 4
DISPLAY_FIRST, DISPLAY_COUNT = 0x5B0, 10
SHOW_CLASS = 0x5B2                 # the Gold Devastator's display: the one Ratchet faces in the room
HIDDEN = 0xFD                      # a display's state when its gold weapon is owned
CLANK_CLASS = 0x259                # Clank on Ratchet's back
GOLD_BOLT_COUNT = 0x11B1B4         # () -> gold bolts collected
ALL_GOLD_BOLTS = 40
OWNED = 0x96C0B2                   # u16 of the save: 1 = Golden Clank is bought (ammunition array + 6)
HERO_KIND, HERO_CLANK_MOBY, HERO_PACK_MOBY = 0x20A4, 0x1184, 0x1180
CIRCLE = 0x20                      # PAD bit
BORROWED_TEXT = 0x5301             # "Gold Weapon purchase" (the table has it twice; weaponlevels borrows 0x5302)
MESSAGE_INDEX = 0x92
BUY_SOUND = 24                     # Ratchet's sound definition 24, the weapon levels' level-up sound
GOLD = 0x0C64B0                    # 00BBGGRR, the weapon levels' gold
DISPLAY_SCALE = 0.3
DISPLAY_LIFT = 0.0                 # added to the display's height
POSE = (1, 2, 1, 1, 0.4)           # frame, next frame, their animations, the blend between them: folded, eyes to the front
FRAME_POINTERS = 0xEF74C           # (r3 moby): +0x68/+0x6c from the animations and frames at +0x50..+0x53
SPIN = 0.02                        # rad a frame
RANGE = 3.5                        # how near Ratchet has to be to the display (x and y)
SHAKE = (30, 0.25)                 # frames, strength of the camera shake at the purchase
TEXT_BUY = b"Press \x11 to buy \x0cGolden Clank\x08 for all 40 \x0cGold Bolts\x08"   # \x11: Circle; \x0c..\x08: highlight
TEXT_COST = b"\x0cGolden Clank\x08 costs all 40 \x0cGold Bolts\x08. You have %d."
TEXT_GOT = b"You got \x0cGolden Clank\x08!"
TEXT_ROOM = 64                     # the formatted text's buffer
GAMEPLAY_FRAME = 0x166FB0          # the frame's update in play
PAD_HOOKS = (0xE14C4, 0xE1904)     # its two calls (bl GAMEPLAY_FRAME), each behind the pad's copy
L3_R3 = 0x600                      # PAD bits: L3 0x200, R3 0x400
MOVES = 0xB0                       # PAD bits: Triangle 0x10, Circle 0x20, Square 0x80
# The pad's button words: three sets of held, pressed, released and the frame before at +0xa0,
# +0xb0 and +0xc0 (the Quick Select also opens on a Triangle at +0xc4), and the presses of the
# last 30 frames at +0xe0 (newest at +0x8e, count at +0x90), which the wrench asks through
# 0x11dfe0(mask, frames, out) (so a Square shortly before still swings it).
PAD_WORDS_AT, PAD_WORDS = 0xA0, 12
PAD_HISTORY_AT, PAD_HISTORY = 0xE0, 30
FREE_STATES = (0x32, 0x1D, 0x72)   # hero states with the buttons left to the game: on a gun, and two the map skips
PUFF = 0x123390                    # the game's puff of glow (see mods/weaponlevels/fx.py)
PUFFS = ">3f4f2f2I2iI"             # a set of puffs, as in mods/weaponlevels/fx.py
# The switch: a burst of puffs from Clank, then gold smoke while he grows (or shrinks).
BURST = ((0.0, 0.0, 0.2), (0.0, 0.0, 0.0), 400000.0, 0.22, (0x3060E0FF, 0x2840D0FF), (30, 35), 30)
SMOKE = ((0.0, 0.0, 0.2), (0.0, 0.0, 0.1), 400000.0, 0.1, (0x0820C8FF, 0x0520B8FF), (30, 34), 2)
CHORD_FRAMES = 8                   # how long a first L3 or R3 waits for the other
GROW_FRAMES = 20
GIANT_SCALE = 1.0                  # backpack Clank in the mode, times his own scale (his parts come instead)
GIANT_SOUNDS = (BUY_SOUND + 1, BUY_SOUND + 1)   # on, off: Ratchet's sound definition + 1 (0 = none)
GIANT_SHAKE = (20, 0.2)            # frames, strength
GIANT_GLOW = (0x40B0FF, 20)        # Ratchet's colour (00BBGGRR) at the switch, frames
GIANT_MODEL_CLASS = 0x1A3          # Giant Clank (rc2data.GIANT_CLASS); the fix-up only compares it with 0x472
CARRIER_CLASS = 0x259              # what a moby showing him is created as
CLASS_INFO = 0x71D1F0              # model +0x2c of the game's models, filled at load
MODEL_FIXUP = 0xDBC38              # (r3 model, r4 = 0, r5 = 0, r6 class)
COPY = 0x50027C                    # (r3 dst, r4 src, r5 size)
MAIN_HEAP, GRAPHICS_HEAP = 0x90D7C8, 0x90D7EC   # bump allocators: +8 and +0xc the end
GCM_PTR = 0x8FA564                 # -> +0x4ac the graphics memory base
MOBY_SET_ANIM = 0xFDDC0            # (r3 moby, r4 animation, r5 = 0, r6 blend frames)
MOBY_DELETE = 0xEFB38              # (r3 moby)
DRAW_DISTANCE = 0x2000             # moby +0x32 (u16); with 0 the moby is never drawn
SKIP_UPDATE = 0x2                  # moby +0x34: left out of the moby loop's list (0xf959c); set on class 0x259
# A moby is in that list when +0x30 (its update distance from the camera, 0xff = any) allows it.
# His parts: each is a copy of the model's header and mesh header (the fixed-up pointers lead to
# the one model's bones, animations, vertices and textures) with an index buffer of its own,
# which has only the triangles of its bones (rc2data.giant_part). Bones: 0-8 hips to chest,
# 9-32 head, 33-52 left arm, 53-72 right arm, 73 on his back, 74-83 legs.
PARTS = (((74, 83),), ((33, 52),), ((53, 72),), ((33, 72),), ((0, 8), (73, 73)))
PART_LEGS, PART_LEFT_ARM, PART_RIGHT_ARM, PART_ARMS, PART_BODY = range(len(PARTS))
# The test moby: shown, its scale, where it stands from Ratchet (x, y, z), its animation, its
# turn, its model (0 the whole of him, 1 + a part).
TEST = (0, 0.15, (2.5, 0.0, 0.0), 0, 0.0, 0)
# His animations (set_state's for his states, NOTES.md): idle 0x5a, walk 0x5b, missiles 0x5f,
# punch 0x60 (9 or 10: left or right), bomb 0x61.
IDLE_ANIM, WALK_ANIM, MISSILE_ANIM, PUNCH_ANIMS, BOMB_ANIM = 0, 3, 8, (9, 10), 12
ANIM_BLEND = 4                     # frames an animation change blends over
# His legs under Ratchet in the mode: scale, where (forward, left, up from Ratchet, turned with
# him), turn, the speed (units a frame, hero +0x194; a run is about 0.09) from which they walk,
# and the walk animation's speed per unit a frame of his (moby +0x58, 1 = its own).
LEGS = (0.25, (0.0, 0.0, 0.0), 0.0, 0.01, 10.0)  # scale: hips at Ratchet's, "its good" (the user, 2026-10-19)
COS, SIN = 0x5E8078, 0x5E8128      # (f1 radians) -> f1
# Robot legs run faster (the user's wish): in the mode, the speed BUILD_VELOCITY makes the
# velocity of (hero +0x194, loaded once at VELOCITY_HOOK) is taken RUN times while Ratchet walks
# (hero state 2; jumps and the rest keep their own). Doubling STICK_TARGET's scale (f1) instead
# left his run at 5.7 units/s: the walk's target speed +0x190 does not come from it.
RUN = 2.0
WALK_STATE = 0x2
VELOCITY_HOOK = 0x9C1F4            # lfs f31, 0x194(r31) in BUILD_VELOCITY (r31 = hero); r11, r12, f0, cr0 free
VELOCITY_HOOK_WORD = 0xC3FF0194
VELOCITY_BACK = VELOCITY_HOOK + 4
# State block (game.py): +0x2a0 the display found this frame (0 = none), +0x2a4 the prompt is up,
# +0x2a8 the display's height as found; for tuning in a running game (0 = the built-in value):
# +0x2ac scale (float), +0x2b0 height above it (float), +0x2b4 turn a frame (float), +0x2b8 colour,
# +0x2bc/+0x2bd animation and frame of the pose, used when +0x2bf is not 0.
# Giant Clank mode: +0x2c0 on, +0x2c4 the L3/R3 held back, +0x2c8 frames they still wait,
# +0x2cc the moves' buttons pressed this frame, +0x2d0 frames of growing or shrinking left,
# +0x2d4 backpack Clank's own scale (0 = not seen yet), +0x2d8 the burst is due, +0x2dc frames
# of Ratchet's glow left.
# Giant Clank's model: +0x2e0 where it is installed (0 = not yet), +0x2e4 the frame counter a
# frame ago (it starts again with each level, and the mobys with it go). A moby showing him has a
# record of 0x10 bytes (gc_show): +0 the moby, +4 the model it was given, +8 its animation;
# +0x2f0 the test moby's, +0x300 the legs'.
S_DISPLAY, S_PROMPT, S_BASE_Z = 0x2A0, 0x2A4, 0x2A8
S_SCALE, S_LIFT, S_SPIN, S_COLOUR = 0x2AC, 0x2B0, 0x2B4, 0x2B8
S_POSE_ANIM, S_POSE_FRAME, S_POSE_ON = 0x2BC, 0x2BD, 0x2BF
S_MODE, S_CHORD, S_CHORD_LEFT, S_MOVES = 0x2C0, 0x2C4, 0x2C8, 0x2CC
S_GROW, S_BASE, S_BURST, S_GLOW = 0x2D0, 0x2D4, 0x2D8, 0x2DC
S_MODEL, S_FRAME, S_TEST_PART, S_LEGS = 0x2E0, 0x2E4, 0x2F0, 0x300
PART_RECORDS = (S_TEST_PART, S_LEGS)
# GIANT, the writable block: +0x00 BURST and +0x38 SMOKE (the layout PUFFS), +0x70 CHORD_FRAMES,
# +0x74 GROW_FRAMES, +0x78 GIANT_SCALE (float), +0x7c/+0x80 GIANT_SOUNDS, +0x84/+0x88 GIANT_SHAKE
# (frames, float), +0x8c/+0x90 GIANT_GLOW, +0x94 TEST: shown, scale (float), x, y, z (floats),
# animation, turn (float), model; +0xb4 LEGS: scale, forward, left, up, turn, walk from, walk
# speed (floats); +0xd0 RUN (float).
G_BURST, G_SMOKE, G_CHORD, G_GROW, G_SCALE = 0x00, 0x38, 0x70, 0x74, 0x78
G_SOUND_ON, G_SOUND_OFF, G_SHAKE_FRAMES, G_SHAKE, G_GLOW, G_GLOW_FRAMES = 0x7C, 0x80, 0x84, 0x88, 0x8C, 0x90
G_TEST, G_TEST_SCALE, G_TEST_AT, G_TEST_ANIM, G_TEST_TURN, G_TEST_MODEL = 0x94, 0x98, 0x9C, 0xA8, 0xAC, 0xB0
G_LEGS_SCALE, G_LEGS_AT, G_LEGS_TURN, G_WALK_FROM, G_WALK_RATE, G_RUN = 0xB4, 0xB8, 0xC4, 0xC8, 0xCC, 0xD0

# pedestal: jumped to from the top of the update (r3 = the moby; LR is the moby loop's).
# gc_frame: replaces bl HERO_MAIN; gc_tick(): the room, the prompt and the purchase.
# gc_say(r3 = a string): the borrowed text entry gets it, and it is shown.
# gc_hud: at the HUD's hook: the gold.
# gc_pad: replaces bl GAMEPLAY_FRAME; gc_input(): the chord and the moves' buttons.
# gc_switch(r31 = state block, r29 = GIANT): the mode was switched: sound, shake, glow, burst.
# gc_giant(): Clank's size, the burst and the smoke. gc_puffs(r3 = a set, r4 = a moby): its puffs.
# gc_velocity: jumped to from VELOCITY_HOOK.
CODE = """
pedestal:
    lhz 11, 0xa6(3)
    addi 11, 11, -{DISPLAY_FIRST}
    cmplwi 11, {DISPLAY_LAST}       # (unsigned: a class below DISPLAY_FIRST is above it too)
    blelr                           # a display: run by gc_tick
pedestal_game:
    stdu 1, -0x80(1)                # the displaced instruction
    b {PEDESTAL_BACK}

gc_frame:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    bl gc_tick
    bl gc_giant
    bl gc_parts
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
gc_frame_next:
    {CHAIN}

gc_tick:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0xd0(1)
    std 31, 0x70(1)
    std 30, 0x78(1)
    std 29, 0x80(1)
    std 28, 0x88(1)
    std 27, 0x90(1)
    std 26, 0x98(1)
    std 25, 0xa0(1)
    lis 31, {STATE_HA}
    addi 31, 31, {STATE_LO}
    lis 30, {HERO_HA}
    addi 30, 30, {HERO_LO}
    lis 25, {POOL_HA}
    addi 25, 25, {POOL_LO}
    li 29, 0                        # the display, if one is found
    lis 9, {PLANET_HA}
    lwz 9, {PLANET_LO}(9)
    cmpwi 9, {ROOM_A}
    beq gt_room
    cmpwi 9, {ROOM_B}
    bne gt_found
gt_room:
    lis 9, {OWNED_HA}
    lhz 28, {OWNED_LO}(9)
    lis 9, {MOBY_ARRAY_HA}
    lwz 27, {MOBY_ARRAY_LO}(9)
gt_scan:                            # every display goes out but the one for Golden Clank
    lbz 9, 0x20(27)
    cmpwi 9, 0xff
    beq gt_found
    lhz 9, 0xa6(27)
    addi 9, 9, -{DISPLAY_FIRST}
    cmplwi 9, {DISPLAY_LAST}
    bgt gt_next
    cmpwi 9, {SHOW_OFF}
    bne gt_hide
    cmpwi 28, 0
    bne gt_hide
    mr 29, 27
    b gt_next
gt_hide:
    li 9, {HIDDEN}
    stb 9, 0x20(27)
gt_next:
    addi 27, 27, 0x100
    b gt_scan
gt_found:
    lwz 9, {S_DISPLAY}(31)
    stw 29, {S_DISPLAY}(31)
    cmpwi 29, 0
    beq gt_away
    cmpw 9, 29
    beq gt_known
    lfs 0, 0x18(29)                 # a new display: its height as found
    stfs 0, {S_BASE_Z}(31)
gt_known:
    li 9, 1                         # drawn and animated (its update is skipped)
    stb 9, 0x20(29)
    lis 9, {CLASS_SLOT_MAP_HA}
    addi 9, 9, {CLASS_SLOT_MAP_LO}
    lbz 9, {CLANK_CLASS}(9)
    cmplwi 9, {MODEL_SLOTS}
    bge gt_model
    slwi 9, 9, 2
    lis 10, {MODEL_TABLE_HA}
    addi 10, 10, {MODEL_TABLE_LO}
    lwzx 10, 10, 9
    cmpwi 10, 0
    beq gt_model
    stw 10, 0x24(29)
    lis 9, {POSE_HI}                # the pose: +0x50/+0x51 two frames, +0x52/+0x53 their animation
    ori 9, 9, {POSE_LO}
    stw 9, 0x50(29)
    lbz 9, {S_POSE_ON}(31)
    cmpwi 9, 0
    beq gt_pose
    lbz 9, {S_POSE_ANIM}(31)
    stb 9, 0x52(29)
    stb 9, 0x53(29)
    lbz 9, {S_POSE_FRAME}(31)
    stb 9, 0x50(29)
    stb 9, 0x51(29)
gt_pose:
    lfs 0, {P_POSE_BLEND}(25)
    stfs 0, 0x54(29)
    lfs 0, {P_POSE_SPEED}(25)
    stfs 0, 0x58(29)
    lfs 0, {P_POSE_EASE}(25)
    stfs 0, 0x5c(29)
    mr 3, 29
    bl {FRAME_POINTERS}
gt_model:
    lfs 1, {P_SCALE}(25)
    lwz 9, {S_SCALE}(31)
    cmpwi 9, 0
    beq gt_scale
    lfs 1, {S_SCALE}(31)
gt_scale:
    stfs 1, 0x2c(29)
    lfs 1, {P_LIFT}(25)
    lwz 9, {S_LIFT}(31)
    cmpwi 9, 0
    beq gt_lift
    lfs 1, {S_LIFT}(31)
gt_lift:
    lfs 0, {S_BASE_Z}(31)
    fadds 0, 0, 1
    stfs 0, 0x18(29)
    lfs 1, {P_SPIN}(25)
    lwz 9, {S_SPIN}(31)
    cmpwi 9, 0
    beq gt_spin
    lfs 1, {S_SPIN}(31)
gt_spin:
    lfs 0, 0x48(29)
    fadds 0, 0, 1
    lfs 1, {P_TWO_PI}(25)
    fcmpu 0, 0, 1
    blt gt_angle
    fsubs 0, 0, 1
gt_angle:
    stfs 0, 0x48(29)
    lbz 9, {HERO_KIND}(30)          # Ratchet only
    cmpwi 9, 0
    bne gt_away
    lfs 0, 0x80(30)                 # near enough?
    lfs 1, 0x10(29)
    fsubs 0, 0, 1
    fmuls 0, 0, 0
    lfs 1, 0x84(30)
    lfs 2, 0x14(29)
    fsubs 1, 1, 2
    fmadds 0, 1, 1, 0
    lfs 1, {P_RANGE2}(25)
    fcmpu 0, 0, 1
    bge gt_away
    lis 26, {PAD_HA}                # Circle is the mod's here, not the weapon's
    addi 26, 26, {PAD_LO}
    lwz 27, 0xa4(26)
    lwz 9, 0xa0(26)
    rlwinm 9, 9, 0, {CIRCLE_CLEAR_MB}, {CIRCLE_CLEAR_ME}
    stw 9, 0xa0(26)
    rlwinm 9, 27, 0, {CIRCLE_CLEAR_MB}, {CIRCLE_CLEAR_ME}
    stw 9, 0xa4(26)
    bl {GOLD_BOLT_COUNT}
    mr 28, 3
    lwz 9, {S_PROMPT}(31)
    cmpwi 9, 0
    bne gt_shown
    li 9, 1
    stw 9, {S_PROMPT}(31)
    cmpwi 28, {ALL_GOLD_BOLTS}
    blt gt_cost
    lis 3, {TEXT_BUY_HA}
    addi 3, 3, {TEXT_BUY_LO}
    bl gc_say
    b gt_shown
gt_cost:
    lis 3, {TEXT_BUFFER_HA}
    addi 3, 3, {TEXT_BUFFER_LO}
    lis 4, {TEXT_COST_HA}
    addi 4, 4, {TEXT_COST_LO}
    mr 5, 28
    bl {SPRINTF}
    lis 3, {TEXT_BUFFER_HA}
    addi 3, 3, {TEXT_BUFFER_LO}
    bl gc_say
gt_shown:
    andi. 9, 27, {CIRCLE}
    beq gt_done
    cmpwi 28, {ALL_GOLD_BOLTS}
    blt gt_done
    li 9, 1                         # bought
    lis 10, {OWNED_HA}
    sth 9, {OWNED_LO}(10)
    lis 3, {TEXT_GOT_HA}
    addi 3, 3, {TEXT_GOT_LO}
    bl gc_say
    li 3, {BUY_SOUND}
    li 4, 0
    lwz 5, 0x2080(30)
    bl {PLAY_MODEL_SOUND}
    lis 9, {CAMERA_STATE_HA}
    addi 9, 9, {CAMERA_STATE_LO}
    lfs 0, {P_SHAKE}(25)
    stfs 0, 0x160(9)
    li 10, {SHAKE_FRAMES}
    stw 10, 0x168(9)
    stw 10, 0x16c(9)
    b gt_done
gt_away:                            # not near it (or no display): the prompt goes
    lwz 9, {S_PROMPT}(31)
    cmpwi 9, 0
    beq gt_done
    li 9, 0
    stw 9, {S_PROMPT}(31)
    bl {CANCEL_MESSAGE}
gt_done:
    ld 25, 0xa0(1)
    ld 26, 0x98(1)
    ld 27, 0x90(1)
    ld 28, 0x88(1)
    ld 29, 0x80(1)
    ld 30, 0x78(1)
    ld 31, 0x70(1)
    addi 1, 1, 0xd0
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_say:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lis 10, {TEXT_TABLE_HA}
    lwz 10, {TEXT_TABLE_LO}(10)
    lis 11, {TEXT_COUNT_HA}
    lwz 11, {TEXT_COUNT_LO}(11)
    cmpwi 11, 0
    ble say_out
    mtctr 11
say_find:
    lwz 12, 4(10)
    cmpwi 12, {BORROWED_TEXT}
    beq say_found
    addi 10, 10, 16
    bdnz say_find
    b say_out
say_found:
    stw 3, 0(10)
    li 3, {BORROWED_TEXT}
    li 4, {MESSAGE_INDEX}
    bl {SHOW_MESSAGE}
say_out:
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_hud:
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lis 12, {GOLD_HI}
    ori 12, 12, {GOLD_LO}
    lwz 9, {S_COLOUR}(11)
    cmpwi 9, 0
    beq gh_colour
    mr 12, 9
gh_colour:
    lis 9, {OWNED_HA}
    lhz 9, {OWNED_LO}(9)
    cmpwi 9, 0
    beq gh_display
    lis 10, {HERO_HA}
    addi 10, 10, {HERO_LO}
    lwz 9, {HERO_CLANK_MOBY}(10)
    cmpwi 9, 0
    beq gh_pack
    stw 12, 0x38(9)
gh_pack:
    lwz 9, {HERO_PACK_MOBY}(10)
    cmpwi 9, 0
    beq gh_glow
    stw 12, 0x38(9)
gh_glow:
    lwz 9, {S_GLOW}(11)             # Ratchet glows after a switch
    cmpwi 9, 0
    ble gh_display
    addi 9, 9, -1
    stw 9, {S_GLOW}(11)
    lwz 9, 0x2080(10)
    cmpwi 9, 0
    beq gh_display
    lis 8, {GIANT_HA}
    addi 8, 8, {GIANT_LO}
    lwz 8, {G_GLOW}(8)
    stw 8, 0x38(9)
gh_display:
    lwz 9, {S_DISPLAY}(11)
    cmpwi 9, 0
    beq gc_hud_next
    stw 12, 0x38(9)
gc_hud_next:
    {CHAIN}

gc_pad:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    bl gc_input
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
gc_pad_next:
    {CHAIN}

gc_input:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x90(1)
    std 31, 0x70(1)
    std 30, 0x78(1)
    std 29, 0x80(1)
    lis 31, {STATE_HA}
    addi 31, 31, {STATE_LO}
    lis 30, {PAD_HA}
    addi 30, 30, {PAD_LO}
    lis 29, {GIANT_HA}
    addi 29, 29, {GIANT_LO}
    li 9, 0
    stw 9, {S_MOVES}(31)
    lis 9, {OWNED_HA}
    lhz 9, {OWNED_LO}(9)
    cmpwi 9, 0
    beq gi_out                      # not bought: the buttons are the game's
    lis 10, {HERO_HA}
    addi 10, 10, {HERO_LO}
    lbz 9, {HERO_KIND}(10)
    cmpwi 9, 0
    bne gi_free
    lwz 9, 0x2084(10)
    cmpwi 9, {FREE_A}
    beq gi_free
    cmpwi 9, {FREE_B}
    beq gi_free
    cmpwi 9, {FREE_C}
    beq gi_free
    lwz 11, 0xa4(30)                # pressed this frame
    andi. 12, 11, {L3_R3}
    lwz 9, {S_CHORD}(31)
    or 12, 12, 9                    # with what waits
    cmpwi 12, {L3_R3}
    beq gi_switch
    cmpwi 12, 0
    beq gi_moves
    li 0, {L3_R3}
    andc 11, 11, 0                  # held back from the game
    stw 11, 0xa4(30)
    stw 12, {S_CHORD}(31)
    cmpwi 9, 0
    bne gi_wait
    lwz 9, {G_CHORD}(29)            # the first: it waits
    stw 9, {S_CHORD_LEFT}(31)
    b gi_moves
gi_wait:
    lwz 9, {S_CHORD_LEFT}(31)
    addi 9, 9, -1
    stw 9, {S_CHORD_LEFT}(31)
    cmpwi 9, 0
    bgt gi_moves
    or 11, 11, 12                   # the other did not come: the game gets it now
    stw 11, 0xa4(30)
    li 9, 0
    stw 9, {S_CHORD}(31)
    b gi_moves
gi_switch:
    li 0, {L3_R3}
    andc 11, 11, 0
    stw 11, 0xa4(30)
    li 9, 0
    stw 9, {S_CHORD}(31)
    lwz 9, {S_MODE}(31)
    xori 9, 9, 1
    stw 9, {S_MODE}(31)
    bl gc_switch
gi_moves:
    lwz 9, {S_MODE}(31)
    cmpwi 9, 0
    beq gi_out
    lwz 11, 0xa4(30)
    andi. 12, 11, {MOVES}
    stw 12, {S_MOVES}(31)
    li 0, {MOVES}
    li 12, {PAD_WORDS}              # every button word of the pad
    mtctr 12
    addi 12, 30, {PAD_WORDS_AT} - 4
gi_clear:
    lwzu 11, 4(12)
    andc 11, 11, 0
    stw 11, 0(12)
    bdnz gi_clear
    li 12, {PAD_HISTORY}            # and the presses of the last frames
    mtctr 12
    addi 12, 30, {PAD_HISTORY_AT} - 4
gi_history:
    lwzu 11, 4(12)
    andc 11, 11, 0
    stw 11, 0(12)
    bdnz gi_history
    b gi_out
gi_free:                            # on a gun and the like: what waits goes to the game
    lwz 9, {S_CHORD}(31)
    cmpwi 9, 0
    beq gi_out
    lwz 11, 0xa4(30)
    or 11, 11, 9
    stw 11, 0xa4(30)
    li 9, 0
    stw 9, {S_CHORD}(31)
gi_out:
    ld 29, 0x80(1)
    ld 30, 0x78(1)
    ld 31, 0x70(1)
    addi 1, 1, 0x90
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_switch:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lwz 9, {G_GROW}(29)
    stw 9, {S_GROW}(31)
    lwz 9, {G_GLOW_FRAMES}(29)
    stw 9, {S_GLOW}(31)
    li 9, 1
    stw 9, {S_BURST}(31)
    lis 9, {CAMERA_STATE_HA}
    addi 9, 9, {CAMERA_STATE_LO}
    lfs 0, {G_SHAKE}(29)
    stfs 0, 0x160(9)
    lwz 10, {G_SHAKE_FRAMES}(29)
    stw 10, 0x168(9)
    stw 10, 0x16c(9)
    lwz 3, {G_SOUND_ON}(29)
    lwz 9, {S_MODE}(31)
    cmpwi 9, 0
    bne gs_sound
    lwz 3, {G_SOUND_OFF}(29)
gs_sound:
    cmpwi 3, 0
    beq gs_out
    addi 3, 3, -1
    li 4, 0
    lis 10, {HERO_HA}
    addi 10, 10, {HERO_LO}
    lwz 5, 0x2080(10)
    bl {PLAY_MODEL_SOUND}
gs_out:
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_giant:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0xa0(1)
    std 31, 0x70(1)
    std 30, 0x78(1)
    std 29, 0x80(1)
    std 28, 0x88(1)
    lis 9, {OWNED_HA}
    lhz 9, {OWNED_LO}(9)
    cmpwi 9, 0
    beq gg_out
    lis 31, {STATE_HA}
    addi 31, 31, {STATE_LO}
    lis 30, {HERO_HA}
    addi 30, 30, {HERO_LO}
    lis 29, {GIANT_HA}
    addi 29, 29, {GIANT_LO}
    lbz 9, {HERO_KIND}(30)
    cmpwi 9, 0
    bne gg_out
    lwz 28, {HERO_CLANK_MOBY}(30)
    cmpwi 28, 0
    beq gg_out
    lwz 9, {S_BASE}(31)
    cmpwi 9, 0
    bne gg_size
    lwz 9, 0x2c(28)                 # his own scale, before the mod changes it
    stw 9, {S_BASE}(31)
gg_size:                            # t = how giant: 0 his own size, 1 GIANT_SCALE
    lwz 3, {S_GROW}(31)
    bl {INT_TO_FLOAT}
    stfs 1, 0x90(1)
    lwz 3, {G_GROW}(29)
    bl {INT_TO_FLOAT}
    lfs 2, 0x90(1)                  # frames of the change left
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    lfs 3, {P_ZERO}(9)
    lfs 4, {P_ONE}(9)
    lwz 10, {S_GROW}(31)
    cmpwi 10, 0
    ble gg_left
    fdivs 3, 2, 1                   # the part of the change left
gg_left:
    lwz 10, {S_MODE}(31)
    cmpwi 10, 0
    beq gg_t
    fsubs 3, 4, 3
gg_t:
    lfs 0, {G_SCALE}(29)
    fsubs 0, 0, 4
    fmadds 0, 0, 3, 4               # 1 + (GIANT_SCALE - 1) * t
    lfs 1, {S_BASE}(31)
    fmuls 0, 0, 1
    stfs 0, 0x2c(28)
    lwz 9, {S_BURST}(31)
    cmpwi 9, 0
    beq gg_smoke
    li 9, 0
    stw 9, {S_BURST}(31)
    addi 3, 29, {G_BURST}
    mr 4, 28
    bl gc_puffs
gg_smoke:
    lwz 9, {S_GROW}(31)
    cmpwi 9, 0
    ble gg_out
    addi 9, 9, -1
    stw 9, {S_GROW}(31)
    addi 3, 29, {G_SMOKE}
    mr 4, 28
    bl gc_puffs
gg_out:
    ld 28, 0x88(1)
    ld 29, 0x80(1)
    ld 30, 0x78(1)
    ld 31, 0x70(1)
    addi 1, 1, 0xa0
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_install:                         # Giant Clank's model, once
    lwz 3, {S_MODEL}(31)
    cmpwi 3, 0
    bnelr
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x90(1)
    std 30, 0x70(1)
    std 28, 0x78(1)
    std 27, 0x80(1)
    std 26, 0x88(1)
    lis 3, {MAIN_HEAP_HA}           # memory from the top of both heaps
    addi 3, 3, {MAIN_HEAP_LO}
    lwz 30, 8(3)
    addis 30, 30, -{MODEL_RESERVE_HI}
    stw 30, 8(3)
    stw 30, 0xc(3)                  # r30 = the model, its texture entries, the parts' headers and index buffers
    lis 3, {GRAPHICS_HEAP_HA}
    addi 3, 3, {GRAPHICS_HEAP_LO}
    lwz 28, 8(3)
    addis 28, 28, -{PIXELS_RESERVE_HI}
    stw 28, 8(3)
    stw 28, 0xc(3)                  # r28 = the pixels
    mr 3, 30
    lis 4, {GIANT_MODEL_HA}
    addi 4, 4, {GIANT_MODEL_LO}
    lis 5, {MODEL_SIZE_HI}
    ori 5, 5, {MODEL_SIZE_LO}
    bl {COPY}
    lis 3, {MODEL_SIZE_HI}
    ori 3, 3, {MODEL_SIZE_LO}
    add 3, 30, 3
    lis 4, {GIANT_TEXTURES_HA}
    addi 4, 4, {GIANT_TEXTURES_LO} + 8
    li 5, {ENTRIES_SIZE}
    bl {COPY}
    mr 3, 28
    lis 4, {GIANT_PIXELS_HA}
    addi 4, 4, {GIANT_PIXELS_LO}
    lis 5, {PIXELS_SIZE_HI}
    ori 5, 5, {PIXELS_SIZE_LO}
    bl {COPY}
    lis 3, {GCM_PTR_HA}             # an entry's +0 is relative to the graphics memory base
    lwz 3, {GCM_PTR_LO}(3)
    lwz 3, 0x4ac(3)
    subf 3, 3, 28
    lis 27, {MODEL_SIZE_HI}
    ori 27, 27, {MODEL_SIZE_LO}
    add 27, 30, 27                  # r27 = the entries
    li 4, {ENTRY_COUNT}
    mtctr 4
    mr 4, 27
gi_entry:
    lwz 5, 0(4)
    add 5, 5, 3
    stw 5, 0(4)
    addi 4, 4, 0x24
    bdnz gi_entry
    mr 3, 30                        # the game's own fix-up turns the offsets into pointers
    li 4, 0
    li 5, 0
    li 6, {GIANT_MODEL_CLASS}
    bl {MODEL_FIXUP}
    lwz 3, 0(30)                    # each mesh group gets its texture's entry
    lwz 3, 8(3)
    lis 4, {GIANT_TEXTURES_HA}
    addi 4, 4, {GIANT_TEXTURES_LO}
    lbz 5, 0(4)
    mtctr 5
gi_group:
    lbzu 5, 1(4)
    mulli 5, 5, 0x24
    add 5, 27, 5
    stw 5, 0(3)
    addi 3, 3, 0x10
    bdnz gi_group
    lis 3, {CLASS_INFO_HI}
    ori 3, 3, {CLASS_INFO_LO}
    stw 3, 0x2c(30)
    lis 26, {IBS_AT_HI}             # the parts' index buffers
    ori 26, 26, {IBS_AT_LO}
    add 26, 30, 26                  # r26 = the first
    mr 3, 26
    lis 4, {GIANT_PARTS_HA}
    addi 4, 4, {GIANT_PARTS_LO}
    lis 5, {PARTS_SIZE_HI}
    ori 5, 5, {PARTS_SIZE_LO}
    bl {COPY}
    lis 28, {HEADERS_AT_HI}
    ori 28, 28, {HEADERS_AT_LO}
    add 28, 30, 28                  # r28 = the first part's header
    li 27, {PART_COUNT}
gi_part:                            # each part: the model's header and mesh with its own index buffer
    mr 3, 28
    mr 4, 30
    li 5, {HEADER}
    bl {COPY}
    lwz 3, 0(30)
    subf 3, 30, 3
    add 3, 28, 3
    stw 3, 0(28)                    # its own mesh
    lis 4, {GCM_PTR_HA}             # the index buffer as an offset from the graphics I/O base, as the fix-up leaves them
    lwz 4, {GCM_PTR_LO}(4)
    lwz 4, 0x4a8(4)
    subf 4, 4, 26
    stw 4, 0x14(3)
    lis 4, {IB_STRIDE_HI}
    ori 4, 4, {IB_STRIDE_LO}
    add 26, 26, 4
    addi 28, 28, {HEADER}
    addic. 27, 27, -1
    bne gi_part
    stw 30, {S_MODEL}(31)
    ld 26, 0x88(1)
    ld 27, 0x80(1)
    ld 28, 0x78(1)
    ld 30, 0x70(1)
    addi 1, 1, 0x90
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_parts:                           # the mobys showing his parts
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0xb0(1)
    std 31, 0x70(1)
    std 30, 0x78(1)
    std 29, 0x80(1)
    std 28, 0x88(1)
    std 27, 0x90(1)
    lis 9, {OWNED_HA}
    lhz 9, {OWNED_LO}(9)
    cmpwi 9, 0
    beq gq_out
    lis 31, {STATE_HA}
    addi 31, 31, {STATE_LO}
    lis 30, {HERO_HA}
    addi 30, 30, {HERO_LO}
    lis 29, {GIANT_HA}
    addi 29, 29, {GIANT_LO}
    lis 9, {FRAME_COUNTER_HA}       # a new level: the mobys went with the old one
    lwz 9, {FRAME_COUNTER_LO}(9)
    lwz 10, {S_FRAME}(31)
    stw 9, {S_FRAME}(31)
    cmplw 9, 10
    bge gq_test
    li 9, 0
@RECORDS_FORGET@
gq_test:
    li 28, 0                        # the model to show, 0 = none
    lwz 9, {G_TEST}(29)
    cmpwi 9, 0
    beq gq_test_show
    bl gc_install
    lwz 3, {G_TEST_MODEL}(29)
    bl gc_model
    mr 28, 3
gq_test_show:
    addi 3, 31, {S_TEST_PART}
    mr 4, 28
    bl gc_show
    mr. 27, 3
    beq gq_legs
    addi 3, 31, {S_TEST_PART}
    lwz 4, {G_TEST_ANIM}(29)
    bl gc_anim
    lfs 0, 0x80(30)
    lfs 1, {G_TEST_AT}(29)
    fadds 0, 0, 1
    stfs 0, 0x10(27)
    lfs 0, 0x84(30)
    lfs 1, {G_TEST_AT} + 4(29)
    fadds 0, 0, 1
    stfs 0, 0x14(27)
    lfs 0, 0x88(30)
    lfs 1, {G_TEST_AT} + 8(29)
    fadds 0, 0, 1
    stfs 0, 0x18(27)
    lfs 0, {G_TEST_SCALE}(29)
    stfs 0, 0x2c(27)
    lfs 0, {G_TEST_TURN}(29)
    stfs 0, 0x48(27)
gq_legs:                            # his legs under Ratchet while the mode is on and he is on foot
    li 28, 0
    lwz 9, {S_MODE}(31)
    cmpwi 9, 0
    beq gq_legs_show
    lbz 9, {HERO_KIND}(30)
    cmpwi 9, 0
    bne gq_legs_show
    lwz 9, 0x2084(30)
    cmpwi 9, {FREE_A}
    beq gq_legs_show
    cmpwi 9, {FREE_B}
    beq gq_legs_show
    cmpwi 9, {FREE_C}
    beq gq_legs_show
    bl gc_install
    li 3, 1 + {PART_LEGS}
    bl gc_model
    mr 28, 3
gq_legs_show:
    addi 3, 31, {S_LEGS}
    mr 4, 28
    bl gc_show
    mr. 27, 3
    beq gq_out
    lfs 1, 0x194(30)                # walking, at his speed, or standing
    lfs 2, {G_WALK_FROM}(29)
    li 4, {IDLE_ANIM}
    fcmpu 0, 1, 2
    blt gq_legs_anim
    li 4, {WALK_ANIM}
gq_legs_anim:
    addi 3, 31, {S_LEGS}
    bl gc_anim
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    lfs 0, {P_ONE}(9)
    lwz 10, {S_LEGS} + 8(31)
    cmpwi 10, {WALK_ANIM}
    bne gq_legs_rate
    lfs 1, 0x194(30)
    lfs 2, {G_WALK_RATE}(29)
    fmuls 0, 1, 2
    lfs 2, {G_RUN}(29)              # he goes RUN times as fast as +0x194 says
    fmuls 0, 0, 2
gq_legs_rate:
    stfs 0, 0x58(27)
    lfs 1, 0x98(30)                 # turned with him
    bl {COS}
    stfs 1, 0xa0(1)
    lfs 1, 0x98(30)
    bl {SIN}
    lfs 2, 0xa0(1)                  # f2 = cos, f1 = sin
    lfs 3, {G_LEGS_AT}(29)          # forward
    lfs 4, {G_LEGS_AT} + 4(29)      # left
    lfs 0, 0x80(30)
    fmadds 0, 3, 2, 0
    fnmsubs 0, 4, 1, 0
    stfs 0, 0x10(27)
    lfs 0, 0x84(30)
    fmadds 0, 3, 1, 0
    fmadds 0, 4, 2, 0
    stfs 0, 0x14(27)
    lfs 0, 0x88(30)
    lfs 3, {G_LEGS_AT} + 8(29)
    fadds 0, 0, 3
    stfs 0, 0x18(27)
    lfs 0, {G_LEGS_SCALE}(29)
    stfs 0, 0x2c(27)
    lfs 0, 0x98(30)
    lfs 1, {G_LEGS_TURN}(29)
    fadds 0, 0, 1
    stfs 0, 0x48(27)
gq_out:
    ld 27, 0x90(1)
    ld 28, 0x88(1)
    ld 29, 0x80(1)
    ld 30, 0x78(1)
    ld 31, 0x70(1)
    addi 1, 1, 0xb0
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_model:                           # (r3 = 0 the whole of him, 1 + a part; r31 = state block) -> r3 = its model, 0 = none yet
    lwz 4, {S_MODEL}(31)
    cmpwi 4, 0
    beq gm_none
    cmpwi 3, 0
    beq gm_whole
    addi 3, 3, -1
    mulli 3, 3, {HEADER}
    add 4, 4, 3
    lis 3, {HEADERS_AT_HI}
    ori 3, 3, {HEADERS_AT_LO}
gm_whole:
    add 3, 4, 3                     # (r3 = 0 here for the whole of him)
    blr
gm_none:
    li 3, 0
    blr

gc_show:                            # (r3 = a record, r4 = the model to show, 0 = none) -> r3 = the moby, 0 = none
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x90(1)
    std 31, 0x70(1)
    std 30, 0x78(1)
    std 29, 0x80(1)
    mr 31, 3
    mr 30, 4
    lwz 29, 0(31)
    cmpwi 29, 0
    beq gs_new
    lwz 9, 0x24(29)                 # still ours?
    lwz 10, 4(31)
    cmpw 9, 10
    beq gs_ours
    li 29, 0
    stw 29, 0(31)
gs_new:
    cmpwi 30, 0
    beq gs_done
    li 3, {CARRIER_CLASS}
    bl {SPAWN}
    mr. 29, 3
    stw 29, 0(31)
    beq gs_done
    li 9, 0xff                      # updated at any distance
    stb 9, 0x30(29)
    li 9, 1                         # and drawn (+0x32: 0 = never)
    stb 9, 0x31(29)
    li 9, {DRAW_DISTANCE}
    sth 9, 0x32(29)
    lhz 9, 0x34(29)                 # and by the moby loop (backpack Clank is moved by the hero code)
    rlwinm 9, 9, 0, {NOT_SKIP_MB}, {NOT_SKIP_ME}
    sth 9, 0x34(29)
    li 9, -1
    stw 9, 8(31)
    b gs_model
gs_ours:
    cmpwi 30, 0
    bne gs_model
    li 9, 0                         # not wanted any more
    stw 9, 0(31)
    mr 3, 29
    li 29, 0
    bl {MOBY_DELETE}
    b gs_done
gs_model:
    stw 30, 0x24(29)
    stw 30, 4(31)
gs_done:
    mr 3, 29
    ld 29, 0x80(1)
    ld 30, 0x78(1)
    ld 31, 0x70(1)
    addi 1, 1, 0x90
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_anim:                            # (r3 = a record with a moby, r4 = the animation): set when it changes
    lwz 5, 8(3)
    cmpw 5, 4
    beqlr
    stw 4, 8(3)
    lwz 3, 0(3)
    li 5, 0
    li 6, {ANIM_BLEND}
    b {MOBY_SET_ANIM}

gc_velocity:
    lfs 31, 0x194(31)               # the displaced instruction: his speed
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, {S_MODE}(11)
    cmpwi 12, 0
    beq gv_back
    lbz 12, {HERO_KIND}(31)
    cmpwi 12, 0
    bne gv_back
    lwz 12, 0x2084(31)
    cmpwi 12, {WALK_STATE}
    bne gv_back
    lis 11, {GIANT_HA}
    addi 11, 11, {GIANT_LO}
    lfs 0, {G_RUN}(11)
    fmuls 31, 31, 0
gv_back:
    b {VELOCITY_BACK}

gc_puffs:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0xb0(1)
    std 28, 0x98(1)
    std 27, 0xa0(1)
    std 26, 0xa8(1)
    mr 28, 3
    mr 26, 4
    lwz 27, 0x34(28)
gp_next:
    cmpwi 27, 0
    ble gp_out
    lfs 0, 0x10(26)
    lfs 1, 0(28)
    fadds 0, 0, 1
    stfs 0, 0x80(1)
    lfs 0, 0x14(26)
    lfs 1, 4(28)
    fadds 0, 0, 1
    stfs 0, 0x84(1)
    lfs 0, 0x18(26)
    lfs 1, 8(28)
    fadds 0, 0, 1
    stfs 0, 0x88(1)
    lfs 0, 0x1c(26)
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
    b gp_next
gp_out:
    ld 26, 0xa8(1)
    ld 27, 0xa0(1)
    ld 28, 0x98(1)
    addi 1, 1, 0xb0
    ld 0, 0x10(1)
    mtlr 0
    blr
"""


def hooks(args):
    return [Hook(PEDESTAL_HOOK, "pedestal", PEDESTAL_HOOK_WORD, jump=True),
            *(Hook(site, "gc_frame", HERO_MAIN, chain=True) for site in FRAME_HOOKS),
            Hook(HUD_HOOK, "gc_hud", HUD_HOOK_WORD, chain=True),
            *(Hook(site, "gc_pad", GAMEPLAY_FRAME, chain=True) for site in PAD_HOOKS),
            Hook(VELOCITY_HOOK, "gc_velocity", VELOCITY_HOOK_WORD, jump=True)]


def data(args):
    def texts(vaddr):
        return TEXT_BUY + b"\0" + TEXT_COST + b"\0" + TEXT_GOT + b"\0" + bytes(TEXT_ROOM)
    def giant(vaddr):
        def puffs(at, rise, f1, scatter, colours, life, count):
            return struct.pack(PUFFS, *at, *rise, 0.0, f1, scatter, *colours, *life, count)

        shown, scale, at, anim, turn, part = TEST
        legs_scale, legs_at, legs_turn, walk_from, walk_rate = LEGS
        block = puffs(*BURST) + puffs(*SMOKE) + struct.pack(">2if2Iif2i", CHORD_FRAMES, GROW_FRAMES, GIANT_SCALE,
                                                              *GIANT_SOUNDS, *GIANT_SHAKE, *GIANT_GLOW)
        assert len(block) == G_TEST
        block += struct.pack(">if3fifi", shown, scale, *at, anim, turn, part)
        assert len(block) == G_LEGS_SCALE
        block += struct.pack(">f3f3f", legs_scale, *legs_at, legs_turn, walk_from, walk_rate)
        assert len(block) == G_RUN
        return block + struct.pack(">f", RUN)

    def index_buffers(vaddr):
        pieces = []
        for part in part_data():
            pieces += [part, bytes(-len(part) % 0x10)]
        return pieces
    model, textures, pixels = giant_data()
    return [("rw", "texts", texts), ("rw", "giant", giant),
            ("rw2", "giant_model", lambda vaddr: [model]), ("rw2", "giant_textures", lambda vaddr: [textures]),
            ("rw2", "giant_pixels", lambda vaddr: [pixels]), ("rw2", "giant_parts", index_buffers)]


@functools.cache
def giant_data():
    """Giant Clank's model, texture block (rc2data.giant_textures) and pixels, from RC1's data."""
    return Extract("giant_model"), Extract("giant_textures"), Extract("giant_pixels")


@functools.cache
def part_data():
    """The parts' index buffers (rc2data.giant_part), in the order of PARTS."""
    return tuple(Extract("giant_part", [list(r) for r in ranges]) for ranges in PARTS)


def main_heap_layout():
    """Where things go in the memory taken from the main heap -> dict of template fields."""
    model, textures, pixels = giant_data()
    entries = (len(textures) - 8) // 0x24
    mesh = struct.unpack_from(">I", model.data, 0)[0]
    header = struct.unpack_from(">I", model.data, mesh + 0x10)[0]    # up to the vertex buffer: the model's header and mesh
    assert mesh + 0x20 <= header and header % 0x10 == 0 and len(model) % 0x10 == 0
    stride = len(part_data()[0]) + -len(part_data()[0]) % 0x10
    headers_at = len(model) + entries * 0x24
    headers_at += -headers_at % 0x10
    ibs_at = headers_at + len(PARTS) * header
    ibs_at += -ibs_at % 0x80
    parts_size = len(PARTS) * stride
    return dict(ENTRY_COUNT=entries, ENTRIES_SIZE=entries * 0x24, HEADER=header, PART_COUNT=len(PARTS),
                HEADERS_AT_HI=headers_at >> 16, HEADERS_AT_LO=headers_at & 0xFFFF, IBS_AT_HI=ibs_at >> 16,
                IBS_AT_LO=ibs_at & 0xFFFF, IB_STRIDE_HI=stride >> 16, IB_STRIDE_LO=stride & 0xFFFF,
                PARTS_SIZE_HI=parts_size >> 16, PARTS_SIZE_LO=parts_size & 0xFFFF,
                MODEL_RESERVE_HI=reserve(ibs_at + parts_size))


def reserve(size):
    """Heap memory for size bytes, in the 64 KB steps addis takes."""
    return (size + 0xFFFF) >> 16


def pool(args):
    return dict(SCALE=DISPLAY_SCALE, LIFT=DISPLAY_LIFT, SPIN=SPIN, TWO_PI=6.283185307179586,
                RANGE2=RANGE * RANGE, SHAKE=SHAKE[1], POSE_BLEND=POSE[4], POSE_SPEED=1.0, POSE_EASE=0.1,
                ZERO=0.0, ONE=1.0)


def parts(args):
    forget = "\n".join(f"    stw 9, {record:#x}(31)" for record in PART_RECORDS)    # r9 = 0: the mobys are gone
    return [CODE.replace("@RECORDS_FORGET@", forget)]


def fields(args, addr):
    at = addr["texts"]
    cost = at + len(TEXT_BUY) + 1
    got = cost + len(TEXT_COST) + 1
    buffer = got + len(TEXT_GOT) + 1
    bit = 31 - (CIRCLE.bit_length() - 1)        # rlwinm keeps bits mb..me (big-endian numbering): all but CIRCLE
    model, textures, pixels = giant_data()
    giant = dict(**pair("GIANT_MODEL", addr["giant_model"]), **pair("GIANT_TEXTURES", addr["giant_textures"]),
                 **pair("GIANT_PIXELS", addr["giant_pixels"]), **pair("GIANT_PARTS", addr["giant_parts"]),
                 MODEL_SIZE_HI=len(model) >> 16, MODEL_SIZE_LO=len(model) & 0xFFFF,
                 PIXELS_SIZE_HI=len(pixels) >> 16, PIXELS_SIZE_LO=len(pixels) & 0xFFFF, **main_heap_layout(),
                 PIXELS_RESERVE_HI=reserve(len(pixels)), CLASS_INFO_HI=CLASS_INFO >> 16, CLASS_INFO_LO=CLASS_INFO & 0xFFFF)
    skip = 31 - (SKIP_UPDATE.bit_length() - 1)   # rlwinm keeps bits mb..me (big-endian numbering): all but SKIP_UPDATE
    giant.update(NOT_SKIP_MB=(skip + 1) % 32, NOT_SKIP_ME=(skip - 1) % 32)
    return dict(**giant, **pair("GIANT", addr["giant"]), FREE_A=FREE_STATES[0], FREE_B=FREE_STATES[1], FREE_C=FREE_STATES[2],
                **pair("TEXT_BUY", at), **pair("TEXT_COST", cost), **pair("TEXT_GOT", got), **pair("TEXT_BUFFER", buffer),
                ROOM_A=ROOMS[0], ROOM_B=ROOMS[1], DISPLAY_LAST=DISPLAY_COUNT - 1, SHOW_OFF=SHOW_CLASS - DISPLAY_FIRST,
                POSE_HI=POSE[0] << 8 | POSE[1], POSE_LO=POSE[2] << 8 | POSE[3],
                GOLD_HI=GOLD >> 16, GOLD_LO=GOLD & 0xFFFF, SHAKE_FRAMES=SHAKE[0],
                CIRCLE_CLEAR_MB=(bit + 1) % 32, CIRCLE_CLEAR_ME=(bit - 1) % 32)
