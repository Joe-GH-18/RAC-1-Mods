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
import math
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
# A moby's colour (+0x38) is the level's light on it (00BBGGRR, set every frame; 0x292929 by day on
# Novalis), so a fixed gold there was a light of its own: Clank and the parts glowed the same in a
# dark room as in the sun (the user: "Why does the golden clank look so weird with the lighting").
# The gold is the light Ratchet stands in (his moby's +0x38) times GOLD_TINT, per channel (red,
# green, blue, in 256ths, at most 255); compared live on Clank, 1.37/0.78/0.09 was brass, 2.7/1.56/0.2
# bright gold.
GOLD_TINT = (563, 320, 38)
DISPLAY_SCALE = 0.3
DISPLAY_LIFT = 0.0                 # added to the display's height
POSE = (1, 2, 1, 1, 0.4)           # frame, next frame, their animations, the blend between them: folded, eyes to the front
FRAME_POINTERS = 0xEF74C           # (r3 moby): +0x68/+0x6c from the animations and frames at +0x50..+0x53
SPIN = 0.02                        # rad a frame
RANGE = 3.5                        # how near Ratchet has to be to the display (x and y)
SHAKE = (30, 0.25)                 # frames, strength of the camera shake at the purchase
TEXT_BUY = b"Press \x12 to buy \x0cGolden Clank\x08 for all 40 \x0cGold Bolts\x08"   # \x0c..\x08: highlight
# The buttons' signs in a text (shown live): 0x10 Cross, 0x11 Circle, 0x12 Triangle, 0x13 Square, 0x14 L1,
# 0x15 R1, 0x16 L2, 0x17 R2, 0x18 and 0x19 the left and the right stick.
TEXT_COST = b"\x0cGolden Clank\x08 costs all 40 \x0cGold Bolts\x08. You have %d."
TEXT_GOT = b"You got \x0cGolden Clank\x08!"
TEXT_HINT = b"Press \x18 + \x19 to switch \x0cGiant Clank\x08 on and off"
# The purchase is a scene (the user: "I want to have the obtaining of golden clank cooler, like a
# custom animation, how it is done with the gold weapon buying"; "make purchase triangle button").
# The game's own for a gold weapon (0x16b650, from the pedestals' update 0x339b70 as one is bought,
# seen live through a test trigger) cuts to a low close-up of Ratchet in a dimmed room, no HUD, and
# he shows the weapon off in his hand for ~4 s (hero state 0x64, 0xa10708 = 5 while it runs, then
# 0xe8aa4(0, -1)): it is made for a weapon in his hand, so Golden Clank's is the mod's own, in the
# same manner. Triangle buys (gc_input takes it from the pad while the prompt is up: the Quick
# Select opens on it otherwise) and gc_scene runs SCENE_END frames (60 a second) with the pad taken
# (buttons, the left stick at +0x8/+0xc and +0x48/+0x4c): the camera on keys (SCENE_CAM: frame,
# distance, pitch (rad, + looks up), turn (from behind him), up, the share of the way to the
# display it looks at; through VIEW, eased between keys), the display on keys (SCENE_SHOW: frame,
# lift, size, spin a frame; never 0, which is "its own"), a ring of gold sparks about it
# (SCENE_RING, frames RING), a stream of them into Clank on his back (SCENE_STREAM, frames STREAM,
# each spark crossing in SCENE_STREAM_LIFE frames), then at BOND_AT Golden Clank is his: a burst at
# Clank (SCENE_BOND), the purchase's sound and shake and the switch's glow, the text at TEXT, at
# GIANT Giant Clank mode comes on (the legs grow under him) and at PUNCH he punches; at the end the
# game's camera is back and the hint (TEXT_HINT) shows.
# Ratchet turns his back to the display as the scene starts (the user: "when i get golden clank
# ratchet should be facing away from the glass container, the camera is also stuck, so it can not
# be properly seen"; SCENE_TURN, through atan2 of the way from the display to him): the stream
# flies into Clank on his back, and the camera keys, which turn from behind him, keep to the room
# (from -1.6, beside him, round to -3.9, ahead of him; behind him, 0, is the dome).
SCENE_TURN = 1
SCENE_CAM = ((0, 4.2, -0.25, -3.59, 1.3, 0.75), (80, 3.0, -0.10, -3.89, 1.5, 0.95),
             (125, 4.2, -0.15, -1.6, 1.2, 0.45), (150, 3.2, -0.05, -2.5, 1.1, 0.0),
             (190, 4.6, 0.12, -3.1, 1.7, 0.0), (260, 5.6, 0.08, -3.4, 2.0, 0.0), (320, 6.0, 0.05, -3.6, 2.0, 0.0))
SCENE_SHOW = ((0, 0.001, 0.3, 0.02), (70, 0.6, 0.33, 0.25), (100, 0.75, 0.33, 0.45), (128, 0.9, 0.01, 0.6))
# The sparks barely go by their velocity (a stream given (Clank - display) / frames piled up into a
# bright ball at the display, seen at 60 fps): the stream is a comet instead, its sparks made each
# frame at a point that goes from the display to Clank over the stream's frames, arched up by
# SCENE_ARC at the middle. With the alpha of the level-up's burst (0x30) and 40 of them the sparks
# were solid yellow clouds this near the camera: fainter, fewer and shorter.
# The ring was a haze in the display's glass dome whatever the puffs' numbers: it is sparks
# instead, the Thruster-Pack's flame's (SPARK, which go by their velocity), flying out from the
# display: SCENE_RING: at, rise, scatter (each axis, at random both ways), the two colours, frames
# from, to, how many a frame, f1 (the distance squared they are drawn to).
SCENE_RING = ((0.0, 0.0, 0.4), (0.0, 0.0, 0.025), 0.055, (0x4F30C8FF, 0x1FFFFFFF), (20, 35), 4, 10000.0)
SCENE_BOND_SPARKS = ((0.0, 0.0, 0.3), (0.0, 0.0, 0.03), 0.12, (0x4F30C8FF, 0x1FFFFFFF), (25, 40), 40, 10000.0)   # and at the bond
SCENE_STREAM = ((0.0, 0.0, 0.3), (0.0, 0.0, 0.0), 400000.0, 0.04, (0x1870F0FF, 0x1050E0FF), (16, 20), 2)
SCENE_BOND = ((0.0, 0.0, 0.3), (0.0, 0.0, 0.0), 400000.0, 0.16, (0x2060E0FF, 0x1840D0FF), (16, 20), 16)
SCENE_ARC = 0.8
SCENE_RING_FROM, SCENE_RING_TO, SCENE_STREAM_FROM, SCENE_STREAM_TO = 5, 100, 95, 128
SCENE_BOND_AT, SCENE_TEXT, SCENE_GIANT, SCENE_PUNCH, SCENE_END = 130, 140, 155, 215, 320
SCENE_CAM_KEYS, SCENE_SHOW_KEYS = len(SCENE_CAM), len(SCENE_SHOW)
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
# 9-32 head, 33-52 left arm, 53-72 right arm, 73 on his back, 74-83 legs. The legs come with
# his pelvis (bone 4, its two hip balls; 6 above it is the dark waist band, 8 the torso): without
# it they were two blocks apart with Ratchet over the gap between them, with it he stands on
# Giant Clank's hips (the pelvis' top is 0.95 up, Ratchet's feet LIFT).
# The last two: the pistons on his forearms (47-48, 67-68; long and thin, on the light texture that
# takes the gold as the legs do), as Clank's legs down to the gold hips (STRUTS). (His upper arms
# were tried first: dark metal, brown in gold, and their shoulder balls with them.) They draw
# tubes in place of the pistons now (TUBES), the arms' (ARM_PISTONS), and a last part on the
# left piston's bone draws the column Clank stands on the legs with.
PARTS = (((4, 4), (74, 83)), ((33, 52),), ((53, 72),), ((33, 72),), ((0, 8), (73, 73)), ((47, 47),), ((67, 67),), ((47, 47),))
PART_LEGS, PART_LEFT_ARM, PART_RIGHT_ARM, PART_ARMS, PART_BODY, PART_STRUT_L, PART_STRUT_R, PART_COLUMN = range(len(PARTS))
# One more part, a ball: the pelvis' left joint (bone 4, all of it beyond y = 1.8) is a hemisphere
# of radius 0.577, its inner half inside the pelvis; rc2data.giant_ball makes it whole about the
# centre of its base, with a vertex buffer of its own (his, the ball's vertices first). Its mobys
# are given an animation of his at its first frame, held (BALL_ANIM; with no animation at all
# they were drawn black, unlit): bone 4 stays about where it is in the bind pose.
BALL = (4, 1.8)
PART_BALL = len(PARTS)
# Clank is joined to the legs (the user's wish: "growing segments connecting clank and the giant
# clank parts, so it is not floating"): a chain of balls from backpack Clank to the legs' hips
# while they are out, grown out from him over the frames of 1 / step and pulled back in when they
# go. (The punch has Clank's own arm instead, PUNCH_ARM.) CHAINS: the balls in a
# chain (up to CHAIN_MAX), their scale at Clank and at the part ("increase scale of the ball, the
# nearer it gets to the giant clank parts", the user; 0.25 is his own joints' size there), the
# grow step a frame. The chain: from and to, as forward, left, up from Ratchet, turned with him;
# "from" is on the lifted Ratchet (LIFT is added).
CHAIN_MAX = 6
# Since the legs have his pelvis and Ratchet stands on it, nothing floats: the legs' chain is off
# (count 0; it looked a tail behind his legs in any colour), kept for trying in a running game.
# Each chain has its count in its record; the balls' scale (CHAINS) is the same for all, times how
# far the chain is grown.
CHAINS = (0.06, 0.28, 1 / 6)
# The connection comes out first, then the arm (the user: "first the connection piece should come
# out and then the giant clank arm"): a part's growth starts ARM_DELAY frames into its move, while
# the chains (and the pistons with them) take 1 / CHAINS[2] = 6 frames from its start; the part
# goes before them at the end (they go back once it is gone). Before that it is ARM_LEAST of its
# size (never 0).
ARM_DELAY, ARM_LEAST = 5, 0.02
# The arms' hubs float beside Clank (the user: "the arm distance was good previous, it just needed
# a connecting piece between it so it does not float in the air"; then "small on clank and then
# gradually grow towards the giant clank arm like a connection"): a chain of balls from Clank's side
# into the hub of each arm out, small at Clank and growing (CHAINS), each side's own (the left's here,
# the right's mirrored), shown while a move has that arm out (MOVE_TABLE: balls) and grown with
# it. Its dark joint texture is made light where the ball samples it (rc2data._lift), so it takes
# the gold as his parts do. ARM_CHAIN: count, from, to (to's height is from Ratchet's feet, without
# LIFT, as the legs' chain wanted it).
ARM_CHAIN = (0, (-0.45, 0.1, 0.75), (-0.4, 0.45, 1.85))   # tried live 2026-10-21 (count 5; now 0: ARM_PISTONS)
# The balls looked like beads beside his panels, discs and pistons; the user chose a gold piston
# instead, the struts' own (so Clank is joined to legs and arms by one kind of part): ARM_PISTONS,
# the right's and the left's (as STRUTS), each laid out as STRUTS (where it stands) and STRUT_JOINTS (the
# piston's bone, turn, scale, place), shown while its arm's chain is grown (they keep growing
# and shrinking, with no balls) and scaled by how far. On: 1, 2 = always and full (for tuning).
# Tried live 2026-10-21: turned 120 degrees (level, thin at Clank's side, into the hub), 0.8 thick
# (0.55 read as flat blades), the struts' places but 0.22 up.
ARM_PISTONS = (1, ((0.3, 0.1, -2.03, 0.22, 0.0), (47, (0.8660254, 0.0, 0.0, 0.5), (0.8, 0.9, 0.8), (209.6, 718.0, 286.9))),
                  ((0.3, -0.15, 1.95, 0.22, 0.0), (67, (-0.8660254, 0.0, 0.0, 0.5), (0.8, 0.9, 0.8), (209.6, -718.0, 286.9))))
# They grew with their moby's scale, which shrinks a moby towards its model's origin (down at
# Giant Clank's feet) and leaves the joint's place as it is: half grown, they hung down by the
# gold legs and far out (the user: "the appear animation of the tubes should come from clank and
# not a random place in the screen"). Now the moby keeps its scale and the joint's scale is taken
# times how far grown (g), with its place moved by (1 - g) times P_GROW, so that the tube's end at
# Clank stays where it is: TUBE_ROOT, that end (the piston's elbow end, t = 0 of the tube) from
# the bone's pivot, in model units (from his bind matrices: pivot (0.703, 8.867, 9.181), the rod's
# middle x 0.362, z 9.173, its inner end |y| 7.680; the right's y mirrored), turned and scaled as
# the joint is and times 1024 * the moby's scale (the units of a joint's place, as STRUT_JOINTS'
# bind places). Tried live 2026-10-21 at g = 0.3: both stubs at Clank's sides.
TUBE_ROOT = (-0.3415, -1.1876, -0.0075)


def piston_grow(place, joint):
    """P_GROW of an ARM_PISTONS entry: turn * (scale x TUBE_ROOT) * 1024 * the moby's scale."""
    bone, (qx, qy, qz, qw), scale, _ = joint
    x, y, z = (s * r for s, r in zip(scale, TUBE_ROOT[:1] + (TUBE_ROOT[1] * (1 if bone == 47 else -1),) + TUBE_ROOT[2:]))
    tx, ty, tz = 2 * (qy * z - qz * y), 2 * (qz * x - qx * z), 2 * (qx * y - qy * x)   # v + w t + q x t
    turned = (x + qw * tx + qy * tz - qz * ty, y + qw * ty + qz * tx - qx * tz, z + qw * tz + qx * ty - qy * tx)
    return tuple(v * 1024 * place[0] for v in turned)
BALL_COLOUR = GOLD
# His parts are gold as Clank is (their grey did not go with him): the colour of every moby
# showing him (gc_show), from PART_COLOUR; his light grey takes the tint well.
PART_COLOUR = GOLD
BALL_ANIM = 0                      # his idle
CHAIN_LEGS = (0, (-0.38, 0.0, 0.3), (-0.42, 0.0, 0.98))  # Clank's lower back -> the pelvis' back, behind Ratchet's legs
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
LEGS = (0.25, (0.0, 0.0, 0.0), 0.0, 0.01, 10.0)  # scale and place: "its good" (the user, 2026-10-19); 1 forward,
                                                  # under his feet from behind, was "way worse"
# Ratchet hovers on the legs (the user's wish): while they are out, his moby and the mobys drawn
# with him (what he holds, his boots, the pack with backpack Clank, ...) are drawn LIFT higher. That is done at the HUD's hook, the last thing before the frame is drawn (and in
# a function's epilogue: no volatile register is live there); the game sets those mobys'
# positions (+0x10) again every frame. The parts are placed there again too, at where he ended
# the frame (placed before his update, they were a frame behind him). (Hanging the legs behind
# him and turned with Clank was a misreading of that wish and is not wanted.)
LIFT = 1.18                        # "he needs to be higher" (the user; 0.3 at first), tried live; at 1.1 his
                                   # boots sank a sole deep into the pelvis' top (the user: "I don't want
                                   # ratchets feet to intersect with giant clanks foot")
# The mobys drawn with him are those 0x7d478 flags with his: two at the start of each of seven
# entries of 0x50 bytes from hero +0x1090 (the four equipment slots of 0x85b30 among them, their
# item at +0x28) and one more of the pack at +0x118c. (The rest of an entry is not mobys: taking
# its words +0x08..+0x14 for them crashed the game on a pack's 0x129e at +0x1194.)
ATTACHED, ATTACHED_SIZE, ATTACHED_COUNT = 0x1090, 0x50, 7
PACK_PART = 0x118C
# The camera backs off while his legs are out ("bit further out, maybe 7.5", the user): the
# current camera's (CAMERA_STATE +0x180) data (+0x70) holds at +0x15c the distance it keeps
# behind Ratchet (4.64 here), which the game eases back towards its own every frame (written
# once, it was back in about a second). At the end of each frame the mod moves it ZOOM_EASE of
# the way towards ZOOM, so the camera starts each frame there; with the legs gone it leaves it,
# and the game brings its own back. (The 4.64 at 0x71d7b0 is only a default for cameras being
# set up, 0x38b94: written there it did nothing; a test seemed to say so only while he ran,
# when the camera trails further anyway.)
# In a jump the camera stays 2 above the ground (+0x160 of its data, eased back to that by the game
# as the distance is); with the high jump Ratchet went 3.5 above it and out of the picture ("it
# should follow ratchet when high jumping you cannot see a thing"). In a jump in the mode the mod
# eases it CAM_JUMP[2] of the way a frame towards CAM_JUMP[0] + CAM_JUMP[1] times his height above
# the ground (hero +0x2d8); after it the game brings its own back.
# The camera's height counts from where he left the ground, not from the ground under him: over a
# drop the ground is far below or none at all (+0x2d8 reads 0), and the camera climbed 2 + 0.9 x
# the drop (the user: "the camera going so far on top of the character"; read live after a jump off
# a ledge of level 14: him at 36, the camera at 68). So his height is taken over the last height he
# stood at (kept at G_CAM_BASE while not in a jump or a hover), never below 0, at most CAM_JUMP[3].
CAMERA_DATA, CAMERA_DISTANCE, CAMERA_HEIGHT = 0x70, 0x15C, 0x160
CAM_JUMP = (2.0, 0.9, 0.3, 8.0)
HERO_GROUND = 0x2D8
ZOOM, ZOOM_EASE = 7.5, 0.08
# A view for looking at the parts (the user: "look also from top perspective, how the tubes
# align"; the game's camera never looks down on him): while VIEW is on, at the end of each frame
# the camera (CAMERA_STATE: place +0x140, rows +0x350: the view axis, left, up) is put DISTANCE
# from a point UP above Ratchet's feet, looking at it from his facing plus a turn and pitched down
# by an angle (kept as its cosine and sine). Off in the build; switched on with tools/peek.py.
# VIEW: on, distance, pitch (rad, down), turn (rad), up.
VIEW = (0, 6.0, 1.45, 0.0, 1.8)
# Ratchet stands still on the legs, Clank does the walking (the user's wish): at the end of the
# frame his moby's animation fields (+0x50..+0x7f) are kept aside and he is given the frame of
# STILL (animation, frame; 0 0 = his idle's first), whose frame pointers FRAME_POINTERS fills;
# before the next frame (gc_input) the kept fields go back, as the animation step 0x8bc30 goes on
# from them (its state machine reads +0x50..+0x54).
STILL = (1, 0, 0)                  # on, animation, frame
# Held so, he still moved: the game turns his head and spine (looking about: bones 2, 7, 18) and
# swings his tail (104, 106, 108, 110) with joint manipulators on his moby (+0x64), which act on
# top of any frame (the user: "fix the animations, so ratchet does not idle move"). While STILL
# holds him, gc_still gives those of the bones in STILL_JOINTS the turn (quaternion) beside them,
# each frame after the game's update. (Switching them off live, +1 = 0, froze the game.)
STILL_JOINTS = ((2, (0.0, 0.0, 0.0, 1.0)), (7, (0.0, 0.0, 0.0, 1.0)), (18, (0.0, 0.0, 0.0, 1.0)),
                (104, (0.0, 0.0, 0.0, 1.0)), (106, (0.0, 0.0, 0.0, 1.0)), (108, (0.0, 0.0, 0.0, 1.0)),
                (110, (0.0, 0.0, 0.0, 1.0)))
# The mobys on him (his boots, the wrench or gun, ...) take their poses from his skeleton in the
# equipment update (EQUIP_UPDATE, called by the hero's frame 0x954c8 after hero_main; 0x91090
# builds an item's pose from his moby's frames): "ratchets boots wrench etc are still moving
# although his model is still", so the still frame is put on him before that call as well
# (EQUIP_HOOK), after his own update has gone on from his real animation.
EQUIP_HOOK, EQUIP_UPDATE = 0x95890, 0x92834
# His boots (hero +0x10e0, +0x10e4: mobys of class 0xc3, the Grindboots or the Charge Boots, no
# update of their own) still walked with his hidden skeleton (the user: "also not his second
# skeleton"; the hero's code gives them matrices from his foot joints of the real animation). While
# the legs are out, gc_boot_seat puts them each frame where they are on the still Ratchet:
# BOOT_SEAT for the left and the right, read live from a standing Ratchet in the mode (2026-10-21)
# in his own frame (his facing, hero +0x98, taken out): the place (forward, left, up from hero
# +0x80), the matrix rows (+0xc0, +0xd0, +0xe0) and the euler (+0x40; the last one plus his facing).
# Their heights are at LIFT BOOT_SEAT_LIFT, and go up and down with LIFT.
BOOT_SEAT = (((0.0522, 0.0608, 1.3601), (0.9903, -0.1199, -0.0699, 0.1308, 0.975, 0.1797, 0.0466, -0.1872, 0.9812), (0.0, 0.07, -0.1205)),
             ((0.0235, -0.122, 1.3497), (0.9366, -0.248, -0.2474, 0.2348, 0.9686, -0.0819, 0.26, 0.0186, 0.9654), (0.0, 0.25, -0.2588)))
