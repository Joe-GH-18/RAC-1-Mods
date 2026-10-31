"""The modes and Clank's flight, every frame before the hero (FRAME_HOOKS).

Modes (C_MODE): docked (on Ratchet's back, as in the game), popping off (T_POP_FRAMES: from
backpack Clank's place up T_POP_UP and back T_POP_BACK in Ratchet's frame), flying, docking
(T_DOCK_FRAMES: from where he was to the seat, easing in). Player 2 joins with Start or Cross,
docks by holding Select (T_DOCK_HOLD frames);
without Player 2's pad for T_GONE_FRAMES he docks by himself. He docks at once (no movement)
while Ratchet is not the hero (hero +0x20a4: Clank or Giant Clank sections), in a scene
(SCENE_FLAG), dying (state 0x77) or without his backpack Clank.

Flight: the stick is taken relative to the camera (CAMERA_STATE +0x350, the view row flattened:
forward is away from it), times T_FLY_SPEED; with the stick at rest for T_SLOT_IDLE frames the
wish is the way to the buddy slot (T_SLOT_AHEAD, T_SLOT_LEFT in Ratchet's frame) times
T_SLOT_GAIN. Past T_LEASH_SOFT from Ratchet a pull towards him grows to the full speed at
T_LEASH_FULL. The velocity moves to the wish by T_FLY_ACCEL (T_FLY_DECEL with no wish). Cross
boosts (T_BOOST_SPEED for T_BOOST_FRAMES, along the wish or his heading). The height springs
(T_SPRING_K, T_SPRING_C) to Ratchet's ground plus the hover height (R2/L2 change it within
T_HOVER_MIN..T_HOVER_MAX); his ground is his z while he is down (hero +0x300 counts frames on the
ground, 0 in the air), so Clank does not bob with his jumps, and Clank stays above it plus
T_FLOOR. Walls, ceilings and floors stop him (coop_fly_move, the game's ray per axis; the user:
"fix the collision errors that clank flies through walls"). Past T_LEASH_HARD, or off the
screen for T_OFFSCREEN frames while more than T_BLINK_NEAR away, he blinks back to the slot (or
over Ratchet when a wall is between them). He turns to his velocity (or Ratchet's heading at
rest), rolls by his sideways speed and pitches by his speed.
"""
from ..game import *  # noqa: F401,F403

SCENE_FLAG = 0xA10708          # not 0 in the game's scenes (5 during the gold weapon scene)
STATE_DEATH = 0x77
HERO_LANDED = 0x300            # frames on the ground (u32), 0 in the air (+0x418 stayed 0 on the ground, 2026-10-26)
# The pack goes with Clank (spec 3.7; the user: "if clank is not on ratchets back, he should be
# unable to use any pack movement"): set_state, after it has saved its registers, at the test of
# the state type (r28 = the state asked for, r27 = hero; r0, r3 free). Out of his back (and
# T_PACK_GATE), the glide (8) is refused the game's own way
# (r3 = 0 to its epilogue, as for state type 0x14) and the crouch's pack jumps (0xa, 0x10 the long
# jumps, 0xf, 0xd the high jumps) are his plain jump, 7, as without a pack.
PACK_HOOK, PACK_HOOK_WORD = 0xB7320, 0x2C050014   # cmpwi r5, 0x14
PACK_REFUSE = 0xB7330                             # li r3, 0; b to the epilogue
PACK_HOVERS, PACK_JUMPS, PLAIN_JUMP = (0x8,), (0xA, 0x10, 0xF, 0xD), 0x7
# (0xe is his double jump, not the pack's: refused at first, the user: "ratchet can also not do a
# double jump fix that")
COS, SIN = 0x5E8078, 0x5E8128  # (f1 angle) -> f1
ANGLE_DIFF = 0x5025E0          # (f1, f2) -> f1 - f2 wrapped to -pi..pi
BUTTON_L2, BUTTON_R2, BUTTON_CROSS = 0x1, 0x2, 0x40
BUTTON_SELECT, BUTTON_START = 0x100, 0x800

