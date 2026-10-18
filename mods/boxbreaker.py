"""Box Breaker: the hyper-strike breaks every crate around Ratchet.

The hyper-strike is hero state 0x14. When it lands, hero_update (0xaaec0) sweeps a 0.4 unit
sphere at 0xb01f4 and damages whatever is inside. That call is redirected into a routine that
runs the original sweep and then a crate-only sweep with a large radius, built from the same
calls the game itself uses for its crate-only sweeps.
As in RC2, the strike shakes the screen when the wrench comes down (RC2 0x83d640): RC2's third
camera shake channel, a roll about the view axis that RC1's camera does not have, is ported and
started with RC2's values. Not in RC2: the bolts of crates that break within 35 frames of the
sweep fly to Ratchet at once, through the bolt spawner's own flag for that.
"""
from . import sweep
from .game import *  # noqa: F401,F403

NAME = "boxbreaker"
TITLE = "Box Breaker"
ABOUT = "The hyper-strike (jump, then Square) breaks every crate within 14 units, with RC2's screen shake; the bolts fly to Ratchet."
USES = (sweep,)

# Box Breaker screen shake. RC2's hyper-strike handler tests, behind its sweep (0x83d640), whether
# the animation frame (hero +0xc38, RC1 +0xaa8) has just passed 25.7 (the step it made is at
# +0xc3c, RC1 +0xaac). With the Box Breaker owned it then starts camera shake channel 2: strength
# 0.1 for frames(30), and it zeroes channel 0's length. RC1's handler has no such block;
# STRIKE_FX_HOOK is the first instruction behind RC1's sweep, reached on every frame of the state.
# A channel is {+0 strength, +4 current value, +8 frames left, +0xc frames in all}. Both games
# run channels 0 and 1 (camera struct +0x160, +0x170; they move the camera along its up and view
# axes) from the camera update, RC1 0x53550 / RC2 0xb00910, with RC1 0x528e8 / RC2 0xaff858.
# RC2 has a third one at +0x180 that rolls the camera matrix (RC2 +0x370, RC1 +0x350) about the
# view axis: value = strength * sin(freq * (t - 10)) * (left / all)^3 * min(6 t, 1), used as the
# sine of half the roll angle. RC1 keeps its camera pointer at +0x180, so the ported channel
# lives in STATE; SHAKE_HOOK is the call for channel 1, and the port runs right behind it.
STRIKE_FX_HOOK = 0xB01FC           # lwz r3, 0x198(r25)
STRIKE_FX_HOOK_WORD = 0x80790198
STRIKE_FRAME = 25.7                # (RC2 hero table 0x838f7c +0x19c)
SHAKE_STRENGTH = 0.1               # (+0x1a0)
SHAKE_FRAMES = 30
SHAKE_HOOK = 0x53724               # bl SHAKE_CHANNEL with r3 = camera +0x170, r4 = 1
SHAKE_CHANNEL = 0x528E8            # (r3 channel, r4 index)                               [RC2 0xaff858]
SHAKE_FREQ = 2001.0 * 0.01745329238474369   # rad/s (RC2 global 0x131eaf4 times table 0xaff81c +0x24)
SHAKE_PHASE = 10.5                 # (+0x34) truncated after scaling: starts 10 s into the wave
SHAKE_RAMP = 6.0                   # (+0x2c)
SIN_TERMS = (-0.16666656732559204, 0.008333025500178337, -0.0001980741071747616, 2.601886990305502e-06)
PI = 3.141592502593994
TIME_SCALE = 0x71F410              # 1.0; the games scale frame counts with it             [RC2 0x1328c4c]
FRAMES = 0x5E7E18                  # (r3 frames) -> frames at the current time scale       [RC2 0x11bcd28]
WRAP_ANGLE = 0x502648              # (f1) -> f1 in -pi..pi                                 [RC2 0x10d73d8]
QUAT_TO_MATRIX = 0x501AB0          # (r3 quaternion, r4 out)                               [RC2 0x10d6840]
MATRIX_MULTIPLY = 0x5014D4         # (r3 out, r4 a, r5 b)                                  [RC2 0x10d6264]

# Bolts. A crate that breaks calls CRATE_BREAK_FX (debris, sound) and then 0x3a4da0, which drops
# its contents; bolts come from 0xfd8d0, which works out a flags word and calls SPAWN_BOLTS at
# BOLTS_HOOK. Flag 2 makes 0x242738 hand every new bolt to 0x240f38, the function the bolt update
# uses when a bolt comes into reach: the bolt goes into its fly-to-Ratchet state. The game sets
# the flag itself, e.g. when it is short of mobys. The strike hook stamps the frame of the Box
# Breaker sweep; a crate that breaks within BOX_WINDOW frames of it (RC2 keeps its Box Breaker
# running for frames(35), hero +0x224) is remembered at CRATE_BREAK_HOOKS (r3 = the crate), and
# its bolts get the flag.
CRATE_BREAK_HOOKS = (0x3A6F58, 0x3A7820, 0x3A7FE0)   # all three bl CRATE_BREAK_FX sites
CRATE_BREAK_FX = 0x3A5468
BOX_WINDOW = 35