BOOT_SEAT_LIFT = 1.1
HERO_BOOTS = 0x10E0
# The rest on him still walked with his hidden skeleton (the user: "there are still animation
# when I move Ratchet ... clank is moving like ratchet is walking"; read live: Clank bobbed 0.08
# up and down and 0.09 forward walking, the wrench in his hand turned by up to 3 rad): the hero's
# frame fills a cache of his joints' matrices (hero +0xac0: joints 0-6, 0x1d, 0x1e, by 0xf1364)
# right before the equipment update, from the real animation, and the mobys on him are placed
# from that cache. After the still frame is put on him (gc_equip), the mod has the game fill it
# again (JOINT_CACHE, its own function for the same nine joints). And Clank and the pack are put
# at one place on him (SEAT_AT: on, forward, left, up from his feet, LIFT added; read live from a
# standing Ratchet in the mode, 2026-10-21) as their turn is (CLANK_SEAT).
JOINT_CACHE = 0x92958              # (r3 moby, 0 = the hero's): the joints' matrices at hero +0xac0
# Ratchet's joint effects (footstep splashes and the like, chosen by the ground: 0x8ec40, 0x8e170,
# 0x8dd38 right after EQUIP_UPDATE): 0xf0854(moby, joint) takes one of FX_SLOT_COUNT slots of 0x40
# bytes at FX_SLOTS and links it into his moby's +0x60 list (next at +0x1c); the handles are kept
# at hero +0xd00..+0xd10, and 0xf0900(moby, &handle) unlinks and frees one. Once (after Ratchet died
# and came back while filming the moves) a handle outlived the list (the slot still in use, the list
# empty): the unlink then read 0x1c and the game froze. gc_fx_guard drops a handle that is not in
# his list any more and frees its slot, every frame before they run.
FX_SLOTS, FX_SLOT_COUNT, FX_HANDLE, FX_HANDLE_END = 0xA2C440, 6, 0xD00, 0xD14
SEAT_AT = (1, (-0.066, -0.016, 0.733))
ANIM_FIELDS, ANIM_FIELDS_SIZE = 0x50, 0x30
# Those fields hold two list heads besides the animation: the joint effects (+0x60) and the joint
# manipulators (+0x64, next at +8). Put back as they were kept, they undid what the game had done
# to the lists meanwhile: after a death the respawn links his manipulators again, and the kept head
# closed the list into a ring that the moby loop (0xf3618) walked for ever (the user: "when i die,
# the games seems to crash or softlock"; read live: his 16 manipulators, the last one's next the
# first; and so, most likely, the joint effects' empty list of the freeze above). They are kept
# live when the fields go back (LIST_HEADS).
LIST_HEADS = (0x60, 0x64)
COS, SIN = 0x5E8078, 0x5E8128      # (f1 radians) -> f1
# The moves, Square, Circle and Triangle in the mode: each grows one of his parts out of Clank,
# plays its animation, goes over to his idle and shrinks back into Clank (the punch first, then
# the user: "please also add the missiles and the bomb now, so i can test all 3"). The fist first
# came out of Clank's arm as the user had it: "clanks arm are already on his model, maybe rotate
# them, then scale them and once they have sufficient size, replace with giant clank fists,
# scaling from small to big, out of the spots of his arms"; then "the growing of clanks arm look
# bad, but it growing out of clank looks good", so his arm is only hidden while the part is out.
# Clank's arms are in the pack's model (class 0x25f, hero +0x1180; his own, 0x259, has none, and no
# legs, only feet): bones 17 (across his shoulders) -> 18, 19, 20 (the hand), fingers 21-26 to his
# left, 27-35 the same to his right. Facing backwards on Ratchet, his right arm (27) is on
# Ratchet's left, by the giant left arm. A part's bone of his is hidden by a joint manipulator
# (moby +0x64 list, 0x40 bytes 16-aligned: {+0 joint, +1 on, +3 1, +4 0x70000000 + 0x40 * bone,
# +8 next, +0xc weight against the animation, +0x10 rotation (quaternion), +0x20 scale (0: the
# bone and all below it are gone), +0x30 place}). (0xf0ea8(moby, joint, manipulator) adds one,
# finding the bone through the model's joint list (+0x1c); the pack's model has an empty one, and
# it read a null there: the mod links it in itself.)
# A move's frames f = 1..F: the part grows from nothing over B frames, plays its animation until
# "idle", then his idle ("can the animation of the punch maybe go to the giant clank idle hand
# animation and then shrink again?"), and shrinks over its last B; its "anchor" (the part's point
# at scale 1, times his model's 0.75) is held to the "spot" on Clank all the while. On the action
# frame it does its move. Places tried live 2026-10-20 from the back and the side: the punch is his
# swing out to the side, so its arm was turned a quarter to go ahead (no more: PUNCH_POSE). (His punch animations 9 and 10 have 13 frames, his missiles' 8 9, his
# bomb's 12 7, his idle 0 23; at speed 1 the punch took the 24 frames the fist was out first, "it
# ends to quickly".)
# The punch ended "so abruptly": it held its last pose until frame 30 and then went to the idle
# over 4 frames; now the idle follows at once, blended over "blend" frames, and the part shrinks
# over "shrink" frames. While a move's "repeat" button is held, it plays again from its action
# frame when it gets to "idle" (the user: "if I hold the missile button it should continue shooting").
# (It went back to B + ARM_DELAY, which the count after it made one frame past the missiles' action
# frame: holding Circle shot one volley, the user: "it is not shooting multiple rockets, just one is
# shot". The part has to be fully grown by the action frame: asserted below MOVE_TABLE.)
# MOVE_TABLE: the part (1 + PARTS index, -1 none), its animation, sided (1: part, animation and Clank's bone
# with the side, 0 left 1 right, taken in turn; left and the anchor's y mirrored), F, the action
# frame, idle from, B (to grow), Clank's bones hidden (left, right; -1 none), its scale, the spot
# (forward, left, up from the lifted Ratchet), the anchor (x, y, z), its turn, its animation's
# speed, repeat (a PAD bit, 0 = none), blend, shrink, the joint pinned to the spot (-1 none: the anchor
# is; a sided move takes the next joint for the right), the arms' balls (ARM_CHAIN: 0 none, 1 the
# move's side, 2 both).
# A move's part is pinned by one of its joints to its spot on Clank (the user: "fix backpack clank
# being physical connected to the legs/arms while punching and shooting"): his animations move
# the shoulders far from where they are at rest, so a fixed anchor left the arm hanging off by
# itself. Each frame JOINT_POSITION gives the joint's place in the part's pose, and the part is
# moved so that it is on the spot. His joint list (model +0x1c: {count, entries}, an entry {u16
# bones, the bones from +4, root first, the joint last}) has no shoulder; the parts get a list of
# their own (G_JOINT_LIST) with his seven and PIN_JOINTS after them: the left shoulder (33), the
# right (53), the chest (8). (Pinning the punch by the upper arm, 35/55, kept its hub on Clank but
# brought the arm too near him; the user wanted the shoulder's distance and a connecting piece
# instead: ARM_CHAIN.)
PIN_JOINTS = (tuple(range(9)) + (33,), tuple(range(9)) + (53,), tuple(range(9)), tuple(range(5)))
OWN_JOINTS = 7
PIN_SHOULDER, PIN_CHEST, PIN_PELVIS = OWN_JOINTS, OWN_JOINTS + 2, OWN_JOINTS + 3   # (the pelvis: RIDE)
# His shoulders are far wider than Clank: with both arms out (the missiles) they stood apart, high
# beside Ratchet's head. That part gets a skeleton of its own (his bone data, model +0x18, copied
# at install to G_ARMS_BONES) with the shoulders (33, 53: their place on the chest, y in model
# units, 1.83 his own) moved in to ARMS_SHOULDERS, so that both hubs sit at Clank.
ARMS_SHOULDERS = (33, 53, 1.3)     # 0 first; 1.3 (2026-10-21) for the tubes between Clank and the hubs, as in the mock-ups
BONES = 84
# Seen from straight above (VIEW, 2026-10-21) the missiles' arms stood askew, the right one
# further back (his missile animation turns his chest): turned 0.25, both launchers and hubs are
# level beside Clank.
MOVE_TABLE = (
    (1 + PART_LEFT_ARM, PUNCH_ANIMS[0], 1, 45, 15, 99, 5, (27, 18), 0.25,    # Square: a fist, its shoulder
     (-0.5, 0.45, 0.18), (0.015, 2.27, 6.19), 0.0, 0.0, 0, 12, 21, PIN_SHOULDER, 1),  # hub out from Clank's side (0.2 first);
    (1 + PART_ARMS, MISSILE_ANIM, 0, 40, 10, 22, 5, (17, 17), 0.2,          # posed (PUNCH_POSE). Circle: both arms, the
     (-0.35, 0.0, 0.45), (0.015, 0.0, 6.19), 0.25, 0.8, 0x20, 10, 10, PIN_CHEST, 2),   # missiles, Clank between the hubs
    (-1, BOMB_ANIM, 0, 72, 45, 72, 6, (-1, -1), 0.25,                       # Triangle: the bomb (no part:
     (-0.3, 0.0, 0.8), (-0.28, 0.0, 5.6), 0.0, 0.8, 0, 10, 10, -1, 0),       # "remove also the torso")
)
assert all(move[4] >= move[6] + ARM_DELAY for move in MOVE_TABLE if move[13])   # a repeat's action: the part grown
MOVE_BUTTONS = (0x80, 0x20, 0x10)  # PAD bits: Square, Circle, Triangle
SQUARE, TRIANGLE = MOVE_BUTTONS[0], MOVE_BUTTONS[2]
# The punch: a sphere ahead of Ratchet gets a damage descriptor as the Walloper's punch makes one
# (0xb10b0: DAMAGE_DESC with the hero moby, flags 0x30000, then +0xc = its push, +0x18 = 0,
# +0x19 = 3, +0x1a = the weapon's class, here his) and COLLECT, which hurts what is in it and
# breaks crates. PUNCH: the sphere's distance ahead and height, its radius, the damage.
PUNCH = ((1.6, 0.9), 1.4, 10.0)
# The punch carries Ratchet a little forward (the user: "a punch should launch the player a small
# bit forward, like its done with giant clank"; his punch state 0x60 sets no speed, his animations
# carry him): from its frame LUNGE[0] to LUNGE[1] the speed BUILD_VELOCITY makes the velocity of
# gets LUNGE[2] (units a frame) added, whatever his state.
# Since the wind-up (PUNCH_POSE) it goes in the strike's frames only, the same ~1 unit in 5 frames.
LUNGE = (11, 15, 0.2)
# Standing, his state code sets his velocity to nothing (BUILD_VELOCITY is not called), so the
# lunge goes in where the hero is moved with his velocity, after his state code (LUNGE_HOOK, in
# 0x8a2b8, called by hero_main; r30 = the hero, r11, r12, f0..f2 free): his facing (his moby's
# first row) times the speed is added to the velocity, standing or walking only (in the air the
# velocity is kept from frame to frame and would build up).
LUNGE_HOOK, LUNGE_HOOK_WORD = 0x8A2F4, 0xC3FE0080   # lfs f31, 0x80(r30)
LUNGE_BACK = LUNGE_HOOK + 4
# His punch animations are hooks: from behind his shoulder the fist swings out to the side, ahead
# at frame 3 and on across his front. The arm was turned a quarter for it (which made the end of
# the swing go ahead), and his idle followed and let the fist drop to hang before it was gone (the
# user: "the punch animation is still weird"). Now the arm is not turned, and the punch is posed
# from its frame (gc_punch_pose; the part's own animation stands still, speed 0): its animation's
# frame goes from 0 up to PEAK (the fist straight ahead beside him) over RISE frames, stays there
# HOLD frames and goes back to 0 over BACK frames, the fist drawn back while the part shrinks into
# Clank (its shrink is BACK). PUNCH_POSE: on, RISE, PEAK (a frame of the animation, between two
# blended), HOLD, BACK (floats but on). Frames 0 to 11.9 stepped live from above (VIEW), 2026-10-21.
# All of it 1.5 times as long since 2026-10-22 (the user: "the punch is a bit too fast"; the
# move's frames, grow and shrink, its hit frame and LUNGE with it, the lunge's length kept).
# Then a wind-up and a fast strike in the same length (the user chose it: "do 1-4"; even speed read
# as a push): the fist stays drawn back (frame 0) for WIND frames while the part grows, goes to PEAK
# in STRIKE frames (the hit frame is their end, the move's action 12), holds, and eases back.
# PUNCH_POSE: on, WIND, STRIKE, PEAK, HOLD, BACK.
PUNCH_POSE = (1, 10.0, 5.0, 3.2, 9.0, 21.0)   # (the wind-up 10: the piston, then the arm, ARM_DELAY)
# His body in it (gc_dance, put on by gc_clank_seat as the throw's is): Clank and the pack turn
# away from the punching arm over the wind-up (eased) and lean back, snap round past ahead and lean
# forward over the strike, and ease back with the fist. At the hit frame gold bursts from the
# punch's sphere (PUNCH_BURST) and the camera kicks; when the punch hurt something (COLLECT's
# count) harder, and the move stands still HITSTOP frames, the fist out (a hit-stop of the punch
# only: the game runs on). PUNCH_TWIST: on, turn at the wind-up, turn at the strike (rad, the
# side's way), lean at the wind-up, lean at the strike (+ = top back), the kick (strength, frames),
# the kick on a hit (strength, frames), HITSTOP. The burst 0.6 above the sphere: at the fist.
PUNCH_TWIST = (1, 0.35, 0.3, 0.12, -0.2, 0.04, 6, 0.1, 10, 6)
PUNCH_BURST = ((0.0, 0.0, 0.6), (0.0, 0.0, 0.005), 400000.0, 0.05, (0x1460E0FF, 0x1040D0FF), (6, 8), 2)   # very small (the user)
PUNCH_LAST = 12                    # the last frame of his punch animations 9 and 10 (13 frames)
# The missiles: his own (state 0x5f, 0xb664c): from his joints 3 and 4 (the forearms' ends; the
# arms part shows his model, so the joint list is his), 1.4 ahead of them along his facing,
# MISSILE_SPAWN(hero moby, position, yaw, 0, 0.5, yaw, 0, 0) once each. MISSILES: how far ahead
# here (1.4 at his size); MISSILE_SIZE scales the spawned missile (0x2c, set only there). The
# missile is a moby of class 0x100, only in his levels (15, 18): its model is taken from the player's RC1 data as his is, installed once (gc_install), and the class
# registered in every level that has not got it (gc_register, as 0xdc0ec does it without the
# model fix-up).
# The bomb: his own (state 0x61, 0xb64b8): BOMB_SPAWN(position as a vector in r5:r6), one at a
# time; class 0x5f3 has no model even in his levels (offset 0), it is registered with none. He
# throws it from 3 ahead and 5 up; BOMB_AT: ahead and up from Ratchet here. Its update (0xec6f0)
# deletes it at once unless the hero kind is 2 (him), and only does its work then: at both of its
# checks (BOMB_KIND_HOOKS, cmpwi r3, 2 with r3 = the kind) Ratchet in the mode counts as him too.
# His bomb is blue; Ratchet's is gold ("the blue bomb should be golden fitting the motto"). Its
# update makes the colours of its four effects (BOMB_COLOUR_HOOKS: the calls, the register with
# the colour 0xAABBGGRR, a second one or 0) from random channels, blue the strongest (0x3f..0x7f,
# green 0x2f..0x3f, red low); in the mode each colour becomes gold from its blue b: red b, green
# 3/4 b, blue 1/4 b. 0x121a40 takes the channels one by one (r4 red, r5 green, r6 blue).
BOMB_COLOUR_HOOKS = ((0xEC9B4, 0x129B00, 3, 0), (0xED0E4, 0x127EA8, 5, 0), (0xED1A4, 0x124E10, 5, 6))
BOMB_CHANNELS_HOOK, BOMB_CHANNELS = 0xECBF8, 0x121A40
BOMB_COLOUR_0, BOMB_COLOUR_1, BOMB_COLOUR_2 = (function for _, function, _, _ in BOMB_COLOUR_HOOKS)
# The bomb has a cooldown of BOMB_COOLDOWN frames from a throw (the user: "give it a cooldown of 10
# seconds"), and while it is ready Clank's eyes glow gold ("clanks eyes are golden glowing, when
# the bomb is ready"; a puff at each eye was "just floating orb, I meant backpack clanks eyes").
# His model (0x259) draws his eyes as mesh group 1, from a corner of the one texture of all of him
# (u 0..0.12, v 0.85..0.98); rc2data.clank_gold_eyes is that texture with its blocks' colours made
# gold. It is installed with the rest (gc_install), and group 1's texture (EYE_GROUP of the mesh's
# groups, +0 the entry) is pointed at it while the bomb is ready and back at the level's otherwise.
BOMB_COOLDOWN = 600
EYE_GROUP = 1
# Clank throws the bomb (the user: "add a cool animation for the golden bomb that clank does"):
# he and the pack (his arms) rise off Ratchet's back, swell and wind up a spin while gold sparks
# gather on him (DANCE_GLOW, a set a frame), leaning back; at the throw (the move's action frame,
# CHARGE) the bomb goes, gold bursts from him (DANCE_BURST), the camera kicks, and he snaps
# forward a size bigger, then sinks back into his seat over BACK frames. gc_dance works his spin,
# rise, lean and size out from the move's frame; gc_clank_seat puts them on him. BOMB_DANCE: on,
# CHARGE, BACK (frames), rise, turns of the spin, lean while charging (rad, + = his top back), lean
# at the throw, swell while charging, size at the throw (both + 1), the camera kick (strength,
# frames). Charging: s = smoothstep(f / CHARGE), the spin goes as (f / CHARGE)^2 (fastest at the
# throw, facing ahead again); after it r = 1 - smoothstep((f - CHARGE) / BACK) eases each back.
BOMB_DANCE = (1, 45.0, 27.0, 0.54, 1.0, 0.5, -0.8, 0.25, 0.4, 0.12, 12)
DANCE_GLOW = ((0.0, 0.0, 0.35), (0.0, 0.0, 0.02), 400000.0, 0.12, (0x1860E0FF, 0x1440D0FF), (8, 10), 1)
DANCE_BURST = ((0.0, 0.0, 0.35), (0.0, 0.0, 0.0), 400000.0, 0.25, (0x2060E0FF, 0x1840D0FF), (12, 16), 6)
# The jump's shockwave: his own (state 0x5e, its landing at 0xc71c0..0xc73e8): as he lands the
# camera shakes (CAMERA_STATE +0x160 strength, +0x168 frames: 0.15, 30) and the frame after,
# SHOCK_SPAWN(hero moby, position as a vector, frames, f1 size, f2 growth, f3 damage) puts a ring
# of class 0x593 on the ground under him (z 0.2 up). The ring's update (0xeb3c0) needs nothing of
# him: it grows by twice the growth a frame (scale = 2 * size * the model's at first), fades out
# and is gone after its frames, and every frame hurts what is within half its scale plus the
# growth (0x105870, flags 0x30000, from the hero moby); his: size 2, growth 0.25, damage 40, 25
# frames (a radius of 2.25 growing to 8.5). The ring's model is only in his levels, so it is
# installed and registered as the missile's is. Here every landing from a jump in the mode (state
# type JUMP before, not now) makes one, smaller. SHOCKWAVE: frames (0 = none), size, growth,
# damage, up, shake strength, shake frames.
SHOCK_SPAWN, SHOCK_CLASS = 0xEB2A8, 0x593
SHOCKWAVE = (25, 1.0, 0.15, 40.0, 0.2, 0.15, 30)
# His ring is a pale see-through disc; here it is gold as the bomb is: its colour (+0x38, which
# the level's lighting sets every frame) is SHOCK_COLOUR (00BBGGRR) at the HUD's hook (gc_late)
# for its frames but one (its update deletes it when they are over).
SHOCK_COLOUR = 0x40E0FF            # brighter than GOLD: the ring is mostly see-through
# Still faint over grass, so gold puffs burst from where he lands as well (SHOCK_BURST, a set as BURST).
# Tried live: BURST's alpha and count hid the legs in a yellow blob, half the alpha showed nothing.
SHOCK_BURST = ((0.0, 0.0, 0.1), (0.0, 0.0, 0.02), 400000.0, 0.25, (0x2860E0FF, 0x2040D0FF), (20, 26), 14)
# The jump is a high one in the mode (the user: "make the giant clank jump like in rac2, like a
# high jump"): a jump's speed up is sqrt(2 * height * gravity), with the height of hero +0x430
# (set_state fills it per jump, 0x9d6b0 can raise it while X is held); at the launch's read of it
# (JUMP_HOOK, lfs f3, 0x430(r29); f0, r11, r12 free) it is taken JUMP times. And the legs play his
# animation JUMP_ANIM while Ratchet is in a jump (state type +0x208c = 4, set for every jump by
# set_state's jump group) ("also add the jump animation"); of his, 6 is set for his state 0x5d.
JUMP, JUMP_ANIM = 2.5, 6
# His feet fly him in a hover (the user: "If I hover I want out of giant clanks feet to come
# flames, instead of ratchets helipack or thruster pack"; "The flames should shoot downwards";
# "reuse the pyrocitor flame for that, just shorten the flame length about 1/2"): while Ratchet
# hovers (HOVER_STATES: the glide 8, and 0xe, the second press that starts it) the legs stand (no
# walk in the air) and the Pyrocitor's flame goes straight down from under each foot.
# The Pyrocitor (fire function 0x29ead8) makes its flame each frame in 0x29e140 (its numbers at
# 0x29e0f8): two fire particles FIRE(position, velocity, frames 30, alpha 0x7f, colour 0xffffff
# (the texture is the fire), a random 0..5; f1 25000, 300, 0.98, 0, 0.85) and an orange spark
# SPARK(position, velocity, 0x4F007FFF, 0x1FFFFFFF, -, frames 20..40, 1; f1 10000), all at
# 0.01..0.06 a frame along its aim plus 0.7 (the spark 0.55) of Ratchet's movement (hero +0x100;
# the positions' and velocities' w 1). Here the aim is straight down and the frames are halved:
# the flame half as long. (The Tesla Claw's stream, class 0xb1, was taken for it first: blue
# lightning.) The soles are under the standing legs' feet (in the model the vertices of bones 76
# and 81, toes 77 and 82: x -1.03..2.83, y about +-1.93, z 0; the pelvis' top, z 5.04, is 0.95 up,
# so a unit of the model is 0.19 here; the vertices' bone numbers are not JOINT_POSITION's, which
# took 76 and crashed the game). FLAMES: on, where under the left foot (forward, left, up from the
# legs, turned with them; the right one mirrored), speed from, to, the fire's frames, fires a foot a
# frame, the sparks' frames from, to, how much of his movement the fire and the sparks carry,
# then aside at most (a frame) and from how far about the sole's middle (at random each).
# "The flame is pretty small it must be a bit bigger" (the user): more fires a frame, each growing
# (FIRE_LOOK's f4, 0 for the Pyrocitor: with 0.035 the flame reached the ground), and scattered
# aside so it widens downward; the size (f5) changed nothing to be seen.
HOVER_STATES = (0x8, 0xE)
FLAMES = (1, (0.17, 0.36, 0.0), (0.01, 0.06), 15, 4, (10, 20), (0.7, 0.55), 0.012, 0.05)
RANDOM, RANDOM_INT = 0xFCBE8, 0xFE484   # (f1 from, f2 to) -> f1; (r3 from, r4 to) -> r3
FIRE, SPARK = 0x12E3E8, 0x1268F8
FIRE_LOOK = (25000.0, 300.0, 0.98, 0.02, 0.85)  # f1..f5 as the Pyrocitor gives them, but f4 (growth)
SPARK_COLOURS, SPARK_FAR = (0x4F007FFF, 0x1FFFFFFF), 10000.0
HERO_MOVED = 0x100                 # the movement he made this frame (x, y)
# One jump in the mode, no double jump (the user: "ratchet should be unable to perform a double
# jump, just a single jump"; a second X still hovers, their pick: "Hover, no extra height"). In
# his air states the transition function (0xbe228) takes a fresh X to the double jump, state 0xe
# (0xc4e58..0xc4f08: not from 0xe itself, with +0x20a8 clear, +0x4af set and enough frames into
# the jump), and else to the glide's test (0xc4f0c: the Heli-Pack owned, X held, high enough over
# the ground: state 8, the hover). In the mode DOUBLE_JUMP_HOOK goes to the glide's test at once.
DOUBLE_JUMP_HOOK, DOUBLE_JUMP_WORD = 0xC4E64, 0x887320A8   # lbz r3, 0x20a8(r19) (r19 = hero; r3 free)
DOUBLE_JUMP_BACK, GLIDE_TEST = DOUBLE_JUMP_HOOK + 4, 0xC4F0C
# No flips either (the user: "remove also sideflips", "and backflips"): the side and back flips
# are state 0xb, set where a jump comes with a strafe button held (pad 0xa) and a flip type from
# 0xa1e78 (the jump choosers 0xa4950 and 0xa56d8, the transition function at 0xc3ff4). In the mode
# set_state takes them for his plain jump (NO_FLIPS_HOOK, at its top). The crouch's jumps stay (the
# user: "Keep high jump, add flames"): PACK_JUMPS, the high jump (0xf with the Heli-Pack, 0xd with
# the Thruster-Pack, set only by the crouch's chooser 0xa56d8) and the long jump on the run (0xa,
# 0x10). In them the feet's flames burn as in the hover (FLAME_STATES), and the pack's sound is
# off: the long jump's (Ratchet's model sound 0x36, from ~0.1 s into 0xa, seen in the voice table)
# comes from no call of the hero code with it, so it is taken for a sound of his animation: in the
# mode, in PACK_JUMPS, JUMP_SOUNDS_HOOK (in 0x8bc30, which plays the sounds of the hero moby's
# animation: those at its frames, its table behind the frame pointers, then its looping one,
# moby +0x7c, from the animation's +0x11) leaves out the frames' sounds and the looping one.
FLIP_STATES, PLAIN_JUMP = (0xB,), 0x7
PACK_JUMPS = (0xF, 0xD, 0xA, 0x10)
FLAME_STATES = HOVER_STATES + PACK_JUMPS
JUMP_SOUNDS_HOOK, JUMP_SOUNDS_WORD = 0x8C070, 0x2C1E0000   # cmpwi r30, 0 (r27 = hero, r31 = his moby; r3, r4 free)
JUMP_SOUNDS_BACK, JUMP_SOUNDS_SKIP = JUMP_SOUNDS_HOOK + 4, 0x8C150
# The flames have a sound of their own (the user: "there is no sound can you maybe take thruster
# sound but pitch it a bit down"): the Thruster-Pack's hover whirr, Ratchet's model sound 0x12 (a
# looping one: its definition's +0x18 is set, so it is played with flag 4), lower. A model's sound
# definitions (model +0x28, 0x20 bytes each, +0xd their count) give the voice a pitch at random
# between +0x10 and +0x14 (PLAY_SOUND_DEF 0x15d0c8 -> voice +0x84; 0 for this one), which the
# sound update hands to the sound library as it starts the voice (0x15ca84). So gc_flame_sound
# copies the definition into GIANT and plays the copy, its pitch range FLAME_SOUND's pitch, at
# Ratchet (as PLAY_MODEL_SOUND does: the voice follows his moby, +0x88), while the flames burn,
# and stops it (SOUND_STOP) when they do not. FLAME_SOUND: on, the model sound, the pitch (the
# definitions' unit; the Thruster-Pack's burst, sound 1, takes -508..1270), the volume (r7 of
# PLAY_SOUND_DEF, 0x400 as the game gives it).
FLAME_SOUND = (1, 0x12, -400, 0x400)
SOUND_STOP = 0x15CDB0              # (r3 voice)
NO_FLIPS_HOOK, NO_FLIPS_WORD = 0xB72DC, 0x2C830064   # cmpwi cr1, r3, 0x64 (r27 = hero; r0, r5 free)
NO_FLIPS_BACK = NO_FLIPS_HOOK + 4
# No Heli-Pack sound in the mode (the user: "fix the sound, so no helipack sound is played"; the
# feet's flames fly him). The hover's state code (from 0xb40a0, in HERO_UPDATE) starts the pack's
# whirr on one of his looping sound channels (0xa0ae0(channel, moby, sound), the voice at hero
# +0x2218 + 4 * channel), by the pack worn (0x7f41c(3)): the Heli-Pack's Ratchet's sound 2 on
# channel 3, the Thruster-Pack's 0x12 on channel 4. In the mode HOVER_SOUND_HOOK jumps past it.
HOVER_SOUND_HOOK, HOVER_SOUND_WORD = 0xB40A0, 0x38600003   # li r3, 3 (r25 = hero)
HOVER_SOUND_BACK, HOVER_SOUND_SKIP = HOVER_SOUND_HOOK + 4, 0xB41CC
# His own sounds (the user: "add the correct sounds, so there is a bomb sound for the bomb shot, a
# missile sound, for shooting and exploding and one for jumping", then "the fist punch also a sound
# and also a walking sound"). All of his come from his animations' frame sounds (an animation's +0x10
# frame count, +0x12 sound count, from +0x1c + 4 * frames {u16 definition, u16 time in 1/16 frames};
# played by the moby loop's animation step 0xf98d8, the hero's 0x8c0a4), none from code: walk 3:
# 2 at 0.5, 3 at 12 (his steps); jump 6: 4 at 3.5, 7 at 4; missiles 8: 5 at 0.5 and 4; punch 9/10:
# 8 at 2.5 (the swing), then steps; bomb 12: 0 at 1.75. The missile (class 0x100) has one, its blast
# (0 from its update at 0xef5f0, with the camera shake); the bomb's update plays none. Their samples
# are in levels 15 and 18 only, so rc2data.giant_sounds takes his 9 and the missile's definitions
# from level 18 with their sounds in its bank and the bank cut down to their samples; gc_sounds
# loads it (BANK_LOAD_FROM_MEM, as the Charge Boots' bank) once his model is in, points the
# definitions at it and gives them to the models: the missile's, and of his parts only the legs'
# (SOUND_PARTS), so the walk and the jump sound from the legs' animations. The fist is posed from
# code and the bomb has no part, and the missiles leave on the move's action frame, not at his
# animation's times: each move plays one of his definitions at a frame of its own (MOVE_SOUNDS:
# definition, frame; gc_giant_sound, at Ratchet).
GIANT_SOUND_COUNT = 9
SOUND_PARTS = (PART_LEGS,)
MOVE_SOUNDS = ((8, 11), (5, 10), (0, 45))   # the punch's swing as the strike starts, a volley, the throw
SOUND_DEFS = GIANT_SOUND_COUNT + 1         # and the missile's
SOUNDS_BANK_OFF = SOUND_DEFS * 0x20 + -(SOUND_DEFS * 0x20) % 0x10
BANK_LOAD_FROM_MEM = 0x60AE8C       # (r3 bank image, 16-aligned, writable) -> handle, 0 on failure
# The Heli-Pack in the mode, whichever pack he wears (the user: "clank always needs to be in heli
# pack form", then "Heli-Pack even if not equipped"). The back is slot 3 of the equipment slots
# (0x85b30; hero +0x1180 the pack, +0x1184 backpack Clank, PACK_ITEM 2 Heli, 3 Thruster, 4 Hydro),
# which changes the pack when its request (PACK_REQUEST) is another item, as the pause menu asks
# for one (0x1130d4). Each frame (gc_pack) in the mode a Thruster-Pack is asked to be the Heli-Pack
# (when that is owned: UNLOCKS + item), and with the mode off (out of water) the pack he wore is
# asked back (S_PACK_BACK). (The slot keeps the pack asked for as its own in a word of the save,
# 0x969c88: saved with the mode on, the game comes back with the Heli-Pack.)
PACK_ITEM, PACK_REQUEST = 0x11A8, 0x20C4
HELI_PACK, THRUSTER_PACK = 2, 3
UNLOCKS = 0x96C140                 # a byte per item: owned
# Ratchet rides the legs (the user: "The movement while walking looks a bit clunky on ratchet
# because he is completely still"): his walk lifts and drops Giant Clank's hips with every step
# (filmed from the side at 60 fps: the boots floated over the pelvis at the long strides and sank
# into it at the short ones). Each frame (gc_ride_height, before anything is put on him) the
# pelvis' height in the legs' pose, JOINT_POSITION of PIN_PELVIS less the legs' place, less its
# height standing, times FOLLOW, is the ride: LIFT is the base plus it, so he and all that LIFT
# raises go with it; his boots (BOOT_SEAT) and the struts, the column and the arms' pistons, which
# are placed without LIFT, get it added (gc_ride). RIDE: on, rest (the pelvis standing, read live:
# the readout at +0x10; 0.97..1.0 in his idle, 0.73..0.98 walking, a step every ~22 frames),
# follow (1: the pelvis' top standing, 4.76 model units up, times the legs' 0.25 is LIFT's 1.18;
# 0.75 left his boots floating over the low pelvis and sunk into the high one, seen from the
# front). He goes aside with it as well (G_RIDER: walking it sways +-0.3 model units aside and
# surges 0.5 ahead), so the column's foot stays on its spot (the user: "It should stay just
# connected how it would in reality and not float in and out"). The legs are drawn between their
# frame (moby +0x50) and the next (+0x51) by +0x54, which JOINT_POSITION leaves out: the pelvis is
# read at both and taken between them (read at its frame only, it lagged up to a frame of his walk).
RIDE = (1, 0.985, 1.0)
# And he sways on them ("add that": lean and roll): bone 2's manipulator (STILL_JOINTS' first,
# held at no turn by gc_still) bends him above the hips, his feet staying on the pelvis: about its
# -y he leans forward, about its x he rolls to his right (tried live from the side and the front).
# He leans forward with his speed (hero +0x194 over LEAN_SPEED, at most LEAN_MAX, eased by
# LEAN_EASE a frame) and rolls toward the side the pelvis sways to (walking it goes about +-0.067
# aside, changing with each step: ROLL_GAIN rad a unit, eased by ROLL_EASE). Backpack Clank and the
# pack (gc_clank_seat) turn with him about PIVOT above his feet. TILT: on, LEAN_MAX, LEAN_SPEED,
# LEAN_EASE, ROLL_GAIN, ROLL_EASE, PIVOT.
TILT = (1, 0.12, 0.09, 0.1, 1.5, 0.3, 0.45)
# With him Clank sways, and the column he stands on (STRUTS' first, from the pelvis up into his
# bottom) stood still: it went into him at another spot with every step (the user: "the rod needs
# to be connected to same spot, make it maybe a joint"). So the column turns on the pelvis
# (gc_rod): where its top is on Clank (ROD: forward, left, up from Ratchet's feet) is carried with
# his sway about PIVOT as his seat is, and the column is turned about its bottom (ROD's last, up
# from his feet) by the angles that bring its top there: a roll (euler +0x40, about ahead) and a
# pitch (+0x44, about left; the game builds the rows from the euler as turn * y * x, tried live),
# its place moved so that the bottom stays. A gold ball (the legs' chain, one ball at ROD's top)
# is the joint. ROD: on, the top, the bottom's height, the ball's size (times the chain's growth).
# The column still went up into Clank and turned in him ("not properly attached to his model, it
# still moves inside him"): with Clank hidden its top is a round end 0.6 over Ratchet's feet and
# its foot 0.12 under them (ROD_REST, as STRUTS and STRUT_JOINTS place it; his bottom is about
# 0.68), and its length goes from the top (STRUT_JOINTS' y scale, tried live). So the top is the
# joint: the ball, its top just in his bottom, and the column's top on it, moved down to it; the
# column turns about it and is made as long (its joint's y scale) as the way to its foot is.
# The ball (ROD's last) stood out of his bottom beside the column ("the ball seems floaty", the
# user): 0, no ball; the column's own round top is the joint, in his bottom.
ROD = (1, (-0.066, -0.016, 0.6), -0.12, 0.0)      # his bottom is about 0.68 (0.48 left a gap)
ROD_REST = (0.6, 0.72)             # the column's top over his feet and its length, as placed
JUMP_HOOK, JUMP_HOOK_WORD = 0x9DACC, 0xC07D0430
JUMP_BACK = JUMP_HOOK + 4
# Clank's legs join the gold legs (the user: "make clanks legs connect to the golden legs"): his
# leg hangs from his hips (bone 1 of his model, 0x259) to bone 26, which carries his foot; while
# the gold legs are out a joint manipulator of the mod's own on bone 26 sets its place against bone
# 1 (weight 1, no turn: the leg straight), in model units * 1024 times his scale (0.146; his bind
# place is about 0, 0, -149). The mod links it in and out itself (MANIP_REMOVE): writing moby
# lists from the tracer crashed the game twice. CLANK_LEG: on, bone, place (x, y, z).
CLANK_LEG = (0, 26, (0.0, 0.0, -149.0))
# His idle sways his body, and the leg with it: its foot swung off the pelvis. While the gold
# legs are out he is held in one frame as Ratchet is (STILL; his moby's animation fields kept and
# put back, gc_clank_still / gc_clank_back); his head's twitch, a manipulator, goes on. CLANK_STILL:
# on, animation, frame.
CLANK_STILL = (1, 1, 0)                     # "keep it still" (the user)
# That did not hold the leg: Clank's moby itself turns on Ratchet's back by -0.6..+1.25 rad (read
# live), as the game places him (his matrix rows +0xc0, unit, his euler +0x40 from them) from
# Ratchet's real skeleton, which looks about in his idle while the still Ratchet is drawn. While
# the gold legs are out, at the end of the frame (gc_clank_seat) his and the pack's rows are made
# upright and turned as Ratchet faces (hero +0x98) plus a turn; their place moves only 0.03.
# CLANK_SEAT: on, the turn.
CLANK_SEAT = (1, 0.0)
# The pack (hero +0x1180: his arms, and what else of him its model has) goes on animating under a
# still Clank; PACK_STILL holds it the same way: on, animation, frame. CLANK_LEG's moby: the hero
# field of it (HERO_CLANK_MOBY or HERO_PACK_MOBY).
PACK_STILL = (1, 1, 0)
# Clank's backpack model has no legs, only feet (the stalk taken for his leg was Ratchet's tail,
# swung by the game's manipulators on Ratchet's bones 104-110). Clank joins the gold hips by two
# gold struts instead (the user's pick: "gold struts as legs"): his forearms' pistons (PART_STRUT_L/R)
# in his idle, held at its first frame, while the gold legs are out. STRUTS: on, the animation;
# then for the left and the right one where they stand (scale, forward, left, up, turn, as LEGS).
STRUTS = (1, IDLE_ANIM, ((0.3, 0.4, -1.7, -0.2, 0.0), (0.3, -0.15, 1.95, -0.2, 0.0)))   # the column first; tried live 2026-10-21
# As they are the pistons were wide gold boards (the two of a forearm side by side), lying as his
# forearm does ("slim and stand them up", the user): one piston each, and on its bone a joint
# manipulator of the strut's own (gc_strut_on/off, linked and removed by the mod) gives it a
# turn, a scale per axis and a place against its parent, the forearm (bone 36 / 56), whatever the
# animation. STRUT_JOINTS: for each, the bone, the turn (quaternion), the scale, the place (its
# bind place to the forearm, (699, +-2393, 956), times the strut's scale).
# Tried live 2026-10-20: turned 60 degrees about x (mirrored), so the two stand as a Λ from under
# Clank to the gold hips. 2026-10-21, seen from behind, the side and the front: 0.55 thick (x, z;
# 0.35 read as sticks), and the two bones are no mirror images, so the left one sits 0.08 further
# out, 0.25 further forward (seen from behind it looked right, but orbiting showed it floating
# beside Clank) and is shorter (y 0.85 against 1.3). Later that day (the user: "the start ... does
# not come out of clanks leg hole and the end should attach to the giant clank part, intersection
# is okay"): turned 72 degrees and moved 0.04 in, so they start under Clank's body where his legs
# would come out and end sunk into the inner tops of the hip blocks, from behind and orbiting.
# They grow thicker towards the gold hips (the user: "the strut should grow the nearer it gets to
# giant clank parts"). The pistons are flat bars ("why are you always using those sheets"); the
# user then had Blender mock-ups made of the whole rig (2026-10-21) and chose: one waist column
# from Clank's bottom down into the pelvis instead of two struts, and smooth tubes flaring into
# the parts ("the connection needs to look more fluent"). The pistons' parts draw tubes
# (rc2data._giant_tubes: rings along a curved profile, smooth normals, a plain patch of his
# shoulder ring's texture), bound to the pistons' bones so STRUT_JOINTS still place them; a vertex
# buffer of their own (his overwritten from the start, its count kept) and index buffers of his
# length. TUBES: for the left arm, the right arm, the column: bone, profile ((t, radius as a share
# of the length), t = 0 at Clank), sides, steps. 12 sides as his shoulder ring, 240 triangles each:
# with the legs and both arms out, 4752 of the 6070 the game draws for the whole of him.
ARM_PROFILE = ((0.0, 0.32), (0.08, 0.25), (0.18, 0.23), (0.4, 0.26), (0.62, 0.32), (0.78, 0.42), (0.9, 0.56), (1.0, 0.78))
COLUMN_PROFILE = ((0.0, 0.5), (0.1, 0.42), (0.4, 0.46), (0.7, 0.58), (0.88, 0.8), (1.0, 1.1))
TUBES = ((47, tuple((t, r / 2.2) for t, r in ARM_PROFILE), 12, 10),    # (the mock-ups' lengths: 2.2, 4.7)
         (67, tuple((t, r / 2.2) for t, r in ARM_PROFILE), 12, 10),
         (47, tuple((t, r / 4.7) for t, r in COLUMN_PROFILE), 12, 10))
STRUT_PARTS = (PART_COLUMN, -1)    # what the two struts show (-1 nothing): the column only
STRUT_PART_0, STRUT_PART_1 = (max(part, 0) for part in STRUT_PARTS)
STRUT_ON_0, STRUT_ON_1 = (int(part >= 0) for part in STRUT_PARTS)
STRUT_TURN = (0.5877853, 0.0, 0.0, 0.8090170)           # 72 degrees about x
COLUMN_TURN = (0.2164396, 0.0, 0.0, 0.9762960)         # 25 degrees about x: upright
STRUT_JOINTS = ((47, COLUMN_TURN, (0.85, 1.1, 0.85), (209.6, 718.0, 286.9)),
                (67, (-STRUT_TURN[0],) + STRUT_TURN[1:], (0.55, 1.3, 0.55), (209.6, -718.0, 286.9)))
LEG_MOBY = 0x1184
STATE_TYPE, STATE_TYPE_JUMP, STATE_TYPE_HOVER = 0x208C, 4, 5
FALL_STATE = 0x6                   # falling (a hover ends in it: 8 -> 6), state type not 4 or 5
# In water he is Ratchet again, and L3 + R3 do not switch there (the user: "if I get into water
# make ratchet go back to normal an he should be unable to go golden clank form in water"): set_state
# gives the state type 0x12 to his two water states only, 0x36 (swimming) and 0x37 (followed
# through its compare tree from 0xb74fc to 0xb8400 and 0xb7f5c; read live in the river).
STATE_TYPE_WATER = 0x12
HERO_LANDED = 0x418                # frames since he touched down (0 in the air, counts to 13); Giant Clank's
                                   # landing code spawns the ring at 1. The ring went by the jump state
                                   # ending, ~0.3 s late (the user: "looks a bit delayed")
