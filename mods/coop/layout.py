"""The mod's block (COOP, writable data behind the tag TAG): its runtime words and, from TUNING,
the values to tune in a running game with tools/peek.py (tools/coop.py names them). Every name
here is a template field of the assembly."""
import math
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
C_MSG, C_MSG_LEFT = 0xBC, 0xC0  # the message shown (MSG_*), frames left
C_WISH = 0xC4                  # the wish velocity (2 floats)
C_STICK = 0xCC                 # the stick or the AI's (2 floats, y up)
C_BUTTONS, C_BUTTONS_NEW = 0xD4, 0xD8   # held / pressed: Player 2's or the AI's
C_SEAT = 0xDC                  # backpack Clank's place (3 floats)
C_TMP = 0xE8                   # scratch (0x18 bytes)
C_RIDE = 0x100                 # frames Ratchet stood still (the AI's idle)
C_COMBO_FLASH = 0x104          # frames of the COMBO text left
C_OVER_TARGETS = 0x108         # a chain reaction's targets: count, then up to 8 mobys
C_LINKS = 0x10C
C_COMBOS = 0x130               # 16 marks {moby, frame wrench, frame zap, frame until}, 0x10 each
COMBO_COUNT = 16
C_LAST_RING = 0x230            # the damage ring's write index a frame ago
C_LOADED = 0x234               # the menu's choice (0 off, 1 AI), as read from the save
C_LIVE = 0x238                 # mobys alive (counted once a second for the trace)
C_TEST = 0x23C                 # not 0: the test input below is Player 2's (tools/coop.py writes it)
C_SEED, C_BOLT_SEED = 0x240, 0x244   # random numbers: now, and the lightning's (new every 2 frames)
C_PUNCH_HIT = 0x248            # the dive punch has hit
C_SWELL = 0x24C                # his scale is T_SCALE * (1 + this) (float)
C_FACE = 0x250                 # cos, sin of his heading
C_AIM = 0x258                  # the way he aims on the ground (2 floats)
C_PUNCH_DIR = 0x260            # 2 floats
C_COMBO_NEXT = 0x268           # the next mark to take
C_AI_ON = 0x26C                # AI Clank chosen (1), with nobody at the second pad
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
C_POUND_POWER = 0x330          # 1 a Thunder Slam (Ratchet in the air beside him)
C_FXW = 0x334                  # (3 words: an effect's second place)
C_RAM_Z = 0x340                # the height the ram dives to
C_LINK = 0x344                 # frames the zap has held Ratchet (the tether)
C_RCHARGE = 0x348              # frames Ratchet stays charged
C_AIR = 0x34C                  # frames Ratchet has been in the air (charged)
C_RATCHET_AT = 0x350           # where the tether reaches him (vec4)
C_TEST_HELD = 0x2E8            # the test input's buttons (PAD's bits), added to the pad's
C_TEST_STICK = 0x2EC           # its stick (2 floats, y up), in place of the pad's
C_BOLT_N = 0x2F4               # bolts in BOLTS this frame (the draw callback draws them)
C_DESC = 0x2F8                 # the draw callback's function descriptor (code, TOC; 0 = not made yet)
RUNTIME_SIZE = 0x380

MODE_DOCKED, MODE_POP, MODE_FLY, MODE_DOCKING = 0, 1, 2, 3
DRIVER_NONE, DRIVER_P2, DRIVER_AI = 0, 1, 2

