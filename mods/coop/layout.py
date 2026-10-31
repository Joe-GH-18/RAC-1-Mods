"""The mod's block (COOP, writable data behind the tag TAG): its runtime words and, from TUNING,
the values to tune in a running game with tools/peek.py (tools/coop.py names them). Every name
here is a template field of the assembly."""
import json
import math
import os
import struct

TAG = b"COOP-CLANK-BLOCK"

# Runtime (zero at boot).
C_READ, C_READS, C_PORT, C_HELD, C_PRESSED = 0x00, 0x04, 0x08, 0x0C, 0x10
C_MODE = 0x14                  # MODE_*
C_TIMER = 0x18                 # frames in the mode
C_FRAME = 0x1C                 # FRAME_COUNTER a frame ago (a new level starts it again)
C_BODY, C_WINGS, C_JET_L, C_JET_R = 0x20, 0x24, 0x28, 0x2C   # mobys (0 = none)
C_MODEL = 0x30                 # Clank's installed model (0 = not yet)
C_KEPT_CLANK, C_KEPT_PACK = 0x34, 0x36   # the backpack mobys' draw distances (+0x32) while hidden
C_HIDDEN = 0x38                # they are hidden
C_KEPT_SCALES = 0x348          # their scales (+0x2c) while hidden at 0: backpack Clank, the pack (0 = none kept)
C_ANIM = 0x3C                  # the body's animation (-1 = none set)
C_POS = 0x40                   # his place (3 floats), +0x4c the hover height over the ground
C_HOVER = 0x4C
C_VEL = 0x50                   # his velocity (3 floats, units/s)
C_YAW, C_ROLL, C_PITCH = 0x5C, 0x60, 0x64
C_ENERGY = 0x68                # float
C_SELECT = 0x6C                # frames Select is held
C_IDLE = 0x70                  # frames the stick is at rest
C_GROUND = 0x74                # Ratchet's ground height (his z while down)
C_FROM = 0x78                  # where a scripted move starts (3 floats)
C_BOOST, C_BOOST_WAIT = 0x88, 0x8C   # frames left
C_BOOST_DIR = 0x90             # 2 floats
C_OFFSCREEN = 0x98             # frames off the screen
C_GONE = 0x9C                  # frames without Player 2's pad
C_TARGET = 0xA0                # the locked enemy (0 = none)
C_ZAP = 0xA4                   # frames the zap is held (0 = not zapping)
C_PUNCH, C_PUNCH_WAIT = 0xA8, 0xAC
C_DRIVER = 0xB4                # 0 nobody, 1 Player 2, 2 AI
C_AI = 0xB8                    # the AI's state
C_WISH = 0xC4                  # the wish velocity (2 floats)
C_STICK = 0xCC                 # the stick or the AI's (2 floats, y up)
C_BUTTONS, C_BUTTONS_NEW = 0xD4, 0xD8   # held / pressed: Player 2's or the AI's
C_SEAT = 0xDC                  # backpack Clank's place (3 floats)
C_TMP = 0xE8                   # scratch (0x18 bytes)
C_STILL = 0x100                # FRAME_COUNTER when an enemy was last near Ratchet (the AI's idle)
C_BANKS_IN = 0x104             # OWN_BANKS loaded (body.coop_banks; once: the loader relocates them in place)
C_OWN_BANKS = 0x110            # their handles, a word each (0 not loaded, -1 failed)
C_SOUND_DEFS = 0x130           # SOUND_DEFS sound definitions of ours, 0x20 each, filled in turn (body.coop_sound)
C_LIVE = 0x238                 # mobys alive (counted once a second for the trace)
C_TEST = 0x23C                 # not 0: the test input below is Player 2's (tools/coop.py writes it)
C_SEED, C_BOLT_SEED = 0x240, 0x244   # random numbers: now, and the lightning's (new every 2 frames)
C_PUNCH_HIT = 0x248            # the dive punch has hit
C_SWELL = 0x24C                # his scale is T_SCALE * (1 + this) (float)
C_FACE = 0x250                 # cos, sin of his heading
C_AIM = 0x258                  # the way he aims on the ground (2 floats)
C_PUNCH_DIR = 0x260            # 2 floats
C_SOUND_NEXT = 0x268           # the next of SOUND_DEFS to fill (body.coop_sound)
C_AI_ON = 0x26C                # AI Clank on (1) whatever the menu's choice (menu.AI_SAVE), with nobody at the second pad
C_FIST = 0x270                 # vec4
C_BOLT_FROM, C_BOLT_TO, C_BOLT_PREV, C_BOLT_POINT, C_BOLT_Q = 0x280, 0x290, 0x2A0, 0x2B0, 0x2C0   # vec4 each
C_DIR = 0x2D0                  # vec4, a damage's direction
C_FLAG_HELP = 0x2E0            # the pack's help shown this level
C_LAST_STATE = 0x2E4           # Ratchet's state a frame ago (pack gating)
C_JOINT_AT = 0x300             # a joint's place (vec4; coop_joint for the device)
C_FXV = 0x310                  # scratch vec4 of the effects (fx.py)
C_FX_NEXT = 0x320              # the next effect slot to take
C_POUND = 0x324                # frames into the ground pound (0 = none)
C_POUND_WAIT = 0x328           # frames before the next one
C_POUND_HIT = 0x32C            # the frame it struck the ground (0 = not yet)
C_BLOCKED = 0x330              # what stopped his last move (flight.coop_fly_move): BLOCK_* bits
BLOCK_X, BLOCK_Y, BLOCK_DOWN, BLOCK_UP = 1, 2, 4, 8
C_FXW = 0x334                  # (3 words: an effect's second place)
C_RAM_Z = 0x340                # the height the ram dives to
# The mini Giant Clank (mini.py):
C_MINI = 0x360                 # his moby (0 = none)
C_MINI_POS = 0x370             # his place (vec4)
C_MINI_VEL = 0x380             # his velocity (vec4, units/s)
C_MINI_YAW = 0x390             # his heading
C_MINI_AIR = 0x394             # frames in the air (0 on the ground)
C_MINI_MOVE = 0x398            # his move: 0 none, 1 the punch, 2 the missiles, 3 the bomb
C_MINI_T = 0x39C               # frames into it
C_MINI_BOMB_WAIT = 0x3A0       # frames before the next bomb
C_MINI_HOVER = 0x3A4           # frames of hover left in this jump
C_MINI_ANIM = 0x3A8            # his animation (-1 none set)
C_MINI_PUNCHES = 0x3AC         # punches so far (left and right fist by turns)
C_MINI_HIT = 0x3B0             # the punch has hit
C_RAY_FROM = 0x3C0             # a ray's ends (vec4 each)
C_RAY_TO = 0x3D0
C_MINI_WISH = 0x3E0            # the stick's way (2 floats)
C_RIDE = 0x3E8                 # Ratchet rides on his back
C_RIDE_WAIT = 0x3EC            # frames before Ratchet can get on again
C_RATCHET_Z = 0x3F0            # Ratchet's height a frame ago
C_DISMOUNT = 0x3F4             # where Ratchet jumps off from: behind the mini (2 floats)
C_RIDE_SEAT = 0x3B4            # the rider's seat: his back's joint (T_RIDE_JOINT) in the world (3 floats)
C_RIDE_N = 0x400               # mobys in C_RIDE_KEPT
C_RIDE_KEPT = 0x404            # each of Ratchet's mobys hidden this frame: the moby, its draw distance (+0x32), its model (+0x24)
RIDE_KEPT_MAX = 20             # (he has 18: his own, two in each of 7 entries, 3 single)
C_RIDER = 0x4F4                # the rider on his back: Ratchet's model in Quartu's pose (0 = none)
C_TEST_HELD = 0x2E8            # the test input's buttons (PAD's bits), added to the pad's
C_TEST_STICK = 0x2EC           # its stick (2 floats, y up), in place of the pad's
C_BOLT_N = 0x2F4               # bolts in BOLTS this frame (the draw callback draws them)
C_DESC = 0x2F8                 # the draw callback's function descriptor (code, TOC; 0 = not made yet)
# The camera (camera.py):
C_CAM_ON = 0x500               # the camera's place is moved this frame (the game's kept)
C_CAM_KEPT = 0x504             # the game's own place (3 floats)
C_CAM_OFF = 0x510              # the offset, eased (3 floats)
C_CAM_APPLIED = 0x51C          # the x it was put at (to tell whether the game's camera moved it since)
C_CAM_WANT = 0x520             # the offset tried (3 floats)
C_CAM_TRIES = 0x52C            # cuts left
C_CAM_RATE = 0x530             # the easing this frame
C_CAM_P2 = 0x534               # Player 2's place (the address of C_POS or C_MINI_POS)
C_CAM_AT = 0x538               # the moved place tried (3 floats)
C_CAM_P2_MOBY = 0x544          # Player 2's moby (his body or the mini), left out of the ray to him
# The Clank Zapper's preview on the menu (preview.py):
C_PREV = 0x548                 # our Clank in the preview (0 = none)
C_PREV_T = 0x54C               # draws so far (the bolts' randomness: the game is paused)
C_PREV_FRAME = 0x550           # FRAME_COUNTER at the last draw
C_PREV_ITEM = 0x554            # the game's item moby, out of the preview's list while ours is in it
C_PREV_ITEM_UPD = 0x55C        # its update (+0x74), off meanwhile
C_KEPT_LIGHT_MOBY = 0x560      # backpack Clank's antenna light while hidden (body.coop_hide), 0 = none
C_KEPT_LIGHT = 0x564           # its draw distance
C_PREV_KEPT = 0x558            # the slots' bytes are kept in C_PREV_FLAGS
C_PREV_TIP = 0x570             # his antenna's tip (vec4)
C_PREV_END = 0x580             # a bolt's end (vec4)
C_PREV_DESC = 0x590            # his update's function descriptor (code, TOC; 0 = not made yet)
C_PREV_BOLTS = 0x5B8           # draw our Clank's bolts in the menu's render
C_PREV_FLAGS = 0x5A0           # the preview's "not drawn" bytes as the game had them (preview.PREVIEW_SLOTS)
C_SOUND_TRY = 0x5BC            # a sound (body.coop_sound) plus 1, played once at the next frame (tools/coop.py sound)
C_PREV_SEG = 0x660             # a bolt's piece on the screen: where, the step (4 floats)
C_GRID_MISS = 0x670            # the game's moby grid: ids it looked for in a cell and did not find (body.coop_grid_search)
RUNTIME_SIZE = 0x680

