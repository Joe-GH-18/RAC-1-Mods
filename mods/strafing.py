"""Strafing: a port of RC2's strafing, with its backwards walk, side flips and ground acceleration.

RC2 keeps a timer at hero +0x1454 that is 1 while L2 or R2 is held (hero_main 0x816aa0) and
tests it in its hero code; RC1's hero code is the older version of the same functions, so each
of those branches is inserted at the matching RC1 instruction:
  * walking (RC2 0x83ee6c, RC1 0xb1630): Ratchet turns to the camera's yaw and moves along the
    stick's heading (RC2 0x82c238), with RC2's damping when left and right are reversed
  * standing: holding the button turns him to the camera (idle -> walk, RC2 0x84bd80), and the
    walk state lasts until he is aligned (RC2 0x84d770); letting the stick go while strafing
    takes him straight to idle at 1.5 units/s at most (RC2 0x84d7f0) instead of RC1's skid
  * moving sideways twists the body through the two joint controllers RC2 uses for it
    (RC2 0x830a5c); moving backwards plays RC2's backwards walk (RC2 0x836018). That is
    Ratchet animation 0x14 in RC2; RC1 has its skid there, so RC2's is embedded
  * jump with the stick held sideways or back: RC1's own flip state 0xb, chosen and aimed by the
    strafe direction as in RC2 (0x835e64, 0x833698, 0x83388c, 0x848810, 0x82f91c)
  * in the air he keeps facing the camera and moves along the stick's heading (RC2 0x83007c,
    0x8429e4)
In RC1, L2 does what L1 does (first-person view) and R2 what R1 does (crouch). While Ratchet is
on foot (states up to 0x15) the two buttons are taken out of the pad's button words every frame,
so they only strafe; in other states (vehicles, the hover with its own L2/R2 strafe) they are
left alone. Strafing is off while RC1's magnetic-surface flag (hero +0x20b3) is set.
Ratchet speeds up and slows down on the ground as in RC2: 18 and 20 units/s^2 instead of RC1's
7.5 and 8.5, with RC2's three rules for speed while he turns in the walk state
(--rc1-acceleration keeps RC1's).
Not ported: RC2's reads of the timer in 0x82e4b0 (speed bookkeeping), 0x817c68 (a counter of
strafing frames), 0x812e28 (resets hero +0x1e8) and 0x819898 (first-person mode sets the timer).
"""
from .rc2 import Extract
from .game import *  # noqa: F401,F403

NAME = "strafing"
TITLE = "Strafing"
ABOUT = "Hold L2 or R2 to strafe as in RC2, with its backwards walk and side flips, and RC2's quicker speeding up and slowing down."