MISSILES = 0.35
MISSILE_SIZE = 0.7                 # times the size it is spawned at (the user: "a bit smaller scaled")
BOMB_AT = (1.0, 1.7)
MISSILE_SPAWN, MISSILE_CLASS, MISSILE_JOINTS = 0xED3E0, 0x100, (3, 4)
BOMB_SPAWN, BOMB_CLASS = 0xEC418, 0x5F3
EXTRA_MODELS = (("MISSILE", MISSILE_CLASS), ("SHOCK", SHOCK_CLASS))   # installed behind his, in this order
BOMB_KIND_HOOKS, BOMB_KIND_WORD = (0xEC798, 0xECEB4), 0x2C030002
BOMB_KIND_A_BACK, BOMB_KIND_B_BACK = BOMB_KIND_HOOKS[0] + 4, BOMB_KIND_HOOKS[1] + 4
JOINT_POSITION = 0xF1114           # (r3 moby, r4 joint, r5 vec4 out)
CLASS_UPDATE = 0xFBFA0             # (r3 class): the slot of SLOT_COUNT gets its update (table 0x9273fc), its model +0x2c
SLOT_COUNT, SLOT_CLASS, SLOT_INFO = 0xA35CC0, 0xA35300, 0xA37B90   # the next slot; u16 per slot; model +0x2c per slot
MANIP_REMOVE = 0xF0F1C             # (r3 moby, r4 manipulator)
DAMAGE_DESC = 0x10581C             # (r3 descriptor, r4 source moby, r5 flags, f1 damage, r7 direction vec4)
MELEE_FLAGS = 0x30000
MELEE_PUSH = 5627.9248             # the Walloper's descriptor +0xc (the hero's float table 0xaaafc +0x26c)
MELEE_UP = 1.3                     # its direction's height (+0x280)
# Robot legs run faster (the user's wish): in the mode, the speed BUILD_VELOCITY makes the
# velocity of (hero +0x194, loaded once at VELOCITY_HOOK) is taken RUN times while Ratchet walks
# (hero state 2; jumps and the rest keep their own). Doubling STICK_TARGET's scale (f1) instead
# left his run at 5.7 units/s: the walk's target speed +0x190 does not come from it.
RUN = 2.0
WALK_STATE = 0x2
# And he moves faster in the air (the user: "increase his air speed also double, i mean the moving
# speed not gravity"): every jump and hover state builds his velocity through BUILD_VELOCITY each
# frame too, so in the state types of a jump (4) and a hover (5) the speed is taken AIR times;
# their heights and gravity are not touched.
AIR = 2.0
# He stands for the punch and the bomb (the user: "think about restricting movement while punching
# and golden bomb"): his own states for them (0x60 at 0xb5f1c, 0x61 at 0xb6524) set the target
# speed +0x190 to 0 and still turn him with the stick (0x9b380, 0x9ba88). Here the walking speed is
# taken 0 while a move of HOLD_MOVES (bits by MOVE_TABLE index: Square, Triangle) is going; he still
# turns, and the punch's lunge still carries him. The missiles leave him free.
HOLD_MOVES = 0b101
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
# +0x2f0 the test moby's, +0x300 the legs', +0x310 the move's part. +0x320 frames into a move (0
# = none), +0x324 the side (0 left, 1 right), +0x328 which move (MOVE_TABLE), +0x32c the moves'
# buttons held, +0x330 frames until the bomb is ready, +0x334 the pack to ask back (0 = none).
S_DISPLAY, S_PROMPT, S_BASE_Z = 0x2A0, 0x2A4, 0x2A8
S_SCALE, S_LIFT, S_SPIN, S_COLOUR = 0x2AC, 0x2B0, 0x2B4, 0x2B8
S_POSE_ANIM, S_POSE_FRAME, S_POSE_ON = 0x2BC, 0x2BD, 0x2BF
S_MODE, S_CHORD, S_CHORD_LEFT, S_MOVES = 0x2C0, 0x2C4, 0x2C8, 0x2CC
S_GROW, S_BASE, S_BURST, S_GLOW = 0x2D0, 0x2D4, 0x2D8, 0x2DC
S_MODEL, S_FRAME, S_TEST_PART, S_LEGS, S_FIST = 0x2E0, 0x2E4, 0x2F0, 0x300, 0x310
S_PUNCH, S_SIDE, S_MOVE, S_HELD, S_BOMB_WAIT, S_PACK_BACK = 0x320, 0x324, 0x328, 0x32C, 0x330, 0x334
PART_RECORDS = (S_TEST_PART, S_LEGS, S_FIST)
# GIANT, the writable block: +0x00 BURST and +0x38 SMOKE (the layout PUFFS), +0x70 CHORD_FRAMES,
# +0x74 GROW_FRAMES, +0x78 GIANT_SCALE (float), +0x7c/+0x80 GIANT_SOUNDS, +0x84/+0x88 GIANT_SHAKE
# (frames, float), +0x8c/+0x90 GIANT_GLOW, +0x94 TEST: shown, scale (float), x, y, z (floats),
# animation, turn (float), model; +0xb4 LEGS: scale, forward, left, up, turn, walk from, walk
# speed (floats); +0xd0 RUN (float); +0xd4 PUNCH: ahead, up, radius, damage (floats); +0x104
# LIFT (float);
# +0x108 ZOOM, ZOOM_EASE (floats); +0x110 STILL: on, animation, frame; +0x11c the moby whose
# animation fields are kept (0 = none), +0x120 those fields; +0x154 CHAINS: scale at Clank,
# at the part, step; +0x160 the legs' chain: from, to (3 floats each), how far grown (0..1);
# +0x180 the balls' records (gc_show); +0x1e0 BALL_ANIM, BALL_COLOUR, PART_COLOUR; +0x1f0 the moby the manipulator is on (0
# = none), +0x1f4 the missile's model (0 = not installed), +0x1f8 MISSILES, +0x1fc MISSILE_SIZE, +0x200 BOMB_AT;
# +0x210 the manipulator; +0x250 MOVE_TABLE, 0x60 bytes each (M_...); +0x370 BOMB_COOLDOWN; +0x380
# the gold eyes' texture entry (0 = not installed), +0x384 the level's own; +0x3c0 JUMP (float),
# JUMP_ANIM, +0x3c8 CAM_JUMP (floats), +0x3d8 the height he last stood at; +0x3e0 CLANK_LEG: on, bone, place (floats); +0x3f4 the moby
# its manipulator is on (0 = none); +0x400 that manipulator; +0x440 CLANK_STILL, +0x44c the moby
# whose animation fields are kept (0 = none), +0x450 those fields; +0x480 CLANK_SEAT; +0x490
# PACK_STILL, the same layout; +0x3f8 LEG_MOBY; +0x4d0 STRUTS: on, animation, +0x4e0 the two places;
# +0x510 the struts' records (gc_show); +0x540 the struts' joints, 0x80 each (S_J_...: the moby its
# manipulator is on, bone, turn, scale, place; +0x40 the manipulator); +0x640 the parts' joint
# list (OWN_JOINTS of his, filled at install, then PIN_JOINTS), +0x680 PIN_JOINTS' entries, 0x10 each;
# +0x6c0 ARMS_SHOULDERS' place (float); +0x6d0 the arms' bone data (BONES of 0x10); then
# G_ARM_CHAINS and G_ARM_BALLS.
G_BURST, G_SMOKE, G_CHORD, G_GROW, G_SCALE = 0x00, 0x38, 0x70, 0x74, 0x78
G_SOUND_ON, G_SOUND_OFF, G_SHAKE_FRAMES, G_SHAKE, G_GLOW, G_GLOW_FRAMES = 0x7C, 0x80, 0x84, 0x88, 0x8C, 0x90
G_TEST, G_TEST_SCALE, G_TEST_AT, G_TEST_ANIM, G_TEST_TURN, G_TEST_MODEL = 0x94, 0x98, 0x9C, 0xA8, 0xAC, 0xB0
G_LEGS_SCALE, G_LEGS_AT, G_LEGS_TURN, G_WALK_FROM, G_WALK_RATE, G_RUN = 0xB4, 0xB8, 0xC4, 0xC8, 0xCC, 0xD0
G_HIT_AT, G_HIT_RADIUS, G_HIT_DAMAGE = 0xD4, 0xDC, 0xE0
G_LIFT, G_ZOOM, G_ZOOM_EASE = 0x104, 0x108, 0x10C
G_STILL, G_STILL_ANIM, G_STILL_FRAME, G_KEPT, G_KEPT_FIELDS = 0x110, 0x114, 0x118, 0x11C, 0x120
G_BALL_SCALE, G_BALL_SCALE_TO, G_GROW_STEP = 0x154, 0x158, 0x15C
G_CHAIN_LEGS, G_BALLS, G_BALL_ANIM, G_BALL_COLOUR, G_PART_COLOUR = 0x160, 0x180, 0x1E0, 0x1E4, 0x1E8
G_ARM_MOBY, G_MISSILE_MODEL, G_MISSILE_AHEAD, G_BOMB_AT, G_MANIP, G_MOVES = 0x1F0, 0x1F4, 0x1F8, 0x200, 0x210, 0x250
G_MISSILE_SIZE = 0x1FC
M_PART, M_ANIM, M_SIDED, M_FRAMES, M_ACTION, M_IDLE, M_GROW, M_BONES = 0x00, 0x04, 0x08, 0x0C, 0x10, 0x14, 0x18, 0x1C
M_SCALE, M_SPOT, M_ANCHOR, M_TURN, M_RATE, M_REPEAT, M_BLEND, M_SHRINK, M_PIN, M_BALLS, M_SOUND, MOVE_SIZE = 0x24, 0x28, 0x34, 0x40, 0x44, 0x48, 0x4C, 0x50, 0x54, 0x58, 0x5C, 0x60
G_BOMB_COOLDOWN, G_EYE_ENTRY, G_EYE_OWN, G_JUMP, G_JUMP_ANIM, G_CAM_JUMP = 0x370, 0x380, 0x384, 0x3C0, 0x3C4, 0x3C8
G_CAM_BASE = G_CAM_JUMP + 0x10                 # the height he last stood at
G_LEG, G_LEG_BONE, G_LEG_AT, G_LEG_MOBY, G_LEG_MANIP = 0x3E0, 0x3E4, 0x3E8, 0x3F4, 0x400
G_CLANK_STILL, G_CLANK_ANIM, G_CLANK_FRAME, G_CLANK_KEPT, G_CLANK_FIELDS = 0x440, 0x444, 0x448, 0x44C, 0x450
G_SEAT, G_SEAT_TURN, G_PACK_STILL, G_LEG_TARGET = 0x480, 0x484, 0x490, 0x3F8
H_ON, H_ANIM, H_FRAME, H_KEPT, H_FIELDS = 0x0, 0x4, 0x8, 0xC, 0x10
G_STRUTS, G_STRUT_ANIM, G_STRUT_AT, G_STRUT_RECORDS, G_STRUT_JOINTS = 0x4D0, 0x4D4, 0x4E0, 0x510, 0x540
S_J_MOBY, S_J_BONE, S_J_TURN, S_J_SCALE, S_J_PLACE, S_J_MANIP, S_J_SIZE = 0x0, 0x4, 0x10, 0x20, 0x30, 0x40, 0x80
G_JOINT_LIST, G_JOINT_ENTRIES, G_ARMS_SHOULDERS, G_ARMS_BONES = 0x640, 0x680, 0x6C0, 0x6D0   # a still pose's record (CLANK_STILL, PACK_STILL)
C_FROM, C_TO, C_GROWN, C_COUNT, CHAIN_SIZE = 0x00, 0x0C, 0x18, 0x1C, 0x20
G_ARM_CHAINS = G_ARMS_BONES + 84 * 0x10        # (BONES) the left arm's chain, then the right's
G_ARM_BALLS = G_ARM_CHAINS + 2 * CHAIN_SIZE    # their balls' records (gc_show), CHAIN_MAX each
G_PISTONS_ON = G_ARM_BALLS + 2 * 6 * 0x10      # (CHAIN_MAX) ARM_PISTONS' on
G_PISTONS = G_PISTONS_ON + 0x10                # the two pistons, PISTON_SIZE each:
P_JOINT, P_RECORD, P_AT, P_GROW, PISTON_SIZE = 0x00, 0x80, 0x90, 0xA4, 0xB0   # its joint (S_J_...), its record (gc_show), where, P_GROW
G_STILL_JOINTS = G_PISTONS + 2 * PISTON_SIZE   # STILL_JOINTS: the count, then {bone, 12 spare, quaternion} 0x20 each
G_BOOT_SEAT = G_STILL_JOINTS + 0x10 + 0x20 * 7 # (STILL_JOINTS) BOOT_SEAT: on, then 0x40 each: place, rows, euler (15 floats)
G_SEAT_AT = G_BOOT_SEAT + 0x10 + 2 * 0x40      # SEAT_AT: on, forward, left, up
G_LUNGE = G_SEAT_AT + 0x10                     # LUNGE: from, to, speed
G_VIEW = G_LUNGE + 0x10                        # VIEW: on, distance, cos and sin of the pitch, turn, up
G_POSE = G_VIEW + 0x20                         # PUNCH_POSE: on, wind, strike, peak, hold, back
G_SHOCK = G_POSE + 0x20                        # SHOCKWAVE (frames, 5 floats, frames), then:
G_SHOCK_MODEL = G_SHOCK + 0x1C                 # the ring's model (0 = not installed)
G_SHOCK_AIR = G_SHOCK + 0x20                   # 1 = Ratchet was in a jump last frame
G_SHOCK_MOBY = G_SHOCK + 0x24                  # the last ring, frames it is still gold for, SHOCK_COLOUR
G_SHOCK_LEFT, G_SHOCK_COLOUR = G_SHOCK + 0x28, G_SHOCK + 0x2C
G_SHOCK_BURST = G_SHOCK + 0x30                 # SHOCK_BURST (the layout PUFFS)
G_DANCE = G_SHOCK_BURST + 0x38                 # BOMB_DANCE (on, 8 floats, kick strength, frames), then:
G_DANCE_PACK = G_DANCE + 0x2C                  # the pack's own size during a throw (0 = none going on)
G_DANCE_NOW = G_DANCE + 0x30                   # now: spin, rise, lean, size (gc_dance)
G_DANCE_GLOW, G_DANCE_BURST = G_DANCE + 0x40, G_DANCE + 0x78   # DANCE_GLOW, DANCE_BURST (PUFFS)
G_PUNCH = G_DANCE_BURST + 0x38                 # PUNCH_TWIST (on, 4 floats, kick, frames, hit kick, frames, hit-stop)
G_PUNCH_STOP = G_PUNCH + 0x28                  # the hit-stop's frames left
G_PUNCH_BURST = G_PUNCH + 0x30                 # PUNCH_BURST (PUFFS)
G_FLAMES = G_PUNCH_BURST + 0x38                # FLAMES: on, where, speeds, frames, count, spark frames, carried;
                                               # +0x30 FIRE_LOOK, +0x44 SPARK_COLOURS, +0x4c SPARK_FAR,
                                               # +0x50 aside, spread
G_RIDE = G_FLAMES + 0x58                       # RIDE: on, LIFT (the base), rest, follow; +0x10 the pelvis' height
G_RIDE_NOW = G_RIDE + 0x14                     # read this frame, +0x14 the ride now, +0x18 the pelvis' x, y off the legs
G_TILT = G_RIDE + 0x20                         # TILT: on, lean max, lean speed, lean ease, roll gain, roll ease, pivot
G_TILT_NOW = G_TILT + 0x20                     # the lean and the roll now (+ = forward, to his left)
G_ROD = G_TILT + 0x30                          # ROD: on, the top (3 floats), the length, the top less the column's place (3),
                                               # +0x20 the ball's size, +0x24 the joint's y scale a unit of length
G_RIDER = G_ROD + 0x30                         # where he rides this frame: x, y (his place and the pelvis' way aside), then that way
G_SCENE = G_RIDER + 0x10                       # the purchase's scene: frame (0 = none), Triangle pressed, a move to press,
                                               # 1 / the stream's frames; +0x10 the display's place, +0x20 the camera's point
                                               # aside of him; +0x30 now: SCENE_CAM's 5, SCENE_SHOW's 3
G_SCENE_CAM = G_SCENE + 0x50                   # SCENE_CAM, 6 floats a key
G_SCENE_SHOW = G_SCENE_CAM + 0x18 * len(SCENE_CAM)          # SCENE_SHOW, 4 floats a key
G_SCENE_RING = G_SCENE_SHOW + 0x10 * len(SCENE_SHOW)        # SCENE_RING (gc_sparks), SCENE_STREAM, SCENE_BOND (PUFFS)
G_SCENE_STREAM, G_SCENE_BOND, G_SCENE_BOND_SPARKS = G_SCENE_RING + 0x38, G_SCENE_RING + 0x70, G_SCENE_RING + 0xA8
G_FLAME_SOUND = G_SCENE_BOND_SPARKS + 0x38     # FLAME_SOUND: on, sound, pitch, volume; +0x10 its voice (-1 none),
                                               # +0x20 the copy of its definition
G_SOUNDS = G_FLAME_SOUND + 0x40                # his sounds (gc_sounds): 0 not yet, 1 in, -1 the bank did not load
G_AIR = G_SOUNDS + 4                           # AIR (float)

# pedestal: jumped to from the top of the update (r3 = the moby; LR is the moby loop's).
# gc_frame: replaces bl HERO_MAIN; gc_tick(): the room, the prompt and the purchase.
# gc_say(r3 = a string): the borrowed text entry gets it, and it is shown.
# gc_hud: at the HUD's hook: the gold.
# gc_pad: replaces bl GAMEPLAY_FRAME; gc_input(): the chord and the moves' buttons.
# gc_switch(r31 = state block, r29 = GIANT): the mode was switched: sound, shake, glow, burst.
# gc_giant(): Clank's size, the burst and the smoke. gc_puffs(r3 = a set, r4 = a moby): its puffs.
# gc_velocity: jumped to from VELOCITY_HOOK.
EXTRA_MODEL = """
    lis 26, {@X@_AT_HI}         # @what@: its model, its texture entries, its pixels
    ori 26, 26, {@X@_AT_LO}
    add 26, 30, 26                  # r26 = its model
    mr 3, 26
    lis 4, {@X@_MODEL_HA}
    addi 4, 4, {@X@_MODEL_LO}
    li 5, {@X@_SIZE}
    bl {COPY}
    addi 3, 26, {@X@_ENTRIES_AT}
    lis 4, {@X@_TEXTURES_HA}
    addi 4, 4, {@X@_TEXTURES_LO} + 8
    li 5, {@X@_ENTRIES_SIZE}
    bl {COPY}
    lis 3, {@X@_PIXELS_AT_HI}
    ori 3, 3, {@X@_PIXELS_AT_LO}
    add 3, 28, 3
    lis 4, {@X@_PIXELS_HA}
    addi 4, 4, {@X@_PIXELS_LO}
    lis 5, {@X@_PIXELS_SIZE_HI}
    ori 5, 5, {@X@_PIXELS_SIZE_LO}
    bl {COPY}
    lis 3, {GCM_PTR_HA}
    lwz 3, {GCM_PTR_LO}(3)
    lwz 3, 0x4ac(3)
    lis 4, {@X@_PIXELS_AT_HI}
    ori 4, 4, {@X@_PIXELS_AT_LO}
    add 4, 28, 4
    subf 3, 3, 4
    li 4, {@X@_ENTRY_COUNT}
    mtctr 4
    addi 4, 26, {@X@_ENTRIES_AT}
gi_@x@_entry:
    lwz 5, 0(4)
    add 5, 5, 3
    stw 5, 0(4)
    addi 4, 4, 0x24
    bdnz gi_@x@_entry
    mr 3, 26
    li 4, 0
    li 5, 0
    li 6, {@X@_CLASS}
    bl {MODEL_FIXUP}
    lwz 3, 0(26)
    lwz 3, 8(3)
    lis 4, {@X@_TEXTURES_HA}
    addi 4, 4, {@X@_TEXTURES_LO}
    lbz 5, 0(4)
    mtctr 5
gi_@x@_group:
    lbzu 5, 1(4)
    mulli 5, 5, 0x24
    add 5, 26, 5
    addi 5, 5, {@X@_ENTRIES_AT}
    stw 5, 0(3)
    addi 3, 3, 0x10
    bdnz gi_@x@_group
    lis 9, {GIANT_HA}
    addi 9, 9, {GIANT_LO}
    stw 26, {G_@X@_MODEL}(9)
"""

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
    bl gc_scene
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
    lis 9, {GIANT_HA}               # (not while the purchase's scene runs)
    addi 9, 9, {GIANT_LO}
    lwz 9, {G_SCENE}(9)
    cmpwi 9, 0
    bne gt_done
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
    lis 9, {GIANT_HA}               # Triangle (gc_input took it from the pad)
    addi 9, 9, {GIANT_LO}
    lwz 10, {G_SCENE} + 4(9)
    li 11, 0
    stw 11, {G_SCENE} + 4(9)
    cmpwi 10, 0
    beq gt_done
    cmpwi 28, {ALL_GOLD_BOLTS}
    blt gt_done
    li 10, 1                        # bought: the scene (gc_scene) does the rest
    stw 10, {G_SCENE}(9)
    lfs 0, 0x10(29)                 # where the display is
    stfs 0, {G_SCENE} + 0x10(9)
    lfs 0, 0x14(29)
    stfs 0, {G_SCENE} + 0x14(9)
    lfs 0, 0x18(29)
    stfs 0, {G_SCENE} + 0x18(9)
    li 9, {SCENE_TURN}              # his back to the display
    cmpwi 9, 0
    beq gt_turned
    lfs 1, 0x84(30)
    lfs 0, 0x14(29)
    fsubs 1, 1, 0
    lfs 2, 0x80(30)
    lfs 0, 0x10(29)
    fsubs 2, 2, 0
    bl gc_atan2
    stfs 1, 0x98(30)
gt_turned:
    li 9, 0
    stw 9, {S_PROMPT}(31)
    bl {CANCEL_MESSAGE}
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

gc_pad_take:                        # (r0 = PAD bits, r30 = the pad): out of every button word and the presses' history (leaf)
    li 12, {PAD_WORDS}
    mtctr 12
    addi 12, 30, {PAD_WORDS_AT} - 4
gpt_word:
    lwzu 11, 4(12)
    andc 11, 11, 0
    stw 11, 0(12)
    bdnz gpt_word
    li 12, {PAD_HISTORY}
    mtctr 12
    addi 12, 30, {PAD_HISTORY_AT} - 4
gpt_history:
    lwzu 11, 4(12)
    andc 11, 11, 0
    stw 11, 0(12)
    bdnz gpt_history
    blr

gc_keys:                            # (r3 keys: frame, then r5 values; r4 their count, r6 out, f1 the frame): eased between keys (leaf)
    addi 7, 5, 1
    slwi 7, 7, 2                    # r7 = a key's size
    li 8, 1
gk_find:
    cmpw 8, 4
    bge gk_last
    mullw 9, 8, 7
    lfsx 0, 3, 9
    fcmpu 0, 1, 0
    blt gk_between
    addi 8, 8, 1
    b gk_find
gk_last:                            # past the last: its values
    addi 9, 4, -1
    mullw 9, 9, 7
    add 9, 3, 9
    addi 6, 6, -4
    mtctr 5
gk_copy:
    lfsu 0, 4(9)
    stfsu 0, 4(6)
    bdnz gk_copy
    blr
gk_between:                         # t from key r8 - 1 (r10) to key r8 (r9), s = t t (1 + 2 (1 - t))
    mullw 9, 8, 7
    add 9, 3, 9
    subf 10, 7, 9
    lfs 2, 0(10)
    lfs 3, 0(9)
    fsubs 0, 1, 2
    fsubs 3, 3, 2
    fdivs 0, 0, 3
    lis 11, {POOL_HA}
    addi 11, 11, {POOL_LO}
    lfs 4, {P_ONE}(11)
    fsubs 3, 4, 0
    fadds 3, 3, 3
    fadds 3, 3, 4
    fmuls 2, 0, 0
    fmuls 0, 2, 3
    addi 6, 6, -4
    mtctr 5
gk_ease:
    lfsu 2, 4(10)
    lfsu 3, 4(9)
    fsubs 3, 3, 2
    fmadds 3, 3, 0, 2
    stfsu 3, 4(6)
    bdnz gk_ease
    blr

gc_scene:                           # (from gc_frame) a frame of the purchase's scene (SCENE_*); G_SCENE 0 = none
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0xc0(1)
    std 31, 0x70(1)
    std 30, 0x78(1)
    std 29, 0x80(1)
    std 28, 0x88(1)
    stfd 31, 0x90(1)
    lis 31, {STATE_HA}
    addi 31, 31, {STATE_LO}
    lis 30, {HERO_HA}
    addi 30, 30, {HERO_LO}
    lis 29, {GIANT_HA}
    addi 29, 29, {GIANT_LO}
    lwz 28, {G_SCENE}(29)
    cmpwi 28, 0
    beq gsc_out
    addi 28, 28, 1
    stw 28, {G_SCENE}(29)
    cmpwi 28, {SCENE_END}
    ble gsc_run
    li 9, 0                         # the end: the game's camera, the display's own numbers, the hint
    stw 9, {G_SCENE}(29)
    stw 9, {G_VIEW}(29)
    stw 9, {S_LIFT}(31)
    stw 9, {S_SCALE}(31)
    stw 9, {S_SPIN}(31)
    stw 9, {G_SCENE} + 0x20(29)
    stw 9, {G_SCENE} + 0x24(29)
    stw 9, {G_SCENE} + 0x28(29)
    lis 3, {TEXT_HINT_HA}
    addi 3, 3, {TEXT_HINT_LO}
    bl gc_say
    b gsc_out
gsc_run:
    mr 3, 28
    bl {INT_TO_FLOAT}
    fmr 31, 1
    addi 3, 29, {G_SCENE_CAM}
    li 4, {SCENE_CAM_KEYS}
    li 5, 5
    addi 6, 29, {G_SCENE} + 0x30
    bl gc_keys
    fmr 1, 31
    addi 3, 29, {G_SCENE_SHOW}
    li 4, {SCENE_SHOW_KEYS}
    li 5, 3
    addi 6, 29, {G_SCENE} + 0x44
    bl gc_keys
    li 9, 1                         # the camera (gc_view)
    stw 9, {G_VIEW}(29)
    lfs 0, {G_SCENE} + 0x30(29)
    stfs 0, {G_VIEW} + 4(29)
    lfs 1, {G_SCENE} + 0x34(29)
    bl {COS}
    stfs 1, {G_VIEW} + 8(29)
    lfs 1, {G_SCENE} + 0x34(29)
    bl {SIN}
    stfs 1, {G_VIEW} + 0xc(29)
    lfs 0, {G_SCENE} + 0x38(29)
    stfs 0, {G_VIEW} + 0x10(29)
    lfs 0, {G_SCENE} + 0x3c(29)
    stfs 0, {G_VIEW} + 0x14(29)
    lfs 1, {G_SCENE} + 0x40(29)     # its point: that share of the way to the display
    lfs 0, {G_SCENE} + 0x10(29)
    lfs 2, 0x80(30)
    fsubs 0, 0, 2
    fmuls 0, 0, 1
    stfs 0, {G_SCENE} + 0x20(29)
    lfs 0, {G_SCENE} + 0x14(29)
    lfs 2, 0x84(30)
    fsubs 0, 0, 2
    fmuls 0, 0, 1
    stfs 0, {G_SCENE} + 0x24(29)
    lfs 0, {G_SCENE} + 0x18(29)
    lfs 2, 0x88(30)
    fsubs 0, 0, 2
    fmuls 0, 0, 1
    stfs 0, {G_SCENE} + 0x28(29)
    lfs 0, {G_SCENE} + 0x44(29)     # the display: lift, size, spin (gc_tick)
    stfs 0, {S_LIFT}(31)
    lfs 0, {G_SCENE} + 0x48(29)
    stfs 0, {S_SCALE}(31)
    lfs 0, {G_SCENE} + 0x4c(29)
    stfs 0, {S_SPIN}(31)
    lwz 4, {S_DISPLAY}(31)          # its ring of gold, then the stream into Clank
    cmpwi 4, 0
    beq gsc_bond
    cmpwi 28, {SCENE_RING_FROM}
    blt gsc_bond
    cmpwi 28, {SCENE_RING_TO}
    bgt gsc_stream
    addi 3, 29, {G_SCENE_RING}
    bl gc_sparks
    lwz 4, {S_DISPLAY}(31)
gsc_stream:
    cmpwi 28, {SCENE_STREAM_FROM}
    blt gsc_bond
    cmpwi 28, {SCENE_STREAM_TO}
    bgt gsc_bond
    lwz 5, {HERO_CLANK_MOBY}(30)
    cmpwi 5, 0
    beq gsc_bond
    addi 9, 28, -{SCENE_STREAM_FROM} # the comet: u of the way from the display to Clank, arched
    std 9, 0xa0(1)
    lfd 3, 0xa0(1)
    fcfid 3, 3
    frsp 3, 3
    lfs 0, {G_SCENE} + 0xc(29)
    fmuls 3, 3, 0                   # f3 = u
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    lfs 4, {P_ONE}(9)
    fsubs 4, 4, 3
    fmuls 4, 4, 3                   # f4 = u (1 - u)
    lfs 0, {P_ARC}(9)
    fmuls 4, 4, 0
    fadds 4, 4, 4
    fadds 4, 4, 4                   # 4 u (1 - u) SCENE_ARC
    lfs 0, 0x10(5)
    lfs 1, 0x10(4)
    fsubs 0, 0, 1
    fmuls 0, 0, 3
    stfs 0, {G_SCENE_STREAM}(29)
    lfs 0, 0x14(5)
    lfs 1, 0x14(4)
    fsubs 0, 0, 1
    fmuls 0, 0, 3
    stfs 0, {G_SCENE_STREAM} + 4(29)
    lfs 0, 0x18(5)
    lfs 1, 0x18(4)
    fsubs 0, 0, 1
    fmadds 0, 0, 3, 4
    stfs 0, {G_SCENE_STREAM} + 8(29)
    addi 3, 29, {G_SCENE_STREAM}
    bl gc_puffs
gsc_bond:
    cmpwi 28, {SCENE_BOND_AT}
    bne gsc_text
    li 9, 1                         # Golden Clank is his
    lis 10, {OWNED_HA}
    sth 9, {OWNED_LO}(10)
    lwz 4, {HERO_CLANK_MOBY}(30)
    cmpwi 4, 0
    beq gsc_sound
    addi 3, 29, {G_SCENE_BOND}
    bl gc_puffs
    addi 3, 29, {G_SCENE_BOND_SPARKS}
    lwz 4, {HERO_CLANK_MOBY}(30)
    bl gc_sparks
gsc_sound:
    li 3, {BUY_SOUND}
    li 4, 0
    lwz 5, 0x2080(30)
    bl {PLAY_MODEL_SOUND}
    lis 9, {CAMERA_STATE_HA}
    addi 9, 9, {CAMERA_STATE_LO}
    lis 10, {POOL_HA}
    addi 10, 10, {POOL_LO}
    lfs 0, {P_SHAKE}(10)
    stfs 0, 0x160(9)
    li 10, {SHAKE_FRAMES}
    stw 10, 0x168(9)
    stw 10, 0x16c(9)
    lwz 9, {G_GLOW_FRAMES}(29)      # and he glows as at a switch
    stw 9, {S_GLOW}(31)
gsc_text:
    cmpwi 28, {SCENE_TEXT}
    bne gsc_giant
    lis 3, {TEXT_GOT_HA}
    addi 3, 3, {TEXT_GOT_LO}
    bl gc_say
gsc_giant:
    cmpwi 28, {SCENE_GIANT}
    bne gsc_punch
    lwz 9, {S_MODE}(31)
    cmpwi 9, 0
    bne gsc_punch
    li 9, 1
    stw 9, {S_MODE}(31)
    bl gc_switch
gsc_punch:
    cmpwi 28, {SCENE_PUNCH}
    bne gsc_out
    li 9, {SQUARE}
    stw 9, {G_SCENE} + 8(29)
gsc_out:
    lfd 31, 0x90(1)
    ld 28, 0x88(1)
    ld 29, 0x80(1)
    ld 30, 0x78(1)
    ld 31, 0x70(1)
    addi 1, 1, 0xc0
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_sparks:                          # (r3 = a set as SCENE_RING, r4 = a moby): its sparks there
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0xd0(1)
    std 28, 0xb8(1)
    std 27, 0xc0(1)
    std 26, 0xc8(1)
    stfd 31, 0xb0(1)
    mr 28, 3
    mr 26, 4
    lwz 27, 0x2c(28)
gsp_one:
    cmpwi 27, 0
    ble gsp_out
    lfs 0, 0x10(26)                 # where: the moby's place and the set's "at", size 1
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
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    lfs 0, {P_ONE}(9)
    stfs 0, 0x8c(1)
    lfs 0, {P_ZERO}(9)
    stfs 0, 0x9c(1)
    li 9, 0                         # the velocity: rise and scatter on each axis