# Tuning, at TUNE (the docs' section 6). (name, kind, value): f float, i int.
TUNE = 0x380
TUNING = (
    ("T_SCALE", "f", 0.25),            # his moby's scale
    ("T_DT", "f", 1 / 60),
    ("T_FLY_SPEED", "f", 7.0), ("T_FLY_ACCEL", "f", 30.0), ("T_FLY_DECEL", "f", 40.0),
    ("T_BOOST_SPEED", "f", 11.5), ("T_BOOST_FRAMES", "i", 21), ("T_BOOST_WAIT", "i", 36),
    ("T_HOVER", "f", 1.7), ("T_HOVER_MIN", "f", 0.6), ("T_HOVER_MAX", "f", 4.0), ("T_HOVER_RATE", "f", 2.0),
    ("T_SPRING_K", "f", 40.0), ("T_SPRING_C", "f", 12.0), ("T_FLOOR", "f", -0.5),
    ("T_SLOT_AHEAD", "f", -0.6), ("T_SLOT_LEFT", "f", 1.0), ("T_SLOT_IDLE", "i", 90), ("T_SLOT_GAIN", "f", 4.0),
    ("T_LEASH_SOFT", "f", 7.0), ("T_LEASH_FULL", "f", 10.0), ("T_LEASH_HARD", "f", 14.0), ("T_OFFSCREEN", "i", 120),
    ("T_POP_UP", "f", 1.2), ("T_POP_BACK", "f", 0.8), ("T_POP_FRAMES", "i", 30), ("T_DOCK_FRAMES", "i", 15),
    ("T_DOCK_HOLD", "i", 42), ("T_DOCK_REACH", "f", 1.2), ("T_GONE_FRAMES", "i", 120),
    ("T_ROLL_MAX", "f", 0.35), ("T_PITCH_MAX", "f", 0.25), ("T_TURN", "f", 0.2), ("T_STICK_DEAD", "f", 0.25),
    # the Thruster-Pack's device on him, from his torso joint in his axes, its size, and turned
    # from his turn by roll, pitch, yaw (euler x, y, z): set by the user in game with
    # tools/coop_align.py on 2026-10-26 ("i have set it properly now"), the wings centred on his
    # body where his arms were
    ("T_WINGS_AHEAD", "f", 0.200), ("T_WINGS_LEFT", "f", 0.0), ("T_WINGS_UP", "f", 0.120), ("T_WINGS_SCALE", "f", 0.270),
    ("T_WINGS_ROLL", "f", 0.000), ("T_WINGS_PITCH", "f", 0.100), ("T_WINGS_YAW", "f", 0.150),
    ("T_SEAT_UP", "f", 0.0),           # his feet under backpack Clank's place while docking / popping
    ("T_ENERGY_MAX", "f", 100.0), ("T_REGEN", "f", 12.0), ("T_REGEN_DOCKED", "f", 40.0),
    ("T_COST_ZAP", "f", 30.0), ("T_COST_PUNCH", "f", 10.0), ("T_COST_BOOST", "f", 15.0),
    ("T_ZAP_RANGE", "f", 9.0), ("T_ZAP_KEEP", "f", 11.0), ("T_ZAP_CONE", "f", math.cos(math.radians(35))),
    # damage measured against Ratchet's wrench, 1.0 a hit (the damage ring, 2026-10-26; the user:
    # "he one-shots everything" at the Tesla Claw's 2.0 a tick): the zap 2.0 * 0.125 = 0.25 a
    # tick, 2.5 a second; the ram one wrench hit; the pound one in its ring; a chain jump one
    ("T_ZAP_TICK", "i", 6), ("T_ZAP_DAMAGE", "f", 0.125),
    ("T_PUNCH_DASH", "f", 18.0), ("T_PUNCH_FRAMES", "i", 20), ("T_PUNCH_RADIUS", "f", 1.4),
    # the ram dives to the height of the target's body (its place + T_TARGET_UP) and hits what is
    # within T_PUNCH_RADIUS on the ground plane and T_RAM_REACH_Z up or down (the user: "does not
    # hit": in 3D his fist never came within 1.0 of the feet of an enemy 1.7 below him)
    ("T_RAM_REACH_Z", "f", 1.6), ("T_RAM_DIVE", "f", 10.0),
    ("T_PUNCH_DAMAGE", "f", 1.0), ("T_PUNCH_WAIT", "i", 30),
    ("T_COMBO_WINDOW", "i", 60), ("T_COMBO_TIME", "i", 120), ("T_COMBO_FACTOR", "f", 2.0),
    ("T_AI_ENGAGE", "f", 8.0), ("T_AI_PROTECT", "f", 2.5), ("T_AI_DAMAGE", "f", 0.6),
    ("T_AI_RETREAT", "f", 25.0), ("T_AI_RESUME", "f", 70.0), ("T_AI_IDLE", "i", 600), ("T_AI_CROWD", "i", 5),
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
    ("T_AI_QUIET", "f", 15.0), ("T_AI_CROWD_RANGE", "f", 10.0), ("T_AI_STILL", "f", 0.01),
    ("T_FLY_ANIM", "i", 4), ("T_POP_ANIM", "i", 7), ("T_PUNCH_ANIM", "i", 15), ("T_ZAP_ANIM", "i", 4),
    ("T_ANIM_BLEND", "i", 6),
    ("T_SOUND_JOIN", "i", 1), ("T_SOUND_DOCK", "i", 24), ("T_SOUND_BLINK", "i", 1), ("T_SOUND_OVER", "i", 24),
    ("T_SOUND_POUND", "i", -1), ("T_SOUND_PUNCH", "i", -1), ("T_SOUND_ZAP", "i", -1), ("T_SOUND_COMBO", "i", 24), ("T_SOUND_ZAP_EVERY", "i", 30),
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
    ("T_POUND_COST", "f", 20.0), ("T_POUND_WAIT", "i", 45), ("T_POUND_RISE", "i", 10), ("T_POUND_UP", "f", 3.0),
    ("T_POUND_SPEED", "f", 20.0), ("T_POUND_FLOOR", "f", 0.1), ("T_POUND_FALL", "i", 45), ("T_POUND_HOLD", "i", 14),
    ("T_POUND_RADIUS", "f", 4.0), ("T_POUND_REACH_Z", "f", 3.0), ("T_POUND_DAMAGE", "f", 1.0), ("T_POUND_SPIN", "f", 0.6), ("T_POUND_SWELL", "f", 0.15),
    ("T_POUND_SHAKE", "f", 0.15), ("T_POUND_SHAKE_FRAMES", "i", 12), ("T_RING_FRAMES", "i", 14),
    ("T_RING_START", "f", 0.15), ("T_RING_JITTER", "f", 0.12), ("T_RING_UP", "f", 0.15),
    # combos: Thunder Slam (a pound within T_THUNDER_NEAR of Ratchet while he is in the air: the
    # ring T_THUNDER_SCALE wider, the damage twice), Lightning Ram (a ram into a charged enemy:
    # T_OVERLOAD times the damage, a ring and a chain at once), Chain Reaction (a charged enemy that
    # dies: lightning to up to T_CHAIN_TARGETS more, the first within T_CHAIN_FIRST, each next
    # within T_CHAIN_LINK), the cage about a charged enemy
    ("T_THUNDER_NEAR", "f", 3.5), ("T_THUNDER_SCALE", "f", 1.8),
    # the Tesla Tether (the zap aimed at Ratchet, in its cone and reach: a beam between them that
    # hurts what is within T_FENCE_WIDTH of it); held T_CHARGE_FRAMES it charges Ratchet for
    # T_RATCHET_CHARGE frames: his wrench hits T_RCHARGE_BONUS more and arc on to the nearest
    # other enemy within T_ARC_REACH (T_ARC_DAMAGE), and landing after T_LAND_AIR frames in the
    # air bursts into a ring of T_LAND_RADIUS (T_LAND_DAMAGE)
    ("T_RATCHET_UP", "f", 0.8), ("T_FENCE_WIDTH", "f", 0.9), ("T_CHARGE_FRAMES", "i", 45),
    ("T_RATCHET_CHARGE", "i", 360), ("T_RCHARGE_BONUS", "f", 1.0), ("T_ARC_REACH", "f", 6.0), ("T_ARC_DAMAGE", "f", 1.0),
    ("T_LAND_AIR", "i", 20), ("T_LAND_RADIUS", "f", 3.5), ("T_LAND_DAMAGE", "f", 1.0),
    ("T_OVERLOAD", "f", 3.0), ("T_CHAIN_TARGETS", "i", 4), ("T_CHAIN_FIRST", "f", 7.0), ("T_CHAIN_LINK", "f", 6.0),
    ("T_CHAIN_DAMAGE", "f", 0.5), ("T_CHAIN_FRAMES", "i", 18),
    ("T_CAGE_R", "f", 0.55), ("T_CAGE_UP", "f", 0.55), ("T_CAGE_SPIN", "f", 14.0), ("T_CAGE_LOW", "f", -0.35), ("T_CAGE_HIGH", "f", 0.4),
    ("T_COMBO_BURST", "i", 10), ("T_COMBO_BURST_R", "f", 1.7), ("T_COMBO_SHAKE", "f", 0.08),
    ("T_HIT_BURST", "i", 3), ("T_HIT_BURST_R", "f", 0.5), ("T_SEAT_BURST", "i", 7), ("T_SEAT_BURST_R", "f", 0.9),
    ("T_PACK_GATE", "i", 1),           # the pack goes with Clank (the user's choice): Ratchet's pack moves off while P2 has him out
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
# +4 frames left, +8 frames in all, +0xc a moby it follows (the cage), +0x10 place A (vec4),
# +0x20 place B (vec4), +0x30 radius (float), +0x34 a count (bolts).
FX_COUNT = 16
F_KIND, F_LEFT, F_TOTAL, F_MOBY, F_A, F_B, F_RADIUS, F_COUNT = 0x0, 0x4, 0x8, 0xC, 0x10, 0x20, 0x30, 0x34
FX_BURST, FX_RING, FX_ARC, FX_CAGE = 1, 2, 3, 4
FX = (MANIPS_ON + 4 + 0xF) & ~0xF
BLOCK_SIZE = (FX + FX_COUNT * 0x40 + 0xFF) & ~0xFF


def block():
    """The block's bytes behind the tag: runtime zeros, the tuning values, the effects."""
    data = bytearray(BLOCK_SIZE)
    for name, kind, value in TUNING:
        struct.pack_into(">f" if kind == "f" else ">i", data, globals()[name], value)
    for at, (pos, rise, f1, scatter, colours, life, count) in EFFECTS.items():
        struct.pack_into(PUFFS, data, at, *pos, *rise, 0.0, f1, scatter, *colours, *life, count)
    struct.pack_into(">i", data, C_ANIM, -1)
    return bytes(data)


def fields():
    """Every offset and constant above as a template field."""
    return {name: value for name, value in globals().items() if name.isupper() and isinstance(value, int)}