# Strafing (see the docstring). Hook sites in RC1, each with the RC2 address it corresponds to.
STRAFE_LAST_STATE = 0x15           # on foot: idle, walk, skid, crouch, the jump states, the wrench
JOINTS = 0x721BD0                  # joint controllers, 0xb0 bytes each: +0x68 angle, +0xa4/+0xa8 rates [RC2 0x13188a0]
WALK_QUICK_HOOK = 0xB16C4          # lis r27, 0x72: in front of the quick-turn flags      [RC2 0x83ef38]
WALK_QUICK_HOOK_WORD = 0x3F600072
WALK_QUICK_SKIP = 0xB1734
WALK_TURN_HOOK = 0xB1804           # lfs f29, 0x14(r26): in front of the turn             [RC2 0x83f1f0]
WALK_TURN_HOOK_WORD = 0xC3BA0014
WALK_TURN_DONE = 0xB1990
WALK_VEL_HOOK = 0xB1A48            # lhz r3, 0x3b8(r25): in front of the velocity         [RC2 0x83f4c0]
WALK_VEL_HOOK_WORD = 0xA07903B8
WALK_VEL_DONE = 0xB1A7C
IDLE_ALIGN_HOOK = 0xBF464          # lfs f1, 0x30(r25): idle -> walk by the stick         [RC2 0x84bd80]
IDLE_ALIGN_HOOK_WORD = 0xC0390030
IDLE_ALIGN_BACK = 0xBF468
IDLE_TO_WALK = 0xBF47C
WALK_ALIGN_HOOK = 0xC0974          # lfs f1, 0x80(r25): walk -> idle by the stick         [RC2 0x84d770]
WALK_ALIGN_HOOK_WORD = 0xC0390080
WALK_ALIGN_BACK = 0xC0978
WALK_STAYS = 0xC0B50
WALK_TO_IDLE = 0xC0AB8             # the walk block's own way to idle, behind its wait     [RC2 0x84d7e0]
STRAFE_STOP_SPEED = 1.5            # units/s kept when the stick is let go                 (RC2 table 0x84ac7c +0x4c)
FLIP_TYPE_HOOK = 0xA1D9C           # bl STICK_TARGET in the flip type function 0xa1d70    [RC2 0x833698]
FLIP_TYPE_EXIT = 0xA1E3C           # r3 = type
FLIP_TIME_HOOK = 0xA1ECC           # bl STICK_TARGET in 0xa1e78                           [RC2 0x83386c]
FLIP_TIME_TAIL = 0xA1F68           # r31 = type
JUMP_CHOICE_HOOK = 0xA49F0         # cmpwi r31, 0 in the jump chooser 0xa4950             [RC2 0x835e64]
JUMP_CHOICE_HOOK_WORD = 0x2C1F0000
JUMP_CHOICE_FLIP = 0xA49D8         # set_state(0xb, 1), return 1
LEAN_HOOK = 0x9F31C                # lwz r3, 0x2084(r31) at the top of the lean function  [RC2 0x830a5c]
LEAN_HOOK_WORD = 0x807F2084
LEAN_EXIT = 0x9FBA8
WALK_ANIM_HOOK = 0xA4AEC           # lis r4, 0xa in the walk animation chooser 0xa4a60    [RC2 0x836018]
WALK_ANIM_HOOK_WORD = 0x3C80000A
WALK_ANIM_RATE = 0xA4D48
WALK_ANIM_EXIT = 0xA4E08
FLIP_HEADING_HOOK = 0xBB84C        # lfs f1, 0x180(r27) in set_state's flip entry         [RC2 0x8487e0]
FLIP_HEADING_HOOK_WORD = 0xC03B0180
FLIP_SPEED_HOOK = 0xBB888          # stfs f27, 0x458(r27)                                 [RC2 0x848814]
FLIP_SPEED_HOOK_WORD = 0xD37B0458
FLIP_AIR_HOOK = 0x9E5C0            # lhz r4, 0x41e(r31) in the air function 0x9de38       [RC2 0x82f91c]
FLIP_AIR_HOOK_WORD = 0xA09F041E
FLIP_AIR_DONE = 0x9E658
AIR_TURN_HOOK = 0x9EC5C            # lis r3, 0xa: in front of the default air turn        [RC2 0x83007c]
AIR_TURN_HOOK_WORD = 0x3C60000A
AIR_TURNED_HOOK = 0x9ECBC          # stfs f1, 0x188(r31): behind it                       [RC2 0x830120]
AIR_TURNED_HOOK_WORD = 0xD03F0188
JUMP_VEL_HOOK = 0xB465C            # lfs f1, 0x128(r26) in the jump handler               [RC2 0x8429e4]
JUMP_VEL_HOOK_WORD = 0xC03A0128
APPROACH_ANGLE = 0x10A050          # (r3 angle*, f1 target, f2, f3, f4, r5 velocity*, r9 = 0) [RC2 0xb68d98]
ANGLE_GAP = 0x5026A0               # (f1, f2) -> |f1 - f2| wrapped                        [RC2 0x10d7430]
# RC2's numbers. Turn (table 0x82c220): reversal factors -0.25 and (4 - frames) * 0.25 over 5
# frames, approach-angle arguments 0.037, 0.25 and 12.2173 rad/s. Alignment thresholds
# (transition table 0x84ac7c +0x18, +0x48). Body twist rates (0x8308f8). Backwards walk
# (0x835f70): blend 11.5 frames, rate = speed * 25 within 0.7..2.2, 7.5 frames back to the gait
# animation. Flip (0x844784 +0x194, 0x82f2c0 +0x3c/+0x48/+0x4c): starts at 5 units/s, then
# towards max(5 * stick, 2) units/s at 37 units/s^2.
STRAFE_REVERSE = -0.25
STRAFE_REVERSE_FRAMES = 5
STRAFE_TURN = (0.037, 0.25, 12.217304229736328 / 60)
STRAFE_ALIGN_IDLE = 0.1745329201221466
STRAFE_ALIGN_WALK = 0.03490658476948738
STRAFE_TWIST = (0.037, 0.27, 0.025)
STRAFE_TWIST_STICK = 0.15
STRAFE_BACK_BLEND, STRAFE_GAIT_BLEND = 11.0, 7.0
# The backwards walk is Ratchet animation 0x14 in RC2 (30 frames). All other ids up to 133 have
# the frame counts of RC1's, but RC1's 0x14 is the 14-frame skid its walk -> skid transition
# sets (0xc0a54). RC2's is embedded behind the charge animation and gets the next free slot.
RC2_BACK_ANIM = 0x14
BACK_SLOT = 135
# Ground acceleration. The hero table (r26 = 0xaaafc in hero_update) has 7.5 at +0x2a8 and 8.5 at
# +0x298, units/s^2 for speeding up and slowing down; six handlers read the pair (walk at
# 0xb199c). RC2's table has 18 and 20 for the same reads (+0x1fc, +0x200; walk at 0x83f3ac) and
# kept the 8.5 at +0x204 for one more read, a speed threshold (RC2 0x83e888, RC1 0xb0f3c).
HERO_TABLE = 0xAAAFC
GROUND_ACCEL = (0x2A8, 7.5, 18.0)       # offset, RC1, RC2
GROUND_DECEL = (0x298, 8.5, 20.0)
SPEED_THRESHOLD_HOOK = 0xB0F3C     # lfs f1, 0x298(r26)
SPEED_THRESHOLD_HOOK_WORD = 0xC03A0298
# Speed while turning, in the walk handler (RC1 0xb1630, r25 = hero, r26 = table; RC2 0x83ee6c).
# "Turn" is the angle left to the stick's heading (hero +0x188, RC2 +0x1a8), "stick" its
# deflection (+0x229c, RC2 +0x24b8); the quick-turn flag is the u16 at +0x3be (RC2 byte +0x40f).
#   * The factor on the acceleration (f31, 1 by default). RC1 0xb1898: with +0x20a8 set it is
#     1 - 0.55 * turn, otherwise 0 when the stick is under 0.8 and the turn over 30 degrees.
#     RC2 0x83f2d8: 0 when the turn is over 45 degrees, unless the stick is at 0.9 or more and
#     either +0x22ba [RC1 +0x20aa] is clear or the quick-turn flag is set. WALK_FACTOR_HOOK is the
#     first instruction of RC1's block and WALK_FACTOR_DONE the first one behind it.
#   * RC2 0x83f33c, not in RC1: during a quick turn the target speed is at most
#     5.95 - 5.5 * turn / pi units/s. WALK_CAP_HOOK is the instruction behind the lean calls.
#   * RC2 0x83f400, not in RC1: with the stick under 0.75 and the turn over 35 degrees the target
#     speed is multiplied by 1 - 0.4 * turn. WALK_SLOW_HOOK is where the target speed is loaded
#     for the approach.
# The rest of that code is the same in both games (quick turn: target times 2.618 - turn within
# 0.2..1, slowing at 17 units/s^2).
WALK_FACTOR_HOOK = 0xB1898         # lbz r3, 0x20a8(r25)
WALK_FACTOR_HOOK_WORD = 0x887920A8
WALK_FACTOR_DONE = 0xB18F0         # expects f1 = stick
WALK_FACTOR_STICK, WALK_FACTOR_TURN = 0.8999999761581421, 0.7853981852531433
WALK_CAP_HOOK = 0xB1998            # lis r28, 0x72
WALK_CAP_HOOK_WORD = 0x3F800072
WALK_CAP_SPEED, WALK_CAP_PER_TURN = 5.95, 5.5 * 0.31830987334251404    # (RC2 table +0x220, +0x40 times +0x224)
WALK_SLOW_HOOK = 0xB1A08           # lfs f3, 0x190(r25)
WALK_SLOW_HOOK_WORD = 0xC0790190
WALK_SLOW_STICK, WALK_SLOW_TURN, WALK_SLOW_RATE = 0.75, 0.6108652353286743, 0.4   # (0x83f404, 0x83f430, table +0x70)
STRAFE_BACK_RATE = (25.0, 0.7, 2.2)
STRAFE_FLIP_STICK = 0.9            # jump -> flip above this stick deflection             (RC2 0x835e7c)
STRAFE_FLIP_AIM_STICK = 0.3        # the flip follows the strafe heading above this       (RC2 0x848838)
STRAFE_FLIP_SPEED = (5.0 / 60, 2.0 / 60, 37.0 / 3600)