gsp_axis:
    stw 9, 0xa8(1)
    lfs 31, 0x18(28)
    fneg 1, 31
    fmr 2, 31
    bl {RANDOM}
    lwz 9, 0xa8(1)
    slwi 10, 9, 2
    addi 11, 10, 0xc
    lfsx 0, 28, 11
    fadds 1, 1, 0
    addi 11, 10, 0x90
    stfsx 1, 1, 11
    addi 9, 9, 1
    cmpwi 9, 3
    blt gsp_axis
    lwz 3, 0x24(28)
    lwz 4, 0x28(28)
    bl {RANDOM_INT}
    mr 8, 3
    addi 3, 1, 0x80
    addi 4, 1, 0x90
    lwz 5, 0x1c(28)
    lwz 6, 0x20(28)
    li 7, 0
    li 9, 1
    lfs 1, 0x30(28)
    bl {SPARK}
    addi 27, 27, -1
    b gsp_one
gsp_out:
    lfd 31, 0xb0(1)
    ld 26, 0xc8(1)
    ld 27, 0xc0(1)
    ld 28, 0xb8(1)
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
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    bl gc_late
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lis 12, {GOLD_HI}               # the gold: his light times GOLD_TINT (no moby: GOLD)
    ori 12, 12, {GOLD_LO}
    lis 10, {HERO_HA}
    addi 10, 10, {HERO_LO}
    lwz 9, 0x2080(10)
    cmpwi 9, 0
    beq gh_lit
    lwz 9, 0x38(9)
    clrlwi 8, 9, 24                 # red
    mulli 8, 8, {TINT_R}
    srwi 8, 8, 8
    cmplwi 8, 255
    ble gh_red
    li 8, 255
gh_red:
    mr 12, 8
    rlwinm 8, 9, 24, 24, 31         # green
    mulli 8, 8, {TINT_G}
    srwi 8, 8, 8
    cmplwi 8, 255
    ble gh_green
    li 8, 255
gh_green:
    slwi 8, 8, 8
    or 12, 12, 8
    rlwinm 8, 9, 16, 24, 31         # blue
    mulli 8, 8, {TINT_B}
    srwi 8, 8, 8
    cmplwi 8, 255
    ble gh_blue
    li 8, 255
gh_blue:
    slwi 8, 8, 16
    or 12, 12, 8
gh_lit:
    lwz 9, {S_COLOUR}(11)
    cmpwi 9, 0
    beq gh_parts
    mr 12, 9
gh_parts:
    lis 8, {GIANT_HA}               # his parts and the balls take it too (gc_show, gc_chain_place)
    addi 8, 8, {GIANT_LO}
    stw 12, {G_PART_COLOUR}(8)
    stw 12, {G_BALL_COLOUR}(8)
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
    lwz 3, {G_KEPT}(29)             # Ratchet's animation fields back, before his animation step
    cmpwi 3, 0
    beq gi_kept
    lis 9, {HERO_HA}                # (not into a moby gone with a level)
    addi 9, 9, {HERO_LO}
    lwz 9, 0x2080(9)
    cmpw 9, 3
    bne gi_drop
    lwz 0, {LIST_A}(3)              # (the live lists stay)
    lwz 8, {LIST_B}(3)
    addi 10, 3, {ANIM_FIELDS} - 4
    addi 11, 29, {G_KEPT_FIELDS} - 4
    li 12, {ANIM_FIELDS_SIZE} / 4
    mtctr 12
gi_restore:
    lwzu 12, 4(11)
    stwu 12, 4(10)
    bdnz gi_restore
    stw 0, {LIST_A}(3)
    stw 8, {LIST_B}(3)
gi_drop:
    li 9, 0
    stw 9, {G_KEPT}(29)
gi_kept:
    bl gc_clank_back
    bl gc_pack
    li 9, 0
    stw 9, {S_MOVES}(31)
    stw 9, {S_HELD}(31)
    lwz 9, {G_SCENE}(29)            # the purchase's scene: the pad is its
    cmpwi 9, 0
    bne gi_scene
    lwz 9, {S_PROMPT}(31)           # before Golden Clank's display: Triangle buys (the Quick Select stays shut)
    cmpwi 9, 0
    beq gi_owned
    lwz 11, 0xa4(30)
    andi. 11, 11, {TRIANGLE}
    beq gi_triangle
    li 9, 1
    stw 9, {G_SCENE} + 4(29)
gi_triangle:
    li 0, {TRIANGLE}
    bl gc_pad_take
gi_owned:
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
    lwz 9, {STATE_TYPE}(10)
    cmpwi 9, {STATE_TYPE_WATER}
    beq gi_water
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
    lwz 11, 0xa0(30)
    lwz 9, {COOP_PILOT}(31)         # two pilots (mods/coop): Player 2's buttons fire the arms
    cmpwi 9, 0
    beq gi_held
    lwz 11, {COOP_HELD}(31)
gi_held:
    andi. 12, 11, {MOVES}
    stw 12, {S_HELD}(31)
    lwz 11, 0xa4(30)
    cmpwi 9, 0
    beq gi_pressed
    lwz 11, {COOP_PRESSED}(31)
gi_pressed:
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
gi_scene:                           # nothing of the pad goes on, but the move the scene asks for
    li 0, -1
    bl gc_pad_take
    li 9, 0
    stw 9, 8(30)                    # the left stick at rest
    stw 9, 0xc(30)
    stw 9, 0x48(30)
    stw 9, 0x4c(30)
    lwz 9, {G_SCENE} + 8(29)
    stw 9, {S_MOVES}(31)
    stw 9, {S_HELD}(31)
    li 9, 0
    stw 9, {G_SCENE} + 8(29)
    b gi_out
gi_water:                           # in water: back to Ratchet, and no switching there
    lwz 9, {S_MODE}(31)
    cmpwi 9, 0
    beq gi_free
    li 9, 0
    stw 9, {S_MODE}(31)
    bl gc_switch
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
    lwz 9, {S_MODE}(31)             # for mods/coop (GC_MODE)
    stw 9, {GC_MODE}(31)
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
    lwz 3, 0x1c(30)                 # his joints first in the parts' list (PIN_JOINTS after them)
    lis 4, {GIANT_HA}
    addi 4, 4, {GIANT_LO}
    addi 4, 4, {G_JOINT_LIST}
    li 5, {OWN_JOINTS}
    mtctr 5
gi_joint:
    lwzu 6, 4(3)
    stwu 6, 4(4)
    bdnz gi_joint
    lis 28, {HEADERS_AT_HI}
    ori 28, 28, {HEADERS_AT_LO}
    add 28, 30, 28                  # r28 = the first part's header
    li 27, {PART_COUNT}
gi_part:                            # each part: the model's header and mesh with its own index buffer
    mr 3, 28
    mr 4, 30
    li 5, {HEADER}
    bl {COPY}
    lis 4, {GIANT_HA}               # its joint list
    addi 4, 4, {GIANT_LO}
    addi 4, 4, {G_JOINT_LIST}
    stw 4, 0x1c(28)
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
    lwz 4, 0x18(30)                 # the arms' skeleton of their own (ARMS_SHOULDERS)
    lis 3, {GIANT_HA}
    addi 3, 3, {GIANT_LO}
    addi 3, 3, {G_ARMS_BONES}
    li 5, {BONES} * 0x10
    bl {COPY}
    lis 3, {GIANT_HA}
    addi 3, 3, {GIANT_LO}
    lfs 0, {G_ARMS_SHOULDERS}(3)
    addi 3, 3, {G_ARMS_BONES}
    stfs 0, {ARMS_LEFT} * 0x10 + 4(3)
    fneg 0, 0
    stfs 0, {ARMS_RIGHT} * 0x10 + 4(3)
    lis 4, {HEADERS_AT_HI}
    ori 4, 4, {HEADERS_AT_LO}
    add 4, 30, 4
    stw 3, {PART_ARMS} * {HEADER} + 0x18(4)
    lis 3, {BALL_HEADER_HI}         # the ball has a vertex buffer of its own, behind the index buffers
    ori 3, 3, {BALL_HEADER_LO}
    add 3, 30, 3
    lwz 3, 0(3)                     # its mesh
    lis 4, {IBS_AT_HI}
    ori 4, 4, {IBS_AT_LO}
    add 4, 30, 4
    lis 5, {BALL_VB_HI}
    ori 5, 5, {BALL_VB_LO}
    add 4, 4, 5
    lis 5, {GCM_PTR_HA}
    lwz 5, {GCM_PTR_LO}(5)
    lwz 5, 0x4a8(5)
    subf 4, 5, 4
    stw 4, 0x10(3)
    lis 6, {STRUT_VB_HI}            # the tubes share one (TUBES), behind the ball's
    ori 6, 6, {STRUT_VB_LO}
    add 4, 4, 6
    lis 6, {BALL_VB_HI}
    ori 6, 6, {BALL_VB_LO}
    subf 4, 6, 4                    # r4 = the ball's offset + STRUT_VB - BALL_VB
    lis 3, {HEADERS_AT_HI}
    ori 3, 3, {HEADERS_AT_LO}
    add 3, 30, 3
    lwz 5, {PART_STRUT_L} * {HEADER}(3)
    stw 4, 0x10(5)
    lwz 5, {PART_STRUT_R} * {HEADER}(3)
    stw 4, 0x10(5)
    lwz 5, {PART_COLUMN} * {HEADER}(3)
    stw 4, 0x10(5)
    lis 3, {GRAPHICS_HEAP_HA}       # r28 = the pixels again (the parts' loop took it)
    addi 3, 3, {GRAPHICS_HEAP_LO}
    lwz 28, 0xc(3)
@EXTRA_MODELS@
    lis 26, {EYE_ENTRY_AT_HI}       # the gold eyes: their entry behind the missile's, their pixels behind its
    ori 26, 26, {EYE_ENTRY_AT_LO}
    add 26, 30, 26                  # r26 = the entry
    mr 3, 26
    lis 4, {EYE_TEXTURE_HA}
    addi 4, 4, {EYE_TEXTURE_LO}
    li 5, 0x24
    bl {COPY}
    lis 3, {EYE_PIXELS_AT_HI}
    ori 3, 3, {EYE_PIXELS_AT_LO}
    add 3, 28, 3
    lis 4, {EYE_TEXTURE_HA}
    addi 4, 4, {EYE_TEXTURE_LO} + 0x80
    lis 5, {EYE_PIXELS_SIZE_HI}
    ori 5, 5, {EYE_PIXELS_SIZE_LO}
    bl {COPY}
    lis 3, {GCM_PTR_HA}
    lwz 3, {GCM_PTR_LO}(3)
    lwz 3, 0x4ac(3)
    lis 4, {EYE_PIXELS_AT_HI}
    ori 4, 4, {EYE_PIXELS_AT_LO}
    add 4, 28, 4
    subf 3, 3, 4
    stw 3, 0(26)
    lis 9, {GIANT_HA}
    addi 9, 9, {GIANT_LO}
    stw 26, {G_EYE_ENTRY}(9)
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
    std 26, 0x98(1)
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
    li 26, 0                        # r26 = his parts may show
    lwz 9, {S_MODE}(31)
    cmpwi 9, 0
    beq gq_allowed
    lbz 9, {HERO_KIND}(30)
    cmpwi 9, 0
    bne gq_allowed
    lwz 9, 0x2084(30)
    cmpwi 9, {FREE_A}
    beq gq_allowed
    cmpwi 9, {FREE_B}
    beq gq_allowed
    cmpwi 9, {FREE_C}
    beq gq_allowed
    bl gc_install
    bl gc_sounds
    lwz 26, {S_MODEL}(31)
gq_allowed:
    bl gc_shock
    li 28, 0
    cmpwi 26, 0
    beq gq_legs_show
    li 3, 1 + {PART_LEGS}
    bl gc_model
    mr 28, 3
gq_legs_show:
    addi 3, 31, {S_LEGS}
    mr 4, 28
    bl gc_show
    mr. 27, 3
    beq gq_punch
    lwz 4, {G_JUMP_ANIM}(29)        # jumping, walking at his speed, or standing (and hovering)
    lwz 9, {STATE_TYPE}(30)
    cmpwi 9, {STATE_TYPE_JUMP}
    beq gq_legs_anim
    li 4, {IDLE_ANIM}
    lwz 9, 0x2084(30)
    cmpwi 9, {HOVER_A}
    beq gq_legs_anim
    cmpwi 9, {HOVER_B}
    beq gq_legs_anim
    lfs 1, 0x194(30)
    lfs 2, {G_WALK_FROM}(29)
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
    mr 3, 27
    addi 4, 29, {G_LEGS_SCALE}
    bl gc_place
    bl gc_flames
gq_punch:                           # Square, Circle, Triangle: a move, one at a time
    bl gc_flame_sound
    bl gc_leg
    li 28, 0                        # the part's model, 0 = none
    cmpwi 26, 0
    bne gq_move_may
    lwz 9, {S_PUNCH}(31)            # not now: a move going on ends
    cmpwi 9, 0
    beq gq_part_show
    li 9, 0
    stw 9, {S_PUNCH}(31)
    bl gc_arm_off
    b gq_part_show
gq_move_may:
    lwz 9, {S_PUNCH}(31)
    cmpwi 9, 0
    bne gq_moving
    lwz 9, {S_MOVES}(31)
    li 10, 0
    andi. 11, 9, {SQUARE}
    bne gq_move_start
    li 10, 1
    andi. 11, 9, {CIRCLE_BUTTON}
    bne gq_move_start
    li 10, 2
    andi. 11, 9, {TRIANGLE}
    beq gq_part_show
    lwz 11, {S_BOMB_WAIT}(31)       # (not before the bomb is ready)
    cmpwi 11, 0
    bne gq_part_show
gq_move_start:
    stw 10, {S_MOVE}(31)
    li 9, 0
    stw 9, {G_PUNCH_STOP}(29)
    lwz 9, {S_SIDE}(31)
    xori 9, 9, 1
    stw 9, {S_SIDE}(31)
    li 9, 1
    stw 9, {S_PUNCH}(31)
    bl gc_arm_on
gq_moving:
    bl gc_move_record
    lwz 9, {S_PUNCH}(31)
    lwz 10, {M_FRAMES}(3)
    cmpw 9, 10
    ble gq_move_on
    li 9, 0
    stw 9, {S_PUNCH}(31)
    bl gc_arm_off
    b gq_part_show
gq_move_on:
    lwz 4, {M_PART}(3)
    cmpwi 4, 0
    blt gq_part_show                # (none)
    lwz 9, {M_SIDED}(3)
    cmpwi 9, 0
    beq gq_part_model
    lwz 9, {S_SIDE}(31)
    add 4, 4, 9
gq_part_model:
    mr 3, 4
    bl gc_model
    mr 28, 3
gq_part_show:                       # (placed by gc_move_place, at the end of the frame)
    addi 3, 31, {S_FIST}
    mr 4, 28
    bl gc_show
    mr. 27, 3
    beq gq_action
    bl gc_move_record
    lwz 4, {M_ANIM}(3)              # its animation, then his idle
    lwz 9, {M_SIDED}(3)
    cmpwi 9, 0
    beq gq_anim_side
    lwz 9, {S_SIDE}(31)
    add 4, 4, 9
gq_anim_side:
    li 6, {ANIM_BLEND}
    lwz 9, {S_PUNCH}(31)
    lwz 10, {M_IDLE}(3)
    cmpw 9, 10
    ble gq_part_anim
    li 4, {IDLE_ANIM}
    lwz 6, {M_BLEND}(3)
gq_part_anim:
    lfs 0, {M_RATE}(3)
    stfs 0, 0x58(27)
    addi 3, 31, {S_FIST}
    bl gc_anim_blend
gq_action:
    lwz 9, {S_PUNCH}(31)
    cmpwi 9, 0
    beq gq_move_next
    bl gc_move_record               # its sound (MOVE_SOUNDS), then its action
    lwz 9, {S_PUNCH}(31)
    lha 10, {M_SOUND} + 2(3)
    cmpw 9, 10
    bne gq_action_frame
    lha 3, {M_SOUND}(3)
    bl gc_giant_sound
    bl gc_move_record
    lwz 9, {S_PUNCH}(31)
gq_action_frame:
    lwz 10, {M_ACTION}(3)
    cmpw 9, 10
    bne gq_move_next
    lwz 9, {S_MOVE}(31)
    cmpwi 9, 1
    blt gq_hit
    beq gq_missiles
    bl gc_bomb
    b gq_move_next
gq_missiles:
    cmpwi 27, 0                     # (they leave from the arms)
    beq gq_move_next
    mr 3, 27
    bl gc_missiles
    b gq_move_next
gq_hit:
    bl gc_hit
gq_move_next:
    lwz 9, {S_PUNCH}(31)
    cmpwi 9, 0
    beq gq_chains
    bl gc_move_record               # held: once more, from where it has grown
    lwz 10, {M_IDLE}(3)
    cmpw 9, 10
    bne gq_move_count
    lwz 10, {M_REPEAT}(3)
    lwz 11, {S_HELD}(31)
    and. 10, 10, 11
    beq gq_move_count
    lwz 9, {M_ACTION}(3)            # (counted up below: its action is the next frame)
    addi 9, 9, -1
    li 10, -1                       # (its animation set again)
    stw 10, {S_FIST} + 8(31)
gq_move_count:
    lwz 10, {G_PUNCH_STOP}(29)      # the punch's hit-stop: its frame stands
    cmpwi 10, 0
    ble gq_move_add
    addi 10, 10, -1
    stw 10, {G_PUNCH_STOP}(29)
    b gq_chains
gq_move_add:
    addi 9, 9, 1
    stw 9, {S_PUNCH}(31)
gq_chains:
    li 3, 0                         # the bomb's cooldown; ready: Clank's eyes are gold
    lwz 9, {S_BOMB_WAIT}(31)
    cmpwi 9, 0
    ble gq_eyes
    addi 9, 9, -1
    stw 9, {S_BOMB_WAIT}(31)
    b gq_eyes_set
gq_eyes:
    cmpwi 26, 0
    beq gq_eyes_set
    li 3, 1
gq_eyes_set:
    bl gc_eyes
    lwz 4, {S_LEGS}(31)
    addi 5, 29, {G_CHAIN_LEGS}
    addi 6, 29, {G_BALLS}
    bl gc_chain
    bl gc_arm_chains
gq_out:
    ld 26, 0x98(1)
    ld 27, 0x90(1)
    ld 28, 0x88(1)
    ld 29, 0x80(1)
    ld 30, 0x78(1)
    ld 31, 0x70(1)
    addi 1, 1, 0xb0
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_chain:                           # (r4 = the part's moby, 0 = none; r5 = a chain, r6 = its records; r29/r31): grown, shown
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x90(1)
    std 28, 0x70(1)
    std 27, 0x78(1)
    std 26, 0x80(1)
    mr 28, 5
    mr 27, 6
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    lfs 0, {C_GROWN}(28)            # out towards the part while it is there, back in when it goes
    lfs 1, {G_GROW_STEP}(29)
    cmpwi 4, 0
    bne gc_grow
    fneg 1, 1
gc_grow:
    fadds 0, 0, 1
    lfs 1, {P_ZERO}(9)
    fsel 0, 0, 0, 1                 # at least 0
    lfs 1, {P_ONE}(9)
    fsubs 2, 0, 1
    fsel 0, 2, 1, 0                 # at most 1
    stfs 0, {C_GROWN}(28)
    lfs 1, {P_ZERO}(9)
    fcmpu 0, 0, 1
    li 26, 0                        # r26 = the ball model, 0 = none
    beq gc_balls
    li 3, 1 + {PART_BALL}
    bl gc_model
    mr 26, 3
gc_balls:
    lwz 9, {C_COUNT}(28)
    cmpwi 9, {CHAIN_MAX}
    ble gc_count
    li 9, {CHAIN_MAX}
gc_count:
    mr 28, 9                        # r28 = the balls wanted
    li 5, 0
gc_ball:
    std 5, 0x88(1)
    mr 4, 26
    cmpw 5, 28
    blt gc_show_ball
    li 4, 0
gc_show_ball:
    mr 3, 27
    bl gc_show
    cmpwi 3, 0
    beq gc_next_ball
    li 9, 0                         # held at its first frame
    stw 9, 0x58(3)
    mr 3, 27
    lwz 4, {G_BALL_ANIM}(29)
    bl gc_anim
gc_next_ball:
    addi 27, 27, 0x10
    ld 5, 0x88(1)
    addi 5, 5, 1
    cmpwi 5, {CHAIN_MAX}
    blt gc_ball
    ld 26, 0x80(1)
    ld 27, 0x78(1)
    ld 28, 0x70(1)
    addi 1, 1, 0x90
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_arm_chains:                      # (r29/r31): the arms' chains grown while the move's part has that arm out (M_BALLS)
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 28, 0x70(1)
    li 28, 0                        # r28 = the sides out: 1 left, 2 right
    lwz 9, {S_FIST}(31)
    cmpwi 9, 0
    beq gac_go
    bl gc_move_record
    lwz 9, {M_BALLS}(3)
    li 28, 3
    cmpwi 9, 2
    beq gac_go
    li 28, 0
    cmpwi 9, 1
    bne gac_go
    lwz 9, {S_SIDE}(31)
    li 28, 1
    slw 28, 28, 9
gac_go:
    andi. 4, 28, 1                  # r4 = the part's moby, or 0
    beq gac_left
    lwz 4, {S_FIST}(31)
gac_left:
    addi 5, 29, {G_ARM_CHAINS}
    addi 6, 29, {G_ARM_BALLS}
    bl gc_chain
    andi. 4, 28, 2
    beq gac_right
    lwz 4, {S_FIST}(31)
gac_right:
    addi 5, 29, {G_ARM_CHAINS} + {CHAIN_SIZE}
    addi 6, 29, {G_ARM_BALLS} + {CHAIN_MAX} * 0x10
    bl gc_chain
    ld 28, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_chains:                          # (r29/r30/r31): the balls placed, from Clank towards the legs
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0xa0(1)
    lfs 1, 0x98(30)
    bl {COS}
    stfs 1, 0x80(1)
    lfs 1, 0x98(30)
    bl {SIN}
    lfs 13, 0x80(1)                 # f13 = cos, f12 = sin (gc_chain_place calls nothing, and keeps them)
    fmr 12, 1
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    lfs 11, {P_ONE}(9)              # f11 = 1, the side
    addi 3, 29, {G_CHAIN_LEGS}
    addi 4, 29, {G_BALLS}
    bl gc_chain_place
    lis 9, {POOL_HA}                # the arms' chains: the left's, then the right's mirrored
    addi 9, 9, {POOL_LO}
    lfs 11, {P_ONE}(9)
    addi 3, 29, {G_ARM_CHAINS}
    addi 4, 29, {G_ARM_BALLS}
    bl gc_chain_place
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    lfs 11, {P_ONE}(9)
    fneg 11, 11
    addi 3, 29, {G_ARM_CHAINS} + {CHAIN_SIZE}
    addi 4, 29, {G_ARM_BALLS} + {CHAIN_MAX} * 0x10
    bl gc_chain_place
    addi 1, 1, 0xa0
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_move_record:                     # (r29/r31) -> r3 = the move's record in MOVE_TABLE (leaf)
    lwz 3, {S_MOVE}(31)
    mulli 3, 3, {MOVE_SIZE}
    addi 3, 3, {G_MOVES}
    add 3, 29, 3
    blr

gc_arm_on:                          # (r29/r30/r31): the manipulator onto Clank's bone of the move (the pack's moby), if any
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lwz 3, {G_ARM_MOBY}(29)
    cmpwi 3, 0
    bne ga_on_out
    lbz 9, {G_MANIP} + 1(29)
    cmpwi 9, 0
    bne ga_on_out
    bl gc_move_record               # its bone, -1 = none
    lwz 9, {M_SIDED}(3)
    cmpwi 9, 0
    beq ga_on_bone
    lwz 9, {S_SIDE}(31)
    slwi 9, 9, 2
    add 3, 3, 9
ga_on_bone:
    lwz 11, {M_BONES}(3)
    cmpwi 11, 0
    blt ga_on_out
    lwz 3, {HERO_PACK_MOBY}(30)
    cmpwi 3, 0
    beq ga_on_out
    stw 3, {G_ARM_MOBY}(29)
    slwi 11, 11, 6
    addis 11, 11, 0x7000
    stw 11, {G_MANIP} + 4(29)
    li 9, 0                         # as 0xf0ea8 would, without the joint list
    stw 9, {G_MANIP}(29)
    li 9, 1
    stb 9, {G_MANIP} + 1(29)
    stb 9, {G_MANIP} + 3(29)
    lis 9, {POOL_HA}                # weight 1, no rotation, scale 0: the bone and all below it gone
    addi 9, 9, {POOL_LO}
    lfs 0, {P_ONE}(9)
    lfs 1, {P_ZERO}(9)
    stfs 0, {G_MANIP} + 0xc(29)
    stfs 1, {G_MANIP} + 0x10(29)
    stfs 1, {G_MANIP} + 0x14(29)
    stfs 1, {G_MANIP} + 0x18(29)
    stfs 0, {G_MANIP} + 0x1c(29)
    stfs 1, {G_MANIP} + 0x20(29)
    stfs 1, {G_MANIP} + 0x24(29)
    stfs 1, {G_MANIP} + 0x28(29)
    stfs 1, {G_MANIP} + 0x2c(29)
    stfs 1, {G_MANIP} + 0x30(29)
    stfs 1, {G_MANIP} + 0x34(29)
    stfs 1, {G_MANIP} + 0x38(29)
    stfs 1, {G_MANIP} + 0x3c(29)
    lwz 9, 0x64(3)
    stw 9, {G_MANIP} + 8(29)
    addi 9, 29, {G_MANIP}
    stw 9, 0x64(3)
ga_on_out:
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_leg:                             # (r29/r30/r31): Clank's leg onto the gold legs while they are out (CLANK_LEG)
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lwz 9, {G_LEG_TARGET}(29)
    lwzx 3, 30, 9
    lwz 11, {G_LEG_MOBY}(29)
    lwz 9, {S_LEGS}(31)
    cmpwi 9, 0
    beq gk_off
    lwz 9, {G_LEG}(29)
    cmpwi 9, 0
    beq gk_off
    cmpwi 3, 0
    beq gk_off
    cmpw 11, 3
    beq gk_fill
    cmpwi 11, 0
    bne gk_off                      # on another moby: off first, on again next frame
    stw 3, {G_LEG_MOBY}(29)
    li 9, 0
    stw 9, {G_LEG_MANIP}(29)
    li 9, 1
    stb 9, {G_LEG_MANIP} + 3(29)
    lwz 9, 0x64(3)                  # in front of his list
    stw 9, {G_LEG_MANIP} + 8(29)
    addi 9, 29, {G_LEG_MANIP}
    stw 9, 0x64(3)
gk_fill:
    lwz 9, {G_LEG_BONE}(29)
    slwi 9, 9, 6
    addis 9, 9, 0x7000
    stw 9, {G_LEG_MANIP} + 4(29)
    lis 9, {POOL_HA}                # weight 1, no turn, scale 1, the place
    addi 9, 9, {POOL_LO}
    lfs 0, {P_ONE}(9)
    lfs 1, {P_ZERO}(9)
    stfs 0, {G_LEG_MANIP} + 0xc(29)
    stfs 1, {G_LEG_MANIP} + 0x10(29)
    stfs 1, {G_LEG_MANIP} + 0x14(29)
    stfs 1, {G_LEG_MANIP} + 0x18(29)
    stfs 0, {G_LEG_MANIP} + 0x1c(29)
    stfs 0, {G_LEG_MANIP} + 0x20(29)
    stfs 0, {G_LEG_MANIP} + 0x24(29)
    stfs 0, {G_LEG_MANIP} + 0x28(29)
    stfs 0, {G_LEG_MANIP} + 0x2c(29)
    lfs 1, {G_LEG_AT}(29)
    stfs 1, {G_LEG_MANIP} + 0x30(29)
    lfs 1, {G_LEG_AT} + 4(29)
    stfs 1, {G_LEG_MANIP} + 0x34(29)
    lfs 1, {G_LEG_AT} + 8(29)
    stfs 1, {G_LEG_MANIP} + 0x38(29)
    stfs 0, {G_LEG_MANIP} + 0x3c(29)
    li 9, 1                         # on (last)
    stb 9, {G_LEG_MANIP} + 1(29)
    b gk_out
gk_off:
    cmpwi 11, 0
    beq gk_out
    li 9, 0
    stw 9, {G_LEG_MOBY}(29)
    lwz 9, {HERO_CLANK_MOBY}(30)    # still Clank or the pack (the target may have changed)?
    cmpw 9, 11
    beq gk_remove
    lwz 9, {HERO_PACK_MOBY}(30)
    cmpw 9, 11
    bne gk_clear                    # (a moby gone: only the record is cleared)
gk_remove:
    mr 3, 11
    addi 4, 29, {G_LEG_MANIP}
    bl {MANIP_REMOVE}
gk_clear:
    li 9, 0
    stw 9, {G_LEG_MANIP}(29)
gk_out:
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_arm_off:                         # (r29/r30): the manipulator off again
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lwz 3, {G_ARM_MOBY}(29)
    cmpwi 3, 0
    beq ga_off_out
    li 9, 0
    stw 9, {G_ARM_MOBY}(29)
    lwz 9, {HERO_PACK_MOBY}(30)
    cmpw 9, 3
    bne ga_off_clear                # (a moby gone: only the record is cleared)
    addi 4, 29, {G_MANIP}
    bl {MANIP_REMOVE}
ga_off_clear:
    li 9, 0
    stw 9, {G_MANIP}(29)
ga_off_out:
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_move_place:                      # (r29/r30/r31): the move's part, grown out of its spot on Clank
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0xc0(1)
    std 28, 0x70(1)
    lwz 9, {S_PUNCH}(31)
    cmpwi 9, 0
    beq gmp_out
    lwz 9, {S_FIST}(31)
    cmpwi 9, 0
    beq gmp_out
    lfs 1, 0x98(30)
    bl {COS}
    stfs 1, 0x80(1)
    lfs 1, 0x98(30)
    bl {SIN}
    stfs 1, 0x84(1)
    bl gc_move_record
    mr 28, 3                        # r28 = the move
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    lfs 13, {P_ONE}(9)              # f13 = the side: 1, or -1 for a sided move's right
    lwz 11, {M_SIDED}(28)
    cmpwi 11, 0
    beq gmp_side
    lwz 11, {S_SIDE}(31)
    cmpwi 11, 0
    beq gmp_side
    fneg 13, 13
gmp_side:
    lwz 9, {S_PUNCH}(31)            # its scale: grown over B frames, shrunk over the last "shrink"
    lwz 11, {M_FRAMES}(28)
    subf 12, 9, 11
    addi 12, 12, 1                  # F - f + 1
    addi 9, 9, -{ARM_DELAY}         # (grown from ARM_DELAY on)
    extsw 9, 9
    std 9, 0x88(1)
    lfd 1, 0x88(1)
    fcfid 1, 1
    frsp 1, 1
    lwz 9, {M_GROW}(28)
    extsw 9, 9
    std 9, 0x88(1)
    lfd 2, 0x88(1)
    fcfid 2, 2
    frsp 2, 2
    fdivs 1, 1, 2                   # f / B
    extsw 12, 12
    std 12, 0x88(1)
    lfd 2, 0x88(1)
    fcfid 2, 2
    frsp 2, 2
    lwz 9, {M_SHRINK}(28)
    extsw 9, 9
    std 9, 0x88(1)
    lfd 3, 0x88(1)
    fcfid 3, 3
    frsp 3, 3
    fdivs 2, 2, 3                   # (F - f + 1) / shrink
    fsubs 3, 2, 1
    fsel 1, 3, 1, 2                 # the smaller
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    lfs 0, {P_ONE}(9)
    fsubs 2, 1, 0
    fsel 1, 2, 0, 1                 # at most 1
    lfs 0, {P_ARM_LEAST}(9)
    fsubs 2, 1, 0
    fsel 1, 2, 1, 0                 # at least ARM_LEAST
    lfs 0, {M_SCALE}(28)
    fmuls 1, 1, 0                   # f1 = its scale
    lwz 3, {S_FIST}(31)
    stfs 1, 0x2c(3)
    lfs 2, {M_SPOT}(28)             # where: the spot less its anchor at that scale (forward f2, left f3, up f4)
    lfs 0, {M_ANCHOR}(28)
    fnmsubs 2, 1, 0, 2
    lfs 3, {M_SPOT} + 4(28)
    lfs 0, {M_ANCHOR} + 4(28)
    fnmsubs 3, 1, 0, 3
    fmuls 3, 3, 13
    lfs 4, {M_SPOT} + 8(28)
    lfs 0, {M_ANCHOR} + 8(28)
    fnmsubs 4, 1, 0, 4
    lfs 0, {G_LIFT}(29)
    fadds 4, 4, 0
    lfs 5, 0x80(1)                  # cos, sin
    lfs 6, 0x84(1)
    lfs 0, {G_RIDER}(29)
    fmadds 0, 2, 5, 0
    fnmsubs 0, 3, 6, 0
    stfs 0, 0x10(3)
    lfs 0, {G_RIDER} + 4(29)
    fmadds 0, 2, 6, 0
    fmadds 0, 3, 5, 0
    stfs 0, 0x14(3)
    lfs 0, 0x88(30)
    fadds 0, 0, 4
    stfs 0, 0x18(3)
    lfs 0, 0x98(30)
    lfs 1, {M_TURN}(28)
    fmadds 0, 1, 13, 0              # (mirrored for a sided move's right)
    stfs 0, 0x48(3)
    stfs 13, 0xb0(1)
    bl gc_punch_pose                # (before its joint is read)
    lfs 13, 0xb0(1)
    lwz 4, {M_PIN}(28)              # pinned: its joint onto the spot (PIN_JOINTS)
    cmpwi 4, 0
    blt gmp_out
    lwz 11, {M_SIDED}(28)
    cmpwi 11, 0
    beq gmp_pin
    lwz 11, {S_SIDE}(31)
    add 4, 4, 11