MODE_DOCKED, MODE_POP, MODE_FLY, MODE_DOCKING, MODE_MINI = 0, 1, 2, 3, 4
# The HUD's texts (hud.py): the badge's, from id 1.
BADGES = ("P2 CLANK", "P2 DOCKED", "P2 GIANT CLANK")
BADGE_OUT, BADGE_DOCKED, BADGE_MINI = range(1, len(BADGES) + 1)
TEXT_SIZE = 24                 # bytes a text (zero-ended)
DRIVER_NONE, DRIVER_P2, DRIVER_AI = 0, 1, 2

# Tuning, at TUNE (the docs' section 6). (name, kind, value): f float, i int, u unsigned (colours).
TUNE = RUNTIME_SIZE
TUNING = (
    ("T_SCALE", "f", 0.25),            # his moby's scale
    ("T_DT", "f", 1 / 60),
    ("T_FLY_SPEED", "f", 7.0), ("T_FLY_ACCEL", "f", 30.0), ("T_FLY_DECEL", "f", 40.0),
    ("T_BOOST_SPEED", "f", 11.5), ("T_BOOST_FRAMES", "i", 21), ("T_BOOST_WAIT", "i", 36),
    ("T_HOVER", "f", 1.7), ("T_HOVER_MIN", "f", 0.6), ("T_HOVER_MAX", "f", 4.0), ("T_HOVER_RATE", "f", 2.0),
    ("T_SPRING_K", "f", 40.0), ("T_SPRING_C", "f", 12.0), ("T_FLOOR", "f", -0.5),
    # walls (flight.coop_fly_move): the rays start T_COLL_UP over his feet and reach his way T_COLL_R
    # beyond the move, down to his feet, up T_COLL_TOP; T_COLL_ON 0 flies through as before
    ("T_COLL_ON", "i", 1), ("T_COLL_UP", "f", 0.5), ("T_COLL_R", "f", 0.5), ("T_COLL_TOP", "f", 0.6),
    ("T_SLOT_AHEAD", "f", -0.6), ("T_SLOT_LEFT", "f", 1.0), ("T_SLOT_IDLE", "i", 90), ("T_SLOT_GAIN", "f", 4.0),
    ("T_LEASH_SOFT", "f", 7.0), ("T_LEASH_FULL", "f", 10.0), ("T_LEASH_HARD", "f", 14.0), ("T_OFFSCREEN", "i", 120),
    ("T_POP_UP", "f", 1.2), ("T_POP_BACK", "f", 0.8), ("T_POP_FRAMES", "i", 30), ("T_DOCK_FRAMES", "i", 15),
    ("T_DOCK_HOLD", "i", 42), ("T_GONE_FRAMES", "i", 120),
    ("T_ROLL_MAX", "f", 0.35), ("T_PITCH_MAX", "f", 0.25), ("T_TURN", "f", 0.2), ("T_STICK_DEAD", "f", 0.25),
    # the Thruster-Pack's device on him, from his torso joint in his axes, its size, and turned
    # from his turn by roll, pitch, yaw (euler x, y, z): set by the user in game with
    # tools/coop_align.py on 2026-10-26 ("i have set it properly now"), the wings centred on his
    # body where his arms were
    ("T_WINGS_AHEAD", "f", 0.200), ("T_WINGS_LEFT", "f", 0.0), ("T_WINGS_UP", "f", 0.120), ("T_WINGS_SCALE", "f", 0.270),
    ("T_WINGS_ROLL", "f", 0.000), ("T_WINGS_PITCH", "f", 0.100), ("T_WINGS_YAW", "f", 0.150),
    ("T_SEAT_UP", "f", 0.0),           # his feet under backpack Clank's place while docking / popping
    ("T_ENERGY_MAX", "f", 100.0), ("T_REGEN", "f", 12.0), ("T_REGEN_DOCKED", "f", 40.0),
    ("T_COST_ZAP", "f", 30.0), ("T_COST_PUNCH", "f", 16.0), ("T_COST_BOOST", "f", 15.0),
    ("T_ZAP_RANGE", "f", 9.0), ("T_ZAP_KEEP", "f", 11.0), ("T_ZAP_CONE", "f", math.cos(math.radians(35))),
    # damage before LEVEL_POWER: the zap 2.0 * 0.125 = 0.25 a tick; the ram 5 ticks, the pound 4
    # in its ring, each costing more than that many ticks of zap (the user: "the other attacks
    # should do more damage but also drain the gauge a bit more")
    ("T_ZAP_TICK", "i", 6), ("T_ZAP_DAMAGE", "f", 0.125),
    ("T_PUNCH_DASH", "f", 18.0), ("T_PUNCH_FRAMES", "i", 20), ("T_PUNCH_RADIUS", "f", 1.4),
    # the ram dives to the height of the target's body (its place + T_TARGET_UP) and hits what is
    # within T_PUNCH_RADIUS on the ground plane and T_RAM_REACH_Z up or down (the user: "does not
    # hit": in 3D his fist never came within 1.0 of the feet of an enemy 1.7 below him)
    ("T_RAM_REACH_Z", "f", 1.6), ("T_RAM_DIVE", "f", 10.0),
    # with no enemy in the aim's cone the ram takes the nearest within T_RAM_SEEK all round (with
    # the stick at rest his heading is the leash's pull, and the ram went home; about one dash)
    ("T_RAM_SEEK", "f", 6.0),
    ("T_PUNCH_DAMAGE", "f", 1.25), ("T_PUNCH_WAIT", "i", 30),
    ("T_POWER", "f", 1.0),             # all his damage, on top of the planet's LEVEL_POWER
    ("T_AI_ENGAGE", "f", 8.0), ("T_AI_PROTECT", "f", 2.5), ("T_AI_DAMAGE", "f", 1.0),
    ("T_AI_RETREAT", "f", 25.0), ("T_AI_RESUME", "f", 70.0), ("T_AI_IDLE", "i", 300), ("T_AI_CROWD", "i", 3), ("T_AI_ZAP_BURST", "i", 25), ("T_AI_RAM_REACH", "f", 10.0),
    ("T_ZERO", "f", 0.0), ("T_ONE", "f", 1.0), ("T_HALF", "f", 0.5), ("T_TWO", "f", 2.0),
    ("T_PI", "f", math.pi), ("T_TWO_PI", "f", 2 * math.pi), ("T_HALF_PI", "f", math.pi / 2),
    ("T_ATAN_A", "f", -0.0464964749), ("T_ATAN_B", "f", 0.15931422), ("T_ATAN_C", "f", -0.327622764),
    ("T_BLINK_NEAR", "f", 4.0), ("T_SCREEN_COS", "f", 0.5), ("T_SMALL", "f", 0.0001),
    ("T_YAW_OFFSET", "f", 0.0),        # his model faces his heading (seen 2026-10-26: pi turned him to the camera)
    # his model's joints (model +0x1c: 4 = bone 4, his torso; 7 = bone 13, the antenna's tip), as
    # JOINT_POSITION gives them, their way from his place times T_JOINT_SCALE (it leaves out a
    # model's own scale, mods/goldenclank.py); the zap leaves the antenna's tip moved by
    # T_ANTENNA_UP/AHEAD in his rows, the device rides the torso at T_WINGS_*
    ("T_JOINT_SCALE", "f", 1.0), ("T_JOINT_TORSO", "i", 4), ("T_JOINT_ANTENNA", "i", 7),
    ("T_ANTENNA_UP", "f", 0.0), ("T_ANTENNA_AHEAD", "f", 0.0),
    ("T_CHEST_UP", "f", 0.45), ("T_CHEST_AHEAD", "f", 0.15), ("T_TARGET_UP", "f", 0.6),
    ("T_BOLT_JITTER", "f", 0.18), ("T_BOLT_SEGMENTS", "i", 8), ("T_BOLT_PUFFS", "i", 3), ("T_THREE", "f", 3.0),
    # the bolt's sparks (SPARK: colours AABBGGRR, frames, how far it shows; speed: how much of a
    # piece of the bolt each one moves a frame, which draws it out into a streak)
    ("T_BOLT_COLOUR", "i", 0x6FFFE8C0), ("T_BOLT_COLOUR2", "i", 0x2FFF9050), ("T_BOLT_FRAMES", "i", 3),
    ("T_BOLT_FAR", "f", 10000.0), ("T_BOLT_SPEED", "f", 0.35), ("T_BOLT_KIND", "i", 2),
    # the Tesla Claw's ribbon (0x2b7d30, T_BOLT_KIND 2): its main bolt's alphas of the core and the
    # glow colour (0x7b7820 white-grey, 0x7b7824 blue), widths and a third number, as its draw
    # 0x2b8520 passes them; then its second, softer pass (alphas 0 = left out)
    ("T_TESLA_A", "i", 0x80), ("T_TESLA_B", "i", 0x40), ("T_TESLA_W1", "f", 0.05), ("T_TESLA_W2", "f", 0.4),
    ("T_TESLA_W3", "f", 0.9),
    ("T_TESLA2_A", "i", 0x10), ("T_TESLA2_B", "i", 0x20), ("T_TESLA2_W1", "f", 0.1), ("T_TESLA2_W2", "f", 0.3),
    ("T_TESLA2_W3", "f", 0.1),
    ("T_FIZZLE_REACH", "f", 2.0), ("T_FIZZLE_FRAMES", "i", 30),
    ("T_TESLA_DAMAGE", "f", 2.0),      # the Tesla Claw's (0x2b47a0), times T_ZAP_DAMAGE a tick
    ("T_ZAP_FLAGS", "i", 0x210000), ("T_PUNCH_FLAGS", "i", 0x10000),
    ("T_KICK", "f", 0.04), ("T_KICK_FRAMES", "i", 6), ("T_SHAKE", "f", 0.2), ("T_SHAKE_FRAMES", "i", 20),
    ("T_FIST_AHEAD", "f", 0.5), ("T_FIST_UP", "f", 0.4), ("T_SEVEN", "f", 7.0),
    ("T_AI_QUIET", "f", 12.0), ("T_AI_CROWD_RANGE", "f", 3.5),
    ("T_FLY_ANIM", "i", 4), ("T_POP_ANIM", "i", 7), ("T_PUNCH_ANIM", "i", 15), ("T_ZAP_ANIM", "i", 4),
    ("T_ANIM_BLEND", "i", 6),
    ("T_SOUND_JOIN", "i", 1), ("T_SOUND_DOCK", "i", 24), ("T_SOUND_BLINK", "i", 1), ("T_SOUND_OVER", "i", 24),
    ("T_SOUND_POUND", "i", 0x10001), ("T_SOUND_PUNCH", "i", 0x10002), ("T_SOUND_ZAP", "i", 0x10000), ("T_SOUND_ZAP_EVERY", "i", 30),
    ("T_SOUND_VOLUME", "i", 0x600),    # the Tesla Claw's definitions' volume (Ratchet's are 0x200..0x800)
    # his arms and legs gone while he flies (the user: "make his legs and arms disappear"): joint
    # manipulators of scale 0 on these bones of his model (class 0x57, seen live 2026-10-26: the
    # arms are 31/41 (forearms and hands) and 51/55 (the black hoses at his shoulders), all from
    # the chest 5; the legs 63/68 from the hips 2; each takes all below it; -1 = none), linked
    # when his body is made (T_LIMBS_HIDE 1)
    ("T_LIMBS_HIDE", "i", 1), ("T_LIMB_0", "i", 31), ("T_LIMB_1", "i", 41), ("T_LIMB_2", "i", 51), ("T_LIMB_3", "i", 55),
    ("T_LIMB_4", "i", 63), ("T_LIMB_5", "i", 68),
    # the jets' variables +0x20..+0x2c while he flies, and while he boosts (the game's lit jet:
    # 0.0125, 0.2, 0.05, 0.025, as Clank's dash in mods/clank.py writes them)
    ("T_JET_0", "f", 0.0125), ("T_JET_1", "f", 0.2), ("T_JET_2", "f", 0.05), ("T_JET_3", "f", 0.025),
    ("T_JET_BOOST_0", "f", 0.0125), ("T_JET_BOOST_1", "f", 0.2), ("T_JET_BOOST_2", "f", 0.05), ("T_JET_BOOST_3", "f", 0.025),
    # the ram (Square): a barrel roll over the dash, a spearhead of lightning ahead of him (3 bolts
    # from T_RAM_FROM to T_RAM_TIP ahead, the side ones T_RAM_SPREAD aside) and a wake behind
    ("T_RAM_FROM", "f", 0.15), ("T_RAM_TIP", "f", 1.0), ("T_RAM_SPREAD", "f", 0.35), ("T_RAM_WAKE", "f", 1.1),
    ("T_RAM_UP", "f", 0.45), ("T_RAM_ROLLS", "f", 1.0),
    ("T_RAM_BURST", "i", 9), ("T_RAM_BURST_R", "f", 1.9), ("T_RAM_BURST_FRAMES", "i", 22),
    # the ground pound (Triangle): T_POUND_RISE frames up (spinning, swelling), the slam down at
    # T_POUND_SPEED to his ground + T_POUND_FLOOR, then a lightning shockwave ring out to
    # T_POUND_RADIUS hitting all in it (and crates), T_POUND_HOLD frames before he flies on
    ("T_POUND_COST", "f", 30.0), ("T_POUND_WAIT", "i", 45), ("T_POUND_RISE", "i", 10), ("T_POUND_UP", "f", 3.0),
    ("T_POUND_SPEED", "f", 20.0), ("T_POUND_FLOOR", "f", 0.1), ("T_POUND_FALL", "i", 45), ("T_POUND_HOLD", "i", 14),
    ("T_POUND_RADIUS", "f", 4.0), ("T_POUND_REACH_Z", "f", 3.0), ("T_POUND_DAMAGE", "f", 1.0), ("T_POUND_SPIN", "f", 0.6), ("T_POUND_SWELL", "f", 0.15),
    ("T_POUND_SHAKE", "f", 0.15), ("T_POUND_SHAKE_FRAMES", "i", 12), ("T_RING_FRAMES", "i", 14),
    ("T_RING_START", "f", 0.15), ("T_RING_JITTER", "f", 0.12), ("T_RING_UP", "f", 0.15),
    ("T_HIT_BURST", "i", 3), ("T_HIT_BURST_R", "f", 0.5), ("T_SEAT_BURST", "i", 7), ("T_SEAT_BURST_R", "f", 0.9),
    # the HUD (hud.py; screen units of the game's HUD, its colours 0xAABBGGRR, 0x80 opaque): the
    # badge's top left, the bar under its text
    ("T_HUD_X", "i", 30), ("T_HUD_Y", "i", 28), ("T_BAR_BELOW", "i", 17), ("T_BAR_W", "i", 64), ("T_BAR_H", "i", 4),
    ("T_HUD_BLUE", "u", 0x80FFC060), ("T_HUD_GOLD", "u", 0x8020D0FF), ("T_HUD_GREY", "u", 0x80A0A0A0),
    ("T_HUD_BACK", "u", 0x40000000), ("T_HUD_LOW", "u", 0x804060FF),
    # the mini Giant Clank (mini.py; the user: with Golden Clank's mode and Player 2 in, "let the
    # second player control a mini version of giant clank"; walks and jumps, Giant Clank's moves,
    # Ratchet back to normal, half the giant legs' size): Golden Clank's model at T_MINI_SCALE
    # (its legs are 0.25), walking at T_MINI_SPEED (T_MINI_GRIP of the way to the stick's speed a
    # frame), T_MINI_JUMP up against T_MINI_GRAVITY, Cross again in the air: a hover falling at
    # T_MINI_HOVER_FALL for T_MINI_HOVER_FRAMES while held; floor and walls by the game's ray
    # (MINI_RAY); back beside Ratchet past T_MINI_LEASH or T_MINI_DROP below him
    ("T_MINI_SCALE", "f", 0.1625), ("T_MINI_SPEED", "f", 5.5), ("T_MINI_GRIP", "f", 0.2), ("T_MINI_JUMP", "f", 3.439),
    ("T_MINI_GRAVITY", "f", 6.500), ("T_MINI_HOVER_FALL", "f", 1.2), ("T_MINI_HOVER_FRAMES", "i", 0),
    ("T_MINI_PROBE_UP", "f", 1.0), ("T_MINI_PROBE_DOWN", "f", 6.0), ("T_MINI_WALL_UP", "f", 0.5), ("T_MINI_WALL_REACH", "f", 0.5),
    ("T_MINI_LEASH", "f", 16.0), ("T_MINI_DROP", "f", 12.0), ("T_MINI_SIDE", "f", 1.5), ("T_MINI_TURN", "f", 0.25),
    ("T_MINI_WALK_RATE", "f", 0.6), ("T_MINI_YAW_OFFSET", "f", 0.0),
    # his animations (Golden Clank's: idle 0, walk 3, jump 6, missiles 8, punches 9 and 10, bomb 12)
    # and moves from its MOVE_TABLE: frames in all, the action's frame
    ("T_MINI_IDLE_ANIM", "i", 0), ("T_MINI_WALK_ANIM", "i", 3), ("T_MINI_JUMP_ANIM", "i", 4), ("T_MINI_MISSILE_ANIM", "i", 8),
    ("T_MINI_PUNCH_ANIM", "i", 9), ("T_MINI_BOMB_ANIM", "i", 12), ("T_MINI_BLEND", "i", 6),
    ("T_MINI_PUNCH_FRAMES", "i", 45), ("T_MINI_PUNCH_ACTION", "i", 15), ("T_MINI_PUNCH_AHEAD", "f", 0.9),
    ("T_MINI_PUNCH_UP", "f", 0.5), ("T_MINI_PUNCH_RADIUS", "f", 1.1), ("T_MINI_PUNCH_DAMAGE", "f", 2.0),
    ("T_MINI_LUNGE", "f", 4.0), ("T_MINI_LUNGE_FROM", "i", 11), ("T_MINI_LUNGE_TO", "i", 16),
    ("T_MINI_MISSILE_FRAMES", "i", 40), ("T_MINI_MISSILE_ACTION", "i", 10),
    ("T_MINI_BOMB_FRAMES", "i", 72), ("T_MINI_BOMB_ACTION", "i", 45), ("T_MINI_BOMB_WAIT", "i", 600),
    # his gold: Ratchet's light (his moby's +0x38, 00BBGGRR) times these in 256ths (red, green,
    # blue: Golden Clank's GOLD_TINT)
    ("T_MINI_TINT_R", "i", 563), ("T_MINI_TINT_G", "i", 320), ("T_MINI_TINT_B", "i", 38),
    # Ratchet rides on his back (the user: "it would be cool, if ratchet could jump on his back"):
    # coming down within T_MOUNT_R of him and T_MOUNT_ABOVE over him he gets on; then he is kept
    # where the mini Giant Clank stands (his stick at rest, his facing the mini's) and hidden with
    # all he carries; in his place rides Quartu's rider (the user: "reuse the quartu animation/
    # model, make og ratchet disappear"; later "scale ratchet down accordingly"): his model in his
    # animation (mini.RIDER_ANIM_SLOT, Quartu's 129, carried into every level), at his scale times
    # T_MINI_SCALE times T_RIDE_SCALE (1 / Quartu's Giant Clank scale 0.75: Quartu's proportions),
    # T_RIDE_UP above and T_RIDE_AHEAD along its facing from his back's joint T_RIDE_JOINT (5: bones
    # 0..8 and 73; bone 73 rests 8.99 up, 2.18 behind: Quartu's seat), in Giant Clank's model units, times
    # T_MINI_SCALE (read on Quartu at scale 0.75: 6.6 up, 1.6 behind; at Ratchet's full size the pose's
    # own offset floated him, 5.5 by eye then); his Cross jumps off from up there,
    # T_DISMOUNT_BACK behind the mini (straight up he came down inside it), T_RIDE_WAIT frames (longer
    # than the jump: at 40 he landed on the mini and was on again) before he can get on again
    ("T_MOUNT_R", "f", 1.2), ("T_MOUNT_ABOVE", "f", 0.3), ("T_RIDE_UP", "f", -0.19), ("T_RIDE_AHEAD", "f", 0.05), ("T_RIDE_JOINT", "i", 5), ("T_RIDE_JOINT_SCALE", "f", 1.0),
    ("T_RIDE_SCALE", "f", 1.3333),
    ("T_RIDE_WAIT", "i", 90), ("T_DISMOUNT_BACK", "f", 1.2),
    # the camera between the players (camera.py): T_CAM_SHARE of the way toward Player 2 (at most
    # T_CAM_SHIFT_MAX), T_CAM_ZOOM back per unit apart beyond T_CAM_ZOOM_FROM (at most T_CAM_ZOOM_MAX),
    # eased by T_CAM_EASE a frame
    ("T_CAM_ON", "i", 1), ("T_CAM_SHARE", "f", 0.5), ("T_CAM_SHIFT_MAX", "f", 5.0), ("T_CAM_ZOOM", "f", 0.6),
    ("T_CAM_ZOOM_FROM", "f", 3.0), ("T_CAM_ZOOM_MAX", "f", 5.0), ("T_CAM_EASE", "f", 0.06),
    ("T_CAM_EASE_IN", "f", 0.3), ("T_CAM_LOOK_UP", "f", 0.8), ("T_CAM_RAY_FLAGS", "i", 2),
    ("T_CAM_MARGIN", "f", 1.5), ("T_CAM_TINY", "f", 0.01),   # (cut back by a wall: faster; the ray to Ratchet's chest)
    # the Clank Zapper's preview (preview.py): his scale, height over Ratchet's place, turn from
    # Ratchet's facing, animation; T_PREV_ARCS bolts a draw out of his antenna, within T_PREV_ARC_R,
    # with a jitter and segments of their own (the zap's 0.18 scribbles these short ones)
    ("T_PREV_ON", "i", 1), ("T_PREV_SCALE", "f", 0.32), ("T_PREV_UP", "f", -0.2), ("T_PREV_YAW", "f", -0.45),
    ("T_PREV_ANIM", "i", 0), ("T_PREV_ARCS", "i", 3), ("T_PREV_ARC_R", "f", 0.25),
    ("T_PREV_JITTER", "f", 0.05), ("T_PREV_SEGMENTS", "i", 6),
    # the bolts drawn flat over the menu (preview.coop_preview_flat): projected from the menu's camera
    # (T_PREV_CX - T_PREV_FX left / depth, T_PREV_CY - T_PREV_FY up / depth, the HUD's 640 x 448), squares
    # T_PREV_STEP apart: the glow's and the core's half sizes and colours (AABBGGRR), then a mark's;
    # T_PREV_MARK 1 marks his antenna's tip and his feet for lining up
    ("T_PREV_CX", "f", 371.7), ("T_PREV_CY", "f", 134.5), ("T_PREV_FX", "f", 246.0), ("T_PREV_FY", "f", 306.0),
    ("T_PREV_STEP", "f", 1.0),
    ("T_PREV_DOT_H", "f", 1.5), ("T_PREV_DOT_H1", "f", 0.5), ("T_PREV_DOT_H2", "f", 4.0),
    ("T_PREV_DOT_COLOUR", "u", 0x30FFA040), ("T_PREV_DOT_COLOUR1", "u", 0x80FFF0E0), ("T_PREV_DOT_COLOUR2", "u", 0x800000FF),
    ("T_PREV_MARK", "i", 0),
    ("T_PREV_AT", "i", 1),
    ("T_PACK_GATE", "i", 1),           # the pack goes with Clank (the user's choice): no pack moves for Ratchet while Clank is off his back (flight.coop_pack)
)
_at = TUNE
for _name, _kind, _value in TUNING:
    globals()[_name] = _at
    _at += 4
