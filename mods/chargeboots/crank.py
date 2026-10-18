"""The bolt crank boost (not in RC2): the charge's double tap at a bolt crank turns it at the
speed of a charge, with the charge's animation, sound and trails."""
from ..game import *  # noqa: F401,F403

# Bolt crank (moby update 0x32adf8, r30 = its variables, hero state 0x3b). The moby moves Ratchet
# round the bolt: the speed at variables +0x1c follows the stick with +-5.5 units/s^2 (table
# 0x32ad58 +0x54/+0x58) and is capped at 3.7 units/s (+0x5c) by the code at CRANK_HOOK, where
# f0 is the new speed, f13 becomes the cap and f11 is 1/60. Not in RC2: double-tapping and
# holding R1 at the crank raises the cap to CRANK_SPEED and drives the speed up
# to it, with the charge sound.
CRANK_HOOK = 0x32BBAC              # fmuls f13, f11, f20
CRANK_HOOK_WORD = 0xEDAB0532
STATE_CRANK = 0x3B
# The crank picks Ratchet's animation from the speed in the block CRANK_ANIM_HOOK..CRANK_ANIM_DONE
# (r28 = hero): 0x3f standing at the wrench, 0x40 pushing, 0x41 pushing fast, each set with
# hero_set_anim(id, 0, 14 frames). While boosting, that block is skipped and RC2's charge
# animation is kept on him instead; afterwards the pushing animation is put back.
CRANK_ANIM_HOOK = 0x32BC94         # lwz r3, 0x2080(r28)
CRANK_ANIM_HOOK_WORD = 0x807C2080
CRANK_ANIM_DONE = 0x32BDF0
CRANK_PUSH_ANIM, CRANK_ANIM_BLEND = 0x40, 14.0
# After the step along the tangent the crank pulls Ratchet back towards the point of its circle
# (radius 1.05, table +0x74) at his new angle: f26/f27 is the offset to that point, f25 its
# length, and the step taken is a spring's, limited to 7 units/s (+0x7c), loaded at
# CRANK_PULL_HOOK. A boosted step leaves the circle by more than that each frame, so while
# boosting the whole offset is taken.
CRANK_PULL_HOOK = 0x32C0A8         # lfs f1, -0x35c0(r29)
CRANK_PULL_HOOK_WORD = 0xC03DCA40
# Ratchet's yaw is turned towards the tangent (his angle on the circle +-pi/2) by at most
# 2 pi rad/s (table +0x0; f27 = 2 pi, f2 = the step per frame at CRANK_TURN_HOOK). A boosted
# crank goes round at about 30 rad/s, so his yaw fell behind and pointed anywhere, e.g. with
# his feet at the bolt. While boosting, the step may be a full turn.
CRANK_TURN_HOOK = 0x32C15C         # fmuls f2, f2, f27
CRANK_TURN_HOOK_WORD = 0xEC4206F2
CRANK_SPEED = 30.0                 # units/s: the burst speed of a charge
CRANK_ACCEL = 90.0                 # units/s^2


CRANK = """
crank:                              # replaces fmuls f13, f11, f20 (speed cap) in the bolt crank
    fmuls 13, 11, 20                # the displaced instruction
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x28(11)
    cmpwi 12, 0
    beqlr
    lis 11, {POOL_HA}
    addi 11, 11, {POOL_LO}
    lfs 13, {P_CRANK_MAX}(11)       # higher cap, and the speed runs up to it by itself
    lfs 1, {P_CRANK_ACCEL}(11)
    fadds 0, 0, 1
    stfs 0, 0x1c(30)
    blr

crank_pull:                         # replaces lfs f1, -0x35c0(r29): the step back onto the circle
    lfs 1, -0x35c0(29)              # the displaced instruction
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x28(11)
    cmpwi 12, 0
    beqlr
    fmr 1, 25
    blr

crank_turn:                         # replaces fmuls f2, f2, f27: the largest yaw step
    fmuls 2, 2, 27                  # the displaced instruction
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x28(11)
    cmpwi 12, 0
    beqlr
    fmr 2, 27
    blr

crank_anim:                         # replaces lwz r3, 0x2080(r28) in front of the crank's animation choice
    lwz 3, 0x2080(28)               # the displaced instruction
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x28(11)
    lbz 4, 0x53(3)
    lis 11, {POOL_HA}
    addi 11, 11, {POOL_LO}
    cmpwi 12, 0
    bne crank_anim_boost
    cmpwi 4, {ANIM_SLOT}
    bnelr
    li 3, {CRANK_PUSH_ANIM}         # the boost is over: back to pushing
    li 4, 0
    lfs 1, {P_CRANK_BLEND}(11)
    bl {HERO_SET_ANIM}
    b {CRANK_ANIM_DONE}
crank_anim_boost:
    lwz 5, 0x24(3)
    lis 6, {ANIM_HA}
    addi 6, 6, {ANIM_LO}
    stw 6, {ANIM_TABLE_OFF}(5)
    cmpwi 4, {ANIM_SLOT}
    beq crank_anim_done
    li 3, {ANIM_SLOT}
    li 4, 0
    lfs 1, {P_ANIM_BLEND}(11)
    bl {HERO_SET_ANIM}
crank_anim_done:
    b {CRANK_ANIM_DONE}
"""