gmp_pin:
    lfs 2, {M_SPOT}(28)             # the spot (forward f2, left f3, up f4) in the world: 0xa0(1)
    lfs 3, {M_SPOT} + 4(28)
    fmuls 3, 3, 13
    lfs 4, {M_SPOT} + 8(28)
    lfs 0, {G_LIFT}(29)
    fadds 4, 4, 0
    lfs 5, 0x80(1)
    lfs 6, 0x84(1)
    lfs 0, {G_RIDER}(29)
    fmadds 0, 2, 5, 0
    fnmsubs 0, 3, 6, 0
    stfs 0, 0xa0(1)
    lfs 0, {G_RIDER} + 4(29)
    fmadds 0, 2, 6, 0
    fmadds 0, 3, 5, 0
    stfs 0, 0xa4(1)
    lfs 0, 0x88(30)
    fadds 0, 0, 4
    stfs 0, 0xa8(1)
    lwz 3, {S_FIST}(31)
    addi 5, 1, 0x90
    bl {JOINT_POSITION}
    lwz 3, {S_FIST}(31)             # its place less the joint's from it, on the spot; the joint's place
    lwz 4, 0x24(3)                  # leaves out the model's scale (+0x24, his 0.75), the drawing does not
    lfs 3, 0x24(4)
    lfs 0, 0x10(3)
    lfs 1, 0x90(1)
    fsubs 1, 1, 0
    lfs 2, 0xa0(1)
    fnmsubs 2, 1, 3, 2
    stfs 2, 0x10(3)
    lfs 0, 0x14(3)
    lfs 1, 0x94(1)
    fsubs 1, 1, 0
    lfs 2, 0xa4(1)
    fnmsubs 2, 1, 3, 2
    stfs 2, 0x14(3)
    lfs 0, 0x18(3)
    lfs 1, 0x98(1)
    fsubs 1, 1, 0
    lfs 2, 0xa8(1)
    fnmsubs 2, 1, 3, 2
    stfs 2, 0x18(3)
gmp_out:
    ld 28, 0x70(1)
    addi 1, 1, 0xc0
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_punch_pose:                      # (r28 = the move, r29/r31): the punch's frame from how far into it (PUNCH_POSE)
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    lwz 9, {G_POSE}(29)
    cmpwi 9, 0
    beq gpp_out
    lwz 9, {S_MOVE}(31)
    cmpwi 9, 0
    bne gpp_out
    lwz 9, {S_PUNCH}(31)
    extsw 9, 9
    std 9, 0x70(1)
    lfd 1, 0x70(1)
    fcfid 1, 1
    frsp 1, 1                       # f1 = its frame
    lfs 2, {G_POSE} + 4(29)         # wind, strike, peak, hold, back
    lfs 3, {G_POSE} + 8(29)
    lfs 10, {G_POSE} + 0xc(29)
    lfs 4, {G_POSE} + 0x10(29)
    lfs 5, {G_POSE} + 0x14(29)
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    lfs 6, {P_ONE}(9)
    lfs 7, {P_ZERO}(9)
    lfs 11, {P_TWO}(9)
    lfs 12, {P_THREE}(9)
    fmr 8, 7                        # the wind-up: frame 0, the fist drawn back
    fcmpu 0, 1, 2
    ble gpp_set
    fsubs 0, 1, 2                   # the strike: up to the peak, evenly
    fcmpu 0, 0, 3
    bgt gpp_hold
    fdivs 0, 0, 3
    fmuls 8, 0, 10
    b gpp_set
gpp_hold:
    fsubs 0, 0, 3
    fsubs 0, 0, 4
    fmr 8, 10                       # held at the peak, then back: peak (1 - smoothstep(v)), v at most 1
    fcmpu 0, 0, 7
    ble gpp_set
    fdivs 0, 0, 5
    fsubs 9, 0, 6
    fsel 0, 9, 6, 0
    fmuls 9, 0, 0
    fnmsubs 13, 11, 0, 12
    fmuls 9, 9, 13
    fsubs 9, 6, 9
    fmuls 8, 10, 9
gpp_set:
    fctiwz 0, 8                     # its two frames and the blend between them
    stfd 0, 0x70(1)
    lwz 9, 0x74(1)
    extsw 10, 9
    std 10, 0x78(1)
    lfd 0, 0x78(1)
    fcfid 0, 0
    frsp 0, 0
    fsubs 8, 8, 0
    lwz 3, {S_FIST}(31)
    stb 9, 0x50(3)
    addi 9, 9, 1
    cmpwi 9, {PUNCH_LAST}           # (past its last frame the game read beyond the animation and crashed)
    ble gpp_frame
    li 9, {PUNCH_LAST}
gpp_frame:
    stb 9, 0x51(3)
    lwz 9, {M_ANIM}(28)
    lwz 10, {S_SIDE}(31)
    add 9, 9, 10
    stb 9, 0x52(3)
    stb 9, 0x53(3)
    stfs 8, 0x54(3)
    stfs 7, 0x58(3)
    bl {FRAME_POINTERS}
gpp_out:
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_register:                        # (r3 = a model or 0, r4 = a class) -> r3 = 0 when the level has no slot for it
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 31, 0x70(1)
    mr 31, 4
    lis 9, {CLASS_SLOT_MAP_HA}      # there already (the level's, or ours)?
    addi 9, 9, {CLASS_SLOT_MAP_LO}
    lbzx 10, 9, 31
    lis 11, {SLOT_COUNT_HA}
    lwz 12, {SLOT_COUNT_LO}(11)
    cmplw 10, 12
    bge gr_new
    lis 7, {SLOT_CLASS_HA}
    addi 7, 7, {SLOT_CLASS_LO}
    slwi 8, 10, 1
    lhzx 8, 7, 8
    cmpw 8, 31
    beq gr_ok
gr_new:                             # the next slot, as 0xdc0ec fills it (without the fix-up: done once)
    cmplwi 12, {MODEL_SLOTS}
    bge gr_none
    stbx 12, 9, 31
    lis 7, {SLOT_CLASS_HA}
    addi 7, 7, {SLOT_CLASS_LO}
    slwi 8, 12, 1
    sthx 31, 7, 8
    lis 7, {MODEL_TABLE_HA}
    addi 7, 7, {MODEL_TABLE_LO}
    slwi 8, 12, 2
    stwx 3, 7, 8
    cmpwi 3, 0
    beq gr_update
    lwz 6, 0x2c(3)
    lis 7, {SLOT_INFO_HA}
    addi 7, 7, {SLOT_INFO_LO}
    stwx 6, 7, 8
gr_update:
    mr 3, 31
    bl {CLASS_UPDATE}
    lis 11, {SLOT_COUNT_HA}
    lwz 12, {SLOT_COUNT_LO}(11)
    addi 12, 12, 1
    stw 12, {SLOT_COUNT_LO}(11)
gr_ok:
    li 3, 1
    b gr_out
gr_none:
    li 3, 0
gr_out:
    ld 31, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_missiles:                        # (r3 = the arms' moby; r29/r30): two missiles from the forearms' ends
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0xc0(1)
    std 31, 0x70(1)
    std 28, 0x78(1)
    mr 31, 3
    lwz 3, {G_MISSILE_MODEL}(29)
    cmpwi 3, 0
    beq gm_out
    li 4, {MISSILE_CLASS}
    bl gc_register
    cmpwi 3, 0
    beq gm_out
    li 28, {MISSILE_JOINTS_FIRST}
gm_one:
    mr 3, 31
    mr 4, 28
    addi 5, 1, 0x90
    bl {JOINT_POSITION}
    lfs 1, 0x98(30)
    bl {COS}
    lfs 0, {G_MISSILE_AHEAD}(29)
    lfs 2, 0x90(1)
    fmadds 2, 1, 0, 2
    stfs 2, 0x90(1)
    lfs 1, 0x98(30)
    bl {SIN}
    lfs 0, {G_MISSILE_AHEAD}(29)
    lfs 2, 0x94(1)
    fmadds 2, 1, 0, 2
    stfs 2, 0x94(1)
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    lwz 3, 0x2080(30)
    addi 4, 1, 0x90
    lfs 1, 0x98(30)
    lfs 2, {P_ZERO}(9)
    lfs 3, {P_HALF}(9)
    fmr 4, 1
    fmr 5, 2
    li 7, 0
    bl {MISSILE_SPAWN}
    cmpwi 3, 0                      # (the missile, or 0) at MISSILE_SIZE of the size it got
    beq gm_next
    lfs 0, 0x2c(3)
    lfs 1, {G_MISSILE_SIZE}(29)
    fmuls 0, 0, 1
    stfs 0, 0x2c(3)
gm_next:
    addi 28, 28, 1
    cmpwi 28, {MISSILE_JOINTS_LAST}
    ble gm_one
gm_out:
    ld 28, 0x78(1)
    ld 31, 0x70(1)
    addi 1, 1, 0xc0
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_eyes:                            # (r3 = 1 gold, 0 his own; r29/r30): backpack Clank's eyes' texture (leaf)
    lwz 4, {HERO_CLANK_MOBY}(30)
    cmpwi 4, 0
    beqlr
    lwz 5, {G_EYE_ENTRY}(29)
    cmpwi 5, 0
    beqlr
    lwz 4, 0x24(4)                  # his model's mesh: its eyes' group
    lwz 4, 0(4)
    lwz 6, 0(4)
    cmpwi 6, {EYE_GROUP}
    blelr
    lwz 4, 8(4)
    addi 4, 4, {EYE_GROUP} * 0x10
    lwz 6, 0(4)
    cmpwi 3, 0
    beq ge_own
    cmpw 6, 5
    beqlr
    stw 6, {G_EYE_OWN}(29)
    stw 5, 0(4)
    blr
ge_own:
    cmpw 6, 5
    bnelr
    lwz 6, {G_EYE_OWN}(29)
    stw 6, 0(4)
    blr

gc_bomb:                            # (r29/r30/r31): the bomb, ahead of Ratchet and up, and its cooldown
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0xa0(1)
    li 3, 0
    li 4, {BOMB_CLASS}
    bl gc_register
    cmpwi 3, 0
    beq gb_out
    lfs 1, 0x98(30)
    bl {COS}
    lfs 0, {G_BOMB_AT}(29)
    lfs 2, 0x80(30)
    fmadds 2, 1, 0, 2
    stfs 2, 0x80(1)
    lfs 1, 0x98(30)
    bl {SIN}
    lfs 0, {G_BOMB_AT}(29)
    lfs 2, 0x84(30)
    fmadds 2, 1, 0, 2
    stfs 2, 0x84(1)
    lfs 0, {G_BOMB_AT} + 4(29)
    lfs 2, 0x88(30)
    fadds 2, 2, 0
    stfs 2, 0x88(1)
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    lfs 0, {P_ZERO}(9)
    stfs 0, 0x8c(1)
    ld 5, 0x80(1)
    ld 6, 0x88(1)
    bl {BOMB_SPAWN}
    lwz 9, {G_BOMB_COOLDOWN}(29)
    stw 9, {S_BOMB_WAIT}(31)
    lwz 9, {G_DANCE}(29)            # Clank's throw: gold bursts from him, the camera kicks
    cmpwi 9, 0
    beq gb_out
    lwz 4, {HERO_CLANK_MOBY}(30)
    cmpwi 4, 0
    beq gb_out
    addi 3, 29, {G_DANCE_BURST}
    bl gc_puffs
    lis 9, {CAMERA_STATE_HA}
    addi 9, 9, {CAMERA_STATE_LO}
    lfs 0, {G_DANCE} + 0x24(29)
    stfs 0, 0x160(9)
    lwz 10, {G_DANCE} + 0x28(29)
    stw 10, 0x168(9)
gb_out:
    addi 1, 1, 0xa0
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_shock:                           # (r26 = his parts may show; r29/r30): the jump's ring as Ratchet lands
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0xa0(1)
    lwz 9, {STATE_TYPE}(30)
    li 10, 0
    cmpwi 9, {STATE_TYPE_JUMP}
    beq gw_jump
    cmpwi 9, {STATE_TYPE_HOVER}     # (a hover after the jump is no landing)
    beq gw_jump
    lwz 9, 0x2084(30)               # nor the fall when a hover ends (the user: "when i stop hover, he
    cmpwi 9, {FALL_STATE}           # does his stomp in the air"): from a jump or a hover, till he is down
    bne gw_air
    lwz 9, {G_SHOCK_AIR}(29)
    cmpwi 9, 0
    beq gw_air
gw_jump:
    lwz 9, {HERO_LANDED}(30)        # down already (the jump state runs on ~11 frames after it)
    cmpwi 9, 0
    bne gw_air
    li 10, 1
gw_air:
    lwz 11, {G_SHOCK_AIR}(29)
    stw 10, {G_SHOCK_AIR}(29)
    cmpwi 10, 0                     # landed: in the air in a jump last frame, not now
    bne gw_out
    cmpwi 11, 0
    beq gw_out
    cmpwi 26, 0
    beq gw_out
    lwz 9, {G_SHOCK}(29)
    cmpwi 9, 0
    beq gw_out
    lwz 3, {G_SHOCK_MODEL}(29)
    cmpwi 3, 0
    beq gw_out
    li 4, {SHOCK_CLASS}
    bl gc_register
    cmpwi 3, 0
    beq gw_out
    lis 9, {CAMERA_STATE_HA}
    addi 9, 9, {CAMERA_STATE_LO}
    lfs 0, {G_SHOCK} + 0x14(29)
    stfs 0, 0x160(9)
    lwz 10, {G_SHOCK} + 0x18(29)
    stw 10, 0x168(9)
    lfs 0, 0x80(30)                 # under him, at 0x80
    stfs 0, 0x80(1)
    lfs 0, 0x84(30)
    stfs 0, 0x84(1)
    lfs 0, 0x88(30)
    lfs 1, {G_SHOCK} + 0x10(29)
    fadds 0, 0, 1
    stfs 0, 0x88(1)
    lfs 0, 0x8c(30)
    stfs 0, 0x8c(1)
    lwz 3, 0x2080(30)
    addi 4, 1, 0x80
    lwz 5, {G_SHOCK}(29)
    lfs 1, {G_SHOCK} + 4(29)
    lfs 2, {G_SHOCK} + 8(29)
    lfs 3, {G_SHOCK} + 0xc(29)
    bl {SHOCK_SPAWN}
    cmpwi 3, 0
    beq gw_out
    stw 3, {G_SHOCK_MOBY}(29)
    lwz 9, {G_SHOCK}(29)
    addi 9, 9, -1
    stw 9, {G_SHOCK_LEFT}(29)
    mr 4, 3
    addi 3, 29, {G_SHOCK_BURST}
    bl gc_puffs
gw_out:
    addi 1, 1, 0xa0
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_atan2:                           # (f1 = y, f2 = x) -> f1 = atan2(y, x), within ~0.005 rad (f0, f3..f7, r9)
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    fabs 3, 1
    fabs 4, 2
    fmr 5, 3                        # f5 = the smaller of |y|, |x|, f6 the larger
    fmr 6, 4
    fcmpu 0, 3, 4
    ble ga_order
    fmr 5, 4
    fmr 6, 3
ga_order:
    lfs 0, {P_ZERO}(9)
    fcmpu 0, 6, 0
    beq ga_zero
    fdivs 5, 5, 6                   # a, then a + a s (A s^2 + B s + C), s = a^2
    fmuls 6, 5, 5
    lfs 0, {P_ATAN_A}(9)
    lfs 7, {P_ATAN_B}(9)
    fmadds 0, 0, 6, 7
    lfs 7, {P_ATAN_C}(9)
    fmadds 0, 0, 6, 7
    fmuls 0, 0, 6
    fmadds 5, 0, 5, 5
    fcmpu 0, 3, 4                   # past the diagonal: pi/2 less it
    ble ga_x
    lfs 0, {P_HALF_PI}(9)
    fsubs 5, 0, 5
ga_x:
    lfs 0, {P_ZERO}(9)
    fcmpu 0, 2, 0                   # x < 0: pi less it
    bge ga_y
    lfs 0, {P_PI}(9)
    fsubs 5, 0, 5
ga_y:
    lfs 0, {P_ZERO}(9)
    fcmpu 0, 1, 0                   # y < 0: below
    bge ga_out
    fneg 5, 5
ga_out:
    fmr 1, 5
    blr
ga_zero:
    fmr 1, 0
    blr

gc_flame_sound:                     # (r27 = the legs' moby, 0 = none; r29/r30): the flames' sound while they burn
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 31, 0x70(1)
    li 31, 0                        # r31 = 1: they burn
    cmpwi 27, 0
    beq gfs_have
    lwz 9, {G_FLAMES}(29)
    cmpwi 9, 0
    beq gfs_have
    lwz 9, {G_FLAME_SOUND}(29)
    cmpwi 9, 0
    beq gfs_have
    lwz 9, 0x2084(30)
{FLAME_SOUND_TESTS}
    b gfs_have
gfs_burn:
    li 31, 1
gfs_have:
    lwz 3, {G_FLAME_SOUND} + 0x10(29)   # its voice, if it is still its (as 0xb40b0 checks the hover's)
    cmpwi 3, 0
    blt gfs_start
    mulli 9, 3, 0x70
    lis 10, {VOICES_HA}
    addi 10, 10, {VOICES_LO}
    add 10, 10, 9
    lwz 11, 0x88(10)
    lwz 12, 0x2080(30)
    cmpw 11, 12
    bne gfs_lost
    lbz 11, 0x74(10)
    cmpwi 11, 0
    beq gfs_lost
    cmpwi 31, 0
    bne gfs_out                     # burning, and heard
    bl {SOUND_STOP}
gfs_lost:
    li 9, -1
    stw 9, {G_FLAME_SOUND} + 0x10(29)
gfs_start:
    cmpwi 31, 0
    beq gfs_out
    lwz 9, 0x2080(30)               # his model's definition of it, copied, at FLAME_SOUND's pitch
    lwz 10, 0x24(9)
    lbz 11, 0xd(10)
    lwz 12, {G_FLAME_SOUND} + 4(29)
    cmpw 12, 11
    bge gfs_out
    lwz 10, 0x28(10)
    cmpwi 10, 0
    beq gfs_out
    slwi 12, 12, 5
    add 10, 10, 12
    addi 10, 10, -4
    addi 11, 29, {G_FLAME_SOUND} + 0x20 - 4
    li 12, 8
    mtctr 12
gfs_copy:
    lwzu 12, 4(10)
    stwu 12, 4(11)
    bdnz gfs_copy
    lwz 9, {G_FLAME_SOUND} + 8(29)
    stw 9, {G_FLAME_SOUND} + 0x30(29)
    stw 9, {G_FLAME_SOUND} + 0x34(29)
    addi 3, 29, {G_FLAME_SOUND} + 0x20
    li 4, 4                         # (looping)
    lwz 5, 0x2080(30)
    li 6, 0
    lwz 7, {G_FLAME_SOUND} + 0xc(29)
    bl {PLAY_SOUND_DEF}
    stw 3, {G_FLAME_SOUND} + 0x10(29)
    cmpwi 3, 0
    blt gfs_out
    mulli 9, 3, 0x70                # the voice follows him (PLAY_MODEL_SOUND 0x15d1c4)
    lis 10, {VOICES_HA}
    addi 10, 10, {VOICES_LO}
    add 10, 10, 9
    lwz 11, 0x2080(30)
    stw 11, 0x88(10)
    lwz 12, {G_FLAME_SOUND} + 4(29)
    sth 12, 0x7e(10)
gfs_out:
    ld 31, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_sounds:                          # (r29/r31): once his model is in, his sounds' bank loaded and his definitions given out
    lwz 9, {G_SOUNDS}(29)
    cmpwi 9, 0
    bnelr
    lwz 9, {S_MODEL}(31)
    cmpwi 9, 0
    beqlr
    lwz 9, {G_MISSILE_MODEL}(29)
    cmpwi 9, 0
    beqlr
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lis 3, {GIANT_SOUNDS_HA}
    addi 3, 3, {GIANT_SOUNDS_LO}
    addi 3, 3, {SOUNDS_BANK_OFF}
    bl {BANK_LOAD_FROM_MEM}
    li 9, -1
    cmpwi 3, 0
    ble gsd_out
    lis 4, {GIANT_SOUNDS_HA}        # r4 = his definitions, the missile's behind them
    addi 4, 4, {GIANT_SOUNDS_LO}
    li 5, {SOUND_DEFS}
    mtctr 5
    addi 5, 4, 0x1c
gsd_bank:                           # each at the bank
    stw 3, 0(5)
    addi 5, 5, 0x20
    bdnz gsd_bank
    lwz 9, {G_MISSILE_MODEL}(29)
    addi 5, 4, {GIANT_SOUND_COUNT} * 0x20
    stw 5, 0x28(9)
    li 5, {SOUND_DEFS} - {GIANT_SOUND_COUNT}
    stb 5, 0xd(9)
    lwz 9, {S_MODEL}(31)            # of his parts, SOUND_PARTS' headers
    lis 5, {HEADERS_AT_HI}
    ori 5, 5, {HEADERS_AT_LO}
    add 9, 9, 5
    li 5, {GIANT_SOUND_COUNT}
{SOUND_PARTS_SET}
    li 9, 1
gsd_out:
    stw 9, {G_SOUNDS}(29)
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_giant_sound:                     # (r3 = one of his definitions, < 0 none; r29/r30): it played at Ratchet
    lwz 9, {G_SOUNDS}(29)
    cmpwi 9, 1
    bnelr
    cmpwi 3, 0
    bltlr
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    slwi 3, 3, 5
    lis 9, {GIANT_SOUNDS_HA}
    addi 9, 9, {GIANT_SOUNDS_LO}
    add 3, 9, 3
    li 4, 0
    lwz 5, 0x2080(30)
    li 6, 0
    li 7, 0x400
    bl {PLAY_SOUND_DEF}
    cmpwi 3, 0
    blt ggs_out
    mulli 9, 3, 0x70                # the voice follows him (as PLAY_MODEL_SOUND)
    lis 10, {VOICES_HA}
    addi 10, 10, {VOICES_LO}
    add 10, 10, 9
    lwz 11, 0x2080(30)
    stw 11, 0x88(10)
ggs_out:
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_flames:                          # (r27 = the legs' moby; r29/r30): the Pyrocitor's flame down from his feet in FLAME_STATES
    lwz 9, {G_FLAMES}(29)
    cmpwi 9, 0
    beqlr
    lwz 9, 0x2084(30)
{FLAME_TESTS}
    blr
gf_go:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x100(1)
    std 31, 0xb0(1)
    std 28, 0xb8(1)
    stfd 31, 0xc8(1)
    stfd 30, 0xd0(1)
    stfd 29, 0xd8(1)
    lfs 1, 0x48(27)                 # the legs' turn: f31 = cos, f30 = sin
    bl {COS}
    fmr 31, 1
    lfs 1, 0x48(27)
    bl {SIN}
    fmr 30, 1
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    lfs 29, {P_ONE}(9)              # f29 = the side: 1 left, -1 right
    li 31, 2                        # r31 = feet to go
gf_foot:
    lfs 2, {G_FLAMES} + 4(29)       # under the sole (0x90): x + f cos - l sin, y + f sin + l cos, z + up
    lfs 3, {G_FLAMES} + 8(29)
    fmuls 3, 3, 29
    lfs 0, 0x10(27)
    fmadds 0, 2, 31, 0
    fnmsubs 0, 3, 30, 0
    stfs 0, 0x90(1)
    lfs 0, 0x14(27)
    fmadds 0, 2, 30, 0
    fmadds 0, 3, 31, 0
    stfs 0, 0x94(1)
    lfs 0, 0x18(27)
    lfs 2, {G_FLAMES} + 0xc(29)
    fadds 0, 0, 2
    stfs 0, 0x98(1)
    fabs 0, 29
    stfs 0, 0x9c(1)
    lwz 28, {G_FLAMES} + 0x1c(29)   # r28 = fires to go, then the spark
gf_one:
    lfs 1, {G_FLAMES} + 0x10(29)    # the velocity (0xa0): down, with his movement
    lfs 2, {G_FLAMES} + 0x14(29)
    bl {RANDOM}
    fneg 1, 1
    stfs 1, 0xa8(1)
    fabs 0, 29
    stfs 0, 0xac(1)
    lfs 2, {G_FLAMES} + 0x28(29)
    cmpwi 28, 0
    bne gf_carried
    lfs 2, {G_FLAMES} + 0x2c(29)
gf_carried:
    lfs 0, {HERO_MOVED}(30)
    fmuls 0, 0, 2
    stfs 0, 0xa0(1)
    lfs 0, {HERO_MOVED} + 4(30)
    fmuls 0, 0, 2
    stfs 0, 0xa4(1)
    addi 3, 1, 0xa0                 # aside at random
    lfs 2, {G_FLAMES} + 0x50(29)
    bl gc_flame_scatter
    lfs 0, 0x90(1)                  # from about the sole (0xe0)
    stfs 0, 0xe0(1)
    lfs 0, 0x94(1)
    stfs 0, 0xe4(1)
    lfs 0, 0x98(1)
    stfs 0, 0xe8(1)
    lfs 0, 0x9c(1)
    stfs 0, 0xec(1)
    addi 3, 1, 0xe0
    lfs 2, {G_FLAMES} + 0x54(29)
    bl gc_flame_scatter
    cmpwi 28, 0
    beq gf_spark
    li 3, 0
    li 4, 5
    bl {RANDOM_INT}
    mr 8, 3
    addi 3, 1, 0xe0
    addi 4, 1, 0xa0
    lwz 5, {G_FLAMES} + 0x18(29)
    li 6, 0x7f
    lis 7, 0xff
    ori 7, 7, 0xffff
    lfs 1, {G_FLAMES} + 0x30(29)
    lfs 2, {G_FLAMES} + 0x34(29)
    lfs 3, {G_FLAMES} + 0x38(29)
    lfs 4, {G_FLAMES} + 0x3c(29)
    lfs 5, {G_FLAMES} + 0x40(29)
    bl {FIRE}
    addi 28, 28, -1
    b gf_one
gf_spark:
    lwz 3, {G_FLAMES} + 0x20(29)
    lwz 4, {G_FLAMES} + 0x24(29)
    bl {RANDOM_INT}
    mr 8, 3
    addi 3, 1, 0xe0
    addi 4, 1, 0xa0
    lwz 5, {G_FLAMES} + 0x44(29)
    lwz 6, {G_FLAMES} + 0x48(29)
    li 7, 0
    li 9, 1
    lfs 1, {G_FLAMES} + 0x4c(29)
    bl {SPARK}
    fneg 29, 29
    addic. 31, 31, -1
    bne gf_foot
    lfd 29, 0xd8(1)
    lfd 30, 0xd0(1)
    lfd 31, 0xc8(1)
    ld 28, 0xb8(1)
    ld 31, 0xb0(1)
    addi 1, 1, 0x100
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_flame_scatter:                   # (r3 = a vector, f2 = how far): its x and y each moved by up to f2 at random
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 31, 0x70(1)
    stfd 31, 0x78(1)
    mr 31, 3
    fmr 31, 2
    fneg 1, 31
    fmr 2, 31
    bl {RANDOM}
    lfs 0, 0(31)
    fadds 0, 0, 1
    stfs 0, 0(31)
    fneg 1, 31
    fmr 2, 31
    bl {RANDOM}
    lfs 0, 4(31)
    fadds 0, 0, 1
    stfs 0, 4(31)
    lfd 31, 0x78(1)
    ld 31, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_chain_place:                     # (r3 = a chain, r4 = its records, f11 = side (used up), f12/f13 = sin/cos; r29/r30; in gc_chains' frame)
    lwz 5, {C_COUNT}(3)
    cmpwi 5, {CHAIN_MAX}
    ble gcp_count
    li 5, {CHAIN_MAX}
gcp_count:
    cmpwi 5, 0
    blelr
    addi 6, 5, -1                   # f10 = from one ball to the next: grown / (count - 1)
    cmpwi 6, 1
    bge gcp_apart
    li 6, 1
gcp_apart:
    extsw 6, 6
    std 6, 0x88(1)
    lfd 10, 0x88(1)
    fcfid 10, 10
    frsp 10, 10
    lfs 0, {C_GROWN}(3)
    fdivs 10, 0, 10
    lfs 1, {C_FROM}(3)              # from, as forward f1, left f2, up f3 (on the lifted Ratchet)
    lfs 2, {C_FROM} + 4(3)
    fmuls 2, 2, 11
    lfs 3, {C_FROM} + 8(3)
    lfs 0, {G_LIFT}(29)
    fadds 3, 3, 0
    lfs 4, {C_TO}(3)                # the way to "to": f4..f6
    fsubs 4, 4, 1
    lfs 5, {C_TO} + 4(3)
    fmuls 5, 5, 11
    fsubs 5, 5, 2
    lfs 6, {C_TO} + 8(3)
    fsubs 6, 6, 3
    lfs 8, {G_RIDER}(29)            # from in the world: f1..f3 (from where he rides)
    fmadds 8, 1, 13, 8              # x + forward cos - left sin
    fnmsubs 8, 2, 12, 8
    lfs 0, {G_RIDER} + 4(29)
    fmadds 0, 1, 12, 0              # y + forward sin + left cos
    fmadds 0, 2, 13, 0
    fmr 1, 8
    fmr 2, 0
    lfs 0, 0x88(30)
    fadds 3, 3, 0
    fmuls 8, 4, 13                  # the way in the world: f4..f6
    fnmsubs 8, 5, 12, 8
    fmuls 0, 4, 12
    fmadds 0, 5, 13, 0
    fmr 4, 8
    fmr 5, 0
    lfs 9, {G_BALL_SCALE}(29)       # f9 = the scale at Clank, f11 = from there to the part's, per share
    lfs 8, {G_BALL_SCALE_TO}(29)
    fsubs 11, 8, 9
    lfs 0, {C_GROWN}(3)             # both times how far it is grown
    fmuls 9, 9, 0
    fmuls 11, 11, 0
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    lfs 7, {P_ZERO}(9)              # f7 = this ball's share of the way
    mtctr 5
gcp_ball:
    lwz 7, 0(4)
    cmpwi 7, 0
    beq gcp_next
    fmadds 0, 4, 7, 1
    stfs 0, 0x10(7)
    fmadds 0, 5, 7, 2
    stfs 0, 0x14(7)
    fmadds 0, 6, 7, 3
    stfs 0, 0x18(7)
    fmadds 0, 11, 7, 9
    stfs 0, 0x2c(7)
    lwz 0, {G_BALL_COLOUR}(29)      # (after the level's lighting has set it this frame)
    stw 0, 0x38(7)
gcp_next:
    addi 4, 4, 0x10
    fadds 7, 7, 10
    bdnz gcp_ball
    blr

gc_late:                            # at the HUD's hook: the parts where he is now, and he on the legs
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x90(1)
    std 31, 0x70(1)
    std 30, 0x78(1)
    std 29, 0x80(1)
    lis 31, {STATE_HA}
    addi 31, 31, {STATE_LO}
    lis 30, {HERO_HA}
    addi 30, 30, {HERO_LO}
    lis 29, {GIANT_HA}
    addi 29, 29, {GIANT_LO}
    lwz 9, {G_SHOCK_LEFT}(29)       # the jump's ring gold while it lasts
    cmpwi 9, 0
    ble gl_ring
    addi 9, 9, -1
    stw 9, {G_SHOCK_LEFT}(29)
    lwz 10, {G_SHOCK_MOBY}(29)
    lwz 11, {G_SHOCK_COLOUR}(29)
    stw 11, 0x38(10)