# Strafing: one routine per hook site, named after what RC2 does there.
STRAFE = """
strafe_frame:                       # replaces bl HERO_MAIN
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    bl strafe_tick
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
strafe_frame_next:
    {CHAIN}

strafe_tick:                        # the timer [RC2 0x816ac4], direction and backwards flag [RC2 0x82cf70]
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lis 10, {PAD_HA}
    addi 10, 10, {PAD_LO}
    lis 9, {HERO_HA}
    addi 9, 9, {HERO_LO}
    lwz 3, 0xa0(10)
    lwz 12, 0x2084(9)
    lwz 5, 0x50(11)
    andi. 4, 3, 3                   # L2 | R2
    beq st_release
    cmplwi 12, {STRAFE_LAST_STATE}
    bgt st_release
    lbz 6, 0x20b3(9)
    cmpwi 6, 0
    bne st_release
    li 6, -4                        # on foot the two buttons only strafe: hide them from the game
    and 3, 3, 6
    stw 3, 0xa0(10)
    lwz 7, 0xa4(10)
    and 7, 7, 6
    stw 7, 0xa4(10)
    stw 4, 0x54(11)
    cmpwi 5, 1
    bge st_state
    li 5, 1
    b st_state
st_release:
    li 4, 0
    stw 4, 0x54(11)
    cmpwi 5, 0
    ble st_state
    addi 5, 5, -1
st_state:
    cmpwi 12, 0x10
    bne st_timer
    li 5, 0
st_timer:
    stw 5, 0x50(11)
    li 6, 0
    cmpwi 5, 0
    bne st_dir
    stw 6, 0x5c(11)
    lwz 7, 0x70(11)                 # strafing is over: undo the body twist
    cmpwi 7, 0
    beqlr
    stw 6, 0x70(11)
    lis 10, {JOINTS_HA}
    addi 10, 10, {JOINTS_LO}
    stw 6, 0x68(10)
    stw 6, 0x118(10)
    blr
st_dir:
    lis 10, {POOL_HA}
    addi 10, 10, {POOL_LO}
    lfs 1, 0x1d20(9)                # stick x, y: the angle atan2(y, x) falls into one of four quarters
    lfs 2, 0x1d24(9)
    fabs 3, 1
    fabs 4, 2
    lfs 0, {P_ZERO}(10)
    li 7, 1
    fadds 5, 3, 4
    fcmpu 0, 5, 0
    beq st_dir_done
    li 7, 3
    fcmpu 0, 2, 3
    bgt st_dir_done
    li 7, 1
    fcmpu 0, 1, 4
    bgt st_dir_done
    li 7, 0
    fneg 5, 1
    fcmpu 0, 5, 4
    bgt st_dir_done
    li 7, 2
st_dir_done:
    stw 7, 0x58(11)
    cmpwi 7, 3
    bne st_flag
    lfs 5, 0x229c(9)
    lfs 0, {P_TWIST_STICK}(10)
    fcmpu 0, 5, 0
    ble st_flag
    li 6, 1
st_flag:
    stw 6, 0x5c(11)
    blr

strafe_turn:                        # [RC2 0x82c238] face the camera, keep the stick's heading to move along
    stdu 1, -0x80(1)
    mflr 0
    std 0, 0x90(1)
    std 31, 0x78(1)
    std 30, 0x70(1)
    std 29, 0x68(1)
    stfd 31, 0x60(1)
    lis 31, {HERO_HA}
    addi 31, 31, {HERO_LO}
    lis 30, {STATE_HA}
    addi 30, 30, {STATE_LO}
    lis 29, {POOL_HA}
    addi 29, 29, {POOL_LO}
    lfs 1, 0x1d20(31)               # with the stick let go the heading is his own yaw, while the stick's length
    lfs 2, 0x1d24(31)               # +0x229c takes some frames to fall and keeps him walking: keep the last
    fabs 1, 1                       # heading then, or he runs forwards out of a strafe backwards
    fabs 2, 2
    fadds 1, 1, 2
    lfs 0, {P_ZERO}(29)
    fcmpu 0, 1, 0
    beq turn_heading_kept
    lfs 1, 0x180(31)
    stfs 1, 0x60(30)
turn_heading_kept:
    addi 3, 30, 0x68
    bl {COUNT_DOWN}
    addi 3, 30, 0x6c
    bl {COUNT_DOWN}
    lfs 31, {P_ONE}(29)             # f31 = speed factor
    lbz 4, 0x20a4(31)
    cmpwi 4, 0
    bne turn_speed
    lwz 4, 0x58(30)
    cmpwi 4, 0
    bne turn_right
    li 5, {STRAFE_REVERSE_FRAMES}   # left: within 5 frames of going right the speed is reversed and quartered
    stw 5, 0x6c(30)
    lwz 5, 0x68(30)
    cmpwi 5, 0
    beq turn_speed
    lfs 31, {P_REVERSE}(29)
    b turn_speed
turn_right:
    cmpwi 4, 1
    bne turn_speed
    li 5, {STRAFE_REVERSE_FRAMES}   # right: within 5 frames of going left it ramps up from 0
    lwz 3, 0x6c(30)
    stw 5, 0x68(30)
    cmpwi 3, 0
    beq turn_speed
    bl {INT_TO_FLOAT}
    lfs 2, {P_FOUR}(29)
    fsubs 1, 2, 1
    lfs 2, {P_QUARTER}(29)
    fmuls 31, 1, 2
turn_speed:
    lfs 1, 0x194(31)
    fmuls 1, 1, 31
    stfs 1, 0x194(31)
    lis 4, {CAMERA_STATE_HA}
    addi 4, 4, {CAMERA_STATE_LO}
    lfs 1, 0x158(4)                 # the camera's yaw becomes the heading to turn to
    stfs 1, 0x180(31)
    lfs 2, 0x64(30)
    stfs 2, 0x184(31)
    lfs 2, {P_TURN_A}(29)
    lfs 3, {P_QUARTER}(29)
    lfs 4, {P_TURN_C}(29)
    addi 3, 31, 0x98
    addi 5, 31, 0x184
    li 9, 0
    bl {APPROACH_ANGLE}
    li 3, 0
    stw 3, 0x188(31)
    lfs 1, 0x184(31)
    stfs 1, 0x64(30)
    stw 3, 0x184(31)
    lfd 31, 0x60(1)
    ld 29, 0x68(1)
    ld 30, 0x70(1)
    ld 31, 0x78(1)
    ld 0, 0x90(1)
    mtlr 0
    addi 1, 1, 0x80
    blr

strafe_align:                       # [RC2 0x82c184] (f1 angle) -> 1 while the button is held and he is not yet facing the camera
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 3, 0x54(11)
    cmpwi 3, 0
    beqlr
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    stfs 1, 0x70(1)
    lis 4, {HERO_HA}
    addi 4, 4, {HERO_LO}
    lfs 1, 0x98(4)
    lis 4, {CAMERA_STATE_HA}
    addi 4, 4, {CAMERA_STATE_LO}
    lfs 2, 0x158(4)
    bl {ANGLE_GAP}
    lfs 2, 0x70(1)
    li 3, 0
    fcmpu 0, 2, 1
    bgt align_out
    li 3, 1
align_out:
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

walk_quick:                         # replaces lis r27, 0x72: no quick-turn flags while strafing
    lis 27, 0x72
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x50(11)
    cmpwi 12, 0
    beqlr
    b {WALK_QUICK_SKIP}

walk_turn:                          # replaces lfs f29, 0x14(r26)
    lfs 29, 0x14(26)
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x50(11)
    cmpwi 12, 0
    bne walk_turn_strafe
    lfs 0, 0x98(25)                 # not strafing: the heading to move along is his own
    stfs 0, 0x60(11)
    blr
walk_turn_strafe:
    fmr 31, 29
    bl strafe_turn
    b {WALK_TURN_DONE}

walk_vel:                           # replaces lhz r3, 0x3b8(r25)
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x50(11)
    cmpwi 12, 0
    bne walk_vel_strafe
    lhz 3, 0x3b8(25)
    blr
walk_vel_strafe:
    lfs 1, 0x60(11)
    bl {BUILD_VELOCITY}
    b {WALK_VEL_DONE}

idle_align:                         # replaces lfs f1, 0x30(r25)
    lis 11, {POOL_HA}
    addi 11, 11, {POOL_LO}
    lfs 1, {P_ALIGN_IDLE}(11)
    bl strafe_align
    cmpwi 3, 0
    bne idle_align_walk
    lfs 1, 0x30(25)
    b {IDLE_ALIGN_BACK}
idle_align_walk:
    b {IDLE_TO_WALK}

walk_align:                         # replaces lfs f1, 0x80(r25)
    lis 11, {POOL_HA}
    addi 11, 11, {POOL_LO}
    lfs 1, {P_ALIGN_WALK}(11)
    bl strafe_align
    cmpwi 3, 0
    bne walk_align_stay
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x50(11)
    cmpwi 12, 0
    beq walk_align_plain
    lfs 1, 0x80(25)
    lfs 2, 0x229c(19)
    fcmpu 0, 2, 1
    bge walk_align_plain
    lis 11, {POOL_HA}               # strafing and the stick let go: to idle with the speed capped, as RC2's
    addi 11, 11, {POOL_LO}          # walk does [RC2 0x84d7f0]; RC1's own way is the skid state 3
    lfs 1, {P_STOP_SPEED}(11)
    lfs 2, 0x194(19)
    fcmpu 0, 2, 1
    ble walk_align_coast
    fmr 2, 1
walk_align_coast:                   # RC1's idle carries the speed on along his facing, RC2's along the way he
    lfs 0, {P_ZERO}(11)             # went: keep the part of it that he made forwards (+0x168 of +0x164), so
    lfs 3, 0x164(19)                # that a strafe backwards or sideways ends on the spot
    fcmpu 0, 3, 0
    ble walk_align_still
    fcmpu 0, 2, 0
    ble walk_align_still
    lfs 4, 0x168(19)
    fdivs 4, 4, 3
    fmuls 0, 2, 4
walk_align_still:
    stfs 0, 0x194(19)
    b {WALK_TO_IDLE}
walk_align_plain:
    lfs 1, 0x80(25)
    b {WALK_ALIGN_BACK}
walk_align_stay:
    b {WALK_STAYS}

flip_type:                          # replaces bl STICK_TARGET: the flip's type is the strafe direction
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x50(11)
    cmpwi 12, 0
    bne flip_type_strafe
    b {STICK_TARGET}
flip_type_strafe:
    lwz 3, 0x58(11)
    b {FLIP_TYPE_EXIT}

flip_time:                          # the same in the function that also gives the jump buffer time
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x50(11)
    cmpwi 12, 0
    bne flip_time_strafe
    b {STICK_TARGET}
flip_time_strafe:
    lwz 31, 0x58(11)
    b {FLIP_TIME_TAIL}

jump_choice:                        # replaces cmpwi r31, 0: strafing with the stick pushed anywhere but forward flips
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x50(11)
    cmpwi 12, 0
    beq jump_choice_plain
    lwz 12, 0x58(11)
    cmpwi 12, 2
    beq jump_choice_plain
    lis 11, {HERO_HA}
    addi 11, 11, {HERO_LO}
    lfs 0, 0x229c(11)
    lis 11, {POOL_HA}
    addi 11, 11, {POOL_LO}
    lfs 13, {P_FLIP_STICK}(11)
    fcmpu 0, 0, 13
    ble jump_choice_plain
    b {JUMP_CHOICE_FLIP}
jump_choice_plain:
    cmpwi 31, 0
    blr

lean:                               # replaces lwz r3, 0x2084(r31): the body twist of a sideways strafe
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lis 10, {JOINTS_HA}
    addi 10, 10, {JOINTS_LO}
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    lwz 12, 0x50(11)
    cmpwi 12, 0
    beq lean_off
    lfs 0, 0x229c(31)
    lfs 13, {P_TWIST_STICK}(9)
    fcmpu 0, 0, 13
    ble lean_off
    lwz 12, 0x2084(31)
    cmpwi 12, 0xb
    beq lean_off
    lwz 12, 0x5c(11)
    cmpwi 12, 0
    bne lean_off
    li 12, 1
    stw 12, 0x70(11)
    lfs 0, {P_TWIST_A}(9)
    stfs 0, 0xa4(10)
    lfs 0, {P_TWIST_B}(9)
    stfs 0, 0xa8(10)
    stfs 0, 0x158(10)
    lfs 0, {P_TWIST_C}(9)
    stfs 0, 0x154(10)
    std 30, 0x98(1)                 # the function has not saved r30 yet; its exit restores it
    mr 30, 10
    lfs 1, 0x60(11)
    lfs 2, 0x98(31)
    bl {ANGLE_DIFF}
    stfs 1, 0x68(30)
    fneg 1, 1
    stfs 1, 0x118(30)
    b {LEAN_EXIT}
lean_off:
    lwz 12, 0x70(11)
    cmpwi 12, 0
    beq lean_plain
    li 12, 0
    stw 12, 0x70(11)
    stw 12, 0x68(10)
    stw 12, 0x118(10)
lean_plain:
    lwz 3, 0x2084(31)
    blr

walk_anim:                          # replaces lis r4, 0xa: the backwards walk
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lis 10, {POOL_HA}
    addi 10, 10, {POOL_LO}
    lwz 12, 0x50(11)
    cmpwi 12, 0
    beq walk_anim_off
    lwz 12, 0x5c(11)
    cmpwi 12, 0
    beq walk_anim_off
    li 12, 1
    stw 12, 0x74(11)
    lwz 3, 0x2080(31)
    lwz 4, 0x24(3)                  # RC2's animation in its slot of the model's table
    lis 5, {BACK_ANIM_HA}
    addi 5, 5, {BACK_ANIM_LO}
    stw 5, {BACK_TABLE_OFF}(4)
    lbz 3, 0x53(3)
    cmpwi 3, {BACK_SLOT}
    beq walk_anim_rate
    li 3, {BACK_SLOT}
    li 4, 0
    lfs 1, {P_BACK_BLEND}(10)
    bl {HERO_SET_ANIM}
walk_anim_rate:
    lis 10, {POOL_HA}
    addi 10, 10, {POOL_LO}
    lfs 1, 0x194(31)
    lfs 2, {P_BACK_RATE}(10)
    fmuls 1, 1, 2
    lfs 2, {P_BACK_MIN}(10)
    fcmpu 0, 1, 2
    bge walk_anim_min
    fmr 1, 2
walk_anim_min:
    lfs 2, {P_BACK_MAX}(10)
    fcmpu 0, 1, 2
    ble walk_anim_max
    fmr 1, 2
walk_anim_max:
    stfs 1, 0xa90(31)
    b {WALK_ANIM_EXIT}
walk_anim_off:
    lwz 12, 0x74(11)
    cmpwi 12, 0
    beq walk_anim_plain
    li 12, 0
    stw 12, 0x74(11)
    lwz 3, 0x2088(31)               # back to the animation of the current gait
    addi 3, 3, 3
    li 4, 0
    lfs 1, {P_GAIT_BLEND}(10)
    bl {HERO_SET_ANIM}
    b {WALK_ANIM_RATE}
walk_anim_plain:
    lis 4, 0xa
    blr

flip_heading:                       # replaces lfs f1, 0x180(r27): a strafe flip goes along the strafe heading
    lfs 1, 0x180(27)
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    li 12, 0
    stw 12, 0x78(11)
    lwz 12, 0x50(11)
    cmpwi 12, 0
    beqlr
    lis 12, {POOL_HA}
    addi 12, 12, {POOL_LO}
    lfs 0, 0x229c(27)
    lfs 13, {P_FLIP_AIM}(12)
    fcmpu 0, 0, 13
    blelr
    li 12, 1
    stw 12, 0x78(11)
    lfs 1, 0x60(11)
    blr

flip_speed:                         # replaces stfs f27, 0x458(r27): its starting speed, and no carried momentum
    stfs 27, 0x458(27)
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x78(11)
    cmpwi 12, 0
    beqlr
    lis 12, {POOL_HA}
    addi 12, 12, {POOL_LO}
    lfs 0, {P_FLIP_SPEED}(12)
    stfs 0, 0x458(27)
    stfs 27, 0x454(27)
    blr

flip_air:                           # replaces lhz r4, 0x41e(r31): the speed of a strafe flip follows the stick
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x78(11)
    cmpwi 12, 0
    bne flip_air_strafe
    lhz 4, 0x41e(31)
    blr
flip_air_strafe:
    lis 11, {POOL_HA}
    addi 11, 11, {POOL_LO}
    lfs 1, 0x229c(31)
    lfs 2, {P_FLIP_SPEED}(11)
    fmuls 1, 1, 2
    lfs 2, {P_FLIP_SPEED_MIN}(11)
    fcmpu 0, 1, 2
    bge flip_air_target
    fmr 1, 2
flip_air_target:
    lfs 2, {P_FLIP_ACCEL}(11)
    addi 3, 31, 0x458
    bl {APPROACH}
    lfs 1, 0x164(31)
    stfs 1, 0x194(31)
    b {FLIP_AIR_DONE}

air_turn:                           # replaces lis r3, 0xa: in the air he turns to the camera, the stick gives the heading to move along
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x50(11)
    cmpwi 12, 0
    beq air_turn_plain
    lfs 0, 0x1d20(31)               # as in strafe_turn: no stick, no new heading
    lfs 13, 0x1d24(31)
    fabs 0, 0
    fabs 13, 13
    fadds 0, 0, 13
    lis 12, {POOL_HA}
    addi 12, 12, {POOL_LO}
    lfs 13, {P_ZERO}(12)
    fcmpu 0, 0, 13
    beq air_turn_kept
    lfs 0, 0x180(31)
    stfs 0, 0x60(11)
air_turn_kept:
    lis 11, {CAMERA_STATE_HA}
    addi 11, 11, {CAMERA_STATE_LO}
    lfs 0, 0x158(11)
    stfs 0, 0x180(31)
air_turn_plain:
    lis 3, 0xa
    blr

air_turned:                         # replaces stfs f1, 0x188(r31)
    stfs 1, 0x188(31)
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x50(11)
    cmpwi 12, 0
    beqlr
    lfs 0, 0x60(11)
    stfs 0, 0x180(31)
    blr

speed_threshold:                    # replaces lfs f1, 0x298(r26): this read keeps RC1's 8.5, as RC2's does
    lis 11, {POOL_HA}
    addi 11, 11, {POOL_LO}
    lfs 1, {P_SPEED_THRESHOLD}(11)
    blr

walk_factor:                        # replaces lbz r3, 0x20a8(r25) and the block it starts; f30 = 0, f31 = 1
    lis 11, {POOL_HA}
    addi 11, 11, {POOL_LO}
    lfs 1, 0x229c(25)
    lfs 2, 0x188(25)
    fabs 2, 2
    fabs 0, 1
    lfs 13, {P_FACTOR_STICK}(11)
    fcmpu 0, 0, 13
    blt walk_factor_turn
    lbz 12, 0x20aa(25)
    cmpwi 12, 0
    beq walk_factor_done
    lhz 12, 0x3be(25)
    cmpwi 12, 0
    bne walk_factor_done
walk_factor_turn:
    lfs 13, {P_FACTOR_TURN}(11)
    fcmpu 0, 2, 13
    ble walk_factor_done
    fmr 31, 30
walk_factor_done:
    b {WALK_FACTOR_DONE}

walk_cap:                           # replaces lis r28, 0x72
    lis 28, 0x72                    # the displaced instruction
    lhz 12, 0x3be(25)
    cmpwi 12, 0
    beqlr
    lis 11, {POOL_HA}
    addi 11, 11, {POOL_LO}
    lfs 0, 0x188(25)
    fabs 0, 0
    lfs 13, {P_CAP_PER_TURN}(11)
    fmuls 0, 0, 13
    lfs 13, {P_CAP_SPEED}(11)
    fsubs 0, 13, 0
    lfs 13, {P_ZERO}(11)
    fcmpu 0, 0, 13
    bge walk_cap_set
    fmr 0, 13
walk_cap_set:
    lfs 13, 0x190(25)
    fcmpu 0, 13, 0
    blelr
    stfs 0, 0x190(25)
    blr

walk_slow:                          # replaces lfs f3, 0x190(r25); f1 and f2 hold the steps
    lis 11, {POOL_HA}
    addi 11, 11, {POOL_LO}
    lfs 0, 0x229c(25)
    fabs 0, 0
    lfs 13, {P_SLOW_STICK}(11)
    fcmpu 0, 0, 13
    bge walk_slow_done
    lfs 0, 0x188(25)
    fabs 0, 0
    lfs 13, {P_SLOW_TURN}(11)
    fcmpu 0, 0, 13
    ble walk_slow_done
    lfs 13, {P_SLOW_RATE}(11)
    fmuls 0, 0, 13
    lfs 13, {P_ONE}(11)
    fsubs 0, 13, 0
    lfs 13, {P_ZERO}(11)
    fcmpu 0, 0, 13
    bge walk_slow_set
    fmr 0, 13
walk_slow_set:
    lfs 13, 0x190(25)
    fmuls 0, 13, 0
    stfs 0, 0x190(25)
walk_slow_done:
    lfs 3, 0x190(25)                # the displaced instruction
    blr

jump_vel:                           # replaces lfs f1, 0x128(r26): the velocity goes along the strafe heading
    lfs 1, 0x128(26)
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x50(11)
    cmpwi 12, 0
    beqlr
    lfs 1, 0x60(11)
    blr
"""