TUNE_END = _at
# Effects: puff sets in the layout PUFFS of mods/goldenclank.py (position, velocity, f1, scatter,
# colours, life, count), behind the tuning values.
PUFFS = ">3f4f2f2I2iI"
PUFF_SIZE = struct.calcsize(PUFFS)
E_ZAP = (TUNE_END + 0xF) & ~0xF
E_END = E_ZAP + PUFF_SIZE
# The mod's own look (the user, 2026-10-26: nothing taken over from Golden Clank): Clank's
# electric blue and white, the colour of his thrusters and of the zap. Colours are AABBGGRR.
EFFECTS = {
    # the bolt's glow when it is drawn with puffs (T_BOLT_KIND 0; an alpha of 0x18 and more is a solid ball)
    E_ZAP: ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 400000.0, 0.005, (0x14FFE0B0, 0x10FFB060), (2, 3), 1),
}
# The bolts drawn this frame: BOLT_MAX of BOLT_POINTS points (vec4) each, then their point counts.
BOLT_MAX, BOLT_POINTS = 24, 12
BOLT_SIZE = BOLT_POINTS * 0x10
BOLTS = (E_END + 0xF) & ~0xF
BOLT_COUNTS = BOLTS + BOLT_MAX * BOLT_SIZE
# His limbs' joint manipulators (0x40 bytes each, 16-aligned; see body.py), and whether they are
# linked into his body's list (+0x64).
LIMBS = 6
MANIPS = (BOLT_COUNTS + BOLT_MAX * 4 + 0xF) & ~0xF
MANIPS_ON = MANIPS + LIMBS * 0x40
# Lightning effects that last (fx.py): FX_COUNT slots of 0x40 bytes: +0 kind (FX_*, 0 = free),
# +4 frames left, +8 frames in all, +0xc a moby it follows, +0x10 place A (vec4),
# +0x20 place B (vec4), +0x30 radius (float), +0x34 a count (bolts).
FX_COUNT = 16
F_KIND, F_LEFT, F_TOTAL, F_MOBY, F_A, F_B, F_RADIUS, F_COUNT = 0x0, 0x4, 0x8, 0xC, 0x10, 0x20, 0x30, 0x34
FX_BURST, FX_RING = 1, 2
FX = (MANIPS_ON + 4 + 0xF) & ~0xF
TEXTS = FX + FX_COUNT * 0x40   # BADGES, TEXT_SIZE bytes each, from id 1
# His moves' sounds (body.coop_sound): any sound of the levels' banks, picked with
# tools/clanksound.py into sounds.json: per move a label, a volume and its index in each level's
# bank (the same sound sits at another index in each, -1 where a level lacks it). The move's
# T_SOUND_* is then SOUND_OURS + its slot here; moves not picked keep the value below in TUNING.
# SOUND_BANK + n plays the level's bank sound n (to try one).
LEVEL_COUNT = 19
SOUND_MOVES = (("zap", "T_SOUND_ZAP"), ("ram", "T_SOUND_PUNCH"), ("pound", "T_SOUND_POUND"),
               ("join", "T_SOUND_JOIN"), ("dock", "T_SOUND_DOCK"), ("blink", "T_SOUND_BLINK"))