gl_ring:
    lwz 9, {S_LEGS}(31)             # the camera: further out while the legs are out
    cmpwi 9, 0
    beq gl_zoom
    lis 9, {CAMERA_STATE_HA}
    addi 9, 9, {CAMERA_STATE_LO}
    lwz 9, 0x180(9)
    cmpwi 9, 0
    beq gl_zoom
    lwz 9, {CAMERA_DATA}(9)
    cmpwi 9, 0
    beq gl_zoom
    lfs 0, {CAMERA_DISTANCE}(9)
    lfs 1, {G_ZOOM}(29)
    fsubs 1, 1, 0
    lfs 2, {G_ZOOM_EASE}(29)
    fmadds 0, 1, 2, 0
    stfs 0, {CAMERA_DISTANCE}(9)
    lwz 10, {STATE_TYPE}(30)        # in a jump, up with him, from where he left the ground
    cmpwi 10, {STATE_TYPE_JUMP}
    beq gl_cam_up
    cmpwi 10, {STATE_TYPE_HOVER}
    beq gl_zoom
    lfs 1, 0x88(30)
    stfs 1, {G_CAM_BASE}(29)
    b gl_zoom
gl_cam_up:
    lfs 1, 0x88(30)
    lfs 2, {G_CAM_BASE}(29)
    fsubs 1, 1, 2
    lis 10, {POOL_HA}
    addi 10, 10, {POOL_LO}
    lfs 2, {P_ZERO}(10)
    fcmpu 0, 1, 2
    bge gl_cam_low
    fmr 1, 2
gl_cam_low:
    lfs 2, {G_CAM_JUMP} + 0xc(29)
    fcmpu 0, 1, 2
    ble gl_cam_high
    fmr 1, 2
gl_cam_high:
    lfs 2, {G_CAM_JUMP} + 4(29)
    lfs 3, {G_CAM_JUMP}(29)
    fmadds 1, 1, 2, 3               # the height wanted
    lfs 0, {CAMERA_HEIGHT}(9)
    fsubs 1, 1, 0
    lfs 2, {G_CAM_JUMP} + 8(29)
    fmadds 0, 1, 2, 0
    stfs 0, {CAMERA_HEIGHT}(9)
gl_zoom:
    bl gc_ride_height
    bl gc_move_place
gl_legs:
    lwz 3, {S_LEGS}(31)
    cmpwi 3, 0
    beq gl_out
    addi 4, 29, {G_LEGS_SCALE}
    bl gc_place
    lfs 1, {G_LIFT}(29)             # his legs carry Ratchet: he is drawn LIFT higher, and aside with the pelvis
    lfs 2, {G_RIDER} + 8(29)
    lfs 3, {G_RIDER} + 0xc(29)
    lwz 9, 0x2080(30)
    cmpwi 9, 0
    beq gl_attached
    lfs 0, 0x18(9)
    fadds 0, 0, 1
    stfs 0, 0x18(9)
    lfs 0, 0x10(9)
    fadds 0, 0, 2
    stfs 0, 0x10(9)
    lfs 0, 0x14(9)
    fadds 0, 0, 3
    stfs 0, 0x14(9)
gl_attached:
    addi 10, 30, {ATTACHED} - 4
    li 11, {ATTACHED_COUNT}
gl_entry:
    li 12, 2
    mtctr 12
    mr 12, 10
gl_moby:
    lwzu 9, 4(12)
    cmpwi 9, 0
    beq gl_next
    lfs 0, 0x18(9)
    fadds 0, 0, 1
    stfs 0, 0x18(9)
    lfs 0, 0x10(9)
    fadds 0, 0, 2
    stfs 0, 0x10(9)
    lfs 0, 0x14(9)
    fadds 0, 0, 3
    stfs 0, 0x14(9)
gl_next:
    bdnz gl_moby
    addi 10, 10, {ATTACHED_SIZE}
    addic. 11, 11, -1
    bne gl_entry
    lwz 9, {PACK_PART}(30)
    cmpwi 9, 0
    beq gl_still
    lfs 0, 0x18(9)
    fadds 0, 0, 1
    stfs 0, 0x18(9)
    lfs 0, 0x10(9)
    fadds 0, 0, 2
    stfs 0, 0x10(9)
    lfs 0, 0x14(9)
    fadds 0, 0, 3
    stfs 0, 0x14(9)
gl_still:
    bl gc_still
    bl gc_clank_still
    bl gc_clank_seat
    bl gc_boot_seat
gl_out:
    bl gc_chains
    bl gc_struts
    bl gc_rod
    bl gc_pistons
    bl gc_view
    ld 29, 0x80(1)
    ld 30, 0x78(1)
    ld 31, 0x70(1)
    addi 1, 1, 0x90
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_view:                            # (r29/r30): the camera looks at Ratchet as VIEW has it (off: as the game has it)
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    lwz 9, {G_VIEW}(29)
    cmpwi 9, 0
    beq gvw_out
    lfs 1, 0x98(30)
    lfs 0, {G_VIEW} + 0x10(29)
    fadds 1, 1, 0
    stfs 1, 0x70(1)
    bl {COS}
    stfs 1, 0x74(1)
    lfs 1, 0x70(1)
    bl {SIN}
    lfs 2, 0x74(1)                  # f2 = cos, f1 = sin of the turn; f3, f4 = cos, sin of the pitch
    lfs 3, {G_VIEW} + 8(29)
    lfs 4, {G_VIEW} + 0xc(29)
    lis 9, {CAMERA_STATE_HA}
    addi 9, 9, {CAMERA_STATE_LO}
    fmuls 5, 3, 2                   # the view axis (cp c, cp s, sp)
    fmuls 6, 3, 1
    stfs 5, 0x350(9)
    stfs 6, 0x354(9)
    stfs 4, 0x358(9)
    fneg 7, 1                       # left (-s, c, 0)
    stfs 7, 0x360(9)
    stfs 2, 0x364(9)
    lis 10, {POOL_HA}
    addi 10, 10, {POOL_LO}
    lfs 0, {P_ZERO}(10)
    stfs 0, 0x368(9)
    fneg 7, 4                       # up = view x left (-sp c, -sp s, cp)
    fmuls 8, 7, 2
    stfs 8, 0x370(9)
    fmuls 8, 7, 1
    stfs 8, 0x374(9)
    stfs 3, 0x378(9)
    lfs 0, {G_VIEW} + 4(29)         # the place: the point less the distance along the view axis
    lfs 8, 0x80(30)
    lfs 7, {G_SCENE} + 0x20(29)     # (the scene's point aside of him)
    fadds 8, 8, 7
    fnmsubs 8, 0, 5, 8
    stfs 8, 0x140(9)
    lfs 8, 0x84(30)
    lfs 7, {G_SCENE} + 0x24(29)
    fadds 8, 8, 7
    fnmsubs 8, 0, 6, 8
    stfs 8, 0x144(9)
    lfs 8, 0x88(30)
    lfs 7, {G_SCENE} + 0x28(29)
    fadds 8, 8, 7
    lfs 7, {G_VIEW} + 0x14(29)
    fadds 8, 8, 7
    fnmsubs 8, 0, 4, 8
    stfs 8, 0x148(9)
gvw_out:
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_still:                           # (r29/r30): he stands still: his animation fields kept, a still frame shown
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lwz 3, 0x2080(30)
    cmpwi 3, 0
    beq gst_out
    lwz 9, {G_STILL}(29)
    cmpwi 9, 0
    beq gst_out
    lwz 9, {G_KEPT}(29)
    cmpwi 9, 0
    bne gst_pose                    # kept already (this frame, or no frame between: the game is paused)
    stw 3, {G_KEPT}(29)
    addi 10, 3, {ANIM_FIELDS} - 4
    addi 11, 29, {G_KEPT_FIELDS} - 4
    li 12, {ANIM_FIELDS_SIZE} / 4
    mtctr 12
gst_keep:
    lwzu 12, 4(10)
    stwu 12, 4(11)
    bdnz gst_keep
gst_pose:
    lwz 9, {G_STILL_FRAME}(29)
    stb 9, 0x50(3)
    stb 9, 0x51(3)
    lwz 9, {G_STILL_ANIM}(29)
    stb 9, 0x52(3)
    stb 9, 0x53(3)
    li 9, 0
    stw 9, 0x54(3)
    bl {FRAME_POINTERS}
    lwz 3, 0x2080(30)               # his manipulators of STILL_JOINTS' bones get their turns
    lwz 3, 0x64(3)
gst_manip:
    cmpwi 3, 0
    beq gst_out
    lwz 9, 4(3)
    addis 9, 9, -0x7000
    srwi 9, 9, 6                    # its bone
    lwz 8, {G_STILL_JOINTS}(29)
    addi 10, 29, {G_STILL_JOINTS} - 0x10
gst_find:
    cmpwi 8, 0
    beq gst_next
    addi 10, 10, 0x20
    addi 8, 8, -1
    lwz 11, 0(10)
    cmpw 11, 9
    bne gst_find
    lwz 11, 0x10(10)
    stw 11, 0x10(3)
    lwz 11, 0x14(10)
    stw 11, 0x14(3)
    lwz 11, 0x18(10)
    stw 11, 0x18(3)
    lwz 11, 0x1c(10)
    stw 11, 0x1c(3)
gst_next:
    lwz 3, 8(3)
    b gst_manip
gst_out:
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_clank_still:                     # (r29/r30): backpack Clank and the pack held in one frame each (CLANK_STILL, PACK_STILL)
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    addi 8, 29, {G_CLANK_STILL}
    li 7, {HERO_CLANK_MOBY}
    bl gc_hold
    addi 8, 29, {G_PACK_STILL}
    li 7, {HERO_PACK_MOBY}
    bl gc_hold
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_hold:                            # (r8 = a still pose's record, r7 = the hero field of its moby, r30): its fields kept, its frame shown
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lwzx 3, 30, 7
    cmpwi 3, 0
    beq gd_out
    lwz 9, {H_ON}(8)
    cmpwi 9, 0
    beq gd_out
    lwz 9, {H_KEPT}(8)
    cmpwi 9, 0
    bne gd_pose                     # kept already (the game is paused)
    stw 3, {H_KEPT}(8)
    addi 10, 3, {ANIM_FIELDS} - 4
    addi 11, 8, {H_FIELDS} - 4
    li 12, {ANIM_FIELDS_SIZE} / 4
    mtctr 12
gd_keep:
    lwzu 12, 4(10)
    stwu 12, 4(11)
    bdnz gd_keep
gd_pose:
    lwz 9, {H_FRAME}(8)
    stb 9, 0x50(3)
    stb 9, 0x51(3)
    lwz 9, {H_ANIM}(8)
    stb 9, 0x52(3)
    stb 9, 0x53(3)
    li 9, 0
    stw 9, 0x54(3)
    bl {FRAME_POINTERS}
gd_out:
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_dance:                           # (r29/r30): Clank's bomb throw now (BOMB_DANCE) -> G_DANCE_NOW: spin, rise, lean, size
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    lfs 0, {P_ZERO}(9)
    lfs 13, {P_ONE}(9)
    stfs 0, {G_DANCE_NOW}(29)
    stfs 0, {G_DANCE_NOW} + 4(29)
    stfs 0, {G_DANCE_NOW} + 8(29)
    stfs 13, {G_DANCE_NOW} + 0xc(29)
    lwz 10, {G_DANCE}(29)
    cmpwi 10, 0
    beq gdn_out
    lis 10, {STATE_HA}
    addi 10, 10, {STATE_LO}
    lwz 11, {S_PUNCH}(10)
    cmpwi 11, 0
    beq gdn_out
    extsw 11, 11
    std 11, 0x70(1)
    lfd 1, 0x70(1)
    fcfid 1, 1
    frsp 1, 1                       # f1 = its frame
    lwz 11, {S_MOVE}(10)
    cmpwi 11, 0
    beq gdn_punch
    cmpwi 11, 2
    bne gdn_out
    lfs 2, {G_DANCE} + 4(29)        # CHARGE
    lfs 11, {P_TWO}(9)
    lfs 12, {P_THREE}(9)
    fcmpu 0, 1, 2
    bgt gdn_back
    fdivs 3, 1, 2                   # charging: u, s = u^2 (3 - 2u)
    fmuls 4, 3, 3
    fnmsubs 5, 11, 3, 12
    fmuls 5, 4, 5
    lfs 6, {P_TWO_PI}(9)
    lfs 7, {G_DANCE} + 0x10(29)
    fmuls 6, 6, 7
    fmuls 6, 6, 4
    stfs 6, {G_DANCE_NOW}(29)
    lfs 7, {G_DANCE} + 0x0c(29)
    fmuls 7, 7, 5
    stfs 7, {G_DANCE_NOW} + 4(29)
    lfs 7, {G_DANCE} + 0x14(29)
    fmuls 7, 7, 5
    stfs 7, {G_DANCE_NOW} + 8(29)
    lfs 7, {G_DANCE} + 0x1c(29)
    fmadds 7, 7, 5, 13
    stfs 7, {G_DANCE_NOW} + 0xc(29)
    lwz 4, {HERO_CLANK_MOBY}(30)    # and gold sparks gather on him
    cmpwi 4, 0
    beq gdn_out
    addi 3, 29, {G_DANCE_GLOW}
    bl gc_puffs
    b gdn_out
gdn_back:                            # after the throw: r = 1 - smoothstep(v), v at most 1
    fsubs 3, 1, 2
    lfs 4, {G_DANCE} + 8(29)
    fdivs 3, 3, 4
    fsubs 4, 3, 13
    fsel 3, 4, 13, 3
    fmuls 4, 3, 3
    fnmsubs 5, 11, 3, 12
    fmuls 5, 4, 5
    fsubs 5, 13, 5
    lfs 7, {G_DANCE} + 0x0c(29)
    fmuls 7, 7, 5
    stfs 7, {G_DANCE_NOW} + 4(29)
    lfs 7, {G_DANCE} + 0x18(29)
    fmuls 7, 7, 5
    stfs 7, {G_DANCE_NOW} + 8(29)
    lfs 7, {G_DANCE} + 0x20(29)
    fmadds 7, 7, 5, 13
    stfs 7, {G_DANCE_NOW} + 0xc(29)
    b gdn_out
gdn_punch:                          # the punch (PUNCH_TWIST, timed by PUNCH_POSE): spin and lean only
    lwz 11, {G_PUNCH}(29)
    cmpwi 11, 0
    beq gdn_out
    lfs 11, {P_TWO}(9)
    lfs 12, {P_THREE}(9)
    lfs 2, {G_POSE} + 4(29)         # wind, strike, hold, back
    lfs 3, {G_POSE} + 8(29)
    lfs 4, {G_POSE} + 0x10(29)
    lfs 5, {G_POSE} + 0x14(29)
    lfs 6, {G_PUNCH} + 4(29)        # turns (wind-up, strike), leans (wind-up, strike)
    lfs 7, {G_PUNCH} + 8(29)
    lfs 8, {G_PUNCH} + 0xc(29)
    lfs 9, {G_PUNCH} + 0x10(29)
    lwz 11, {S_SIDE}(10)            # the other arm: turned the other way
    cmpwi 11, 0
    beq gdn_side
    fneg 6, 6
    fneg 7, 7
gdn_side:
    fcmpu 0, 1, 2
    bgt gdn_strike
    fdivs 3, 1, 2                   # winding up: smoothstep(f / wind)
    fmuls 4, 3, 3
    fnmsubs 10, 11, 3, 12
    fmuls 10, 4, 10
    fmuls 0, 6, 10
    stfs 0, {G_DANCE_NOW}(29)
    fmuls 0, 8, 10
    stfs 0, {G_DANCE_NOW} + 8(29)
    b gdn_out
gdn_strike:
    fsubs 0, 1, 2
    fcmpu 0, 0, 3
    bgt gdn_after
    fdivs 0, 0, 3                   # striking: u from the wind-up's turn and lean to the strike's
    fadds 10, 6, 7
    fnmsubs 10, 10, 0, 6
    stfs 10, {G_DANCE_NOW}(29)
    fsubs 10, 9, 8
    fmadds 10, 10, 0, 8
    stfs 10, {G_DANCE_NOW} + 8(29)
    b gdn_out
gdn_after:                          # held, then eased back with the fist: r = 1 - smoothstep(v)
    fsubs 0, 0, 3
    fsubs 0, 0, 4
    fdivs 0, 0, 5
    lfs 3, {P_ZERO}(9)
    fsel 0, 0, 0, 3
    fsubs 10, 0, 13
    fsel 0, 10, 13, 0
    fmuls 10, 0, 0
    fnmsubs 2, 11, 0, 12
    fmuls 10, 10, 2
    fsubs 10, 13, 10
    fmuls 0, 7, 10
    fneg 0, 0
    stfs 0, {G_DANCE_NOW}(29)
    fmuls 0, 9, 10
    stfs 0, {G_DANCE_NOW} + 8(29)
gdn_out:
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_clank_seat:                      # (r29/r30): backpack Clank and the pack upright, turned as Ratchet faces (CLANK_SEAT), and his throw (gc_dance)
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x120(1)
    lwz 9, {G_SEAT}(29)
    cmpwi 9, 0
    beq gse_out
    bl gc_dance
    lfs 1, 0x98(30)
    lfs 0, {G_SEAT_TURN}(29)
    fadds 1, 1, 0
    stfs 1, 0x98(1)                 # the seat's turn: cos 0x9c, sin 0xa0
    bl {COS}
    stfs 1, 0x9c(1)
    lfs 1, 0x98(1)
    bl {SIN}
    stfs 1, 0xa0(1)
    lfs 1, 0x98(1)
    lfs 0, {G_DANCE_NOW}(29)
    fadds 1, 1, 0
    lis 9, {POOL_HA}                # kept within -pi..pi: the euler (+0x48) a turn past it throws the
    addi 9, 9, {POOL_LO}            # bomb as a long stretched bar (the throw's frame is before gc_dance's)
    lfs 2, {P_PI}(9)
    lfs 3, {P_TWO_PI}(9)
    fneg 4, 2
    b gse_wrap_down
gse_wrap_sub:                       # (only an ordered compare loops: a NaN goes straight through)
    fsubs 1, 1, 3
gse_wrap_down:
    fcmpu 0, 1, 2
    bgt gse_wrap_sub
    b gse_wrap_up
gse_wrap_add:
    fadds 1, 1, 3
gse_wrap_up:
    fcmpu 0, 1, 4
    blt gse_wrap_add
    stfs 1, 0x70(1)                 # his turn, with the spin: cos 0x74, sin 0x78
    bl {COS}
    stfs 1, 0x74(1)
    lfs 1, 0x70(1)
    bl {SIN}
    stfs 1, 0x78(1)
    lfs 1, {G_DANCE_NOW} + 8(29)    # t = the throw's lean (+ = top back) less his ride's lean: c 0xa4, s 0xa8
    lfs 0, {G_TILT_NOW}(29)
    fsubs 1, 1, 0
    stfs 1, 0xbc(1)
    bl {COS}
    stfs 1, 0xa4(1)
    lfs 1, 0xbc(1)
    bl {SIN}
    stfs 1, 0xa8(1)
    lfs 1, {G_TILT_NOW} + 4(29)     # r = his roll, as a turn about ahead (+ = top to his right): c 0xac, s 0xb0
    fneg 1, 1
    stfs 1, 0xbc(1)
    bl {COS}
    stfs 1, 0xac(1)
    lfs 1, 0xbc(1)
    bl {SIN}
    stfs 1, 0xb0(1)
    lfs 1, {G_TILT_NOW}(29)         # l = his ride's lean (+ = forward): c 0xb4, s 0xb8
    bl {COS}
    stfs 1, 0xb4(1)
    lfs 1, {G_TILT_NOW}(29)
    bl {SIN}
    stfs 1, 0xb8(1)
    lfs 12, 0x74(1)                 # the rows (0xc0..0xe0), in his frame ahead (ct, -st sr, st cr),
    lfs 13, 0x78(1)                 # left (0, cr, sr), up (-st, -ct sr, ct cr), turned with him
    lfs 2, 0xa4(1)
    lfs 3, 0xa8(1)
    lfs 4, 0xac(1)
    lfs 5, 0xb0(1)
    fmuls 6, 3, 5
    fneg 6, 6
    fmuls 0, 2, 12
    fnmsubs 0, 6, 13, 0
    stfs 0, 0xc0(1)
    fmuls 0, 2, 13
    fmadds 0, 6, 12, 0
    stfs 0, 0xc4(1)
    fmuls 0, 3, 4
    stfs 0, 0xc8(1)
    fmuls 0, 4, 13
    fneg 0, 0
    stfs 0, 0xcc(1)
    fmuls 0, 4, 12
    stfs 0, 0xd0(1)
    stfs 5, 0xd4(1)
    fneg 6, 3
    fmuls 7, 2, 5
    fneg 7, 7
    fmuls 0, 6, 12
    fnmsubs 0, 7, 13, 0
    stfs 0, 0xd8(1)
    fmuls 0, 6, 13
    fmadds 0, 7, 12, 0
    stfs 0, 0xdc(1)
    fmuls 0, 2, 4
    stfs 0, 0xe0(1)
    lfs 7, {G_SEAT_AT} + 4(29)      # the seat about PIVOT, leant and rolled (0xe4..0xec, off his feet):
    lfs 8, {G_SEAT_AT} + 8(29)      # f' = f cl + z sl, z' = z cl - f sl; l' = l cr - z' sr, z'' = l sr + z' cr
    lfs 9, {G_SEAT_AT} + 0xc(29)
    lfs 10, {G_TILT} + 0x18(29)
    fsubs 9, 9, 10
    lfs 2, 0xb4(1)
    lfs 3, 0xb8(1)
    fmuls 0, 7, 2
    fmadds 0, 9, 3, 0               # f0 = f'
    fmuls 1, 9, 2
    fnmsubs 1, 7, 3, 1              # f1 = z'
    lfs 4, 0xac(1)
    lfs 5, 0xb0(1)
    fmuls 6, 8, 4
    fnmsubs 6, 1, 5, 6              # f6 = l'
    fmuls 11, 1, 4
    fmadds 11, 8, 5, 11             # f11 = z''
    fadds 11, 11, 10
    stfs 11, 0xec(1)
    lfs 12, 0x9c(1)
    lfs 13, 0xa0(1)
    fmuls 11, 0, 12
    fnmsubs 11, 6, 13, 11
    stfs 11, 0xe4(1)
    fmuls 11, 0, 13
    fmadds 11, 6, 12, 11
    stfs 11, 0xe8(1)
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    lfs 6, {P_ZERO}(9)
    li 10, {HERO_CLANK_MOBY}
gse_moby:
    lwzx 3, 30, 10
    cmpwi 3, 0
    beq gse_next
    lfs 0, 0xc0(1)
    stfs 0, 0xc0(3)
    lfs 0, 0xc4(1)
    stfs 0, 0xc4(3)
    lfs 0, 0xc8(1)
    stfs 0, 0xc8(3)
    lfs 0, 0xcc(1)
    stfs 0, 0xd0(3)
    lfs 0, 0xd0(1)
    stfs 0, 0xd4(3)
    lfs 0, 0xd4(1)
    stfs 0, 0xd8(3)
    lfs 0, 0xd8(1)
    stfs 0, 0xe0(3)
    lfs 0, 0xdc(1)
    stfs 0, 0xe4(3)
    lfs 0, 0xe0(1)
    stfs 0, 0xe8(3)
    stfs 6, 0x40(3)
    lfs 0, {G_DANCE_NOW} + 8(29)
    fneg 0, 0
    stfs 0, 0x44(3)
    lfs 0, 0x70(1)
    stfs 0, 0x48(3)
    lfs 0, {G_DANCE_NOW} + 0xc(29)  # his size: Clank's is set every frame (gc_giant), the pack's is read once
    cmpwi 10, {HERO_CLANK_MOBY}
    bne gse_pack
    lfs 7, 0x2c(3)
    fmuls 7, 7, 0
    stfs 7, 0x2c(3)
    b gse_place
gse_pack:                           # (read as a throw starts, put back after it, however it ended)
    lfs 7, {G_DANCE_PACK}(29)
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    lfs 11, {P_ONE}(9)
    fcmpu 0, 0, 11
    bne gse_pack_dance
    fcmpu 0, 7, 6
    beq gse_place
    stfs 7, 0x2c(3)
    stfs 6, {G_DANCE_PACK}(29)
    b gse_place
gse_pack_dance:
    fcmpu 0, 7, 6
    bne gse_pack_size
    lfs 7, 0x2c(3)
    stfs 7, {G_DANCE_PACK}(29)
gse_pack_size:
    fmuls 7, 7, 0
    stfs 7, 0x2c(3)
gse_place:
    lwz 9, {G_SEAT_AT}(29)          # and at one place on him (SEAT_AT), risen
    cmpwi 9, 0
    beq gse_next
    lfs 0, {G_RIDER}(29)
    lfs 7, 0xe4(1)
    fadds 0, 0, 7
    stfs 0, 0x10(3)
    lfs 0, {G_RIDER} + 4(29)
    lfs 7, 0xe8(1)
    fadds 0, 0, 7
    stfs 0, 0x14(3)
    lfs 0, 0x88(30)
    lfs 7, 0xec(1)
    fadds 0, 0, 7
    lfs 7, {G_LIFT}(29)
    fadds 0, 0, 7
    lfs 7, {G_DANCE_NOW} + 4(29)
    fadds 0, 0, 7
    stfs 0, 0x18(3)
gse_next:
    cmpwi 10, {HERO_PACK_MOBY}
    li 10, {HERO_PACK_MOBY}
    bne gse_moby
gse_out:
    addi 1, 1, 0x120
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_boot_seat:                       # (r29/r30): his boots where they are on the still Ratchet (BOOT_SEAT)
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    lwz 9, {G_BOOT_SEAT}(29)
    cmpwi 9, 0
    beq gbs_out
    lfs 1, 0x98(30)
    bl {COS}
    stfs 1, 0x70(1)
    lfs 1, 0x98(30)
    bl {SIN}
    lfs 2, 0x70(1)                  # f2 = cos, f1 = sin
    li 10, 0                        # r10 = 4 * the boot
gbs_boot:
    addi 9, 10, {HERO_BOOTS}
    lwzx 3, 30, 9
    cmpwi 3, 0
    beq gbs_next
    slwi 8, 10, 4                   # its record: BOOT_SEAT + 0x10 + 0x40 * the boot
    addi 8, 8, {G_BOOT_SEAT} + 0x10
    add 8, 29, 8
    lfs 3, 0(8)                     # the place: x + f cos - l sin, y + f sin + l cos, z + up
    lfs 4, 4(8)
    lfs 0, {G_RIDER}(29)
    fmadds 0, 3, 2, 0
    fnmsubs 0, 4, 1, 0
    stfs 0, 0x10(3)
    lfs 0, {G_RIDER} + 4(29)
    fmadds 0, 3, 1, 0
    fmadds 0, 4, 2, 0
    stfs 0, 0x14(3)
    lfs 0, 0x88(30)
    lfs 3, 8(8)
    fadds 0, 0, 3
    lfs 3, {G_RIDE_NOW}(29)         # riding the pelvis
    fadds 0, 0, 3
    stfs 0, 0x18(3)
    addi 7, 8, 0xc                  # the rows: (a cos - b sin, a sin + b cos, c)
    addi 6, 3, 0xc0
    li 5, 3
gbs_row:
    lfs 3, 0(7)
    lfs 4, 4(7)
    fmuls 0, 3, 2
    fnmsubs 0, 4, 1, 0
    stfs 0, 0(6)
    fmuls 0, 3, 1
    fmadds 0, 4, 2, 0
    stfs 0, 4(6)
    lfs 0, 8(7)
    stfs 0, 8(6)
    addi 7, 7, 0xc
    addi 6, 6, 0x10
    addic. 5, 5, -1
    bne gbs_row
    lfs 0, 0x30(8)                  # the euler, the last plus his facing
    stfs 0, 0x40(3)
    lfs 0, 0x34(8)
    stfs 0, 0x44(3)
    lfs 0, 0x38(8)
    lfs 3, 0x98(30)
    fadds 0, 0, 3
    stfs 0, 0x48(3)
gbs_next:
    addi 10, 10, 4
    cmpwi 10, 8
    blt gbs_boot
gbs_out:
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_struts:                          # (r29/r30/r31): Clank's gold struts down to the gold hips while those are out (STRUTS)
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x90(1)
    std 27, 0x70(1)
    std 26, 0x78(1)
    li 26, 0                        # r26 = they show
    lwz 9, {S_LEGS}(31)
    cmpwi 9, 0
    beq gsr_go
    lwz 26, {G_STRUTS}(29)
gsr_go:
    li 4, 0
    li 9, {STRUT_ON_0}
    cmpwi 9, 0
    beq gsr_off_0
    cmpwi 26, 0
    beq gsr_off_0
    li 3, 1 + {STRUT_PART_0}
    bl gc_model
    mr. 4, 3
    bne gsr_show_0
gsr_off_0:
    addi 8, 29, {G_STRUT_JOINTS} + {S_J_SIZE} * 0
    addi 7, 29, {G_STRUT_RECORDS} + 0
    bl gc_strut_off                 # (before the moby goes)
    li 4, 0
gsr_show_0:
    addi 3, 29, {G_STRUT_RECORDS} + 0
    bl gc_show
    mr. 27, 3
    beq gsr_next_0
    li 9, 0                         # held at its first frame
    stw 9, 0x58(27)
    addi 3, 29, {G_STRUT_RECORDS} + 0
    lwz 4, {G_STRUT_ANIM}(29)
    bl gc_anim
    mr 3, 27
    addi 4, 29, {G_STRUT_AT} + 0
    bl gc_place
    mr 3, 27
    bl gc_ride
    mr 3, 27
    addi 8, 29, {G_STRUT_JOINTS} + {S_J_SIZE} * 0
    bl gc_strut_on
gsr_next_0:
    li 4, 0
    li 9, {STRUT_ON_1}
    cmpwi 9, 0
    beq gsr_off_1
    cmpwi 26, 0
    beq gsr_off_1
    li 3, 1 + {STRUT_PART_1}
    bl gc_model
    mr. 4, 3
    bne gsr_show_1
gsr_off_1:
    addi 8, 29, {G_STRUT_JOINTS} + {S_J_SIZE} * 1
    addi 7, 29, {G_STRUT_RECORDS} + 16
    bl gc_strut_off                 # (before the moby goes)
    li 4, 0
gsr_show_1:
    addi 3, 29, {G_STRUT_RECORDS} + 16
    bl gc_show
    mr. 27, 3
    beq gsr_next_1
    li 9, 0                         # held at its first frame
    stw 9, 0x58(27)
    addi 3, 29, {G_STRUT_RECORDS} + 16
    lwz 4, {G_STRUT_ANIM}(29)
    bl gc_anim
    mr 3, 27
    addi 4, 29, {G_STRUT_AT} + 20
    bl gc_place
    mr 3, 27
    bl gc_ride
    mr 3, 27
    addi 8, 29, {G_STRUT_JOINTS} + {S_J_SIZE} * 1
    bl gc_strut_on