def options(ap):
    ap.add_argument("--rc1-acceleration", action="store_true",
                    help="keep RC1's ground acceleration (7.5 and 8.5 units/s^2; RC2: 18 and 20) and its slowing in turns")


def hooks(args):
    hooks = [Hook(site, "strafe_frame", HERO_MAIN, chain=True) for site in FRAME_HOOKS]
    hooks += [
        Hook(WALK_QUICK_HOOK, "walk_quick", WALK_QUICK_HOOK_WORD), Hook(WALK_TURN_HOOK, "walk_turn", WALK_TURN_HOOK_WORD),
        Hook(WALK_VEL_HOOK, "walk_vel", WALK_VEL_HOOK_WORD), Hook(IDLE_ALIGN_HOOK, "idle_align", IDLE_ALIGN_HOOK_WORD),
        Hook(WALK_ALIGN_HOOK, "walk_align", WALK_ALIGN_HOOK_WORD), Hook(FLIP_TYPE_HOOK, "flip_type", STICK_TARGET),
        Hook(FLIP_TIME_HOOK, "flip_time", STICK_TARGET), Hook(JUMP_CHOICE_HOOK, "jump_choice", JUMP_CHOICE_HOOK_WORD),
        Hook(LEAN_HOOK, "lean", LEAN_HOOK_WORD), Hook(WALK_ANIM_HOOK, "walk_anim", WALK_ANIM_HOOK_WORD),
        Hook(FLIP_HEADING_HOOK, "flip_heading", FLIP_HEADING_HOOK_WORD), Hook(FLIP_SPEED_HOOK, "flip_speed", FLIP_SPEED_HOOK_WORD),
        Hook(FLIP_AIR_HOOK, "flip_air", FLIP_AIR_HOOK_WORD), Hook(AIR_TURN_HOOK, "air_turn", AIR_TURN_HOOK_WORD),
        Hook(AIR_TURNED_HOOK, "air_turned", AIR_TURNED_HOOK_WORD), Hook(JUMP_VEL_HOOK, "jump_vel", JUMP_VEL_HOOK_WORD)]
    if not args.rc1_acceleration:
        hooks += [Hook(SPEED_THRESHOLD_HOOK, "speed_threshold", SPEED_THRESHOLD_HOOK_WORD),
                  Hook(WALK_FACTOR_HOOK, "walk_factor", WALK_FACTOR_HOOK_WORD),
                  Hook(WALK_CAP_HOOK, "walk_cap", WALK_CAP_HOOK_WORD), Hook(WALK_SLOW_HOOK, "walk_slow", WALK_SLOW_HOOK_WORD)]
    return hooks