SOUND_SLOTS, SOUND_DEFS = 8, 8
SOUND_OURS, SOUND_BANK, SOUND_NONE = 0x10000, 0x20000, 0xFFFF
SOUND_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sounds.json")
with open(SOUND_FILE) as _f:
    PICKED = json.load(_f)
TUNING = [(name, kind, SOUND_OURS + [t for _, t in SOUND_MOVES].index(name)
           if name in [t for m, t in SOUND_MOVES if m in PICKED] else value) for name, kind, value in TUNING]
# A pick some levels lack is played from a bank of its own (the user: "make the sound available
# everywhere"): the bank of the first level that has it, cut down to the samples of the picks taken
# from that level (rc2data.level_sound_bank, embedded by __init__.data), loaded once by
# body.coop_banks. OWN_BANKS: (level, its bank indices) each; the slot's SOUND_SLOT_BANK is 1 + which
# (0: the level's own bank), and its row in SOUND_TABLE that index on every level.
OWN_BANK_MAX = 4


def _own_banks():
    banks = {}
    for move, _ in SOUND_MOVES:
        levels = PICKED.get(move, {}).get("levels", [])
        if levels and -1 in levels and any(i >= 0 for i in levels):
            level = next(lv for lv, i in enumerate(levels) if i >= 0)
            banks.setdefault(level, set()).add(levels[level])
    return [(level, sorted(indices)) for level, indices in sorted(banks.items())]


