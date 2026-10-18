"""What level 2 does for the five weapons without a gold version, and for every level 2 weapon:
double damage (Visibomb Gun, Walloper, Drone Device), the R.Y.N.O.'s three rockets, the
Visibomb's larger blast, the Walloper's reach, lunge and red sparks, and bolts that fly to
Ratchet. (The Drone Device's twelve drones are in experience.py, with its other drone code.)
"""
from ..game import *  # noqa: F401,F403

# Both writers of the damage ring are leaf functions that never save their return address, so
# these two hooks are jumps: each routine stores the damage itself and jumps back.
DAMAGE_HOOK = 0x105C78         # stfs f1, 0x2c(r4) in DEAL_DAMAGE (r3 target, r12 flags)
DAMAGE_HOOK_WORD = 0xD024002C
DAMAGE_BACK = DAMAGE_HOOK + 4
SWEEP_DAMAGE_HOOK = 0x105BD4   # stfs f1, 0x2c(r8) in 0x105ab4 (r3 target, r6 flags)
SWEEP_DAMAGE_HOOK_WORD = 0xD028002C
SWEEP_DAMAGE_BACK = SWEEP_DAMAGE_HOOK + 4
BOOST = 2.0
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

# What a level 2 weapon does that the others do not, whichever kind it is, while it is in his hand:
#   * the bolts of whatever drops some fly to Ratchet at once (the flag BOLT_FLY, at BOLTS_HOOK)
# (Its ammunition coming back by itself was tried and taken out at the user's wish on 2026-10-09: a
# second level is to make the weapon do more, not to refill it. For the record: what an item holds
# is the u16 at 0x737d30 + 24 * item + 0xe.)

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


def damage_part(name, flags, entry, back):
    return DAMAGE.replace("@NAME@", name).replace("@FLAGS@", flags).replace("@ENTRY@", entry).replace("@BACK@", back)


# ryno_fan: replaces bl ROCKET in the R.Y.N.O.'s update.
RYNO_PERK = """
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
"""

WALLOPER_VISIBOMB = """
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
"""

# magnet: replaces bl SPAWN_BOLTS (r6 = flags).
MAGNET = """
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