def words(args, addr):
    """RC2's ground acceleration in the hero table."""
    if args.rc1_acceleration:
        return {}
    return {HERO_TABLE + offset: (floats(rc1), floats(rc2)) for offset, rc1, rc2 in (GROUND_ACCEL, GROUND_DECEL)}


def data(args):
    return [("ro", "back_anim", lambda vaddr: [Extract("animation", RC2_BACK_ANIM, vaddr)])]


def pool(args):
    return dict(
        ZERO=0.0, ONE=1.0, REVERSE=STRAFE_REVERSE, FOUR=4.0, QUARTER=0.25, TURN_A=STRAFE_TURN[0], TURN_C=STRAFE_TURN[2],
        ALIGN_IDLE=STRAFE_ALIGN_IDLE, ALIGN_WALK=STRAFE_ALIGN_WALK, STOP_SPEED=STRAFE_STOP_SPEED / 60,
        TWIST_STICK=STRAFE_TWIST_STICK, TWIST_A=STRAFE_TWIST[0], TWIST_B=STRAFE_TWIST[1], TWIST_C=STRAFE_TWIST[2],
        BACK_BLEND=STRAFE_BACK_BLEND, SPEED_THRESHOLD=GROUND_DECEL[1], FACTOR_STICK=WALK_FACTOR_STICK,
        FACTOR_TURN=WALK_FACTOR_TURN, CAP_SPEED=WALK_CAP_SPEED / 60, CAP_PER_TURN=WALK_CAP_PER_TURN / 60,
        SLOW_STICK=WALK_SLOW_STICK, SLOW_TURN=WALK_SLOW_TURN, SLOW_RATE=WALK_SLOW_RATE, GAIT_BLEND=STRAFE_GAIT_BLEND,
        BACK_RATE=STRAFE_BACK_RATE[0], BACK_MIN=STRAFE_BACK_RATE[1], BACK_MAX=STRAFE_BACK_RATE[2],
        FLIP_STICK=STRAFE_FLIP_STICK, FLIP_AIM=STRAFE_FLIP_AIM_STICK, FLIP_SPEED=STRAFE_FLIP_SPEED[0],
        FLIP_SPEED_MIN=STRAFE_FLIP_SPEED[1], FLIP_ACCEL=STRAFE_FLIP_SPEED[2])


def parts(args):
    return [STRAFE]


def fields(args, addr):
    return dict(BACK_TABLE_OFF=0x48 + 4 * BACK_SLOT, **pair("BACK_ANIM", addr["back_anim"]))