OWN_BANKS = _own_banks()
assert len(OWN_BANKS) <= OWN_BANK_MAX, "picks from more than OWN_BANK_MAX levels that others lack"
SOUND_TABLE = TEXTS + len(BADGES) * TEXT_SIZE          # u16 [SOUND_SLOTS][LEVEL_COUNT]
SOUND_VOLUMES = (SOUND_TABLE + 2 * SOUND_SLOTS * LEVEL_COUNT + 3) & ~3   # u32 [SOUND_SLOTS]
SOUND_SLOT_BANK = SOUND_VOLUMES + 4 * SOUND_SLOTS        # u32 [SOUND_SLOTS]
# His damage grows with the furthest planet unlocked, the ship's list (the user: "make coop clank
# stronger based on the level he gets way to weak on later level", "based on unlocked level or so,
# that clank can 2-hit the minor enemies ... with the shoker with circle"). MINOR_HEALTH is the
# health of what counts as a minor enemy by then, read from the game (moby +0x78 -> its record,
# +0 the health, a float; 2026-10-30, every level, awake): the zap's tick is half of it (T_TESLA_DAMAGE
# * T_ZAP_DAMAGE = 0.25 times the factor, so factor = 2 * health), so two ticks kill all of that
# health or less and tougher enemies take more. The 1% keeps two ticks from stopping just short.
MINOR_HEALTH = (3, 3, 3, 3, 3, 3, 4, 4, 4, 4,
                5, 5, 5, 5, 6, 6, 6, 6, 6)
