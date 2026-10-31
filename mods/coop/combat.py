"""Clank's fighting: the zap (Circle), the ram (Square) and the ground pound (Triangle).

Targets are found as the Tesla Claw finds its own (its stream 0x2b4818): the moby list at
MOBY_LIST (moby pointers, ended by 0), a moby whose model has +0x46 = 5, whose state byte is
neither 0xfd nor 0xfe and that has an AI record (AI_RECORD: moby +0x78 when +0x34 has 0x20).
The zap locks the nearest within T_ZAP_RANGE of him inside a cone of T_ZAP_CONE (the cosine)
about his aim (the stick's way, or his heading), and keeps it while it is within T_ZAP_KEEP.

Damage goes through DEAL_DAMAGE with his body as the source (so the weapon levels leave it
alone: mods/weaponlevels, CLANK_CARRIER), times T_POWER and the LEVEL_POWER of the furthest planet
unlocked (layout.py). The zap deals the Tesla Claw's damage (2.0 at its first level, from 0x2b47a0,
with its flags 0x210000) times T_ZAP_DAMAGE every T_ZAP_TICK frames.

The lightning is the Tesla Claw's own bolt (TESLA_RIBBON 0x2b7d30, drawn by coop_bolt_draw, a
draw callback of the mod's on his body): from the tip of his antenna (his model's joint 7) to
the target, T_BOLT_SEGMENTS pieces whose joints move by up to T_BOLT_JITTER at random, new every
2 frames. Every other effect is lightning too (fx.py; the user: "dont use the fog animation").

The ram (Square; the user: "the ram should be cooler looking"): T_PUNCH_FRAMES at T_PUNCH_DASH
towards the target, a barrel roll (T_RAM_ROLLS) over it, the jets at their boost, three bolts
ahead of him as a spearhead and one behind as a wake (coop_ram_fx); a hit (T_PUNCH_DAMAGE with
the wrench's flag, crates through the shared crate sweep) bursts into a star of lightning.

The ground pound (Triangle; the user: "let triangle do the thruster pack groundpound, with a
small blue shockwave"): up and round while he swells (T_POUND_RISE frames), the slam down to his
ground, then a ring of lightning out to T_POUND_RADIUS (FX_RING) hitting every enemy in it
(coop_area_hit) and the crates, the camera shaking, and T_POUND_HOLD frames on the ground.

The combos (team moves) were dropped on 2026-10-29 (the user: "they are not really good and
confuse").
"""
from ..game import *  # noqa: F401,F403

MOBY_LIST = 0xA49344           # moby pointers, ended by 0 (the Tesla Claw's and the Taunter's)
AI_RECORD = 0xFCCCC            # (r3 moby) -> its AI record, 0 = none
TARGET_KIND = 5                # model +0x46 of what the Tesla Claw takes
UNLOCKED_PLANETS, UNLOCKED_COUNT = 0x96C18C, 20   # the ship's list of planets, in the order they came, saved (ints, 0 = free)
BUTTON_ZAP, BUTTON_PUNCH, BUTTON_POUND = 0x20, 0x80, 0x10   # Circle zaps, Square rams, Triangle pounds (the user's, 2026-10-26)
SHAKE_CHANNEL = 0x160          # CAMERA_STATE: +0 strength, +8 frames left
TESLA_RIBBON = 0x2B7D30        # (r3 points vec4, r4/r5 alphas of 0x7b7820/0x7b7824, r9 count; f1..f3): the Tesla Claw's bolt, in a draw callback
SPARK = 0x1268F8               # (r3 place vec4, r4 velocity vec4, r5/r6 colours, r7 0, r8 frames, r9 1; f1 how far it shows)