STRIKE_HOOK = 0xB01F4              # bl COLLECT in the state 0x14 landing code

# Replaces the hyper-strike's bl COLLECT: original sweep, then the Box Breaker sweep.
STRIKE = """
strike:
    stdu 1, -0x70(1)
    mflr 0
    std 0, 0x80(1)
    bl {COLLECT}            # arguments untouched
    lis 3, {HERO_HA}
    addi 3, 3, {HERO_LO}
    addi 3, 3, 0x80
    lis 4, {POOL_HA}
    addi 4, 4, {POOL_LO}
    lfs 1, {P_BOX_RADIUS}(4)
    bl {CRATE_SWEEP}
    lis 3, {FRAME_COUNTER_HA}               # the frame of the sweep, for the bolts
    lwz 3, {FRAME_COUNTER_LO}(3)
    lis 4, {STATE_HA}
    addi 4, 4, {STATE_LO}
    stw 3, 0x30(4)
    ld 0, 0x80(1)
    mtlr 0
    addi 1, 1, 0x70
    blr
"""

# strike_fx: replaces lwz r3, 0x198(r25) behind the hyper-strike's sweep (r25 = hero).
# shake: replaces bl SHAKE_CHANNEL for channel 1 in the camera update, then runs RC2's channel 2.
# crate_break: replaces bl CRATE_BREAK_FX (r3 = the crate).
# bolts: replaces bl SPAWN_BOLTS (r3 = source moby, r6 = flags).
BOX = """
strike_fx:
    lis 11, {POOL_HA}
    addi 11, 11, {POOL_LO}
    lfs 0, 0xaa8(25)                # has the animation just passed the frame of the hit?
    lfs 13, {P_STRIKE_FRAME}(11)
    fcmpu 0, 0, 13
    ble sfx_out
    fsubs 0, 0, 13
    lfs 13, 0xaac(25)
    fcmpu 0, 0, 13
    bgt sfx_out
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lfs 0, {P_SHAKE}(11)
    lis 12, {STATE_HA}
    addi 12, 12, {STATE_LO}
    stfs 0, 0x40(12)
    li 3, {SHAKE_FRAMES}
    bl {FRAMES}
    lis 12, {STATE_HA}
    addi 12, 12, {STATE_LO}
    stw 3, 0x48(12)
    lis 12, {CAMERA_STATE_HA}
    addi 12, 12, {CAMERA_STATE_LO}
    li 3, 0
    stw 3, 0x16c(12)                # RC2 zeroes channel 0's length here
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
sfx_out:
    lwz 3, 0x198(25)                # the displaced instruction
    blr

shake:
    stdu 1, -0x100(1)
    mflr 0
    std 0, 0x110(1)
    std 31, 0xf8(1)
    std 30, 0xf0(1)
    std 29, 0xe8(1)
    stfd 31, 0xe0(1)
    stfd 30, 0xd8(1)
    bl {SHAKE_CHANNEL}              # arguments untouched
    lis 30, {STATE_HA}
    addi 30, 30, {STATE_LO}
    addi 30, 30, 0x40               # r30 = the channel
    lis 29, {CAMERA_STATE_HA}
    addi 29, 29, {CAMERA_STATE_LO}
    lis 31, {POOL_HA}
    addi 31, 31, {POOL_LO}
    lwz 3, 0x180(29)                # camera type 6 cancels a shake
    cmpwi 3, 0
    beq shake_run
    lhz 3, 0x86(3)
    cmpwi 3, 6
    bne shake_run
    li 3, 0
    stw 3, 8(30)
    stw 3, 0xc(30)
    b shake_out
shake_run:
    lwz 3, 8(30)
    cmpwi 3, 0
    bne shake_on
    stw 3, 0xc(30)
    b shake_out
shake_on:
    lwz 4, 0xc(30)                  # frames in all = the most frames left ever seen
    cmpw 4, 3
    bge shake_length
    mr 4, 3
shake_length:
    stw 4, 0xc(30)
    addi 3, 30, 8
    bl {COUNT_DOWN}
    lwz 3, 8(30)
    bl {INT_TO_FLOAT}
    fmr 31, 1
    lwz 3, 0xc(30)
    bl {INT_TO_FLOAT}
    fdivs 31, 31, 1
    fmuls 1, 31, 31
    fmuls 31, 1, 31                 # f31 = (left / all)^3
    lwz 3, 0xc(30)
    lwz 4, 8(30)
    subf 3, 4, 3
    bl {INT_TO_FLOAT}               # frames since the start
    lis 3, {TIME_SCALE_HA}
    lfs 5, {TIME_SCALE_LO}(3)
    lfs 2, {P_SIXTY}(31)
    fmuls 2, 5, 2
    fdivs 1, 1, 2                   # f1 = t, seconds since the start
    lfs 3, {P_SHAKE_PHASE}(31)
    fmuls 3, 5, 3
    fctidz 3, 3
    fcfid 3, 3
    frsp 3, 3
    lfs 6, {P_SHAKE_FREQ}(31)
    fmuls 3, 3, 6
    lfs 2, {P_SHAKE_RAMP}(31)
    fmuls 2, 1, 2
    fmsubs 1, 6, 1, 3               # angle = freq * (t - 10)
    lfs 4, {P_ONE}(31)
    fsub 3, 4, 2
    fsel 30, 3, 2, 4                # f30 = min(6 t, 1)
    bl {WRAP_ANGLE}
    lfs 4, {P_PI}(31)               # sine: fold into -pi/2..pi/2, then the series
    fsubs 2, 4, 1
    fneg 4, 4
    fsubs 3, 4, 1
    fsub 5, 1, 2
    fsel 1, 5, 2, 1
    fsub 2, 3, 1
    fsel 1, 2, 3, 1
    fmuls 3, 1, 1
    fmuls 4, 3, 1
    fmuls 5, 3, 4
    lfs 6, {P_SIN3}(31)
    fmadds 1, 4, 6, 1
    fmuls 4, 3, 5
    lfs 6, {P_SIN5}(31)
    fmadds 1, 5, 6, 1
    fmuls 3, 3, 4
    lfs 6, {P_SIN7}(31)
    fmadds 1, 4, 6, 1
    lfs 6, {P_SIN9}(31)
    fmadds 1, 3, 6, 1
    lfs 2, 0(30)
    fmuls 1, 2, 1
    fmuls 1, 1, 31
    fmuls 1, 1, 30
    stfs 1, 4(30)

    addi 4, 29, 0x350               # quaternion about the view axis (RC2 0xb6fc60): axis * value, sqrt(1 - value^2)
    lfs 2, 0(4)
    lfs 3, 4(4)
    lfs 4, 8(4)
    fmuls 5, 3, 3
    fmadds 5, 2, 2, 5
    fmadds 5, 4, 4, 5
    fsqrts 5, 5
    lfs 6, {P_ZERO}(31)
    fmr 7, 6
    fcmpu 0, 5, 6
    beq shake_axis
    fdivs 7, 1, 5
shake_axis:
    fmuls 2, 2, 7
    fmuls 3, 3, 7
    fmuls 4, 4, 7
    stfs 2, 0x70(1)
    stfs 3, 0x74(1)
    stfs 4, 0x78(1)
    lfs 6, {P_ONE}(31)
    fnmsubs 1, 1, 1, 6
    fsqrts 1, 1
    stfs 1, 0x7c(1)
    addi 3, 1, 0x70
    addi 4, 1, 0x80
    bl {QUAT_TO_MATRIX}
    addi 3, 29, 0x350               # camera matrix = roll * camera matrix
    addi 4, 1, 0x80
    mr 5, 3
    bl {MATRIX_MULTIPLY}
shake_out:
    lfd 30, 0xd8(1)
    lfd 31, 0xe0(1)
    ld 29, 0xe8(1)
    ld 30, 0xf0(1)
    ld 31, 0xf8(1)
    ld 0, 0x110(1)
    mtlr 0
    addi 1, 1, 0x100
    blr

crate_break:
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    li 0, 0
    lwz 12, 0x30(11)                # frame of the last Box Breaker sweep
    cmpwi 12, 0
    beq cb_store
    lis 10, {FRAME_COUNTER_HA}
    lwz 10, {FRAME_COUNTER_LO}(10)
    subf 10, 12, 10
    cmplwi 10, {BOX_WINDOW}
    bgt cb_store
    mr 0, 3
cb_store:
    stw 0, 0x34(11)
    b {CRATE_BREAK_FX}

bolts:
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x34(11)
    cmpwi 12, 0
    beq bolts_run
    cmpw 12, 3
    bne bolts_run
    li 12, 0
    stw 12, 0x34(11)
    ori 6, 6, {BOLT_FLY}
bolts_run:
bolts_next:
    {CHAIN}
"""


def options(ap):
    ap.add_argument("--radius", type=float, default=14.0, help="Box Breaker radius in game units (default 14)")


def hooks(args):
    return [Hook(STRIKE_HOOK, "strike", COLLECT), Hook(STRIKE_FX_HOOK, "strike_fx", STRIKE_FX_HOOK_WORD),
            Hook(SHAKE_HOOK, "shake", SHAKE_CHANNEL), Hook(BOLTS_HOOK, "bolts", SPAWN_BOLTS, chain=True),
            *(Hook(site, "crate_break", CRATE_BREAK_FX) for site in CRATE_BREAK_HOOKS)]


def pool(args):
    return dict(ZERO=0.0, ONE=1.0, BOX_RADIUS=args.radius, STRIKE_FRAME=STRIKE_FRAME, SHAKE=SHAKE_STRENGTH, SIXTY=60.0,
                SHAKE_PHASE=SHAKE_PHASE, SHAKE_FREQ=SHAKE_FREQ, SHAKE_RAMP=SHAKE_RAMP, PI=PI,
                **{f"SIN{power}": term for power, term in zip((3, 5, 7, 9), SIN_TERMS)})


def parts(args):
    return [STRIKE, BOX]