POWER_BY_LEVEL = tuple(2.02 * health for health in MINOR_HEALTH)
LEVEL_POWER = SOUND_SLOT_BANK + 4 * SOUND_SLOTS
BLOCK_SIZE = (LEVEL_POWER + 4 * len(POWER_BY_LEVEL) + 0xFF) & ~0xFF


def sound_bank_of(slot):
    """0: the slot's sound is in every level's bank (or none is picked); else 1 + its OWN_BANKS entry."""
    move = SOUND_MOVES[slot][0] if slot < len(SOUND_MOVES) else None
    levels = PICKED[move]["levels"] if move in PICKED else []
    if -1 not in levels or all(i < 0 for i in levels):
        return 0
    level = next(lv for lv, i in enumerate(levels) if i >= 0)
    return 1 + [lv for lv, _ in OWN_BANKS].index(level)


def sound_levels(slot):
    """The slot's bank index per level (SOUND_NONE where it has none; its own bank's on every level)."""
    move = SOUND_MOVES[slot][0] if slot < len(SOUND_MOVES) else None
    levels = PICKED[move]["levels"] if move in PICKED else [-1] * LEVEL_COUNT
    if sound_bank_of(slot):
        return [next(i for i in levels if i >= 0)] * LEVEL_COUNT
    return [SOUND_NONE if index < 0 else index for index in levels]