gsr_next_1:
    ld 27, 0x70(1)
    ld 26, 0x78(1)
    addi 1, 1, 0x90
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_rod:                             # (r29/r30/r31): the column turned on the pelvis to its spot on the swaying Clank, the ball there (ROD)
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x100(1)
    std 28, 0xf8(1)
    lwz 9, {G_ROD}(29)
    cmpwi 9, 0
    beq grd_out
    lwz 28, {G_STRUT_RECORDS}(29)   # the column's moby
    cmpwi 28, 0
    beq grd_out
    lfs 1, {G_TILT_NOW}(29)         # cos, sin of his lean (0x80, 0x84) and of -roll (0x88, 0x8c)
    bl {COS}
    stfs 1, 0x80(1)
    lfs 1, {G_TILT_NOW}(29)
    bl {SIN}
    stfs 1, 0x84(1)
    lfs 1, {G_TILT_NOW} + 4(29)
    fneg 1, 1
    stfs 1, 0x90(1)
    bl {COS}
    stfs 1, 0x88(1)
    lfs 1, 0x90(1)
    bl {SIN}
    stfs 1, 0x8c(1)
    lfs 7, {G_ROD} + 4(29)          # the top about PIVOT, swayed as Clank's seat: the way it goes, d (0xa0..0xa8)
    lfs 8, {G_ROD} + 8(29)
    lfs 9, {G_ROD} + 0xc(29)
    lfs 10, {G_TILT} + 0x18(29)
    fsubs 9, 9, 10
    lfs 2, 0x80(1)
    lfs 3, 0x84(1)
    fmuls 0, 7, 2
    fmadds 0, 9, 3, 0               # f0 = f'
    fmuls 1, 9, 2
    fnmsubs 1, 7, 3, 1              # f1 = z'
    lfs 4, 0x88(1)
    lfs 5, 0x8c(1)
    fmuls 6, 8, 4
    fnmsubs 6, 1, 5, 6              # f6 = l'
    fmuls 11, 1, 4
    fmadds 11, 8, 5, 11             # f11 = z''
    fsubs 0, 0, 7
    stfs 0, 0xa0(1)
    fsubs 6, 6, 8
    stfs 6, 0xa4(1)
    fsubs 11, 11, 9
    stfs 11, 0xa8(1)
    lfs 2, {G_ROD} + 0x10(29)       # its length: the way from the top to the foot, (-d ahead, -d left, -(length + d up))
    fadds 3, 2, 11
    fmuls 3, 3, 3
    fmadds 3, 0, 0, 3
    fmadds 3, 6, 6, 3
    fsqrts 3, 3
    lfs 4, {G_ROD} + 0x24(29)
    fmuls 3, 3, 4
    stfs 3, {G_STRUT_JOINTS} + {S_J_MANIP} + 0x24(29)
    fdivs 0, 0, 2                   # the column's turn: pitch b = d ahead / length (0x94), roll a = -d left / length (0x98)
    stfs 0, 0x94(1)
    stfs 0, 0x44(28)
    fdivs 6, 6, 2
    fneg 6, 6
    stfs 6, 0x98(1)
    stfs 6, 0x40(28)
    lfs 1, 0x94(1)                  # cos, sin of b (0xb0, 0xb4) and a (0xb8, 0xbc)
    bl {COS}
    stfs 1, 0xb0(1)
    lfs 1, 0x94(1)
    bl {SIN}
    stfs 1, 0xb4(1)
    lfs 1, 0x98(1)
    bl {COS}
    stfs 1, 0xb8(1)
    lfs 1, 0x98(1)
    bl {SIN}
    stfs 1, 0xbc(1)
    lfs 7, {G_ROD} + 0x14(29)       # u = the top less the place; the place moved by u - Ry(b) Rx(a) u + d (the top on the joint)
    lfs 8, {G_ROD} + 0x18(29)
    lfs 9, {G_ROD} + 0x1c(29)
    lfs 2, 0xb8(1)
    lfs 3, 0xbc(1)
    fmuls 1, 8, 2                   # y1 = y ca - z sa, z1 = y sa + z ca
    fnmsubs 1, 9, 3, 1
    fmuls 4, 8, 3
    fmadds 4, 9, 2, 4
    lfs 2, 0xb0(1)
    lfs 3, 0xb4(1)
    fmuls 5, 7, 2                   # x2 = x cb + z1 sb, z2 = z1 cb - x sb
    fmadds 5, 4, 3, 5
    fmuls 6, 4, 2
    fnmsubs 6, 7, 3, 6
    fsubs 5, 7, 5                   # (f5, f1, f6) = u - turned u + d, in his frame
    fsubs 1, 8, 1
    fsubs 6, 9, 6
    lfs 0, 0xa0(1)
    fadds 5, 5, 0
    lfs 0, 0xa4(1)
    fadds 1, 1, 0
    lfs 0, 0xa8(1)
    fadds 6, 6, 0
    stfs 5, 0xc0(1)
    stfs 1, 0xc4(1)
    stfs 6, 0xc8(1)
    lfs 1, 0x98(30)                 # into the world: his facing
    bl {COS}
    stfs 1, 0xcc(1)
    lfs 1, 0x98(30)
    bl {SIN}
    lfs 2, 0xcc(1)                  # f2 = cos, f1 = sin
    lfs 3, 0xc0(1)
    lfs 4, 0xc4(1)
    lfs 0, 0x10(28)
    fmadds 0, 3, 2, 0
    fnmsubs 0, 4, 1, 0
    stfs 0, 0x10(28)
    lfs 0, 0x14(28)
    fmadds 0, 3, 1, 0
    fmadds 0, 4, 2, 0
    stfs 0, 0x14(28)
    lfs 0, 0x18(28)
    lfs 3, 0xc8(1)
    fadds 0, 0, 3
    stfs 0, 0x18(28)
    lwz 9, {G_BALLS}(29)            # the ball goes with the top: d in the world
    cmpwi 9, 0
    beq grd_out
    lfs 3, 0xa0(1)
    lfs 4, 0xa4(1)
    lfs 0, 0x10(9)
    fmadds 0, 3, 2, 0
    fnmsubs 0, 4, 1, 0
    stfs 0, 0x10(9)
    lfs 0, 0x14(9)
    fmadds 0, 3, 1, 0
    fmadds 0, 4, 2, 0
    stfs 0, 0x14(9)
    lfs 0, 0x18(9)
    lfs 3, 0xa8(1)
    fadds 0, 0, 3
    stfs 0, 0x18(9)
    lfs 0, {G_ROD} + 0x20(29)       # its size, grown in with the chain
    lfs 1, {G_CHAIN_LEGS} + {C_GROWN}(29)
    fmuls 0, 0, 1
    stfs 0, 0x2c(9)
grd_out:
    ld 28, 0xf8(1)
    addi 1, 1, 0x100
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_pistons:                         # (r29/r30/r31): the arms' pistons (ARM_PISTONS) while their arms' chains are grown
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x90(1)
    std 28, 0x70(1)
    std 27, 0x78(1)
    std 26, 0x80(1)
    li 26, 0                        # r26 = the piston
gpi_one:
    mulli 28, 26, {PISTON_SIZE}
    addi 28, 28, {G_PISTONS}
    add 28, 29, 28                  # r28 = its block
    subfic 9, 26, 1                 # (piston 0, the struts' first, is on Ratchet's right: the right arm's chain)
    mulli 9, 9, {CHAIN_SIZE}
    add 9, 29, 9
    lfs 13, {G_ARM_CHAINS} + {C_GROWN}(9)
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    lwz 10, {G_PISTONS_ON}(29)
    cmpwi 10, 2                     # 2: always, full
    bne gpi_grown
    lfs 13, {P_ONE}(9)
gpi_grown:
    stfs 13, 0x88(1)
    li 4, 0
    cmpwi 10, 0
    beq gpi_off
    lfs 0, {P_ZERO}(9)
    fcmpu 0, 13, 0
    ble gpi_off
    addi 3, 26, 1 + {PART_STRUT_L}
    bl gc_model
    mr. 4, 3
    bne gpi_show
gpi_off:
    addi 8, 28, {P_JOINT}
    addi 7, 28, {P_RECORD}
    bl gc_strut_off                 # (before the moby goes)
    li 4, 0
gpi_show:
    addi 3, 28, {P_RECORD}
    bl gc_show
    mr. 27, 3
    beq gpi_next
    li 9, 0                         # held at its first frame
    stw 9, 0x58(27)
    addi 3, 28, {P_RECORD}
    lwz 4, {G_STRUT_ANIM}(29)
    bl gc_anim
    mr 3, 27
    addi 4, 28, {P_AT}
    bl gc_place
    mr 3, 27
    bl gc_ride
    mr 3, 27
    addi 8, 28, {P_JOINT}
    bl gc_strut_on
    lfs 13, 0x88(1)                 # grown with its arm, out of Clank: the joint's scale times g, its
    lis 9, {POOL_HA}                # place moved by (1 - g) P_GROW
    addi 9, 9, {POOL_LO}
    lfs 12, {P_ONE}(9)
    fsubs 12, 12, 13
    addi 10, 28, {P_JOINT}
    li 11, 3
    mtctr 11
gpi_grow:
    lfs 0, {S_J_SCALE}(10)
    fmuls 0, 0, 13
    stfs 0, {S_J_MANIP} + 0x20(10)
    lfs 0, {S_J_PLACE}(10)
    lfs 1, {P_GROW} - {P_JOINT}(10)
    fmadds 0, 1, 12, 0
    stfs 0, {S_J_MANIP} + 0x30(10)
    addi 10, 10, 4
    bdnz gpi_grow
gpi_next:
    addi 26, 26, 1
    cmpwi 26, 2
    blt gpi_one
    ld 26, 0x80(1)
    ld 27, 0x78(1)
    ld 28, 0x70(1)
    addi 1, 1, 0x90
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_strut_on:                        # (r3 = a strut's moby, r8 = its joint record): its manipulator linked in and filled
    lwz 11, {S_J_MOBY}(8)
    cmpw 11, 3
    beq gso_fill                    # (another moby there: the old one went, with its list)
    stw 3, {S_J_MOBY}(8)
    li 9, 0
    stw 9, {S_J_MANIP}(8)
    li 9, 1
    stb 9, {S_J_MANIP} + 3(8)
    lwz 9, 0x64(3)
    stw 9, {S_J_MANIP} + 8(8)
    addi 9, 8, {S_J_MANIP}
    stw 9, 0x64(3)
gso_fill:
    lwz 9, {S_J_BONE}(8)
    slwi 9, 9, 6
    addis 9, 9, 0x7000
    stw 9, {S_J_MANIP} + 4(8)
    lis 9, {POOL_HA}                # weight 1, then turn, scale, place as the record has them
    addi 9, 9, {POOL_LO}
    lfs 0, {P_ONE}(9)
    stfs 0, {S_J_MANIP} + 0xc(8)
    addi 10, 8, {S_J_TURN} - 4
    addi 11, 8, {S_J_MANIP} + 0x10 - 4
    li 12, 12
    mtctr 12
gso_copy:
    lwzu 12, 4(10)
    stwu 12, 4(11)
    bdnz gso_copy
    stfs 0, {S_J_MANIP} + 0x2c(8)
    stfs 0, {S_J_MANIP} + 0x3c(8)
    li 9, 1
    stb 9, {S_J_MANIP} + 1(8)
    blr

gc_strut_off:                       # (r8 = a strut's joint record, r7 = its gc_show record): the manipulator out
    lwz 3, {S_J_MOBY}(8)
    cmpwi 3, 0
    beqlr
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    std 8, 0x60(1)
    li 9, 0
    stw 9, {S_J_MOBY}(8)
    lwz 9, 0(7)                     # its moby still there?
    cmpw 9, 3
    bne gsf_clear
    addi 4, 8, {S_J_MANIP}
    bl {MANIP_REMOVE}
gsf_clear:
    ld 8, 0x60(1)
    li 9, 0
    stw 9, {S_J_MANIP}(8)
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_clank_back:                      # (r29): their fields back before the frame (as Ratchet's at gc_input)
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    addi 8, 29, {G_CLANK_STILL}
    li 7, {HERO_CLANK_MOBY}
    bl gc_unhold
    addi 8, 29, {G_PACK_STILL}
    li 7, {HERO_PACK_MOBY}
    bl gc_unhold
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_unhold:                          # (r8 = a still pose's record, r7 = the hero field of its moby)
    lwz 3, {H_KEPT}(8)
    cmpwi 3, 0
    beqlr
    lis 9, {HERO_HA}                # (not into a moby gone with a level)
    addi 9, 9, {HERO_LO}
    lwzx 9, 9, 7
    cmpw 9, 3
    bne gu_drop
    lwz 0, {LIST_A}(3)              # (the live lists stay)
    lwz 7, {LIST_B}(3)
    addi 10, 3, {ANIM_FIELDS} - 4
    addi 11, 8, {H_FIELDS} - 4
    li 12, {ANIM_FIELDS_SIZE} / 4
    mtctr 12
gu_restore:
    lwzu 12, 4(11)
    stwu 12, 4(10)
    bdnz gu_restore
    stw 0, {LIST_A}(3)
    stw 7, {LIST_B}(3)
gu_drop:
    li 9, 0
    stw 9, {H_KEPT}(8)
    blr

gc_equip:                           # replaces bl EQUIP_UPDATE: he is still before the mobys on him follow his pose
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x90(1)
    std 31, 0x70(1)
    std 30, 0x78(1)
    std 29, 0x80(1)
    lis 31, {STATE_HA}
    addi 31, 31, {STATE_LO}
    lis 30, {HERO_HA}
    addi 30, 30, {HERO_LO}
    lis 29, {GIANT_HA}
    addi 29, 29, {GIANT_LO}
    lwz 9, {S_LEGS}(31)
    cmpwi 9, 0
    beq geq_go
    bl gc_still
    li 3, 0                         # the joints' cache again, from the still frame
    bl {JOINT_CACHE}
geq_go:
    bl gc_fx_guard
    ld 29, 0x80(1)
    ld 30, 0x78(1)
    ld 31, 0x70(1)
    addi 1, 1, 0x90
    ld 0, 0x10(1)
    mtlr 0
    b {EQUIP_UPDATE}

gc_fx_guard:                        # (r30 = hero): his joint effects' handles that left his moby's list are dropped (FX_SLOTS)
    lwz 3, 0x2080(30)
    cmpwi 3, 0
    beqlr
    lis 5, {FX_SLOTS_HA}
    addi 5, 5, {FX_SLOTS_LO}
    li 10, {FX_HANDLE}
gfg_handle:
    lwzx 4, 30, 10
    subf 6, 5, 4
    cmplwi 6, {FX_SLOT_COUNT} * 0x40
    bge gfg_next                    # none (or not a slot)
    lwz 7, 0x60(3)
    li 8, {FX_SLOT_COUNT} + 2
gfg_walk:
    cmpwi 7, 0
    beq gfg_lost
    cmpw 7, 4
    beq gfg_next                    # in his list: fine
    subf 6, 5, 7
    cmplwi 6, {FX_SLOT_COUNT} * 0x40
    bge gfg_next                    # a list of something else: left alone
    lwz 7, 0x1c(7)
    addic. 8, 8, -1
    bne gfg_walk
    b gfg_next
gfg_lost:
    li 0, 0
    stwx 0, 30, 10
    li 6, 0x40
gfg_free:
    addi 6, 6, -4
    stwx 0, 4, 6
    cmpwi 6, 0
    bne gfg_free
gfg_next:
    addi 10, 10, 4
    cmpwi 10, {FX_HANDLE_END}
    blt gfg_handle
    blr

gc_ride:                            # (r3 = a moby; r29): with the pelvis, up and down and aside (RIDE)
    lfs 0, 0x18(3)
    lfs 1, {G_RIDE_NOW}(29)
    fadds 0, 0, 1
    stfs 0, 0x18(3)
gc_ride_xy:                         # (r3 = a moby; r29): aside with the pelvis
    lfs 0, 0x10(3)
    lfs 1, {G_RIDER} + 8(29)
    fadds 0, 0, 1
    stfs 0, 0x10(3)
    lfs 0, 0x14(3)
    lfs 1, {G_RIDER} + 0xc(29)
    fadds 0, 0, 1
    stfs 0, 0x14(3)
    blr

gc_ride_height:                     # (r29/r30/r31): the ride now, and LIFT with it (RIDE); his sway (TILT)
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0xd0(1)
    std 28, 0x88(1)
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    lfs 0, {P_ZERO}(9)
    stfs 0, 0x80(1)
    lwz 28, {S_LEGS}(31)
    cmpwi 28, 0
    beq grh_set
    lwz 9, {G_RIDE}(29)
    cmpwi 9, 0
    beq grh_set
    mr 3, 28
    li 4, {PIN_PELVIS}
    addi 5, 1, 0x70
    bl {JOINT_POSITION}
    lbz 9, 0x50(28)                 # drawn between its frame (+0x50) and the next (+0x51) by +0x54, which
    lbz 10, 0x51(28)                # JOINT_POSITION leaves out: the next frame's too, and between them
    cmpw 9, 10
    beq grh_between
    stw 9, 0xc0(1)
    stb 10, 0x50(28)
    mr 3, 28
    li 4, {PIN_PELVIS}
    addi 5, 1, 0xb0
    bl {JOINT_POSITION}
    lwz 9, 0xc0(1)
    stb 9, 0x50(28)
    lfs 3, 0x54(28)
    lfs 0, 0x70(1)
    lfs 1, 0xb0(1)
    fsubs 1, 1, 0
    fmadds 0, 1, 3, 0
    stfs 0, 0x70(1)
    lfs 0, 0x74(1)
    lfs 1, 0xb4(1)
    fsubs 1, 1, 0
    fmadds 0, 1, 3, 0
    stfs 0, 0x74(1)
    lfs 0, 0x78(1)
    lfs 1, 0xb8(1)
    fsubs 1, 1, 0
    fmadds 0, 1, 3, 0
    stfs 0, 0x78(1)
grh_between:
    lfs 0, 0x70(1)                  # (and aside of it)
    lfs 1, 0x10(28)
    fsubs 0, 0, 1
    stfs 0, {G_RIDE_NOW} + 4(29)
    lfs 0, 0x74(1)
    lfs 1, 0x14(28)
    fsubs 0, 0, 1
    stfs 0, {G_RIDE_NOW} + 8(29)
    lfs 0, 0x78(1)                  # the pelvis above the legs' place
    lfs 1, 0x18(28)
    fsubs 0, 0, 1
    stfs 0, {G_RIDE} + 0x10(29)
    lfs 1, {G_RIDE} + 0xc(29)       # the way aside he rides (standing the pelvis is over the legs' place)
    lfs 0, {G_RIDE_NOW} + 4(29)
    fmuls 0, 0, 1
    stfs 0, {G_RIDER} + 8(29)
    lfs 0, {G_RIDE_NOW} + 8(29)
    fmuls 0, 0, 1
    stfs 0, {G_RIDER} + 0xc(29)
    lfs 0, {G_RIDE} + 0x10(29)
    lfs 1, {G_RIDE} + 8(29)
    fsubs 0, 0, 1
    lfs 1, {G_RIDE} + 0xc(29)
    fmuls 0, 0, 1
    stfs 0, 0x80(1)
    lwz 9, {G_TILT}(29)
    cmpwi 9, 0
    beq grh_set
    lfs 1, 0x194(30)                # the lean: toward his speed's share of LEAN_MAX
    lfs 2, {G_TILT} + 8(29)
    fdivs 1, 1, 2
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    lfs 2, {P_ONE}(9)
    fcmpu 0, 1, 2
    ble grh_lean
    fmr 1, 2
grh_lean:
    lfs 2, {G_TILT} + 4(29)
    fmuls 1, 1, 2
    lfs 0, {G_TILT_NOW}(29)
    fsubs 1, 1, 0
    lfs 2, {G_TILT} + 0xc(29)
    fmadds 0, 1, 2, 0
    stfs 0, {G_TILT_NOW}(29)
    lfs 1, 0x48(28)                 # the roll: toward the pelvis aside, in the legs' frame
    bl {COS}
    stfs 1, 0x90(1)
    lfs 1, 0x48(28)
    bl {SIN}
    lfs 2, {G_RIDE_NOW} + 4(29)
    lfs 3, {G_RIDE_NOW} + 8(29)
    lfs 4, 0x90(1)
    fmuls 0, 3, 4                   # left = -x sin + y cos
    fnmsubs 0, 2, 1, 0
    lfs 1, {G_TILT} + 0x10(29)
    fmuls 0, 0, 1
    lfs 1, {G_TILT_NOW} + 4(29)
    fsubs 0, 0, 1
    lfs 2, {G_TILT} + 0x14(29)
    fmadds 1, 0, 2, 1
    stfs 1, {G_TILT_NOW} + 4(29)
    b grh_quat
grh_set:
    lis 9, {POOL_HA}                # no sway, no way aside
    addi 9, 9, {POOL_LO}
    lfs 0, {P_ZERO}(9)
    stfs 0, {G_TILT_NOW}(29)
    stfs 0, {G_TILT_NOW} + 4(29)
    stfs 0, {G_RIDER} + 8(29)
    stfs 0, {G_RIDER} + 0xc(29)
grh_quat:
    lfs 0, 0x80(30)                 # where he rides
    lfs 1, {G_RIDER} + 8(29)
    fadds 0, 0, 1
    stfs 0, {G_RIDER}(29)
    lfs 0, 0x84(30)
    lfs 1, {G_RIDER} + 0xc(29)
    fadds 0, 0, 1
    stfs 0, {G_RIDER} + 4(29)
    lfs 1, {G_TILT_NOW} + 4(29)     # bone 2's turn: x = -roll / 2, y = -lean / 2, w the rest of 1
    lfs 2, {G_TILT_NOW}(29)
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    lfs 3, {P_HALF}(9)
    fmuls 1, 1, 3
    fneg 1, 1
    fmuls 2, 2, 3
    fneg 2, 2
    stfs 1, {G_STILL_JOINTS} + 0x20(29)
    stfs 2, {G_STILL_JOINTS} + 0x24(29)
    lfs 0, {P_ZERO}(9)
    stfs 0, {G_STILL_JOINTS} + 0x28(29)
    lfs 0, {P_ONE}(9)
    fnmsubs 0, 1, 1, 0
    fnmsubs 0, 2, 2, 0
    fsqrts 0, 0
    stfs 0, {G_STILL_JOINTS} + 0x2c(29)
    lfs 0, 0x80(1)
    stfs 0, {G_RIDE_NOW}(29)
    lfs 1, {G_RIDE} + 4(29)
    fadds 0, 0, 1
    stfs 0, {G_LIFT}(29)
    ld 28, 0x88(1)
    addi 1, 1, 0xd0
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_place:                           # (r3 = a moby, r4 = scale, forward, left, up, turn as floats; r30 = hero): at Ratchet, turned with him
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x90(1)
    std 31, 0x70(1)
    std 29, 0x78(1)
    mr 31, 3
    mr 29, 4
    lfs 1, 0x98(30)
    bl {COS}
    stfs 1, 0x80(1)
    lfs 1, 0x98(30)
    bl {SIN}
    lfs 2, 0x80(1)                  # f2 = cos, f1 = sin
    lfs 3, 4(29)                    # forward
    lfs 4, 8(29)                    # left
    lfs 0, 0x80(30)
    fmadds 0, 3, 2, 0
    fnmsubs 0, 4, 1, 0
    stfs 0, 0x10(31)
    lfs 0, 0x84(30)
    fmadds 0, 3, 1, 0
    fmadds 0, 4, 2, 0
    stfs 0, 0x14(31)
    lfs 0, 0x88(30)
    lfs 3, 0xc(29)
    fadds 0, 0, 3
    stfs 0, 0x18(31)
    lfs 0, 0(29)
    stfs 0, 0x2c(31)
    lfs 0, 0x98(30)
    lfs 1, 0x10(29)
    fadds 0, 0, 1
    stfs 0, 0x48(31)
    ld 29, 0x78(1)
    ld 31, 0x70(1)
    addi 1, 1, 0x90
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_hit:                             # (r29 = GIANT, r30 = hero): the punch's sphere ahead of Ratchet
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x100(1)
    lfs 1, 0x98(30)
    bl {COS}
    stfs 1, 0xf0(1)
    lfs 1, 0x98(30)
    bl {SIN}
    lfs 2, 0xf0(1)                  # f2 = cos, f1 = sin
    lfs 3, {G_HIT_AT}(29)
    lfs 0, 0x80(30)                 # the centre, at 0xb0
    fmadds 0, 3, 2, 0
    stfs 0, 0xb0(1)
    lfs 0, 0x84(30)
    fmadds 0, 3, 1, 0
    stfs 0, 0xb4(1)
    lfs 0, 0x88(30)
    lfs 3, {G_HIT_AT} + 4(29)
    fadds 0, 0, 3
    stfs 0, 0xb8(1)
    stfs 2, 0xc0(1)                 # the direction, at 0xc0: ahead and up
    stfs 1, 0xc4(1)
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    lfs 0, {P_MELEE_UP}(9)
    stfs 0, 0xc8(1)
    lfs 0, {P_ZERO}(9)
    stfs 0, 0xcc(1)
    stfs 0, 0xbc(1)
    addi 3, 1, 0x80                 # the descriptor, at 0x80
    lwz 4, 0x2080(30)
    lis 5, {MELEE_FLAGS_HI}
    lfs 1, {G_HIT_DAMAGE}(29)
    addi 7, 1, 0xc0
    bl {DAMAGE_DESC}
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    lfs 0, {P_MELEE_PUSH}(9)
    stfs 0, 0x8c(1)
    li 9, 0
    stb 9, 0x98(1)
    li 9, 3
    stb 9, 0x99(1)
    li 9, {GIANT_MODEL_CLASS}
    sth 9, 0x9a(1)
    addi 3, 1, 0xb0
    lfs 1, {G_HIT_RADIUS}(29)
    li 5, 0
    lwz 6, 0x2080(30)
    addi 7, 1, 0x80
    bl {COLLECT}
    stw 3, 0xd0(1)                  # what it hurt
    lwz 9, {G_PUNCH}(29)
    cmpwi 9, 0
    beq gh_out
    addi 3, 29, {G_PUNCH_BURST}     # gold from the sphere (taken as a moby: its place at +0x10)
    addi 4, 1, 0xa0
    bl gc_puffs
    lis 9, {CAMERA_STATE_HA}        # the camera kicks, harder on a hit, and a hit stops the punch a moment
    addi 9, 9, {CAMERA_STATE_LO}
    lwz 10, 0xd0(1)
    cmpwi 10, 0
    bne gh_struck
    lfs 0, {G_PUNCH} + 0x14(29)
    stfs 0, 0x160(9)
    lwz 10, {G_PUNCH} + 0x18(29)
    stw 10, 0x168(9)
    b gh_out
gh_struck:
    lfs 0, {G_PUNCH} + 0x1c(29)
    stfs 0, 0x160(9)
    lwz 10, {G_PUNCH} + 0x20(29)
    stw 10, 0x168(9)
    lwz 10, {G_PUNCH} + 0x24(29)
    stw 10, {G_PUNCH_STOP}(29)
gh_out:
    addi 1, 1, 0x100
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
    lis 9, {GIANT_HA}               # gold (a ball's colour is set again where it is placed)
    addi 9, 9, {GIANT_LO}
    lwz 9, {G_PART_COLOUR}(9)
    stw 9, 0x38(29)
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
    li 6, {ANIM_BLEND}
gc_anim_blend:                      # (as gc_anim, r6 = the frames to blend over)
    lwz 5, 8(3)
    cmpw 5, 4
    beqlr
    stw 4, 8(3)
    lwz 3, 0(3)
    li 5, 0
    b {MOBY_SET_ANIM}

gc_bomb_colour_0:                  # (r3: a colour of the bomb's, 0xAABBGGRR; r0, r11, r12 free)
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, {S_MODE}(11)
    cmpwi 12, 0
    beq gbc_0_game
    lis 11, {HERO_HA}
    addi 11, 11, {HERO_LO}
    lbz 12, {HERO_KIND}(11)
    cmpwi 12, 2
    beq gbc_0_game
    rlwinm 11, 3, 16, 24, 31       # b
    rlwinm 3, 3, 0, 0, 7          # its alpha
    or 3, 3, 11                   # red b
    mulli 0, 11, 3
    srwi 0, 0, 2
    rlwimi 3, 0, 8, 16, 23          # green 3/4 b
    srwi 0, 11, 2
    rlwimi 3, 0, 16, 8, 15          # blue 1/4 b
gbc_0_game:
    b {BOMB_COLOUR_0}

gc_bomb_colour_1:                  # (r5: a colour of the bomb's, 0xAABBGGRR; r0, r11, r12 free)
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, {S_MODE}(11)
    cmpwi 12, 0
    beq gbc_1_game
    lis 11, {HERO_HA}
    addi 11, 11, {HERO_LO}
    lbz 12, {HERO_KIND}(11)
    cmpwi 12, 2
    beq gbc_1_game
    rlwinm 11, 5, 16, 24, 31       # b
    rlwinm 5, 5, 0, 0, 7          # its alpha
    or 5, 5, 11                   # red b
    mulli 0, 11, 3
    srwi 0, 0, 2
    rlwimi 5, 0, 8, 16, 23          # green 3/4 b
    srwi 0, 11, 2
    rlwimi 5, 0, 16, 8, 15          # blue 1/4 b
gbc_1_game:
    b {BOMB_COLOUR_1}

gc_bomb_colour_2:                  # (r5 and r6: a colour of the bomb's, 0xAABBGGRR; r0, r11, r12 free)
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, {S_MODE}(11)
    cmpwi 12, 0
    beq gbc_2_game
    lis 11, {HERO_HA}
    addi 11, 11, {HERO_LO}
    lbz 12, {HERO_KIND}(11)
    cmpwi 12, 2
    beq gbc_2_game
    rlwinm 11, 5, 16, 24, 31       # b
    rlwinm 5, 5, 0, 0, 7          # its alpha
    or 5, 5, 11                   # red b
    mulli 0, 11, 3
    srwi 0, 0, 2
    rlwimi 5, 0, 8, 16, 23          # green 3/4 b
    srwi 0, 11, 2
    rlwimi 5, 0, 16, 8, 15          # blue 1/4 b
    rlwinm 11, 6, 16, 24, 31       # b
    rlwinm 6, 6, 0, 0, 7          # its alpha
    or 6, 6, 11                   # red b
    mulli 0, 11, 3
    srwi 0, 0, 2
    rlwimi 6, 0, 8, 16, 23          # green 3/4 b
    srwi 0, 11, 2
    rlwimi 6, 0, 16, 8, 15          # blue 1/4 b
gbc_2_game:
    b {BOMB_COLOUR_2}

gc_bomb_channels:                   # (r4, r5, r6 = red, green, blue of a colour of the bomb's)
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, {S_MODE}(11)
    cmpwi 12, 0
    beq gbch_game
    lis 11, {HERO_HA}
    addi 11, 11, {HERO_LO}
    lbz 12, {HERO_KIND}(11)
    cmpwi 12, 2
    beq gbch_game
    mr 4, 6                         # red b, green 3/4 b, blue 1/4 b
    mulli 5, 6, 3
    srwi 5, 5, 2
    srwi 6, 6, 2
gbch_game:
    b {BOMB_CHANNELS}

gc_bomb_kind_a:                     # (in the bomb's update, r3 = the hero kind): him, or Ratchet in the mode
    cmpwi 3, 2
    beq gbk_a_back
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, {S_MODE}(11)
    cmpwi 12, 1
gbk_a_back:
    b {BOMB_KIND_A_BACK}

gc_bomb_kind_b:
    cmpwi 3, 2
    beq gbk_b_back
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, {S_MODE}(11)
    cmpwi 12, 1
gbk_b_back:
    b {BOMB_KIND_B_BACK}

gc_pack:                            # (r31 = state block): the Heli-Pack while the mode is on (PACK_ITEM)
    lis 10, {HERO_HA}
    addi 10, 10, {HERO_LO}
    lwz 11, {S_PACK_BACK}(31)
    lwz 9, {S_MODE}(31)
    cmpwi 9, 0
    beq gp_back
    cmpwi 11, 0                     # on: a Thruster-Pack changed for the Heli-Pack, once
    bnelr
    lwz 9, {PACK_ITEM}(10)
    cmpwi 9, {THRUSTER_PACK}
    bnelr
    lis 12, {UNLOCKS_HA}
    lbz 12, {UNLOCKS_LO} + {HELI_PACK}(12)
    cmpwi 12, 0
    beqlr
    stw 9, {S_PACK_BACK}(31)
    li 9, {HELI_PACK}
    stw 9, {PACK_REQUEST}(10)
    blr
gp_back:                            # off: the pack he wore asked back, out of water
    cmpwi 11, 0
    beqlr
    lwz 9, {STATE_TYPE}(10)
    cmpwi 9, {STATE_TYPE_WATER}
    beqlr
    stw 11, {PACK_REQUEST}(10)
    li 9, 0
    stw 9, {S_PACK_BACK}(31)
    blr

gc_double_jump:                     # (r19 = hero, r3 free): in the mode a second X goes to the glide's test
    lis 3, {STATE_HA}
    lwz 3, {STATE_LO} + {S_MODE}(3)
    cmpwi 3, 0
    beq gdj_game
    lbz 3, {HERO_KIND}(19)
    cmpwi 3, 0
    bne gdj_game
    b {GLIDE_TEST}
gdj_game:
    lbz 3, 0x20a8(19)               # the displaced instruction
    b {DOUBLE_JUMP_BACK}

gc_no_flips:                        # (r3 = the state asked for, r27 = hero): in the mode a flip is his plain jump
{FLIP_TESTS}
    b gnf_game
gnf_mode:
    lis 5, {STATE_HA}
    lwz 5, {STATE_LO} + {S_MODE}(5)
    cmpwi 5, 0
    beq gnf_game
    lbz 5, {HERO_KIND}(27)
    cmpwi 5, 0
    bne gnf_game
    li 3, {PLAIN_JUMP}