CODE = r"""
coop_frame:                         # replaces bl HERO_MAIN; r31 = state block, r30 = hero, r29 = the mod's block
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0xa0(1)
    std 31, 0x70(1)
    std 30, 0x78(1)
    std 29, 0x80(1)
    std 28, 0x88(1)
    std 27, 0x90(1)
    lis 31, {STATE_HA}
    addi 31, 31, {STATE_LO}
    lis 30, {HERO_HA}
    addi 30, 30, {HERO_LO}
    lis 29, {COOP_HA}
    addi 29, 29, {COOP_LO}
    bl coop_new_level               # (first: the others must not touch the old level's mobys)
    bl coop_cam_restore             # the game's camera place back before its update (camera.py)
    bl coop_preview_late            # the menu's preview Clank away once the game runs again (preview.py)
    bl coop_banks                   # our own sound banks in, once (body.py)
    bl coop_sound_try
    bl coop_tick
    ld 27, 0x90(1)
    ld 28, 0x88(1)
    ld 29, 0x80(1)
    ld 30, 0x78(1)
    ld 31, 0x70(1)
    addi 1, 1, 0xa0
    ld 0, 0x10(1)
    mtlr 0
coop_frame_next:
    {CHAIN}

coop_new_level:                     # (r29) a new level: the mobys went with the old one
    lis 9, {FRAME_COUNTER_HA}
    lwz 9, {FRAME_COUNTER_LO}(9)
    lwz 10, {C_FRAME}(29)
    stw 9, {C_FRAME}(29)
    cmplw 9, 10
    bgelr
    b coop_forget

coop_tick:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    li 9, 0                         # the bolts are made anew each frame
    stw 9, {C_BOLT_N}(29)
    lis 9, {FRAME_COUNTER_HA}       # the lightning's shape: new every 2 frames
    lwz 9, {FRAME_COUNTER_LO}(9)
    srwi 9, 9, 1
    lis 10, 0x9e37
    ori 10, 10, 0x79b1
    mullw 9, 9, 10
    stw 9, {C_BOLT_SEED}(29)
    stw 9, {C_SEED}(29)
    bl coop_input
    bl coop_mini_check              # the mini Giant Clank (mini.py) has the frame
    cmpwi 3, 0
    bne ct_shared
    bl coop_suspended
    cmpwi 3, 0
    beq ct_modes
    lwz 9, {C_MODE}(29)
    cmpwi 9, {MODE_DOCKED}
    beq ct_shared
    bl coop_dock_now
    b ct_shared
ct_modes:
    bl coop_seat
    lwz 9, {C_MODE}(29)
    cmpwi 9, {MODE_POP}
    beq ct_pop
    cmpwi 9, {MODE_FLY}
    beq ct_fly
    cmpwi 9, {MODE_DOCKING}
    beq ct_docking
    lfs 1, {T_REGEN_DOCKED}(29)     # docked
    bl coop_regen
    lwz 9, {C_DRIVER}(29)
    cmpwi 9, {DRIVER_NONE}
    beq ct_shared
    lwz 9, {C_BUTTONS_NEW}(29)
    andi. 9, 9, {BUTTON_START} | {BUTTON_CROSS}
    beq ct_shared
    bl coop_join
    b ct_shared
ct_pop:
    bl coop_pop
    b ct_body
ct_fly:
    bl coop_fly
    lwz 9, {C_MODE}(29)
    cmpwi 9, {MODE_FLY}
    bne ct_body
    bl coop_combat
    b ct_body
ct_docking:
    bl coop_docking
ct_body:
    lwz 9, {C_MODE}(29)
    cmpwi 9, {MODE_DOCKED}
    beq ct_shared
    bl coop_body_place
ct_shared:
    bl coop_fx
    lwz 9, {C_MODE}(29)
    subfic 9, 9, 0
    li 9, 0
    adde 9, 9, 9
    xori 9, 9, 1                    # 1 when out
    stw 9, {COOP_OUT}(31)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_input:                         # (r29/r31) who drives him, and the stick and buttons of it
    lwz 9, {C_TEST}(29)             # the test input: Player 2, pad or not
    cmpwi 9, 0
    bne ci_test
    lwz 9, {COOP_PAD}(31)
    cmpwi 9, 0
    beq ci_gone
    li 10, 0
    stw 10, {C_GONE}(29)
    li 10, 1
    stw 10, {COOP_P2}(31)
    li 10, {DRIVER_P2}
    stw 10, {C_DRIVER}(29)
    lfs 0, 8(9)                     # the stick, y up
    stfs 0, {C_STICK}(29)
    lfs 0, 0xc(9)
    fneg 0, 0
    stfs 0, {C_STICK} + 4(29)
    lwz 10, {C_HELD}(29)
    stw 10, {C_BUTTONS}(29)
    lwz 10, {C_PRESSED}(29)
    stw 10, {C_BUTTONS_NEW}(29)
    blr
ci_test:
    li 10, 0
    stw 10, {C_GONE}(29)
    li 10, 1
    stw 10, {COOP_P2}(31)
    li 10, {DRIVER_P2}
    stw 10, {C_DRIVER}(29)
    lwz 10, {C_TEST_STICK}(29)
    stw 10, {C_STICK}(29)
    lwz 10, {C_TEST_STICK} + 4(29)
    stw 10, {C_STICK} + 4(29)
    lwz 10, {C_HELD}(29)
    stw 10, {C_BUTTONS}(29)
    lwz 10, {C_PRESSED}(29)
    stw 10, {C_BUTTONS_NEW}(29)
    blr
ci_gone:
    li 10, 0
    stw 10, {COOP_P2}(31)
    stw 10, {C_STICK}(29)
    stw 10, {C_STICK} + 4(29)
    stw 10, {C_BUTTONS}(29)
    stw 10, {C_BUTTONS_NEW}(29)
    lwz 10, {C_GONE}(29)
    addi 10, 10, 1
    stw 10, {C_GONE}(29)
    lwz 11, {T_GONE_FRAMES}(29)
    cmpw 10, 11
    bltlr
    lwz 10, {C_AI_ON}(29)           # nobody at the second pad: AI Clank, if chosen on the menu (menu.py)
    lis 11, {AI_SAVE_HA}            # or set by tools/coop.py (ai.py)
    lhz 11, {AI_SAVE_LO}(11)
    or. 10, 10, 11
    bne coop_ai
    li 10, {DRIVER_NONE}
    stw 10, {C_DRIVER}(29)
    blr

coop_suspended:                     # (r29/r30/r31) -> r3 = 1 when he must be on Ratchet's back
    li 3, 1
    lwz 9, {GC_MODE}(31)            # Giant Clank on Ratchet (mods/goldenclank): Player 2 pilots his arms
    cmpwi 9, 0
    bnelr
    lbz 9, {HERO_KIND}(30)
    cmpwi 9, 0
    bnelr
    lis 9, {SCENE_FLAG_HA}
    lwz 9, {SCENE_FLAG_LO}(9)
    cmpwi 9, 0
    bnelr
    lwz 9, 0x2084(30)
    cmpwi 9, {STATE_DEATH}
    beqlr
    lwz 9, 0x2080(30)
    cmpwi 9, 0
    beqlr
    lwz 9, {HERO_CLANK_MOBY}(30)
    cmpwi 9, 0
    beqlr
    li 3, 0
    blr

coop_seat:                          # (r29/r30) C_SEAT = backpack Clank's place; C_TMP = cos, sin of Ratchet's heading
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lwz 9, {HERO_CLANK_MOBY}(30)
    lfs 0, 0x10(9)
    stfs 0, {C_SEAT}(29)
    lfs 0, 0x14(9)
    stfs 0, {C_SEAT} + 4(29)
    lfs 0, 0x18(9)
    lfs 1, {T_SEAT_UP}(29)
    fadds 0, 0, 1
    stfs 0, {C_SEAT} + 8(29)
    lfs 1, 0x98(30)
    bl {COS}
    stfs 1, {C_TMP}(29)
    lfs 1, 0x98(30)
    bl {SIN}
    stfs 1, {C_TMP} + 4(29)
    lwz 9, {HERO_LANDED}(30)        # his ground: his z while he is down
    cmpwi 9, 0
    beq cs_out
    lfs 0, 0x88(30)
    stfs 0, {C_GROUND}(29)
cs_out:
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_regen:                         # (f1 = energy a second; r29) energy up to T_ENERGY_MAX
    lfs 0, {C_ENERGY}(29)
    lfs 2, {T_DT}(29)
    fmadds 0, 1, 2, 0
    lfs 2, {T_ENERGY_MAX}(29)
    fcmpu 0, 0, 2
    ble cr_store
    fmr 0, 2
cr_store:
    stfs 0, {C_ENERGY}(29)
    blr

coop_join:                          # (r29/r30) off Ratchet's back
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    li 9, {MODE_POP}
    stw 9, {C_MODE}(29)
    li 9, 0
    stw 9, {C_TIMER}(29)
    stw 9, {C_VEL}(29)
    stw 9, {C_VEL} + 4(29)
    stw 9, {C_VEL} + 8(29)
    stw 9, {C_IDLE}(29)
    stw 9, {C_SELECT}(29)
    stw 9, {C_OFFSCREEN}(29)
    stw 9, {C_ROLL}(29)
    stw 9, {C_PITCH}(29)
    lwz 9, {T_HOVER}(29)
    stw 9, {C_HOVER}(29)
    lwz 9, 0x98(30)
    stw 9, {C_YAW}(29)
    lwz 9, 0x88(30)
    stw 9, {C_GROUND}(29)
    addi 3, 29, {C_SEAT}            # a star of lightning at the seat
    lwz 4, {T_SEAT_BURST}(29)
    li 5, 10
    lfs 1, {T_SEAT_BURST_R}(29)
    bl coop_burst
    lwz 3, {T_SOUND_JOIN}(29)
    bl coop_sound
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_pop:                           # (r29/r30) up and back off the seat, then flying
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lwz 9, {C_TIMER}(29)
    addi 9, 9, 1
    stw 9, {C_TIMER}(29)
    lwz 10, {T_POP_FRAMES}(29)
    cmpw 9, 10
    blt cpo_arc
    li 9, {MODE_FLY}
    stw 9, {C_MODE}(29)
    lwz 9, {T_FLY_ANIM}(29)
    mr 3, 9
    bl coop_anim
    b cpo_out
cpo_arc:
    bl coop_t                       # f1 = t
    lfs 2, {T_TWO}(29)
    fsubs 2, 2, 1
    fmuls 2, 2, 1                   # 2t - t^2: up fast, slowing
    lfs 3, {T_POP_UP}(29)
    fmuls 2, 2, 3
    lfs 3, {T_POP_BACK}(29)
    fmuls 3, 3, 1                   # back by t
    lfs 4, {C_TMP}(29)
    lfs 5, {C_TMP} + 4(29)
    lfs 0, {C_SEAT}(29)
    fnmsubs 0, 4, 3, 0
    stfs 0, {C_POS}(29)
    lfs 0, {C_SEAT} + 4(29)
    fnmsubs 0, 5, 3, 0
    stfs 0, {C_POS} + 4(29)
    lfs 0, {C_SEAT} + 8(29)
    fadds 0, 0, 2
    stfs 0, {C_POS} + 8(29)
    lwz 9, 0x98(30)
    stw 9, {C_YAW}(29)
    lwz 3, {T_POP_ANIM}(29)
    bl coop_anim
cpo_out:
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_t:                             # (r9 = frames, r10 = of them, both >= 0; r29) -> f1 = r9 / r10
    lis 11, 0x4330
    stw 11, {C_TMP} + 0x10(29)
    stw 9, {C_TMP} + 0x14(29)
    lfd 1, {C_TMP} + 0x10(29)
    stw 10, {C_TMP} + 0x14(29)
    lfd 2, {C_TMP} + 0x10(29)
    li 9, 0
    stw 9, {C_TMP} + 0x14(29)
    lfd 3, {C_TMP} + 0x10(29)
    fsub 1, 1, 3
    fsub 2, 2, 3
    fdiv 1, 1, 2
    frsp 1, 1
    blr

coop_docking:                       # (r29/r30) to the seat, easing in, then docked
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lwz 9, {C_TIMER}(29)
    addi 9, 9, 1
    stw 9, {C_TIMER}(29)
    lwz 10, {T_DOCK_FRAMES}(29)
    cmpw 9, 10
    blt cdk_move
    addi 3, 29, {C_SEAT}            # a star of lightning at the seat
    lwz 4, {T_SEAT_BURST}(29)
    li 5, 10
    lfs 1, {T_SEAT_BURST_R}(29)
    bl coop_burst
    lwz 3, {T_SOUND_DOCK}(29)
    bl coop_sound
    bl coop_dock_now
    b cdk_out
cdk_move:
    bl coop_t
    fmuls 1, 1, 1                   # t^2
    li 7, 0
cdk_axis:
    addi 8, 7, {C_FROM}
    lfsx 0, 29, 8
    addi 8, 7, {C_SEAT}
    lfsx 2, 29, 8
    fsubs 2, 2, 0
    fmadds 0, 2, 1, 0
    addi 8, 7, {C_POS}
    stfsx 0, 29, 8
    addi 7, 7, 4
    cmpwi 7, 12
    blt cdk_axis
    lfs 1, 0x98(30)                 # he turns as Ratchet faces
    lfs 2, {C_YAW}(29)
    bl {ANGLE_DIFF}
    lfs 2, {C_YAW}(29)
    lfs 0, {T_HALF}(29)
    fmadds 1, 1, 0, 2
    stfs 1, {C_YAW}(29)
    li 9, 0
    stw 9, {C_ROLL}(29)
    stw 9, {C_PITCH}(29)
cdk_out:
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_dock_start:                    # (r29) from where he is to the seat
    li 9, {MODE_DOCKING}
    stw 9, {C_MODE}(29)
    li 9, 0
    stw 9, {C_TIMER}(29)
    stw 9, {C_ZAP}(29)
    stw 9, {C_PUNCH}(29)
    stw 9, {C_POUND}(29)
    stw 9, {C_BOOST}(29)
    stw 9, {C_SWELL}(29)
    lwz 9, {C_POS}(29)
    stw 9, {C_FROM}(29)
    lwz 9, {C_POS} + 4(29)
    stw 9, {C_FROM} + 4(29)
    lwz 9, {C_POS} + 8(29)
    stw 9, {C_FROM} + 8(29)
    blr

coop_dock_now:                      # (r29/r30) on Ratchet's back at once
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    li 9, {MODE_DOCKED}
    stw 9, {C_MODE}(29)
    li 9, 0
    stw 9, {C_TIMER}(29)
    stw 9, {C_TARGET}(29)
    stw 9, {C_ZAP}(29)
    stw 9, {C_PUNCH}(29)
    stw 9, {C_POUND}(29)
    stw 9, {C_BOOST}(29)
    stw 9, {C_SWELL}(29)
    li 3, 0
    bl coop_wings
    li 3, 0
    bl coop_body
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_body_place:                    # (r29/r30) the body (made if need be) at his place, turned, scaled
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    li 3, 1
    bl coop_body
    cmpwi 3, 0
    beq cbp_out
    lwz 9, {C_POS}(29)
    stw 9, 0x10(3)
    lwz 9, {C_POS} + 4(29)
    stw 9, 0x14(3)
    lwz 9, {C_POS} + 8(29)
    stw 9, 0x18(3)
    lwz 9, {C_ROLL}(29)
    stw 9, 0x40(3)
    lwz 9, {C_PITCH}(29)
    stw 9, 0x44(3)
    std 3, 0x60(1)
    lfs 1, {C_YAW}(29)              # his model faces T_YAW_OFFSET from his heading
    lfs 0, {T_YAW_OFFSET}(29)
    fadds 1, 1, 0
    lfs 2, {T_ZERO}(29)
    bl {ANGLE_DIFF}
    ld 3, 0x60(1)
    stfs 1, 0x48(3)
    lfs 1, {C_SWELL}(29)            # T_SCALE * (1 + the swell)
    lfs 0, {T_ONE}(29)
    fadds 1, 1, 0
    lfs 0, {T_SCALE}(29)
    fmuls 1, 1, 0
    stfs 1, 0x2c(3)
    li 3, 1
    bl coop_wings
    bl coop_wings_put               # (before the moby loop, which animates it and builds its joints)
cbp_out:
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_fly:                           # (r29/r30) a frame of flight
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    stfd 31, 0x70(1)
    stfd 30, 0x78(1)
    lwz 3, {T_FLY_ANIM}(29)
    bl coop_anim
    lwz 9, {C_DRIVER}(29)           # no driver: home
    cmpwi 9, {DRIVER_NONE}
    beq cf_dock
    lwz 9, {C_BUTTONS}(29)          # Select held: home
    lwz 10, {C_SELECT}(29)
    andi. 9, 9, {BUTTON_SELECT}
    li 11, 0
    beq cf_select
    addi 11, 10, 1
cf_select:
    stw 11, {C_SELECT}(29)
    lwz 10, {T_DOCK_HOLD}(29)
    cmpw 11, 10
    bge cf_dock
    b cf_energy                     # (Triangle is the ground pound: Select held docks)
cf_dock:
    bl coop_dock_start
    b cf_out
cf_energy:
    lwz 9, {C_ZAP}(29)
    cmpwi 9, 0
    bne cf_stick
    lfs 1, {T_REGEN}(29)
    bl coop_regen
cf_stick:
    lfs 1, {C_STICK}(29)            # the stick, relative to the camera
    lfs 2, {C_STICK} + 4(29)
    fmuls 3, 1, 1
    fmadds 3, 2, 2, 3
    fsqrts 3, 3
    lfs 0, {T_STICK_DEAD}(29)
    fcmpu 0, 3, 0
    blt cf_rest
    li 9, 0
    stw 9, {C_IDLE}(29)
    lis 9, {CAMERA_STATE_HA}
    addi 9, 9, {CAMERA_STATE_LO}
    lfs 4, 0x350(9)
    lfs 5, 0x354(9)
    fmuls 6, 4, 4
    fmadds 6, 5, 5, 6
    fsqrts 6, 6
    lfs 0, {T_SMALL}(29)
    fcmpu 0, 6, 0
    blt cf_rest
    fdivs 4, 4, 6                   # f4, f5 = forward on the ground; right = (f5, -f4)
    fdivs 5, 5, 6
    fmuls 7, 4, 2
    fmadds 7, 5, 1, 7               # x: fx sy + fy sx
    fmuls 8, 5, 2
    fnmsubs 8, 4, 1, 8              # y: fy sy - fx sx
    lfs 0, {T_ONE}(29)
    fcmpu 0, 3, 0
    ble cf_speed
    fdivs 7, 7, 3
    fdivs 8, 8, 3
cf_speed:
    lfs 0, {T_FLY_SPEED}(29)
    fmuls 7, 7, 0
    fmuls 8, 8, 0
    b cf_wish
cf_rest:
    lfs 7, {T_ZERO}(29)
    fmr 8, 7
    lwz 9, {C_IDLE}(29)
    addi 9, 9, 1
    lwz 10, {C_ZAP}(29)             # zapping he holds his place
    cmpwi 10, 0
    beq cf_idle
    li 9, 0
cf_idle:
    stw 9, {C_IDLE}(29)
    cmpwi 10, 0
    bne cf_wish
    lwz 10, {T_SLOT_IDLE}(29)
    cmpw 9, 10
    blt cf_wish
    bl coop_slot                    # f1, f2 = the slot
    lfs 0, {C_POS}(29)
    fsubs 7, 1, 0
    lfs 0, {C_POS} + 4(29)
    fsubs 8, 2, 0
    lfs 0, {T_SLOT_GAIN}(29)
    fmuls 7, 7, 0
    fmuls 8, 8, 0
    fmuls 3, 7, 7
    fmadds 3, 8, 8, 3
    fsqrts 3, 3
    lfs 0, {T_FLY_SPEED}(29)
    fcmpu 0, 3, 0
    ble cf_wish
    fdivs 0, 0, 3
    fmuls 7, 7, 0
    fmuls 8, 8, 0
cf_wish:
    lfs 1, 0x80(30)                 # the leash: a pull to Ratchet past T_LEASH_SOFT
    lfs 0, {C_POS}(29)
    fsubs 1, 1, 0
    lfs 2, 0x84(30)
    lfs 0, {C_POS} + 4(29)
    fsubs 2, 2, 0
    fmuls 3, 1, 1
    fmadds 3, 2, 2, 3
    fsqrts 3, 3                     # f3 = how far
    lfs 0, {T_LEASH_HARD}(29)
    fcmpu 0, 3, 0
    bgt cf_blink
    lfs 0, {T_LEASH_SOFT}(29)
    fsubs 4, 3, 0
    lfs 0, {T_ZERO}(29)
    fcmpu 0, 4, 0
    ble cf_pulled
    lfs 0, {T_LEASH_FULL}(29)
    lfs 5, {T_LEASH_SOFT}(29)
    fsubs 0, 0, 5
    fdivs 4, 4, 0
    lfs 0, {T_ONE}(29)
    fcmpu 0, 4, 0
    ble cf_pull
    fmr 4, 0
cf_pull:
    lfs 0, {T_FLY_SPEED}(29)
    fmuls 4, 4, 0
    fdivs 4, 4, 3
    fmadds 7, 1, 4, 7
    fmadds 8, 2, 4, 8
cf_pulled:
    fmuls 3, 7, 7                   # never faster than T_FLY_SPEED (the slot and the pull add up)
    fmadds 3, 8, 8, 3
    fsqrts 3, 3
    lfs 0, {T_FLY_SPEED}(29)
    fcmpu 0, 3, 0
    ble cf_capped
    fdivs 0, 0, 3
    fmuls 7, 7, 0
    fmuls 8, 8, 0
cf_capped:
    stfs 7, {C_WISH}(29)
    stfs 8, {C_WISH} + 4(29)
    bl coop_offscreen               # -> r3 = 1 when he has been off the screen too long
    cmpwi 3, 0
    bne cf_blink
    lwz 9, {C_PUNCH}(29)            # the dive punch and the overcharge set his velocity themselves
    lwz 10, {C_POUND}(29)
    or. 9, 9, 10
    bne cf_height
    bl coop_boost
    lwz 9, {C_BOOST}(29)
    cmpwi 9, 0
    bne cf_height
    lfs 7, {C_WISH}(29)             # the velocity to the wish
    lfs 8, {C_WISH} + 4(29)
    lfs 1, {C_VEL}(29)
    lfs 2, {C_VEL} + 4(29)
    fsubs 3, 7, 1
    fsubs 4, 8, 2
    fmuls 5, 3, 3
    fmadds 5, 4, 4, 5
    fsqrts 5, 5
    lfs 6, {T_FLY_ACCEL}(29)
    fmuls 0, 7, 7
    fmadds 0, 8, 8, 0
    lfs 9, {T_SMALL}(29)
    fcmpu 0, 0, 9
    bgt cf_rate
    lfs 6, {T_FLY_DECEL}(29)
cf_rate:
    lfs 0, {T_DT}(29)
    fmuls 6, 6, 0                   # f6 = the step this frame
    fcmpu 0, 5, 6
    ble cf_step
    fdivs 0, 6, 5
    fmuls 3, 3, 0
    fmuls 4, 4, 0
cf_step:
    fadds 1, 1, 3
    fadds 2, 2, 4
    stfs 1, {C_VEL}(29)
    stfs 2, {C_VEL} + 4(29)
cf_height:
    lwz 9, {C_BUTTONS}(29)          # R2 / L2: the hover height
    lfs 1, {C_HOVER}(29)
    lfs 2, {T_HOVER_RATE}(29)
    lfs 0, {T_DT}(29)
    fmuls 2, 2, 0
    andi. 10, 9, {BUTTON_R2}
    beq cf_lower
    fadds 1, 1, 2
cf_lower:
    andi. 10, 9, {BUTTON_L2}
    beq cf_clamp
    fsubs 1, 1, 2
cf_clamp:
    lfs 0, {T_HOVER_MIN}(29)
    fcmpu 0, 1, 0
    bge cf_max
    fmr 1, 0
cf_max:
    lfs 0, {T_HOVER_MAX}(29)
    fcmpu 0, 1, 0
    ble cf_hover
    fmr 1, 0
cf_hover:
    stfs 1, {C_HOVER}(29)
    lwz 9, {C_POUND}(29)            # the ground pound and the ram move him up and down themselves
    lwz 10, {C_PUNCH}(29)
    or. 9, 9, 10
    beq cf_spring
    lfs 0, {T_DT}(29)
    b cf_place
cf_spring:
    lfs 0, {C_GROUND}(29)           # spring to his ground plus the hover (and up as he swells)
    fadds 1, 1, 0
    lfs 0, {C_SWELL}(29)
    lfs 2, {T_TWO}(29)
    fmadds 1, 0, 2, 1
    lfs 2, {C_POS} + 8(29)
    fsubs 1, 1, 2
    lfs 0, {T_SPRING_K}(29)
    fmuls 1, 1, 0
    lfs 3, {C_VEL} + 8(29)
    lfs 0, {T_SPRING_C}(29)
    fnmsubs 1, 3, 0, 1              # k (target - z) - c vz
    lfs 0, {T_DT}(29)
    fmadds 3, 1, 0, 3
    stfs 3, {C_VEL} + 8(29)
cf_place:
    bl coop_fly_move                # the place, stopped by walls
    lfs 1, {C_GROUND}(29)           # never under his ground
    lfs 0, {T_FLOOR}(29)
    fadds 1, 1, 0
    lfs 2, {C_POS} + 8(29)
    fcmpu 0, 2, 1
    bge cf_turn
    stfs 1, {C_POS} + 8(29)
    lfs 0, {T_ZERO}(29)
    stfs 0, {C_VEL} + 8(29)
cf_turn:
    bl coop_turn
    b cf_out
cf_blink:
    bl coop_blink
cf_out:
    lfd 30, 0x78(1)
    lfd 31, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_fly_move:                      # (r29) his place moved by C_VEL for a frame, each axis on its own (so he
    mflr 0                          # slides along a wall): unless the game's ray from his middle, the move and
    std 0, 0x10(1)                  # T_COLL_R (down: to his feet, up: T_COLL_TOP) beyond, meets something; then
    stdu 1, -0x90(1)                # that axis stays and its speed is 0 (C_BLOCKED: which)
    std 28, 0x70(1)
    std 27, 0x78(1)
    stfd 31, 0x80(1)
    stfd 30, 0x88(1)
    li 27, 0                        # r27 = BLOCK_* bits
    li 28, 0                        # r28 = the axis (byte offset)
cfm_axis:
    addi 8, 28, {C_VEL}
    lfsx 1, 29, 8
    lfs 0, {T_DT}(29)
    fmuls 31, 1, 0                  # f31 = this frame's move
    fabs 1, 31
    lfs 0, {T_SMALL}(29)
    fcmpu 0, 1, 0
    blt cfm_next
    lwz 9, {T_COLL_ON}(29)
    cmpwi 9, 0
    beq cfm_go
    lwz 9, {C_POS}(29)              # the ray from his middle
    stw 9, {C_RAY_FROM}(29)
    lwz 9, {C_POS} + 4(29)
    stw 9, {C_RAY_FROM} + 4(29)
    lfs 0, {C_POS} + 8(29)
    lfs 1, {T_COLL_UP}(29)
    fadds 0, 0, 1
    stfs 0, {C_RAY_FROM} + 8(29)
    lfs 0, {T_ONE}(29)
    stfs 0, {C_RAY_FROM} + 12(29)
    li 9, 0
cfm_copy:
    addi 8, 9, {C_RAY_FROM}
    lwzx 10, 29, 8
    addi 8, 9, {C_RAY_TO}
    stwx 10, 29, 8
    addi 9, 9, 4
    cmpwi 9, 16
    blt cfm_copy
    lfs 30, {T_COLL_R}(29)          # f30 = the reach beyond the move, r9 = the bit
    li 9, {BLOCK_X}
    cmpwi 28, 4
    blt cfm_sign
    li 9, {BLOCK_Y}
    beq cfm_sign
    lfs 30, {T_COLL_UP}(29)
    li 9, {BLOCK_DOWN}
    lfs 0, {T_ZERO}(29)
    fcmpu 0, 31, 0
    blt cfm_sign
    lfs 30, {T_COLL_TOP}(29)
    li 9, {BLOCK_UP}
cfm_sign:
    lfs 0, {T_ZERO}(29)
    fcmpu 0, 31, 0
    bge cfm_reach
    fneg 30, 30
cfm_reach:
    std 9, 0x60(1)
    addi 8, 28, {C_RAY_TO}
    lfsx 0, 29, 8
    fadds 0, 0, 31
    fadds 0, 0, 30
    stfsx 0, 29, 8
    lwz 6, {C_BODY}(29)             # (him left out)
    bl coop_cam_ray
    ld 9, 0x60(1)
    cmpwi 3, 0
    beq cfm_go
    or 27, 27, 9
    li 9, 0
    addi 8, 28, {C_VEL}
    stwx 9, 29, 8
    b cfm_next
cfm_go:
    addi 8, 28, {C_POS}
    lfsx 0, 29, 8
    fadds 0, 0, 31
    stfsx 0, 29, 8
cfm_next:
    addi 28, 28, 4
    cmpwi 28, 12
    blt cfm_axis
    stw 27, {C_BLOCKED}(29)
    lfd 30, 0x88(1)
    lfd 31, 0x80(1)
    ld 27, 0x78(1)
    ld 28, 0x70(1)
    addi 1, 1, 0x90
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_distance:                      # (r3 = a place, 3 floats; r29) -> f1 = his distance to it
    lfs 1, 0(3)
    lfs 0, {C_POS}(29)
    fsubs 1, 1, 0
    lfs 2, 4(3)
    lfs 0, {C_POS} + 4(29)
    fsubs 2, 2, 0
    lfs 3, 8(3)
    lfs 0, {C_POS} + 8(29)
    fsubs 3, 3, 0
    fmuls 1, 1, 1
    fmadds 1, 2, 2, 1
    fmadds 1, 3, 3, 1
    fsqrts 1, 1
    blr

coop_slot:                          # (r29/r30) -> f1, f2 = the buddy slot on the ground plane (C_TMP: cos, sin)
    lfs 3, {C_TMP}(29)
    lfs 4, {C_TMP} + 4(29)
    lfs 5, {T_SLOT_AHEAD}(29)
    lfs 6, {T_SLOT_LEFT}(29)
    lfs 1, 0x80(30)
    fmadds 1, 3, 5, 1               # x + c ahead - s left
    fnmsubs 1, 4, 6, 1
    lfs 2, 0x84(30)
    fmadds 2, 4, 5, 2               # y + s ahead + c left
    fmadds 2, 3, 6, 2
    blr

coop_offscreen:                     # (r29/r30) -> r3 = 1 when he has been off the screen for T_OFFSCREEN frames
    li 3, 0
    lfs 1, 0x80(30)                 # near Ratchet he counts as seen
    lfs 0, {C_POS}(29)
    fsubs 1, 1, 0
    lfs 2, 0x84(30)
    lfs 0, {C_POS} + 4(29)
    fsubs 2, 2, 0
    fmuls 1, 1, 1
    fmadds 1, 2, 2, 1
    fsqrts 1, 1
    lfs 0, {T_BLINK_NEAR}(29)
    fcmpu 0, 1, 0
    ble co_seen
    lis 9, {CAMERA_STATE_HA}
    addi 9, 9, {CAMERA_STATE_LO}
    lfs 1, {C_POS}(29)
    lfs 0, 0x140(9)
    fsubs 1, 1, 0
    lfs 2, {C_POS} + 4(29)
    lfs 0, 0x144(9)
    fsubs 2, 2, 0
    lfs 3, {C_POS} + 8(29)
    lfs 0, 0x148(9)
    fsubs 3, 3, 0
    fmuls 4, 1, 1
    fmadds 4, 2, 2, 4
    fmadds 4, 3, 3, 4
    fsqrts 4, 4                     # f4 = from the camera
    lfs 0, 0x350(9)
    fmuls 5, 1, 0
    lfs 0, 0x354(9)
    fmadds 5, 2, 0, 5
    lfs 0, 0x358(9)
    fmadds 5, 3, 0, 5               # f5 = along its view
    lfs 0, {T_SCREEN_COS}(29)
    fmuls 0, 0, 4
    fcmpu 0, 5, 0
    bge co_seen
    lwz 9, {C_OFFSCREEN}(29)
    addi 9, 9, 1
    stw 9, {C_OFFSCREEN}(29)
    lwz 10, {T_OFFSCREEN}(29)
    cmpw 9, 10
    bltlr
    li 3, 1
    blr
co_seen:
    li 9, 0
    stw 9, {C_OFFSCREEN}(29)
    blr

coop_blink:                         # (r29/r30) back to the slot at once
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    addi 3, 29, {C_POS}             # a crackle where he leaves and where he comes out
    lwz 4, {T_SEAT_BURST}(29)
    li 5, 8
    lfs 1, {T_HIT_BURST_R}(29)
    bl coop_burst
    bl coop_slot
    stfs 1, {C_RAY_TO}(29)          # the slot, unless a wall is between Ratchet and it: then over him
    stfs 2, {C_RAY_TO} + 4(29)
    lfs 0, {C_GROUND}(29)
    lfs 1, {C_HOVER}(29)
    fadds 0, 0, 1
    stfs 0, {C_RAY_TO} + 8(29)
    lfs 1, {T_COLL_UP}(29)
    fadds 0, 0, 1
    stfs 0, {C_RAY_TO} + 8(29)
    lfs 0, {T_ONE}(29)
    stfs 0, {C_RAY_TO} + 12(29)
    stfs 0, {C_RAY_FROM} + 12(29)
    lwz 9, 0x80(30)
    stw 9, {C_RAY_FROM}(29)
    lwz 9, 0x84(30)
    stw 9, {C_RAY_FROM} + 4(29)
    lfs 0, 0x88(30)
    lfs 1, {T_CAM_LOOK_UP}(29)
    fadds 0, 0, 1
    stfs 0, {C_RAY_FROM} + 8(29)
    lwz 6, {C_BODY}(29)
    bl coop_cam_ray
    lwz 9, {C_RAY_TO}(29)
    lwz 10, {C_RAY_TO} + 4(29)
    cmpwi 3, 0
    beq cbl_place
    lwz 9, 0x80(30)
    lwz 10, 0x84(30)
cbl_place:
    stw 9, {C_POS}(29)
    stw 10, {C_POS} + 4(29)
    lfs 0, {C_GROUND}(29)
    lfs 1, {C_HOVER}(29)
    fadds 0, 0, 1
    stfs 0, {C_POS} + 8(29)
    li 9, 0
    stw 9, {C_VEL}(29)
    stw 9, {C_VEL} + 4(29)
    stw 9, {C_VEL} + 8(29)
    stw 9, {C_OFFSCREEN}(29)
    stw 9, {C_BOOST}(29)
    lwz 9, 0x98(30)
    stw 9, {C_YAW}(29)
    addi 3, 29, {C_POS}             # a crackle where he leaves and where he comes out
    lwz 4, {T_SEAT_BURST}(29)
    li 5, 8
    lfs 1, {T_HIT_BURST_R}(29)
    bl coop_burst
    lwz 3, {T_SOUND_BLINK}(29)
    bl coop_sound
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_boost:                         # (r29) Cross: a short burst along the wish (or his heading)
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lwz 9, {C_BOOST_WAIT}(29)
    cmpwi 9, 0
    ble cb_ready
    addi 9, 9, -1
    stw 9, {C_BOOST_WAIT}(29)
cb_ready:
    lwz 9, {C_BOOST}(29)
    cmpwi 9, 0
    bgt cb_burn
    lwz 10, {C_BOOST_WAIT}(29)
    cmpwi 10, 0
    bgt cbo_out
    lwz 10, {C_BUTTONS_NEW}(29)
    andi. 10, 10, {BUTTON_CROSS}
    beq cbo_out
    lfs 1, {C_ENERGY}(29)
    lfs 2, {T_COST_BOOST}(29)
    fcmpu 0, 1, 2
    blt cbo_out
    fsubs 1, 1, 2
    stfs 1, {C_ENERGY}(29)
    lwz 9, {T_BOOST_WAIT}(29)
    stw 9, {C_BOOST_WAIT}(29)
    lwz 9, {T_BOOST_FRAMES}(29)
    stw 9, {C_BOOST}(29)
    lfs 1, {C_WISH}(29)             # its way: the wish's, else his heading
    lfs 2, {C_WISH} + 4(29)
    fmuls 3, 1, 1
    fmadds 3, 2, 2, 3
    fsqrts 3, 3
    lfs 0, {T_SMALL}(29)
    fcmpu 0, 3, 0
    ble cb_heading
    fdivs 1, 1, 3
    fdivs 2, 2, 3
    stfs 1, {C_BOOST_DIR}(29)
    stfs 2, {C_BOOST_DIR} + 4(29)
    b cb_go
cb_heading:
    lfs 1, {C_YAW}(29)
    bl {COS}
    stfs 1, {C_BOOST_DIR}(29)
    lfs 1, {C_YAW}(29)
    bl {SIN}
    stfs 1, {C_BOOST_DIR} + 4(29)
cb_go:
    lwz 3, {T_SOUND_BLINK}(29)
    bl coop_sound
    lwz 9, {C_BOOST}(29)
cb_burn:
    addi 9, 9, -1
    stw 9, {C_BOOST}(29)
    lfs 0, {T_BOOST_SPEED}(29)
    lfs 1, {C_BOOST_DIR}(29)
    fmuls 1, 1, 0
    stfs 1, {C_VEL}(29)
    lfs 1, {C_BOOST_DIR} + 4(29)
    fmuls 1, 1, 0
    stfs 1, {C_VEL} + 4(29)
cbo_out:
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_turn:                          # (r29/r30) heading to the velocity (Ratchet's at rest), roll and pitch
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    lfs 1, {C_VEL} + 4(29)
    lfs 2, {C_VEL}(29)
    fmuls 3, 1, 1
    fmadds 3, 2, 2, 3
    fsqrts 3, 3
    stfs 3, {C_TMP} + 8(29)         # the speed
    lfs 0, {T_HALF}(29)
    fcmpu 0, 3, 0
    lfs 1, 0x98(30)
    blt ctn_aim
    lfs 1, {C_VEL} + 4(29)
    lfs 2, {C_VEL}(29)
    bl coop_atan2
ctn_aim:
    lwz 9, {C_TARGET}(29)           # zapping: to the target
    cmpwi 9, 0
    beq ctn_turn
    lwz 10, {C_ZAP}(29)
    cmpwi 10, 0
    beq ctn_turn
    lfs 1, 0x14(9)
    lfs 0, {C_POS} + 4(29)
    fsubs 1, 1, 0
    lfs 2, 0x10(9)
    lfs 0, {C_POS}(29)
    fsubs 2, 2, 0
    bl coop_atan2
ctn_turn:
    lfs 2, {C_YAW}(29)
    bl {ANGLE_DIFF}
    lfs 2, {C_YAW}(29)
    lfs 0, {T_TURN}(29)
    fmadds 1, 1, 0, 2
    lfs 2, {T_ZERO}(29)
    bl {ANGLE_DIFF}                 # kept within -pi..pi
    stfs 1, {C_YAW}(29)
    bl {SIN}                        # sideways speed: along his left (-sin, cos)
    stfs 1, {C_TMP} + 0xc(29)
    stfs 1, {C_FACE} + 4(29)
    lfs 1, {C_YAW}(29)
    bl {COS}
    stfs 1, {C_FACE}(29)
    lfs 2, {C_VEL} + 4(29)
    fmuls 1, 1, 2
    lfs 2, {C_VEL}(29)
    lfs 0, {C_TMP} + 0xc(29)
    fnmsubs 1, 0, 2, 1              # f1 = sideways speed
    lfs 0, {T_FLY_SPEED}(29)
    fdivs 1, 1, 0
    lfs 0, {T_ROLL_MAX}(29)
    fmuls 1, 1, 0
    fneg 1, 1
    fabs 2, 0
    fcmpu 0, 1, 2
    ble ctn_roll_low
    fmr 1, 2
ctn_roll_low:
    fneg 2, 2
    fcmpu 0, 1, 2
    bge ctn_roll
    fmr 1, 2
ctn_roll:
    lfs 0, {C_ROLL}(29)
    fsubs 1, 1, 0
    lfs 2, {T_TURN}(29)
    fmadds 1, 1, 2, 0
    stfs 1, {C_ROLL}(29)
    lfs 1, {C_TMP} + 8(29)          # pitch by speed
    lfs 0, {T_FLY_SPEED}(29)
    fdivs 1, 1, 0
    lfs 0, {T_ONE}(29)
    fcmpu 0, 1, 0
    ble ctn_pitch
    fmr 1, 0
ctn_pitch:
    lfs 0, {T_PITCH_MAX}(29)
    fmuls 1, 1, 0
    lfs 0, {C_PITCH}(29)
    fsubs 1, 1, 0
    lfs 2, {T_TURN}(29)
    fmadds 1, 1, 2, 0
    stfs 1, {C_PITCH}(29)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_atan2:                         # (f1 = y, f2 = x; r29) -> f1 = atan2(y, x), within ~0.005 rad
    fabs 3, 1
    fabs 4, 2
    fmr 5, 3                        # f5 = the smaller of |y|, |x|, f6 the larger
    fmr 6, 4
    fcmpu 0, 3, 4
    ble cat_order
    fmr 5, 4
    fmr 6, 3
cat_order:
    lfs 0, {T_ZERO}(29)
    fcmpu 0, 6, 0
    beq cat_zero
    fdivs 5, 5, 6                   # a + a s (A s^2 + B s + C), s = a^2
    fmuls 6, 5, 5
    lfs 0, {T_ATAN_A}(29)
    lfs 7, {T_ATAN_B}(29)
    fmadds 0, 0, 6, 7
    lfs 7, {T_ATAN_C}(29)
    fmadds 0, 0, 6, 7
    fmuls 0, 0, 6
    fmadds 5, 0, 5, 5
    fcmpu 0, 3, 4
    ble cat_x
    lfs 0, {T_HALF_PI}(29)
    fsubs 5, 0, 5
cat_x:
    lfs 0, {T_ZERO}(29)
    fcmpu 0, 2, 0
    bge cat_y
    lfs 0, {T_PI}(29)
    fsubs 5, 0, 5
cat_y:
    lfs 0, {T_ZERO}(29)
    fcmpu 0, 1, 0
    bge cat_out
    fneg 5, 5
cat_out:
    fmr 1, 5
    blr
cat_zero:
    fmr 1, 0
    blr
coop_pack:                          # (set_state: r28 the state asked for, r27 hero; r0, r3 free) no pack moves while he is out
    lis 3, {COOP_HA}
    addi 3, 3, {COOP_LO}
    lwz 0, {T_PACK_GATE}(3)
    cmpwi 0, 0
    beq cpk_game
    lwz 0, {C_MODE}(3)
    cmpwi 0, {MODE_DOCKED}
    beq cpk_game
    lbz 0, {HERO_KIND}(27)
    cmpwi 0, 0
    bne cpk_game
    cmpwi 28, 0x8
    beq cpk_refuse
    cmpwi 28, 0xa
    beq cpk_plain
    cmpwi 28, 0x10
    beq cpk_plain
    cmpwi 28, 0xf
    beq cpk_plain
    cmpwi 28, 0xd
    beq cpk_plain
    b cpk_game
cpk_plain:
    li 28, {PLAIN_JUMP}
    b cpk_game
cpk_refuse:
    lis 3, {PACK_REFUSE_HA}         # (r3, not r0: addi takes 0 there for the number 0)
    addi 3, 3, {PACK_REFUSE_LO}
    mtlr 3
    blr
cpk_game:
    cmpwi 5, 0x14                   # the displaced instruction
    blr
"""