def sound_volume(slot):
    move = SOUND_MOVES[slot][0] if slot < len(SOUND_MOVES) else None
    return PICKED[move]["volume"] if move in PICKED else 0x600


def block():
    """The block's bytes behind the tag: runtime zeros, the tuning values, the effects."""
    data = bytearray(BLOCK_SIZE)
    for name, kind, value in TUNING:
        struct.pack_into({"f": ">f", "i": ">i", "u": ">I"}[kind], data, globals()[name], value)
    for at, (pos, rise, f1, scatter, colours, life, count) in EFFECTS.items():
        struct.pack_into(PUFFS, data, at, *pos, *rise, 0.0, f1, scatter, *colours, *life, count)
    struct.pack_into(">i", data, C_ANIM, -1)
    for k, text in enumerate(BADGES):
        assert len(text) < TEXT_SIZE
        data[TEXTS + TEXT_SIZE * k:TEXTS + TEXT_SIZE * k + len(text)] = text.encode()
    for slot in range(SOUND_SLOTS):
        struct.pack_into(f">{LEVEL_COUNT}H", data, SOUND_TABLE + 2 * LEVEL_COUNT * slot, *sound_levels(slot))
        struct.pack_into(">I", data, SOUND_VOLUMES + 4 * slot, sound_volume(slot))
        struct.pack_into(">I", data, SOUND_SLOT_BANK + 4 * slot, sound_bank_of(slot))
    struct.pack_into(f">{len(POWER_BY_LEVEL)}f", data, LEVEL_POWER, *POWER_BY_LEVEL)
    return bytes(data)


def fields():
    """Every offset and constant above as a template field."""
    return {name: value for name, value in globals().items() if name.isupper() and isinstance(value, int)}
