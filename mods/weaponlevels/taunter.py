"""The Taunter: experience from the enemies it lured, and at level 2 a stun when they arrive."""
from ..game import *  # noqa: F401,F403

# The Taunter (the user's wish, 2026-10-18) kills nothing itself either; it gets what dies of the
# enemies it lured. Its moby (class 0xaf, update 0x2b1300) calls the lure 0x2b06f0(f1 radius,
# r4 its moby) as it whistles: for every moby of the list 0xa49344 with an AI record (moby +0x78
# -> +0, as 0xfcccc reads it) in reach and in front of it, the record's +0x18 becomes the
# Taunter's moby (stored at the two LURE_HOOKS, r27 the enemy). (Before that it breaks the crates
# within 12 units.) Who reads +0x18 differs by enemy, so the mod keeps its own table of the lured
# (state +LURES): a lured enemy that dies within LURE_FRAMES counts for the Taunter.
# Level 2, the user's pick: a lured enemy that comes within STUN_ARRIVE of Ratchet stands stunned
# for STUN_FRAMES. The moby loop (MOBY_LOOP_HOOKS) runs each moby's animation (MOBY_ANIM, unless moby +0x34
# has 0x40) and its update (the descriptor at +0x74); a stunned enemy gets neither, so it stands
# in its pose, with gold puffs above it (DAZE). An enemy only takes its damage in its own update,
# so a hit ends the stun: DEAL_DAMAGE writes the ring entry's index into moby +0xa4. It can be
# stunned again by a lure STUN_COOLDOWN after a stun ends.
TAUNTER = 0x0E
LURE_HOOKS = (0x2B0D64, 0x2B0D70)      # stw r31, 0x18(r26)
LURE_HOOK_WORD = 0x93FA0018
# The moby loop exists three times (0xfc024, 0xfc168, 0xfc238, the last with a second, profiling
# copy); the first build hooked only 0xfc238 and stunned nothing in game. Each pair: bl MOBY_ANIM
# (r3 = the moby) and lwz r3, 0x74(r31) (r31 = the moby) two instructions behind it.
MOBY_LOOP_HOOKS = (0xFC0EC, 0xFC1B4, 0xFC2D8, 0xFC3F4)
MOBY_UPDATE_HOOK_WORD = 0x807F0074
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