gnf_game:
    cmpwi 1, 3, 0x64                # the displaced instruction
    b {NO_FLIPS_BACK}

gc_jump_sounds:                     # (r27 = hero, r31 = his moby; r3, r4 free): in the mode no animation sounds in PACK_JUMPS
    lis 3, {STATE_HA}
    lwz 3, {STATE_LO} + {S_MODE}(3)
    cmpwi 3, 0
    beq gjs_game
    lbz 3, {HERO_KIND}(27)
    cmpwi 3, 0
    bne gjs_game
    lwz 3, 0x2084(27)
{PACK_JUMP_TESTS}
gjs_game:
    cmpwi 30, 0                     # the displaced instruction
    b {JUMP_SOUNDS_BACK}
gjs_quiet:
    li 3, 0xff                      # no looping sound (one going stops: 0x8c150)
    stb 3, 0x7c(31)
    b {JUMP_SOUNDS_SKIP}

gc_hover_sound:                     # (r25 = hero, r3 free): in the mode the pack's whirr is not started
    lis 3, {STATE_HA}
    lwz 3, {STATE_LO} + {S_MODE}(3)
    cmpwi 3, 0
    beq ghs_game
    lbz 3, {HERO_KIND}(25)
    cmpwi 3, 0
    bne ghs_game
    b {HOVER_SOUND_SKIP}
ghs_game:
    li 3, 3                         # the displaced instruction
    b {HOVER_SOUND_BACK}

gc_jump:
    lfs 3, 0x430(29)                # the displaced instruction: the jump's height (r29 = hero)
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, {S_MODE}(11)
    cmpwi 12, 0
    beq gj_back
    lbz 12, {HERO_KIND}(29)
    cmpwi 12, 0
    bne gj_back
    lis 11, {GIANT_HA}
    addi 11, 11, {GIANT_LO}
    lfs 0, {G_JUMP}(11)
    fmuls 3, 3, 0
gj_back:
    b {JUMP_BACK}

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
    bne gv_air
    lwz 12, {S_PUNCH}(11)           # a punch or the bomb going: he stands (HOLD_MOVES)
    cmpwi 12, 0
    beq gv_run
    lwz 12, {S_MOVE}(11)
    li 11, {HOLD_MOVES}
    srw 11, 11, 12
    andi. 11, 11, 1
    beq gv_run
    lis 11, {POOL_HA}
    addi 11, 11, {POOL_LO}
    lfs 0, {P_ZERO}(11)
    fmuls 31, 31, 0
    b gv_back
gv_run:
    lis 11, {GIANT_HA}
    addi 11, 11, {GIANT_LO}
    lfs 0, {G_RUN}(11)
    fmuls 31, 31, 0
    b gv_back
gv_air:                             # in a jump or a hover: AIR
    lwz 12, {STATE_TYPE}(31)
    cmpwi 12, {STATE_TYPE_JUMP}
    beq gv_air_on
    cmpwi 12, {STATE_TYPE_HOVER}
    bne gv_back
gv_air_on:
    lis 11, {GIANT_HA}
    addi 11, 11, {GIANT_LO}
    lfs 0, {G_AIR}(11)
    fmuls 31, 31, 0
gv_back:
    b {VELOCITY_BACK}

gc_lunge:                           # at LUNGE_HOOK (r30 = hero): the punch carries him forward (LUNGE)
    lfs 31, 0x80(30)                # the displaced instruction
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, {S_MODE}(11)
    cmpwi 12, 0
    beq gln_back
    lwz 12, {S_MOVE}(11)
    cmpwi 12, 0
    bne gln_back
    lwz 12, {S_PUNCH}(11)
    lis 11, {GIANT_HA}
    addi 11, 11, {GIANT_LO}
    lwz 11, {G_LUNGE}(11)
    cmpw 12, 11
    blt gln_back
    lis 11, {GIANT_HA}
    addi 11, 11, {GIANT_LO}
    lwz 11, {G_LUNGE} + 4(11)
    cmpw 12, 11
    bgt gln_back
    lbz 12, {HERO_KIND}(30)
    cmpwi 12, 0
    bne gln_back
    lwz 12, 0x2084(30)              # standing or walking
    cmpwi 12, 0
    beq gln_go
    cmpwi 12, {WALK_STATE}
    bne gln_back
gln_go:
    lwz 12, 0x2080(30)
    cmpwi 12, 0
    beq gln_back
    lis 11, {GIANT_HA}
    addi 11, 11, {GIANT_LO}
    lfs 0, {G_LUNGE} + 8(11)
    lfs 1, 0xc0(12)
    lfs 2, 0xe0(30)
    fmadds 2, 1, 0, 2
    stfs 2, 0xe0(30)
    lfs 1, 0xc4(12)
    lfs 2, 0xe4(30)
    fmadds 2, 1, 0, 2
    stfs 2, 0xe4(30)
gln_back:
    b {LUNGE_BACK}

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


def tests(register, values, label):
    """Assembly: to label when the register is one of the values (falls through otherwise)."""
    return "\n".join(f"    cmpwi {register}, {value}\n    beq {label}" for value in values)


def hooks(args):
    return [Hook(PEDESTAL_HOOK, "pedestal", PEDESTAL_HOOK_WORD, jump=True),
            *(Hook(site, "gc_frame", HERO_MAIN, chain=True) for site in FRAME_HOOKS),
            Hook(HUD_HOOK, "gc_hud", HUD_HOOK_WORD, chain=True),
            *(Hook(site, "gc_pad", GAMEPLAY_FRAME, chain=True) for site in PAD_HOOKS),
            Hook(VELOCITY_HOOK, "gc_velocity", VELOCITY_HOOK_WORD, jump=True),
            Hook(LUNGE_HOOK, "gc_lunge", LUNGE_HOOK_WORD, jump=True),
            Hook(BOMB_KIND_HOOKS[0], "gc_bomb_kind_a", BOMB_KIND_WORD, jump=True),
            Hook(BOMB_KIND_HOOKS[1], "gc_bomb_kind_b", BOMB_KIND_WORD, jump=True),
            *(Hook(site, f"gc_bomb_colour_{i}", function) for i, (site, function, _, _) in enumerate(BOMB_COLOUR_HOOKS)),
            Hook(BOMB_CHANNELS_HOOK, "gc_bomb_channels", BOMB_CHANNELS),
            Hook(JUMP_HOOK, "gc_jump", JUMP_HOOK_WORD, jump=True),
            Hook(DOUBLE_JUMP_HOOK, "gc_double_jump", DOUBLE_JUMP_WORD, jump=True),
            Hook(HOVER_SOUND_HOOK, "gc_hover_sound", HOVER_SOUND_WORD, jump=True),
            Hook(NO_FLIPS_HOOK, "gc_no_flips", NO_FLIPS_WORD, jump=True),
            Hook(JUMP_SOUNDS_HOOK, "gc_jump_sounds", JUMP_SOUNDS_WORD, jump=True),
            Hook(EQUIP_HOOK, "gc_equip", EQUIP_UPDATE)]


def data(args):
    def texts(vaddr):
        return TEXT_BUY + b"\0" + TEXT_COST + b"\0" + TEXT_GOT + b"\0" + bytes(TEXT_ROOM) + TEXT_HINT + b"\0"
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
        block += struct.pack(">f", RUN)
        hit_at, radius, damage = PUNCH
        assert len(block) == G_HIT_AT
        block += struct.pack(">4f32x", *hit_at, radius, damage)
        assert len(block) == G_LIFT
        block += struct.pack(">3f3iI", LIFT, ZOOM, ZOOM_EASE, *STILL, 0)
        assert len(block) == G_KEPT_FIELDS
        block += bytes(ANIM_FIELDS_SIZE)
        assert len(block) == G_BALL_SCALE - 4
        block += struct.pack(">4x3f", *CHAINS)
        legs_chain = CHAIN_LEGS
        if ROD[0] and ROD[3]:                  # one ball, the column's joint on Clank (ROD)
            legs_chain = (1, ROD[1], ROD[1][:2] + (ROD[1][2] + LIFT,))
        block += struct.pack(">3f3ffi", *legs_chain[1], *legs_chain[2], 0.0, legs_chain[0])
        assert len(block) == G_BALLS and CHAIN_SIZE == 0x20
        block += bytes(CHAIN_MAX * 0x10)
        assert len(block) == G_BALL_ANIM
        block += struct.pack(">iII4x", BALL_ANIM, BALL_COLOUR, PART_COLOUR)
        assert len(block) == G_ARM_MOBY
        block += struct.pack(">IIff2f8x", 0, 0, MISSILES, MISSILE_SIZE, *BOMB_AT)
        assert len(block) == G_MANIP and (vaddr + G_MANIP) % 0x10 == 0
        block += bytes(0x40)
        assert len(block) == G_MOVES
        assert len(MOVE_SOUNDS) == len(MOVE_TABLE)
        for (part, anim, sided, frames, action, idle, grow, bones, scale, spot, anchor, turn, rate, repeat, blend, shrink, pin,
             balls), sound in zip(MOVE_TABLE, MOVE_SOUNDS):
            block += struct.pack(">7i2if3f3f2f3iii2h", part, anim, sided, frames, action, idle, grow, *bones, scale, *spot, *anchor,
                                 turn, rate, repeat, blend, shrink, pin, balls, *sound)
        assert len(block) == G_MOVES + len(MOVE_TABLE) * MOVE_SIZE == G_BOMB_COOLDOWN
        block += struct.pack(">i12x", BOMB_COOLDOWN)
        assert len(block) == G_EYE_ENTRY
        block += bytes(G_JUMP - G_EYE_ENTRY)
        assert len(block) == G_JUMP
        block += struct.pack(">fi4ff", JUMP, JUMP_ANIM, *CAM_JUMP, 0.0)
        block += bytes(G_LEG - len(block))
        block += struct.pack(">ii3f", CLANK_LEG[0], CLANK_LEG[1], *CLANK_LEG[2])
        assert len(block) == G_LEG_MOBY
        block += struct.pack(">II4x", 0, LEG_MOBY)
        assert (vaddr + G_LEG_MANIP) % 0x10 == 0
        block += bytes(0x40)
        assert len(block) == G_CLANK_STILL
        block += struct.pack(">3iI", *CLANK_STILL, 0)
        assert len(block) == G_CLANK_FIELDS
        block += bytes(ANIM_FIELDS_SIZE)
        assert len(block) == G_SEAT
        block += struct.pack(">if8x", *CLANK_SEAT)
        assert len(block) == G_PACK_STILL
        block += struct.pack(">3iI", *PACK_STILL, 0) + bytes(ANIM_FIELDS_SIZE)
        assert len(block) == G_STRUTS
        block += struct.pack(">ii8x", *STRUTS[:2])
        for k, place in enumerate(STRUTS[2]):
            if k == 0 and ROD[0]:              # the column down to the joint (ROD)
                place = place[:3] + (place[3] + ROD[1][2] - ROD_REST[0],) + place[4:]
            block += struct.pack(">5f", *place)
        block += bytes(G_STRUT_RECORDS - len(block))
        block += bytes(2 * 0x10)
        block += bytes(G_STRUT_JOINTS - len(block))
        assert (vaddr + G_STRUT_JOINTS) % 0x10 == 0
        for bone, turn, scale, place in STRUT_JOINTS:
            block += struct.pack(">Ii8x4f3f4x3f4x", 0, bone, *turn, *scale, *place) + bytes(0x40)
        assert len(block) == G_JOINT_LIST
        block += struct.pack(">I", OWN_JOINTS + len(PIN_JOINTS)) + bytes(4 * OWN_JOINTS)
        block += b"".join(struct.pack(">I", vaddr + G_JOINT_ENTRIES + 0x10 * k) for k in range(len(PIN_JOINTS)))
        block += bytes(G_JOINT_ENTRIES - len(block))
        for bones in PIN_JOINTS:
            assert len(bones) <= 12
            block += struct.pack(">H2x", len(bones)) + bytes(bones) + bytes(12 - len(bones))
        block += bytes(G_ARMS_SHOULDERS - len(block))
        block += struct.pack(">f12x", ARMS_SHOULDERS[2])
        assert len(block) == G_ARMS_BONES and (vaddr + G_ARMS_BONES) % 0x10 == 0
        block += bytes(BONES * 0x10)
        assert len(block) == G_ARM_CHAINS and BONES == 84
        for side in range(2):                       # (the same: gc_chains mirrors the right's)
            count, start, end = ARM_CHAIN
            block += struct.pack(">3f3ffi", *start, *end, 0.0, count)
        block += bytes(2 * CHAIN_MAX * 0x10)
        assert len(block) == G_PISTONS_ON
        block += struct.pack(">i12x", ARM_PISTONS[0])
        assert (vaddr + G_PISTONS) % 0x10 == 0
        for place, joint in ARM_PISTONS[1:]:
            bone, turn, scale, at = joint
            block += struct.pack(">4xi8x4f3f4x3f4x", bone, *turn, *scale, *at) + bytes(0x40)
            block += bytes(0x10) + struct.pack(">5f3f", *place, *piston_grow(place, joint))
            assert P_GROW == P_AT + 0x14 and PISTON_SIZE == P_GROW + 0xc
        assert len(block) == G_STILL_JOINTS
        block += struct.pack(">i12x", len(STILL_JOINTS))
        for bone, turn in STILL_JOINTS:
            block += struct.pack(">i12x4f", bone, *turn)
        assert len(block) == G_BOOT_SEAT and len(STILL_JOINTS) == 7
        block += struct.pack(">i12x", 1)
        for place, rows, euler in BOOT_SEAT:
            block += struct.pack(">3f9f3f4x", place[0], place[1], place[2] + LIFT - BOOT_SEAT_LIFT, *rows, *euler)
        assert len(block) == G_SEAT_AT
        block += struct.pack(">i3f", SEAT_AT[0], *SEAT_AT[1])
        assert len(block) == G_LUNGE
        block += struct.pack(">iif4x", *LUNGE)
        assert len(block) == G_VIEW
        on, distance, pitch, turn, up = VIEW
        block += struct.pack(">i5f8x", on, distance, math.cos(pitch), -math.sin(pitch), turn, up)
        assert len(block) == G_POSE
        block += struct.pack(">i5f8x", *PUNCH_POSE)
        assert len(block) == G_SHOCK
        block += struct.pack(">i5fiIIIiI", *SHOCKWAVE, 0, 0, 0, 0, SHOCK_COLOUR)
        assert len(block) == G_SHOCK_BURST
        block += puffs(*SHOCK_BURST)
        assert len(block) == G_DANCE
        block += struct.pack(">i8ffi", *BOMB_DANCE) + struct.pack(">f3ff", 0.0, 0.0, 0.0, 0.0, 1.0)
        assert len(block) == G_DANCE_GLOW
        block += puffs(*DANCE_GLOW) + puffs(*DANCE_BURST)
        assert len(block) == G_PUNCH
        block += struct.pack(">i4ffifii", *PUNCH_TWIST) + struct.pack(">i4x", 0)
        assert len(block) == G_PUNCH_BURST
        block += puffs(*PUNCH_BURST)
        assert len(block) == G_FLAMES
        on, where, speeds, frames, count, spark_frames, carried, aside, spread = FLAMES
        block += struct.pack(">i3f2f2i2i2f", on, *where, *speeds, frames, count, *spark_frames, *carried)
        block += struct.pack(">5f2If2f", *FIRE_LOOK, *SPARK_COLOURS, SPARK_FAR, aside, spread)
        assert len(block) == G_RIDE
        block += struct.pack(">i3f2f2f", RIDE[0], LIFT, *RIDE[1:], 0.0, 0.0, 0.0, 0.0)
        assert len(block) == G_TILT and STILL_JOINTS[0][0] == 2
        block += struct.pack(">i6f4x2f8x", *TILT, 0.0, 0.0)
        assert len(block) == G_ROD
        rod_on, rod_top, rod_bottom, rod_ball = ROD
        column = STRUTS[2][0]                  # (scale, forward, left, up, turn) from his place on the ground
        block += struct.pack(">i3ff3fff8x", rod_on, *rod_top, rod_top[2] - rod_bottom,
                             rod_top[0] - column[1], rod_top[1] - column[2], LIFT + ROD_REST[0] - column[3], rod_ball,
                             STRUT_JOINTS[0][2][1] / ROD_REST[1])
        assert len(block) == G_RIDER
        block += bytes(0x10)
        assert len(block) == G_SCENE
        block += struct.pack(">3if", 0, 0, 0, 1.0 / (SCENE_STREAM_TO - SCENE_STREAM_FROM)) + bytes(0x40)
        assert len(block) == G_SCENE_CAM
        block += b"".join(struct.pack(">6f", *key) for key in SCENE_CAM)
        assert len(block) == G_SCENE_SHOW
        block += b"".join(struct.pack(">4f", *key) for key in SCENE_SHOW)
        assert len(block) == G_SCENE_RING
        block += struct.pack(">3f3ff2I2iIf4x", *SCENE_RING[0], *SCENE_RING[1], SCENE_RING[2], *SCENE_RING[3], *SCENE_RING[4],
                             *SCENE_RING[5:])
        block += puffs(*SCENE_STREAM) + puffs(*SCENE_BOND)
        sparks = SCENE_BOND_SPARKS
        block += struct.pack(">3f3ff2I2iIf4x", *sparks[0], *sparks[1], sparks[2], *sparks[3], *sparks[4], *sparks[5:])
        assert len(block) == G_FLAME_SOUND
        block += struct.pack(">4i4i32x", *FLAME_SOUND, -1, 0, 0, 0)
        assert len(block) == G_SOUNDS and G_AIR == G_SOUNDS + 4
        block += struct.pack(">if8x", 0, AIR)
        punch = MOVE_TABLE[0]
        assert punch[3] == sum(PUNCH_POSE[1:3]) + sum(PUNCH_POSE[4:]) and punch[4] == PUNCH_POSE[1] + PUNCH_POSE[2]
        assert LUNGE[:2] == (PUNCH_POSE[1] + 1, punch[4])
        bomb = MOVE_TABLE[2]
        assert bomb[3] == bomb[5] == BOMB_DANCE[1] + BOMB_DANCE[2] and bomb[4] == BOMB_DANCE[1]
        return block

    def index_buffers(vaddr):
        pieces = []
        for part in part_data():
            pieces += [part, bytes(-len(part) % 0x10)]
        pieces.append(bytes(-sum(map(len, pieces)) % 0x80))
        pieces += [ball_vertices(), bytes(-len(ball_vertices()) % 0x80)]
        return pieces + [strut_vertices()]
    model, textures, pixels = giant_data()
    missile, missile_textures, missile_pixels = giant_data(MISSILE_CLASS)
    shock, shock_textures, shock_pixels = giant_data(SHOCK_CLASS)
    return [("rw", "texts", texts), ("rw", "giant", giant),
            ("rw2", "giant_model", lambda vaddr: [model]), ("rw2", "giant_textures", lambda vaddr: [textures]),
            ("rw2", "giant_pixels", lambda vaddr: [pixels]), ("rw2", "giant_parts", index_buffers),
            ("rw2", "missile_model", lambda vaddr: [missile]), ("rw2", "missile_textures", lambda vaddr: [missile_textures]),
            ("rw2", "missile_pixels", lambda vaddr: [missile_pixels]),
            ("rw2", "shock_model", lambda vaddr: [shock]), ("rw2", "shock_textures", lambda vaddr: [shock_textures]),
            ("rw2", "shock_pixels", lambda vaddr: [shock_pixels]),
            ("rw2", "eye_texture", lambda vaddr: [eye_texture()]),
            ("rw2", "giant_sounds", lambda vaddr: [sound_data()])]


@functools.cache
def giant_data(cls=None):
    """Giant Clank's model (or that of cls, of his level), texture block (rc2data.giant_textures)
    and pixels, from RC1's data."""
    args = () if cls is None else (cls,)
    return Extract("giant_model", *args), Extract("giant_textures", *args), Extract("giant_pixels", *args)


@functools.cache
def part_data():
    """The parts' index buffers (rc2data.giant_part), in the order of PARTS, then the ball's."""
    tubes = {PART_STRUT_L: 0, PART_STRUT_R: 1, PART_COLUMN: 2}
    return tuple(Extract("giant_tube_indices", tube_args(), tubes[k]) if k in tubes
                 else Extract("giant_part", [list(r) for r in ranges]) for k, ranges in enumerate(PARTS)) + (Extract("giant_ball_indices", *BALL),)


@functools.cache
def sound_data():
    """His sound definitions and the missile's, then from SOUNDS_BANK_OFF their bank (rc2data.giant_sounds)."""
    data = Extract("giant_sounds", [GIANT_MODEL_CLASS, MISSILE_CLASS])
    assert struct.unpack_from(">I", data.data, SOUNDS_BANK_OFF)[0] == 3       # the bank's first word
    return data


def sound_parts():
    """Assembly for gc_sounds (r9 = the first part's header, r4 his definitions, r5 their count): SOUND_PARTS get them."""
    header = main_heap_layout()["HEADER"]
    return "\n".join(f"    lis 6, {k * header >> 16}\n    ori 6, 6, {k * header & 0xFFFF}\n    add 6, 9, 6\n"
                     f"    stw 4, 0x28(6)\n    stb 5, 0xd(6)" for k in SOUND_PARTS)


@functools.cache
def eye_texture():
    """Backpack Clank's texture in gold (rc2data.clank_gold_eyes): its entry, then from +0x80 its pixels."""
    return Extract("clank_gold_eyes")


@functools.cache
def ball_vertices():
    """The ball's vertex buffer (rc2data.giant_ball_vertices)."""
    return Extract("giant_ball_vertices", *BALL)


@functools.cache
def strut_vertices():
    """The tubes' vertex buffer (rc2data.giant_tube_vertices)."""
    return Extract("giant_tube_vertices", tube_args())


def tube_args():
    return [[bone, [list(p) for p in profile], sides, steps] for bone, profile, sides, steps in TUBES]


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
    count = len(part_data())
    assert all(len(part) == len(part_data()[0]) for part in part_data())
    ibs_at = headers_at + count * header
    ibs_at += -ibs_at % 0x80
    ball_vb = count * stride
    ball_vb += -ball_vb % 0x80
    strut_vb = ball_vb + len(ball_vertices())
    strut_vb += -strut_vb % 0x80
    parts_size = strut_vb + len(strut_vertices())
    extra, end = {}, ibs_at + parts_size
    for name, cls in EXTRA_MODELS:                  # the missile's and the ring's models, their entries behind each
        model_x, textures_x, _ = giant_data(cls)
        at = end + -end % 0x80
        entries_at = len(model_x) + -len(model_x) % 0x10
        count_x = (len(textures_x) - 8) // 0x24
        end = at + entries_at + count_x * 0x24
        extra.update({f"{name}_AT_HI": at >> 16, f"{name}_AT_LO": at & 0xFFFF, f"{name}_SIZE": len(model_x),
                      f"{name}_ENTRIES_AT": entries_at, f"{name}_ENTRY_COUNT": count_x, f"{name}_ENTRIES_SIZE": count_x * 0x24})
    eye_entry_at = end + -end % 0x10
    return dict(EYE_ENTRY_AT_HI=eye_entry_at >> 16, EYE_ENTRY_AT_LO=eye_entry_at & 0xFFFF, **extra,
                ENTRY_COUNT=entries, ENTRIES_SIZE=entries * 0x24, HEADER=header, PART_COUNT=count,
                BALL_HEADER_HI=(headers_at + PART_BALL * header) >> 16, BALL_HEADER_LO=(headers_at + PART_BALL * header) & 0xFFFF,
                BALL_VB_HI=ball_vb >> 16, BALL_VB_LO=ball_vb & 0xFFFF,
                STRUT_VB_HI=strut_vb >> 16, STRUT_VB_LO=strut_vb & 0xFFFF,
                HEADERS_AT_HI=headers_at >> 16, HEADERS_AT_LO=headers_at & 0xFFFF, IBS_AT_HI=ibs_at >> 16,
                IBS_AT_LO=ibs_at & 0xFFFF, IB_STRIDE_HI=stride >> 16, IB_STRIDE_LO=stride & 0xFFFF,
                PARTS_SIZE_HI=parts_size >> 16, PARTS_SIZE_LO=parts_size & 0xFFFF,
                MODEL_RESERVE_HI=reserve(eye_entry_at + 0x24))


def reserve(size):
    """Heap memory for size bytes, in the 64 KB steps addis takes."""
    return (size + 0xFFFF) >> 16


def pool(args):
    return dict(SCALE=DISPLAY_SCALE, LIFT=DISPLAY_LIFT, SPIN=SPIN, PI=3.141592653589793, TWO_PI=6.283185307179586,
                RANGE2=RANGE * RANGE, SHAKE=SHAKE[1], POSE_BLEND=POSE[4], POSE_SPEED=1.0, POSE_EASE=0.1,
                ZERO=0.0, ONE=1.0, HALF=0.5, ARM_LEAST=ARM_LEAST, TWO=2.0, THREE=3.0, MELEE_PUSH=MELEE_PUSH, MELEE_UP=MELEE_UP, ARC=SCENE_ARC,
                HALF_PI=1.5707963267948966, ATAN_A=-0.0464964749, ATAN_B=0.15931422, ATAN_C=-0.327622764)


def parts(args):
    forget = "\n".join(f"    stw 9, {record:#x}(31)" for record in PART_RECORDS)    # r9 = 0: the mobys are gone
    forget += "".join(f"\n    stw 9, {G_BALLS + 0x10 * ball:#x}(29)" for ball in range(CHAIN_MAX))
    forget += "".join(f"\n    stw 9, {G_ARM_BALLS + 0x10 * ball:#x}(29)" for ball in range(2 * CHAIN_MAX))
    forget += "".join(f"\n    stw 9, {G_ARM_CHAINS + CHAIN_SIZE * side + C_GROWN:#x}(29)" for side in range(2))
    forget += "".join(f"\n    stw 9, {G_PISTONS + PISTON_SIZE * side + at:#x}(29)" for side in range(2)
                      for at in (P_RECORD, P_JOINT + S_J_MOBY, P_JOINT + S_J_MANIP))
    forget += "".join(f"\n    stw 9, {at:#x}(29)" for at in (G_CHAIN_LEGS + C_GROWN, G_SHOCK_LEFT, G_DANCE_PACK, G_PUNCH_STOP, G_ARM_MOBY, G_MANIP, G_LEG_MOBY, G_LEG_MANIP, G_CLANK_KEPT, G_PACK_STILL + H_KEPT,
                                                                     G_STRUT_RECORDS, G_STRUT_RECORDS + 0x10,
                                                                     G_STRUT_JOINTS, G_STRUT_JOINTS + S_J_SIZE,
                                                                     G_STRUT_JOINTS + S_J_MANIP, G_STRUT_JOINTS + S_J_SIZE + S_J_MANIP))
    extra = "\n".join(EXTRA_MODEL.replace("@X@", name).replace("@x@", name.lower()).replace("@what@", what)
                      for (name, _), what in zip(EXTRA_MODELS, ("the missile", "the jump's ring")))
    return [CODE.replace("@RECORDS_FORGET@", forget).replace("@EXTRA_MODELS@", extra)]


def fields(args, addr):
    at = addr["texts"]
    cost = at + len(TEXT_BUY) + 1
    got = cost + len(TEXT_COST) + 1
    buffer = got + len(TEXT_GOT) + 1
    hint = buffer + TEXT_ROOM
    bit = 31 - (CIRCLE.bit_length() - 1)        # rlwinm keeps bits mb..me (big-endian numbering): all but CIRCLE
    model, textures, pixels = giant_data()
    giant = dict(**pair("GIANT_MODEL", addr["giant_model"]), **pair("GIANT_TEXTURES", addr["giant_textures"]),
                 **pair("GIANT_PIXELS", addr["giant_pixels"]), **pair("GIANT_PARTS", addr["giant_parts"]),
                 MODEL_SIZE_HI=len(model) >> 16, MODEL_SIZE_LO=len(model) & 0xFFFF,
                 PIXELS_SIZE_HI=len(pixels) >> 16, PIXELS_SIZE_LO=len(pixels) & 0xFFFF, **main_heap_layout(),
                 CLASS_INFO_HI=CLASS_INFO >> 16, CLASS_INFO_LO=CLASS_INFO & 0xFFFF)
    end = len(pixels)
    for name, cls in EXTRA_MODELS:                  # their pixels behind his
        pixels_x = giant_data(cls)[2]
        pixels_at = end + -end % 0x80              # (not "at": that is the texts', used below)
        end = pixels_at + len(pixels_x)
        low = name.lower()
        giant.update(**pair(f"{name}_MODEL", addr[f"{low}_model"]), **pair(f"{name}_TEXTURES", addr[f"{low}_textures"]),
                     **pair(f"{name}_PIXELS", addr[f"{low}_pixels"]),
                     **{f"{name}_PIXELS_AT_HI": pixels_at >> 16, f"{name}_PIXELS_AT_LO": pixels_at & 0xFFFF,
                        f"{name}_PIXELS_SIZE_HI": len(pixels_x) >> 16, f"{name}_PIXELS_SIZE_LO": len(pixels_x) & 0xFFFF})
    eye_pixels_at = end + -end % 0x80
    eye_size = len(eye_texture()) - 0x80
    giant.update(PIXELS_RESERVE_HI=reserve(eye_pixels_at + eye_size),
                 **pair("EYE_TEXTURE", addr["eye_texture"]), **pair("GIANT_SOUNDS", addr["giant_sounds"]),
                 SOUND_PARTS_SET=sound_parts(),
                 EYE_PIXELS_AT_HI=eye_pixels_at >> 16, EYE_PIXELS_AT_LO=eye_pixels_at & 0xFFFF,
                 EYE_PIXELS_SIZE_HI=eye_size >> 16, EYE_PIXELS_SIZE_LO=eye_size & 0xFFFF,
                 MISSILE_JOINTS_FIRST=MISSILE_JOINTS[0], MISSILE_JOINTS_LAST=MISSILE_JOINTS[-1],
                 HOVER_A=HOVER_STATES[0], HOVER_B=HOVER_STATES[1],
                 FLIP_TESTS=tests(3, FLIP_STATES, "gnf_mode"), FLAME_TESTS=tests(9, FLAME_STATES, "gf_go"),
                 PACK_JUMP_TESTS=tests(3, PACK_JUMPS, "gjs_quiet"), FLAME_SOUND_TESTS=tests(9, FLAME_STATES, "gfs_burn"),
                 LIST_A=LIST_HEADS[0], LIST_B=LIST_HEADS[1])
    assert MISSILE_JOINTS == tuple(range(MISSILE_JOINTS[0], MISSILE_JOINTS[-1] + 1))
    skip = 31 - (SKIP_UPDATE.bit_length() - 1)   # rlwinm keeps bits mb..me (big-endian numbering): all but SKIP_UPDATE
    giant.update(NOT_SKIP_MB=(skip + 1) % 32, NOT_SKIP_ME=(skip - 1) % 32)
    giant.update(TINT_R=GOLD_TINT[0], TINT_G=GOLD_TINT[1], TINT_B=GOLD_TINT[2])
    giant.update(MELEE_FLAGS_HI=MELEE_FLAGS >> 16, CIRCLE_BUTTON=MOVE_BUTTONS[1],
                 ARMS_LEFT=ARMS_SHOULDERS[0], ARMS_RIGHT=ARMS_SHOULDERS[1])
    assert model.data[8] == BONES
    assert PUNCH_ANIMS[1] == PUNCH_ANIMS[0] + 1 and PART_RIGHT_ARM == PART_LEFT_ARM + 1
    return dict(**giant, **pair("GIANT", addr["giant"]), FREE_A=FREE_STATES[0], FREE_B=FREE_STATES[1], FREE_C=FREE_STATES[2],
                **pair("TEXT_BUY", at), **pair("TEXT_COST", cost), **pair("TEXT_GOT", got), **pair("TEXT_BUFFER", buffer), **pair("TEXT_HINT", hint),
                ROOM_A=ROOMS[0], ROOM_B=ROOMS[1], DISPLAY_LAST=DISPLAY_COUNT - 1, SHOW_OFF=SHOW_CLASS - DISPLAY_FIRST,
                POSE_HI=POSE[0] << 8 | POSE[1], POSE_LO=POSE[2] << 8 | POSE[3],
                GOLD_HI=GOLD >> 16, GOLD_LO=GOLD & 0xFFFF, SHAKE_FRAMES=SHAKE[0],
                CIRCLE_CLEAR_MB=(bit + 1) % 32, CIRCLE_CLEAR_ME=(bit - 1) % 32)