CODE = r"""
coop_enemy:                         # (r3 = a moby) -> r3 = not 0 when it is something to fight
    cmpwi 3, 0
    beqlr
    lwz 9, 0x24(3)
    cmpwi 9, 0
    beq cen_no
    lha 9, 0x46(9)
    cmpwi 9, {TARGET_KIND}
    bne cen_no
    lbz 9, 0x20(3)
    cmpwi 9, 0xfd
    beq cen_no
    cmpwi 9, 0xfe
    beq cen_no
    b {AI_RECORD}
cen_no:
    li 3, 0
    blr

coop_nearest:                       # (r3 = a place, f1 = how far, r4 = 1 in the aim's cone, r5 = mobys to leave out
                                    #  (count, then mobys) or 0; r29) -> r3 = the nearest enemy, 0 = none
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0xc0(1)
    std 31, 0x70(1)
    std 30, 0x78(1)
    std 28, 0x80(1)
    std 27, 0x88(1)
    std 26, 0x90(1)
    std 25, 0x98(1)
    stfd 31, 0xa0(1)
    mr 31, 3
    mr 26, 4
    mr 25, 5
    fmr 31, 1
    li 28, 0
    lis 27, {MOBY_LIST_HA}
    addi 27, 27, {MOBY_LIST_LO} - 4
cn_next:
    lwzu 30, 4(27)
    cmpwi 30, 0
    beq cn_done
    mr 3, 30
    bl coop_enemy
    cmpwi 3, 0
    beq cn_next
    cmpwi 25, 0                     # left out?
    beq cn_far
    lwz 9, 0(25)
    mtctr 9
    cmpwi 9, 0
    beq cn_far
    mr 10, 25
cn_out:
    lwzu 11, 4(10)
    cmpw 11, 30
    beq cn_next
    bdnz cn_out
cn_far:
    lfs 1, 0x10(30)
    lfs 0, 0(31)
    fsubs 1, 1, 0
    lfs 2, 0x14(30)
    lfs 0, 4(31)
    fsubs 2, 2, 0
    lfs 3, 0x18(30)
    lfs 0, 8(31)
    fsubs 3, 3, 0
    fmuls 4, 1, 1
    fmadds 4, 2, 2, 4
    fmuls 5, 3, 3
    fadds 5, 4, 5
    fsqrts 5, 5
    fcmpu 0, 5, 31
    bge cn_next
    cmpwi 26, 0
    beq cn_take
    fsqrts 4, 4                     # in the cone: on the ground plane, against the aim
    lfs 0, {T_SMALL}(29)
    fcmpu 0, 4, 0
    blt cn_take                     # straight above or below: in it
    lfs 0, {C_AIM}(29)
    fmuls 6, 1, 0
    lfs 0, {C_AIM} + 4(29)
    fmadds 6, 2, 0, 6
    lfs 0, {T_ZAP_CONE}(29)
    fmuls 0, 0, 4
    fcmpu 0, 6, 0
    blt cn_next
cn_take:
    fmr 31, 5
    mr 28, 30
    b cn_next
cn_done:
    mr 3, 28
    lfd 31, 0xa0(1)
    ld 25, 0x98(1)
    ld 26, 0x90(1)
    ld 27, 0x88(1)
    ld 28, 0x80(1)
    ld 30, 0x78(1)
    ld 31, 0x70(1)
    addi 1, 1, 0xc0
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_target:                        # (r29) C_TARGET kept while in reach, else the nearest in the cone -> r3
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lwz 3, {C_TARGET}(29)
    bl coop_enemy
    cmpwi 3, 0
    beq ctg_find
    lwz 3, {C_TARGET}(29)
    addi 3, 3, 0x10
    bl coop_distance
    lfs 0, {T_ZAP_KEEP}(29)
    fcmpu 0, 1, 0
    lwz 3, {C_TARGET}(29)
    ble ctg_out
ctg_find:
    addi 3, 29, {C_POS}
    lfs 1, {T_ZAP_RANGE}(29)
    li 4, 1
    li 5, 0
    bl coop_nearest
    stw 3, {C_TARGET}(29)
ctg_out:
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_rand:                          # (r29) -> f1 in -1..1
    lwz 9, {C_SEED}(29)
    lis 10, 0x41c6
    ori 10, 10, 0x4e6d
    mullw 9, 9, 10
    addi 9, 9, 12345
    stw 9, {C_SEED}(29)
    srwi 10, 9, 9                   # 2.0 to 4.0, less 3
    oris 10, 10, 0x4000
    stw 10, {C_TMP} + 0x10(29)
    lfs 1, {C_TMP} + 0x10(29)
    lfs 0, {T_THREE}(29)
    fsubs 1, 1, 0
    blr

coop_antenna:                       # (r3 = out vec4; r29) where his zap leaves him: the tip of his antenna
    lwz 9, {C_BODY}(29)             # (the user: "The Tesla effect should come out of his antenna")
    cmpwi 9, 0
    beq can_none
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    std 3, 0x60(1)
    mr 4, 3
    lwz 3, {T_JOINT_ANTENNA}(29)    # the joint ending at its tip, as it moves with his animation
    bl coop_joint
    ld 3, 0x60(1)
    lwz 9, {C_BODY}(29)
    lfs 1, {T_ANTENNA_AHEAD}(29)    # moved along his rows (forward +0xc0, up +0xe0)
    lfs 2, {T_ANTENNA_UP}(29)
    li 7, 0
can_axis:
    add 8, 9, 7
    lfsx 0, 3, 7
    lfs 4, 0xc0(8)
    fmadds 0, 4, 1, 0
    lfs 4, 0xe0(8)
    fmadds 0, 4, 2, 0
    stfsx 0, 3, 7
    addi 7, 7, 4
    cmpwi 7, 12
    blt can_axis
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr
can_none:
    lfs 4, {T_CHEST_AHEAD}(29)
    lfs 0, {C_POS}(29)
    lfs 5, {C_FACE}(29)
    fmadds 0, 5, 4, 0
    stfs 0, 0(3)
    lfs 0, {C_POS} + 4(29)
    lfs 5, {C_FACE} + 4(29)
    fmadds 0, 5, 4, 0
    stfs 0, 4(3)
    lfs 0, {C_POS} + 8(29)
    lfs 4, {T_CHEST_UP}(29)
    fadds 0, 0, 4
    stfs 0, 8(3)
    blr

coop_aimed:                         # (r3 = a moby, r4 = out vec4; r29) where the zap reaches it
    lfs 0, 0x10(3)
    stfs 0, 0(4)
    lfs 0, 0x14(3)
    stfs 0, 4(4)
    lfs 0, 0x18(3)
    lfs 1, {T_TARGET_UP}(29)
    fadds 0, 0, 1
    stfs 0, 8(4)
    blr

coop_bolt:                          # (r29) lightning from C_BOLT_FROM to C_BOLT_TO
    lwz 9, {T_BOLT_KIND}(29)
    cmpwi 9, 2
    beq coop_bolt_ribbon
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 28, 0x70(1)
    std 27, 0x78(1)
    lwz 9, {C_BOLT_FROM}(29)
    stw 9, {C_BOLT_PREV}(29)
    lwz 9, {C_BOLT_FROM} + 4(29)
    stw 9, {C_BOLT_PREV} + 4(29)
    lwz 9, {C_BOLT_FROM} + 8(29)
    stw 9, {C_BOLT_PREV} + 8(29)
    li 28, 1
cbt_point:
    mr 9, 28
    lwz 10, {T_BOLT_SEGMENTS}(29)
    bl coop_t
    li 7, 0
cbt_axis:
    addi 8, 7, {C_BOLT_FROM}
    lfsx 0, 29, 8
    addi 8, 7, {C_BOLT_TO}
    lfsx 2, 29, 8
    fsubs 2, 2, 0
    fmadds 0, 2, 1, 0
    addi 8, 7, {C_BOLT_POINT}
    stfsx 0, 29, 8
    addi 7, 7, 4
    cmpwi 7, 12
    blt cbt_axis
    lwz 10, {T_BOLT_SEGMENTS}(29)   # the joints between move, the ends stay
    cmpw 28, 10
    bge cbt_line
    li 27, 0
cbt_jitter:
    bl coop_rand
    addi 8, 27, {C_BOLT_POINT}
    lfsx 0, 29, 8
    lfs 2, {T_BOLT_JITTER}(29)
    fmadds 0, 1, 2, 0
    stfsx 0, 29, 8
    addi 27, 27, 4
    cmpwi 27, 12
    blt cbt_jitter
cbt_line:
    li 27, 1                        # puffs along the piece
cbt_puff:
    mr 9, 27
    lwz 10, {T_BOLT_PUFFS}(29)
    bl coop_t
    li 7, 0
cbt_q:
    addi 8, 7, {C_BOLT_PREV}
    lfsx 0, 29, 8
    addi 8, 7, {C_BOLT_POINT}
    lfsx 2, 29, 8
    fsubs 2, 2, 0
    fmadds 0, 2, 1, 0
    addi 8, 7, {C_BOLT_Q}
    stfsx 0, 29, 8
    addi 7, 7, 4
    cmpwi 7, 12
    blt cbt_q
    lwz 9, {T_BOLT_KIND}(29)
    cmpwi 9, 0
    beq cbt_glow
    bl coop_bolt_spark
    b cbt_next
cbt_glow:
    addi 3, 29, {E_ZAP}
    addi 4, 29, {C_BOLT_Q}
    bl coop_puffs
cbt_next:
    addi 27, 27, 1
    lwz 10, {T_BOLT_PUFFS}(29)
    cmpw 27, 10
    ble cbt_puff
    lwz 9, {C_BOLT_POINT}(29)
    stw 9, {C_BOLT_PREV}(29)
    lwz 9, {C_BOLT_POINT} + 4(29)
    stw 9, {C_BOLT_PREV} + 4(29)
    lwz 9, {C_BOLT_POINT} + 8(29)
    stw 9, {C_BOLT_PREV} + 8(29)
    addi 28, 28, 1
    lwz 10, {T_BOLT_SEGMENTS}(29)
    cmpw 28, 10
    ble cbt_point
    ld 27, 0x78(1)
    ld 28, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_bolt_ribbon:                   # (r29) the bolt as points in BOLTS, for coop_bolt_draw
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 28, 0x70(1)
    std 27, 0x78(1)
    std 26, 0x68(1)
    lwz 9, {C_BOLT_N}(29)
    cmpwi 9, {BOLT_MAX}
    bge cbr_out
    addi 10, 9, 1
    stw 10, {C_BOLT_N}(29)
    lwz 10, {T_BOLT_SEGMENTS}(29)   # points: the segments' ends, at most BOLT_POINTS
    cmpwi 10, {BOLT_POINTS} - 1
    ble cbr_count
    li 10, {BOLT_POINTS} - 1
cbr_count:
    mr 26, 10                       # r26 = the segments
    addi 11, 10, 1
    slwi 8, 9, 2
    addi 8, 8, {BOLT_COUNTS}
    stwx 11, 29, 8
    mulli 28, 9, {BOLT_SIZE}
    addi 28, 28, {BOLTS}
    add 28, 28, 29                  # r28 = the bolt's first point
    li 27, 0
cbr_point:
    mr 9, 27
    mr 10, 26
    bl coop_t
    li 7, 0
cbr_axis:
    addi 8, 7, {C_BOLT_FROM}
    lfsx 0, 29, 8
    addi 8, 7, {C_BOLT_TO}
    lfsx 2, 29, 8
    fsubs 2, 2, 0
    fmadds 0, 2, 1, 0
    stfsx 0, 28, 7
    addi 7, 7, 4
    cmpwi 7, 12
    blt cbr_axis
    lfs 0, {T_ONE}(29)
    stfs 0, 12(28)
    cmpwi 27, 0                     # the ends stay, the joints between move
    beq cbr_next
    cmpw 27, 26
    bge cbr_next
    li 7, 0
cbr_jitter:
    std 7, 0x60(1)
    bl coop_rand
    ld 7, 0x60(1)
    lfsx 0, 28, 7
    lfs 2, {T_BOLT_JITTER}(29)
    fmadds 0, 1, 2, 0
    stfsx 0, 28, 7
    addi 7, 7, 4
    cmpwi 7, 12
    blt cbr_jitter
cbr_next:
    addi 28, 28, 0x10
    addi 27, 27, 1
    cmpw 27, 26
    ble cbr_point
cbr_out:
    ld 26, 0x68(1)
    ld 27, 0x78(1)
    ld 28, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_bolt_desc:                     # (r29) C_DESC made: the address of the trampoline behind the bl, and this TOC
    mflr 10
    bl cbd_got
    b coop_bolt_draw
cbd_got:
    mflr 9
    stw 9, {C_DESC}(29)
    stw 2, {C_DESC} + 4(29)
    mtlr 10
    blr

coop_bolt_draw:                     # draw callback (r3 = the moby it was registered with): the bolts in BOLTS
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x90(1)
    std 31, 0x70(1)
    std 30, 0x78(1)
    std 29, 0x80(1)
    lis 29, {COOP_HA}
    addi 29, 29, {COOP_LO}
    li 31, 0
cbw_next:
    lwz 9, {C_BOLT_N}(29)
    cmpw 31, 9
    bge cbw_out
    mulli 30, 31, {BOLT_SIZE}
    addi 30, 30, {BOLTS}
    add 30, 30, 29
    mr 3, 30
    lwz 4, {T_TESLA_A}(29)
    lwz 5, {T_TESLA_B}(29)
    slwi 9, 31, 2
    addi 9, 9, {BOLT_COUNTS}
    lwzx 9, 29, 9
    lfs 1, {T_TESLA_W1}(29)
    lfs 2, {T_TESLA_W2}(29)
    lfs 3, {T_TESLA_W3}(29)
    bl {TESLA_RIBBON}
    lwz 4, {T_TESLA2_A}(29)         # the softer pass
    lwz 5, {T_TESLA2_B}(29)
    or. 9, 4, 5
    beq cbw_skip
    mr 3, 30
    slwi 9, 31, 2
    addi 9, 9, {BOLT_COUNTS}
    lwzx 9, 29, 9
    lfs 1, {T_TESLA2_W1}(29)
    lfs 2, {T_TESLA2_W2}(29)
    lfs 3, {T_TESLA2_W3}(29)
    bl {TESLA_RIBBON}
cbw_skip:
    addi 31, 31, 1
    b cbw_next
cbw_out:
    ld 29, 0x80(1)
    ld 30, 0x78(1)
    ld 31, 0x70(1)
    addi 1, 1, 0x90
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_bolt_show:                     # (r29, at the HUD hook) the bolts' draw callback registered on his body
    lwz 9, {C_BOLT_N}(29)
    cmpwi 9, 0
    beqlr
    lwz 4, {C_BODY}(29)
    cmpwi 4, 0
    beqlr
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lwz 9, {C_DESC}(29)
    cmpwi 9, 0
    bne cbs_have
    bl coop_bolt_desc
cbs_have:
    addi 3, 29, {C_DESC}
    lwz 4, {C_BODY}(29)
    bl {DRAW_REGISTER}
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_bolt_spark:                    # (r29) a spark at C_BOLT_Q moving along the piece C_BOLT_PREV -> C_BOLT_POINT
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lfs 1, {T_BOLT_SPEED}(29)
    li 7, 0
cbs_axis:
    addi 8, 7, {C_BOLT_POINT}
    lfsx 0, 29, 8
    addi 8, 7, {C_BOLT_PREV}
    lfsx 2, 29, 8
    fsubs 0, 0, 2
    fmuls 0, 0, 1
    addi 8, 7, {C_DIR}
    stfsx 0, 29, 8
    addi 7, 7, 4
    cmpwi 7, 12
    blt cbs_axis
    lfs 0, {T_ZERO}(29)
    stfs 0, {C_DIR} + 12(29)
    lfs 0, {T_ONE}(29)
    stfs 0, {C_BOLT_Q} + 12(29)
    addi 3, 29, {C_BOLT_Q}
    addi 4, 29, {C_DIR}
    lwz 5, {T_BOLT_COLOUR}(29)
    lwz 6, {T_BOLT_COLOUR2}(29)
    li 7, 0
    lwz 8, {T_BOLT_FRAMES}(29)
    li 9, 1
    lfs 1, {T_BOLT_FAR}(29)
    bl {SPARK}
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_shake:                         # (f1 = strength, r3 = frames) the camera's shake channel 0
    lis 9, {CAMERA_STATE_HA}
    addi 9, 9, {CAMERA_STATE_LO}
    stfs 1, {SHAKE_CHANNEL}(9)
    stw 3, {SHAKE_CHANNEL} + 8(9)
    blr

coop_hit:                           # (r3 = an enemy, f1 = damage, r4 = flags; r29/r30)
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x90(1)
    std 28, 0x70(1)
    std 27, 0x78(1)
    stfd 31, 0x88(1)
    mr 28, 3
    mr 27, 4
    fmr 31, 1
    bl coop_enemy
    cmpwi 3, 0
    beq chi_out
    lfs 0, {T_POWER}(29)            # stronger with the furthest planet unlocked (LEVEL_POWER)
    fmuls 31, 31, 0
    lis 9, {PLANET_HA}
    lwz 9, {PLANET_LO}(9)
    lis 10, {UNLOCKED_PLANETS_HA}
    addi 10, 10, {UNLOCKED_PLANETS_LO} - 4
    li 11, {UNLOCKED_COUNT}
    mtctr 11
chi_unlocked:
    lwzu 11, 4(10)
    cmplwi 11, {LEVEL_COUNT}
    bge chi_further
    cmplw 11, 9
    ble chi_further
    mr 9, 11
chi_further:
    bdnz chi_unlocked
    cmplwi 9, {LEVEL_COUNT}
    bge chi_ai
    slwi 9, 9, 2
    addi 9, 9, {LEVEL_POWER}
    lfsx 0, 29, 9
    fmuls 31, 31, 0
chi_ai:
    lwz 9, {C_DRIVER}(29)           # AI Clank's share
    cmpwi 9, {DRIVER_AI}
    bne chi_deal
    lfs 0, {T_AI_DAMAGE}(29)
    fmuls 31, 31, 0
chi_deal:
    lfs 1, 0x10(28)                 # its way: from him to it, as long as the game's sweeps make it
    lfs 0, {C_POS}(29)
    fsubs 1, 1, 0
    lfs 2, 0x14(28)
    lfs 0, {C_POS} + 4(29)
    fsubs 2, 2, 0
    fmuls 3, 1, 1
    fmadds 3, 2, 2, 3
    fsqrts 3, 3
    lfs 0, {T_SMALL}(29)
    fcmpu 0, 3, 0
    bgt chi_way
    lfs 0, {T_ONE}(29)
    fmr 3, 0
chi_way:
    lfs 0, {T_SEVEN}(29)
    fdivs 0, 0, 3
    fmuls 1, 1, 0
    fmuls 2, 2, 0
    stfs 1, {C_DIR}(29)
    stfs 2, {C_DIR} + 4(29)
    lfs 0, {T_ZERO}(29)
    stfs 0, {C_DIR} + 8(29)
    stfs 0, {C_DIR} + 12(29)
    mr 3, 28
    lwz 4, {C_BODY}(29)             # the source: his body, or the mini Giant Clank's
    cmpwi 4, 0
    bne chi_source
    lwz 4, {C_MINI}(29)
chi_source:
    mr 5, 27
    fmr 1, 31
    addi 7, 28, 0x10
    addi 8, 29, {C_DIR}
    bl {DEAL_DAMAGE}
chi_out:
    lfd 31, 0x88(1)
    ld 27, 0x78(1)
    ld 28, 0x70(1)
    addi 1, 1, 0x90
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_combat:                        # (r29/r30, flying) aim, then the ground pound, the ram or the zap
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lwz 9, {C_POUND_WAIT}(29)
    cmpwi 9, 0
    ble ccb_aim_now
    addi 9, 9, -1
    stw 9, {C_POUND_WAIT}(29)
ccb_aim_now:
    lwz 9, {C_IDLE}(29)             # the stick at rest: his heading (the wish is then the leash's or the slot's)
    cmpwi 9, 0
    bne ccb_face
    lfs 1, {C_WISH}(29)             # the aim: the wish's way, else his heading
    lfs 2, {C_WISH} + 4(29)
    fmuls 3, 1, 1
    fmadds 3, 2, 2, 3
    fsqrts 3, 3
    lfs 0, {T_SMALL}(29)
    fcmpu 0, 3, 0
    ble ccb_face
    fdivs 1, 1, 3
    fdivs 2, 2, 3
    b ccb_aim
ccb_face:
    lfs 1, {C_FACE}(29)
    lfs 2, {C_FACE} + 4(29)
ccb_aim:
    stfs 1, {C_AIM}(29)
    stfs 2, {C_AIM} + 4(29)
    lwz 9, {C_POUND}(29)
    cmpwi 9, 0
    bne ccb_pound
    bl coop_punch
    lwz 9, {C_PUNCH}(29)
    cmpwi 9, 0
    bne ccb_out
    lwz 9, {C_BUTTONS_NEW}(29)      # Triangle: the ground pound
    andi. 9, 9, {BUTTON_POUND}
    beq ccb_zap
    lwz 9, {C_POUND_WAIT}(29)
    cmpwi 9, 0
    bgt ccb_zap
    lfs 1, {C_ENERGY}(29)
    lfs 2, {T_POUND_COST}(29)
    fcmpu 0, 1, 2
    blt ccb_zap
    fsubs 1, 1, 2
    stfs 1, {C_ENERGY}(29)
    li 9, 0
    stw 9, {C_ZAP}(29)
    stw 9, {C_POUND_HIT}(29)
    lwz 9, {T_POUND_WAIT}(29)
    stw 9, {C_POUND_WAIT}(29)
ccb_pound:
    bl coop_pound
    b ccb_out
ccb_zap:
    bl coop_zap
ccb_out:
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_zap:                           # (r29/r30) Circle held
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 28, 0x70(1)
    lwz 9, {C_BUTTONS}(29)
    andi. 9, 9, {BUTTON_ZAP}
    bne cz_on
    li 9, 0
    stw 9, {C_ZAP}(29)
    stw 9, {C_TARGET}(29)
    b cz_out
cz_on:
    lwz 9, {C_ZAP}(29)
    addi 9, 9, 1
    stw 9, {C_ZAP}(29)
    lwz 3, {T_ZAP_ANIM}(29)
    bl coop_anim
    addi 3, 29, {C_BOLT_FROM}
    bl coop_antenna
    bl coop_target
    mr. 28, 3
    beq cz_fizzle
    lfs 1, {C_ENERGY}(29)           # out of energy: nothing
    lfs 0, {T_ZERO}(29)
    fcmpu 0, 1, 0
    ble cz_out
    lfs 2, {T_COST_ZAP}(29)
    lfs 0, {T_DT}(29)
    fnmsubs 1, 2, 0, 1
    lfs 0, {T_ZERO}(29)
    fcmpu 0, 1, 0
    bge cz_energy
    fmr 1, 0
cz_energy:
    stfs 1, {C_ENERGY}(29)
    mr 3, 28
    addi 4, 29, {C_BOLT_TO}
    bl coop_aimed
    bl coop_bolt
    lwz 9, {C_ZAP}(29)              # the tick, and its sparks
    addi 9, 9, -1
    lwz 10, {T_ZAP_TICK}(29)
    divwu 11, 9, 10
    mullw 11, 11, 10
    cmpw 11, 9
    bne cz_sound
    addi 3, 29, {C_BOLT_TO}         # a crackle where it strikes
    lwz 4, {T_HIT_BURST}(29)
    li 5, 4
    lfs 1, {T_HIT_BURST_R}(29)
    bl coop_burst
    mr 3, 28
    lfs 1, {T_TESLA_DAMAGE}(29)
    lfs 0, {T_ZAP_DAMAGE}(29)
    fmuls 1, 1, 0
    lwz 4, {T_ZAP_FLAGS}(29)
    bl coop_hit
cz_sound:
    lwz 9, {C_ZAP}(29)
    addi 9, 9, -1
    lwz 10, {T_SOUND_ZAP_EVERY}(29)
    divwu 11, 9, 10
    mullw 11, 11, 10
    cmpw 11, 9
    bne cz_out
    lwz 3, {T_SOUND_ZAP}(29)
    bl coop_sound
    b cz_out
cz_fizzle:                          # nothing in reach: a short crackle ahead, for a moment
    lwz 9, {C_ZAP}(29)
    lwz 10, {T_FIZZLE_FRAMES}(29)
    cmpw 9, 10
    bgt cz_out
    lfs 3, {T_FIZZLE_REACH}(29)
    lfs 0, {C_BOLT_FROM}(29)
    lfs 1, {C_AIM}(29)
    fmadds 0, 1, 3, 0
    stfs 0, {C_BOLT_TO}(29)
    lfs 0, {C_BOLT_FROM} + 4(29)
    lfs 1, {C_AIM} + 4(29)
    fmadds 0, 1, 3, 0
    stfs 0, {C_BOLT_TO} + 4(29)
    lwz 9, {C_BOLT_FROM} + 8(29)
    stw 9, {C_BOLT_TO} + 8(29)
    bl coop_bolt
cz_out:
    ld 28, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_punch:                         # (r29/r30) Square: the ram, a dash at the target, rolling, lightning ahead
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 28, 0x70(1)
    lwz 9, {C_PUNCH_WAIT}(29)
    cmpwi 9, 0
    ble cpu_ready
    addi 9, 9, -1
    stw 9, {C_PUNCH_WAIT}(29)
cpu_ready:
    lwz 9, {C_PUNCH}(29)
    cmpwi 9, 0
    bgt cpu_dash
    lwz 9, {C_BUTTONS_NEW}(29)
    andi. 9, 9, {BUTTON_PUNCH}
    beq cpu_out
    lwz 9, {C_PUNCH_WAIT}(29)
    cmpwi 9, 0
    bgt cpu_out
    lfs 1, {C_ENERGY}(29)
    lfs 2, {T_COST_PUNCH}(29)
    fcmpu 0, 1, 2
    blt cpu_out
    fsubs 1, 1, 2
    stfs 1, {C_ENERGY}(29)
    lwz 9, {T_PUNCH_FRAMES}(29)
    stw 9, {C_PUNCH}(29)
    lwz 9, {T_PUNCH_WAIT}(29)
    stw 9, {C_PUNCH_WAIT}(29)
    li 9, 0
    stw 9, {C_PUNCH_HIT}(29)
    stw 9, {C_ZAP}(29)
    stw 9, {C_IDLE}(29)             # (no drifting home right after it)
    lwz 9, {C_POS} + 8(29)          # it keeps his height, or dives to the target's
    stw 9, {C_RAM_Z}(29)
    lwz 9, {C_AIM}(29)              # its way: to the target, else the aim
    stw 9, {C_PUNCH_DIR}(29)
    lwz 9, {C_AIM} + 4(29)
    stw 9, {C_PUNCH_DIR} + 4(29)
    bl coop_target
    cmpwi 3, 0
    bne cpu_at
    addi 3, 29, {C_POS}             # none in the aim (at rest it is his heading, which the leash turns
    lfs 1, {T_RAM_SEEK}(29)         # home): the nearest within T_RAM_SEEK all round
    li 4, 0
    li 5, 0
    bl coop_nearest
    cmpwi 3, 0
    beq cpu_go
cpu_at:
    lfs 0, 0x18(3)
    lfs 1, {T_TARGET_UP}(29)
    fadds 0, 0, 1
    stfs 0, {C_RAM_Z}(29)
    lfs 1, 0x10(3)
    lfs 0, {C_POS}(29)
    fsubs 1, 1, 0
    lfs 2, 0x14(3)
    lfs 0, {C_POS} + 4(29)
    fsubs 2, 2, 0
    fmuls 3, 1, 1
    fmadds 3, 2, 2, 3
    fsqrts 3, 3
    lfs 0, {T_SMALL}(29)
    fcmpu 0, 3, 0
    ble cpu_go
    fdivs 1, 1, 3
    fdivs 2, 2, 3
    stfs 1, {C_PUNCH_DIR}(29)
    stfs 2, {C_PUNCH_DIR} + 4(29)
cpu_go:
    lwz 3, {T_PUNCH_ANIM}(29)
    bl coop_anim
    lwz 3, {T_SOUND_PUNCH}(29)
    bl coop_sound
    lwz 9, {C_PUNCH}(29)
cpu_dash:
    addi 9, 9, -1
    stw 9, {C_PUNCH}(29)
    lfs 0, {T_PUNCH_DASH}(29)
    lfs 1, {C_PUNCH_DIR}(29)
    fmuls 1, 1, 0
    stfs 1, {C_VEL}(29)
    lfs 2, {C_PUNCH_DIR} + 4(29)
    fmuls 2, 2, 0
    stfs 2, {C_VEL} + 4(29)
    lfs 1, {C_RAM_Z}(29)            # diving to the height
    lfs 0, {C_POS} + 8(29)
    fsubs 1, 1, 0
    lfs 0, {T_RAM_DIVE}(29)
    fmuls 1, 1, 0
    stfs 1, {C_VEL} + 8(29)
    lfs 1, {C_PUNCH_DIR} + 4(29)    # facing the way he rams
    lfs 2, {C_PUNCH_DIR}(29)
    bl coop_atan2
    stfs 1, {C_YAW}(29)
    lwz 9, {T_PUNCH_FRAMES}(29)     # a barrel roll over the dash
    lwz 10, {C_PUNCH}(29)
    subf 9, 10, 9
    lwz 10, {T_PUNCH_FRAMES}(29)
    bl coop_t
    lfs 0, {T_TWO_PI}(29)
    fmuls 1, 1, 0
    lfs 0, {T_RAM_ROLLS}(29)
    fmuls 1, 1, 0
    lfs 2, {T_ZERO}(29)
    bl {ANGLE_DIFF}
    stfs 1, {C_ROLL}(29)
    bl coop_ram_fx
    lfs 3, {T_FIST_AHEAD}(29)       # the fist: where he hits
    lfs 0, {C_POS}(29)
    lfs 1, {C_PUNCH_DIR}(29)
    fmadds 0, 1, 3, 0
    stfs 0, {C_FIST}(29)
    lfs 0, {C_POS} + 4(29)
    lfs 1, {C_PUNCH_DIR} + 4(29)
    fmadds 0, 1, 3, 0
    stfs 0, {C_FIST} + 4(29)
    lfs 0, {C_POS} + 8(29)
    lfs 1, {T_FIST_UP}(29)
    fadds 0, 0, 1
    stfs 0, {C_FIST} + 8(29)
    lfs 0, {T_ONE}(29)
    stfs 0, {C_FIST} + 12(29)
    addi 3, 29, {C_FIST}            # crates
    lfs 1, {T_PUNCH_RADIUS}(29)
    bl {CRATE_SWEEP}
    lwz 9, {C_PUNCH_HIT}(29)
    cmpwi 9, 0
    bne cpu_out
    addi 3, 29, {C_FIST}
    lfs 1, {T_PUNCH_RADIUS}(29)
    lfs 2, {T_RAM_REACH_Z}(29)
    bl coop_nearest_flat
    mr. 28, 3
    beq cpu_out
    li 9, 1
    stw 9, {C_PUNCH_HIT}(29)
    mr 3, 28
    lfs 1, {T_PUNCH_DAMAGE}(29)
    lwz 4, {T_PUNCH_FLAGS}(29)
    bl coop_hit
    addi 3, 29, {C_FIST}            # a star of lightning where it struck
    lwz 4, {T_RAM_BURST}(29)
    lwz 5, {T_RAM_BURST_FRAMES}(29)
    lfs 1, {T_RAM_BURST_R}(29)
    bl coop_burst
    lfs 1, {T_KICK}(29)
    lwz 3, {T_KICK_FRAMES}(29)
    bl coop_shake
cpu_out:
    ld 28, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_ram_fx:                        # (r29) the ram's lightning: a spearhead of three bolts ahead, a wake behind
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 28, 0x70(1)
    li 28, -1                       # the side bolts: -1, 0, 1 times T_RAM_SPREAD aside
cr_bolt:
    lfs 1, {C_PUNCH_DIR}(29)
    lfs 2, {C_PUNCH_DIR} + 4(29)
    lfs 3, {T_RAM_FROM}(29)
    lfs 0, {C_POS}(29)
    fmadds 0, 1, 3, 0
    stfs 0, {C_BOLT_FROM}(29)
    lfs 0, {C_POS} + 4(29)
    fmadds 0, 2, 3, 0
    stfs 0, {C_BOLT_FROM} + 4(29)
    lfs 0, {C_POS} + 8(29)
    lfs 4, {T_RAM_UP}(29)
    fadds 0, 0, 4
    stfs 0, {C_BOLT_FROM} + 8(29)
    stfs 0, {C_BOLT_TO} + 8(29)
    lfs 5, {T_RAM_SPREAD}(29)       # aside: (-dy, dx) times -spread, 0 or spread
    cmpwi 28, 0
    bgt cr_side
    lfs 5, {T_ZERO}(29)
    beq cr_side
    lfs 5, {T_RAM_SPREAD}(29)
    fneg 5, 5
cr_side:
    lfs 3, {T_RAM_TIP}(29)
    lfs 0, {C_POS}(29)
    fmadds 0, 1, 3, 0
    fnmsubs 0, 2, 5, 0
    stfs 0, {C_BOLT_TO}(29)
    lfs 0, {C_POS} + 4(29)
    fmadds 0, 2, 3, 0
    fmadds 0, 1, 5, 0
    stfs 0, {C_BOLT_TO} + 4(29)
    bl coop_bolt
    addi 28, 28, 1
    cmpwi 28, 1
    ble cr_bolt
    lfs 1, {C_PUNCH_DIR}(29)        # the wake: from his front back behind him
    lfs 2, {C_PUNCH_DIR} + 4(29)
    lfs 3, {T_RAM_WAKE}(29)
    lfs 0, {C_POS}(29)
    fnmsubs 0, 1, 3, 0
    stfs 0, {C_BOLT_TO}(29)
    lfs 0, {C_POS} + 4(29)
    fnmsubs 0, 2, 3, 0
    stfs 0, {C_BOLT_TO} + 4(29)
    lfs 0, {C_POS} + 8(29)
    lfs 4, {T_RAM_UP}(29)
    fadds 0, 0, 4
    stfs 0, {C_BOLT_TO} + 8(29)
    bl coop_bolt
    ld 28, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_pound:                         # (r29/r30) C_POUND frames in: up and round, the slam, the shockwave, a hold
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 28, 0x70(1)
    lwz 9, {C_POUND}(29)
    addi 9, 9, 1
    stw 9, {C_POUND}(29)
    li 10, 0                        # no way about meanwhile
    stw 10, {C_VEL}(29)
    stw 10, {C_VEL} + 4(29)
    lwz 10, {C_POUND_HIT}(29)
    cmpwi 10, 0
    bne cpd_hold
    lwz 10, {T_POUND_RISE}(29)
    cmpw 9, 10
    bgt cpd_slam
    lfs 0, {T_POUND_UP}(29)         # the wind-up: up, round, swelling
    stfs 0, {C_VEL} + 8(29)
    lwz 10, {T_POUND_RISE}(29)
    bl coop_t
    lfs 0, {T_POUND_SWELL}(29)
    fmuls 1, 1, 0
    stfs 1, {C_SWELL}(29)
    lfs 1, {C_YAW}(29)
    lfs 0, {T_POUND_SPIN}(29)
    fadds 1, 1, 0
    lfs 2, {T_ZERO}(29)
    bl {ANGLE_DIFF}
    stfs 1, {C_YAW}(29)
    b cpd_out
cpd_slam:
    lfs 0, {T_POUND_SPEED}(29)      # down
    fneg 0, 0
    stfs 0, {C_VEL} + 8(29)
    lwz 9, {C_BLOCKED}(29)          # a floor stopped his fall (over his ground: a ledge): it struck there
    andi. 9, 9, {BLOCK_DOWN}
    lfs 0, {C_POS} + 8(29)
    bne cpd_hit
    lfs 0, {C_GROUND}(29)
    lfs 1, {T_POUND_FLOOR}(29)
    fadds 0, 0, 1
    lfs 1, {C_POS} + 8(29)
    lfs 2, {T_POUND_SPEED}(29)      # (where this frame's fall takes him)
    lfs 3, {T_DT}(29)
    fnmsubs 1, 2, 3, 1
    fcmpu 0, 1, 0
    ble cpd_hit
    lwz 9, {C_POUND}(29)            # never falling for ever
    lwz 10, {T_POUND_RISE}(29)
    lwz 11, {T_POUND_FALL}(29)
    add 10, 10, 11
    cmpw 9, 10
    blt cpd_out
cpd_hit:
    stfs 0, {C_POS} + 8(29)         # on the ground: the shockwave
    lfs 0, {T_ZERO}(29)
    stfs 0, {C_VEL} + 8(29)
    stfs 0, {C_SWELL}(29)
    lwz 9, {C_POUND}(29)
    stw 9, {C_POUND_HIT}(29)
    bl coop_pound_hit
    b cpd_out
cpd_hold:
    lfs 0, {T_ZERO}(29)
    stfs 0, {C_VEL} + 8(29)
    lwz 10, {T_POUND_HOLD}(29)
    lwz 11, {C_POUND_HIT}(29)
    add 10, 10, 11
    cmpw 9, 10
    blt cpd_out
    li 9, 0
    stw 9, {C_POUND}(29)
cpd_out:
    ld 28, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_pound_hit:                     # (r29/r30) the shockwave: a ring, a star, all in reach hit, crates, the camera
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x90(1)
    stfd 31, 0x70(1)
    stfd 30, 0x78(1)
    lfs 31, {T_POUND_RADIUS}(29)    # f31 = its reach, f30 = its damage
    lfs 30, {T_POUND_DAMAGE}(29)
    li 3, {FX_RING}
    lwz 4, {T_RING_FRAMES}(29)
    addi 5, 29, {C_POS}
    li 6, 0
    li 7, 0
    li 8, 0
    fmr 1, 31
    bl coop_fx_add
    addi 3, 29, {C_POS}
    lwz 4, {T_RAM_BURST}(29)
    lwz 5, {T_RAM_BURST_FRAMES}(29)
    lfs 1, {T_RAM_BURST_R}(29)
    bl coop_burst
    addi 3, 29, {C_POS}             # all in reach
    fmr 1, 31
    fmr 2, 30
    bl coop_area_hit
    lwz 9, {C_POS}(29)              # crates
    stw 9, {C_FIST}(29)
    lwz 9, {C_POS} + 4(29)
    stw 9, {C_FIST} + 4(29)
    lfs 0, {C_POS} + 8(29)
    lfs 1, {T_FIST_UP}(29)
    fadds 0, 0, 1
    stfs 0, {C_FIST} + 8(29)
    lfs 0, {T_ONE}(29)
    stfs 0, {C_FIST} + 12(29)
    addi 3, 29, {C_FIST}
    fmr 1, 31
    bl {CRATE_SWEEP}
    lfs 1, {T_POUND_SHAKE}(29)
    lwz 3, {T_POUND_SHAKE_FRAMES}(29)
    bl coop_shake
    lwz 3, {T_SOUND_POUND}(29)
    bl coop_sound
    lfd 30, 0x78(1)
    lfd 31, 0x70(1)
    addi 1, 1, 0x90
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_area_hit:                      # (r3 a place, f1 reach, f2 damage; r29/r30) every enemy within reach hit
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0xa0(1)
    std 28, 0x70(1)
    std 27, 0x78(1)
    std 26, 0x80(1)
    stfd 31, 0x88(1)
    stfd 30, 0x90(1)
    mr 26, 3
    fmr 31, 1
    fmr 30, 2
    lis 27, {MOBY_LIST_HA}
    addi 27, 27, {MOBY_LIST_LO} - 4
cah_next:
    lwzu 28, 4(27)
    cmpwi 28, 0
    beq cah_out
    mr 3, 28
    bl coop_enemy
    cmpwi 3, 0
    beq cah_next
    lfs 1, 0x10(28)                 # on the ground plane, and not far above or below
    lfs 0, 0(26)
    fsubs 1, 1, 0
    lfs 2, 0x14(28)
    lfs 0, 4(26)
    fsubs 2, 2, 0
    fmuls 1, 1, 1
    fmadds 1, 2, 2, 1
    fsqrts 1, 1
    fcmpu 0, 1, 31
    bgt cah_next
    lfs 1, 0x18(28)
    lfs 0, 8(26)
    fsubs 1, 1, 0
    fabs 1, 1
    lfs 0, {T_POUND_REACH_Z}(29)
    fcmpu 0, 1, 0
    bgt cah_next
    mr 3, 28
    fmr 1, 30
    lwz 4, {T_ZAP_FLAGS}(29)
    bl coop_hit
    mr 3, 28                        # and a crackle on it
    bl coop_hit_burst
    b cah_next
cah_out:
    lfd 30, 0x90(1)
    lfd 31, 0x88(1)
    ld 26, 0x80(1)
    ld 27, 0x78(1)
    ld 28, 0x70(1)
    addi 1, 1, 0xa0
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_nearest_flat:                  # (r3 a place, f1 reach on the ground plane, f2 up or down to its body; r29)
    mflr 0                          #  -> r3 = the nearest enemy so, 0 = none
    std 0, 0x10(1)
    stdu 1, -0xa0(1)
    std 28, 0x70(1)
    std 27, 0x78(1)
    std 26, 0x80(1)
    stfd 31, 0x88(1)
    stfd 30, 0x90(1)
    stfd 29, 0x98(1)
    mr 26, 3
    fmr 31, 1
    fmr 30, 2
    li 3, 0
    std 3, 0x60(1)                  # the best so far
    lis 27, {MOBY_LIST_HA}
    addi 27, 27, {MOBY_LIST_LO} - 4
cnf_next:
    lwzu 28, 4(27)
    cmpwi 28, 0
    beq cnf_out
    mr 3, 28
    bl coop_enemy
    cmpwi 3, 0
    beq cnf_next
    lfs 1, 0x18(28)                 # its body's height
    lfs 0, {T_TARGET_UP}(29)
    fadds 1, 1, 0
    lfs 0, 8(26)
    fsubs 1, 1, 0
    fabs 1, 1
    fcmpu 0, 1, 30
    bgt cnf_next
    lfs 1, 0x10(28)
    lfs 0, 0(26)
    fsubs 1, 1, 0
    lfs 2, 0x14(28)
    lfs 0, 4(26)
    fsubs 2, 2, 0
    fmuls 1, 1, 1
    fmadds 1, 2, 2, 1
    fsqrts 1, 1
    fcmpu 0, 1, 31
    bgt cnf_next
    fmr 31, 1                       # the nearest yet: the reach shrinks to it
    std 28, 0x60(1)
    b cnf_next
cnf_out:
    ld 3, 0x60(1)
    lfd 29, 0x98(1)
    lfd 30, 0x90(1)
    lfd 31, 0x88(1)
    ld 26, 0x80(1)
    ld 27, 0x78(1)
    ld 28, 0x70(1)
    addi 1, 1, 0xa0
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_hit_burst:                     # (r3 a moby; r29) a small crackle of lightning on it
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    addi 4, 29, {C_FXV}
    bl coop_aimed
    addi 3, 29, {C_FXV}
    lwz 4, {T_HIT_BURST}(29)
    li 5, 5
    lfs 1, {T_HIT_BURST_R}(29)
    bl coop_burst
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr
"""
