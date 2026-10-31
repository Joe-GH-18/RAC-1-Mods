"""The mini Giant Clank: Player 2's own Giant Clank while Golden Clank's mode is called with
Player 2 in.

The user (2026-10-26): "if its golden clank, let the second player control a mini version of
giant clank instead of just hitting"; their picks: he walks and jumps, has Giant Clank's moves,
Ratchet goes back to normal, half the size of the giant legs.

Golden Clank's switch (L3 + R3, mods/goldenclank.py gc_mini_switch) with Player 2 in installs
Giant Clank's model and sets GC_MINI instead of turning Ratchet into Golden Clank; its model is
GC_MODEL. Then (coop_mini_check) Clank docks and this moby walks beside Ratchet instead: created
as a backpack Clank (CARRIER_CLASS) with that model, at T_MINI_SCALE (the legs are 0.25), gold as
Golden Clank's parts are (Ratchet's light times T_MINI_TINT_*, at the HUD hook).

He walks camera-relative at T_MINI_SPEED, jumps with Cross (T_MINI_JUMP against T_MINI_GRAVITY)
and, Cross held while falling, hovers (T_MINI_HOVER_FALL, T_MINI_HOVER_FRAMES a jump; 0 now: Quartu's
Giant Clank does not hover). The jump is his, scaled: on Quartu (set_state 0x5e at 0xbaf78) 4.2 high
against 30 units/s^2 at scale 0.75, animation 4 (0xbbae4; 6 is his hurt state 0x5d's). Floors and
walls come from the game's ray MINI_RAY (the hero's ground probe 0x7e5e8 calls it: r3 from, r4
to, r5 2, r6 a moby left out, r7 0 -> r3 not 0 on a hit, the place at RAY_HIT): down from
T_MINI_PROBE_UP above him to T_MINI_PROBE_DOWN below for the floor, and ahead of him at
T_MINI_WALL_UP for walls (a hit stops him). Too far from Ratchet (T_MINI_LEASH, or T_MINI_DROP
below him) he is put back beside him.

His moves, with Giant Clank's animations and Golden Clank's MOVE_TABLE timing: Square the punch
(left and right by turns, a lunge, a hit at its action frame: T_MINI_PUNCH_*), Circle the missile
volley (repeats while held); he stands in them. The golden bomb is gone (the user). The missiles
and the bomb are Golden Clank's: COOP_FIRE asks it to fire them from his moby (COOP_MINI_MOBY),
his forearms' joints and his heading, at half the giant's size.
"""
from ..game import *  # noqa: F401,F403

MINI_RAY = 0x57820             # (r3 from vec4, r4 to vec4, r5 2, r6 moby left out, r7 0) -> r3 not 0 on a hit
RAY_HIT = 0xA10960             # the hit's place (vec4)
MINI_JUMP_BUTTON, MINI_PUNCH_BUTTON, MINI_MISSILE_BUTTON, MINI_BOMB_BUTTON = 0x40, 0x80, 0x20, 0x10
MOVE_PUNCH, MOVE_MISSILES, MOVE_BOMB = 1, 2, 3
HERO_ON_GROUND = 0x300         # u32 frames on the ground, 0 in the air
P1_CROSS = 0x40
# Ratchet's mobys drawn with him (Golden Clank's ATTACHED: two at the start of each of seven
# entries of 0x50 bytes from hero +0x1090, the pack part +0x118c; and the pack and backpack Clank)
RIDE_ATTACHED, RIDE_ATTACHED_SIZE, RIDE_ATTACHED_COUNT = 0x1090, 0x50, 7
RIDE_SINGLE_0, RIDE_SINGLE_1, RIDE_SINGLE_2 = 0x118C, 0x1180, 0x1184
# Quartu's rider: Ratchet's animation 129, his pose on Giant Clank's back (seen there: the game keeps
# his moby, hero +0xa88, on the back with moby +0x53 = 0x81); only levels 0, 15 and 18 have it, so
# the mod carries level 15's (RIDER_ANIM) and puts it in the empty slot of his model's table (+0x48)
RIDER_ANIM_SLOT = 129
RIDER_ANIM_LEVEL = 15
RIDER_ANIM_TABLE = 0x48 + 4 * RIDER_ANIM_SLOT

CODE = r"""
coop_mini_check:                    # (r29/r30/r31) -> r3 = 1 when the mini Giant Clank had this frame
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lwz 9, {GC_MINI}(31)            # wanted: Golden Clank's switch with Player 2 in, and nothing in the way
    cmpwi 9, 0
    beq cmc_not
    lwz 9, {C_DRIVER}(29)
    cmpwi 9, {DRIVER_P2}
    bne cmc_not
    bl coop_suspended
    cmpwi 3, 0
    bne cmc_not
    lwz 9, {C_MODE}(29)
    cmpwi 9, {MODE_MINI}
    beq cmc_go
    bl coop_mini_enter
cmc_go:
    bl coop_mini
    li 3, 1
    b cmc_out
cmc_not:
    li 3, 0
    lwz 9, {C_MODE}(29)
    cmpwi 9, {MODE_MINI}
    bne cmc_out
    bl coop_mini_leave
    li 3, 1
cmc_out:
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_mini_spawn:                    # (r29/r31) his moby with Giant Clank's model -> r3 (0 = none yet)
    lwz 9, {GC_MODEL}(31)
    cmpwi 9, 0
    li 3, 0
    beqlr
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    li 3, {CARRIER_CLASS}
    bl {SPAWN}
    cmpwi 3, 0
    beq cms_out
    stw 3, {C_MINI}(29)
    lwz 4, {GC_MODEL}(31)
    stw 4, 0x24(3)
    li 4, 0xff                      # in the moby loop at any distance, drawn
    stb 4, 0x30(3)
    li 4, 1
    stb 4, 0x31(3)
    li 4, {DRAW_DISTANCE}
    sth 4, 0x32(3)
    lhz 4, 0x34(3)
    rlwinm 4, 4, 0, {NOT_SKIP_MB}, {NOT_SKIP_ME}
    sth 4, 0x34(3)
    lfs 0, {T_MINI_SCALE}(29)
    stfs 0, 0x2c(3)
    li 4, -1
    stw 4, {C_MINI_ANIM}(29)
cms_out:
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_mini_beside:                   # (r29/r30) his place beside Ratchet (to his left), standing
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lfs 1, 0x98(30)
    bl {COS}
    stfs 1, {C_TMP}(29)
    lfs 1, 0x98(30)
    bl {SIN}
    lfs 0, {T_MINI_SIDE}(29)
    lfs 2, 0x80(30)
    fnmsubs 2, 1, 0, 2              # x - sin side
    stfs 2, {C_MINI_POS}(29)
    lfs 1, {C_TMP}(29)
    lfs 2, 0x84(30)
    fmadds 2, 1, 0, 2               # y + cos side
    stfs 2, {C_MINI_POS} + 4(29)
    lwz 9, 0x88(30)
    stw 9, {C_MINI_POS} + 8(29)
    lfs 0, {T_ONE}(29)
    stfs 0, {C_MINI_POS} + 12(29)
    li 9, 0
    stw 9, {C_MINI_VEL}(29)
    stw 9, {C_MINI_VEL} + 4(29)
    stw 9, {C_MINI_VEL} + 8(29)
    stw 9, {C_MINI_AIR}(29)
    lwz 9, 0x98(30)
    stw 9, {C_MINI_YAW}(29)
    addi 3, 29, {C_MINI_POS}        # a crackle where he appears
    lwz 4, {T_SEAT_BURST}(29)
    li 5, 10
    lfs 1, {T_SEAT_BURST_R}(29)
    bl coop_burst
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_mini_enter:                    # (r29/r30/r31) Clank docks, the mini Giant Clank appears beside Ratchet
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lwz 9, {C_MODE}(29)
    cmpwi 9, {MODE_DOCKED}
    beq cme_place
    bl coop_dock_now
cme_place:
    bl coop_mini_beside
    li 9, 0
    stw 9, {C_MINI_MOVE}(29)
    stw 9, {C_MINI_HOVER}(29)
    stw 9, {C_MINI}(29)
    li 9, {MODE_MINI}
    stw 9, {C_MODE}(29)
    bl coop_mini_spawn
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_mini_leave:                    # (r29/r31) his moby away, Clank on Ratchet's back
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    bl coop_ride_restore
    bl coop_rider_delete
    lwz 3, {C_MINI}(29)
    cmpwi 3, 0
    beq cml_none
    lwz 4, 0x24(3)                  # (still his: not a moby the game has taken again)
    lwz 5, {GC_MODEL}(31)
    cmpw 4, 5
    bne cml_none
    bl {MOBY_DELETE}
cml_none:
    li 9, 0
    stw 9, {C_RIDE}(29)
    stw 9, {C_MINI}(29)
    stw 9, {COOP_MINI_MOBY}(31)
    stw 9, {C_MINI_MOVE}(29)
    stw 9, {C_TIMER}(29)
    li 9, {MODE_DOCKED}
    stw 9, {C_MODE}(29)
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_mini:                          # (r29/r30/r31) a frame of the mini Giant Clank
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lwz 3, {C_MINI}(29)             # his moby, made again if it went
    cmpwi 3, 0
    beq cm_spawn
    lwz 4, 0x24(3)
    lwz 5, {GC_MODEL}(31)
    cmpw 4, 5
    beq cm_have
cm_spawn:
    li 9, 0
    stw 9, {C_MINI}(29)
    bl coop_mini_spawn
cm_have:
    lwz 9, {C_MINI}(29)
    stw 9, {COOP_MINI_MOBY}(31)
    lwz 9, {C_MINI_BOMB_WAIT}(29)
    cmpwi 9, 0
    ble cm_moves
    addi 9, 9, -1
    stw 9, {C_MINI_BOMB_WAIT}(29)
cm_moves:
    bl coop_mini_moves
    bl coop_mini_walk
    bl coop_mini_body
    bl coop_ride_restore            # (Ratchet's update sees his mobys as they were)
    bl coop_mini_ride
    bl coop_rider_tick
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_mini_anim:                     # (r3 an animation of his; r29) set when it changes
    lwz 4, {C_MINI_ANIM}(29)
    cmpw 4, 3
    beqlr
    lwz 5, {C_MINI}(29)
    cmpwi 5, 0
    beqlr
    stw 3, {C_MINI_ANIM}(29)
    mr 4, 3
    mr 3, 5
    li 5, 0
    lwz 6, {T_MINI_BLEND}(29)
    b {MOBY_SET_ANIM}

coop_mini_moves:                    # (r29/r30/r31) Square the punch, Circle the missiles, Triangle the bomb
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lwz 9, {C_MINI_MOVE}(29)
    cmpwi 9, 0
    bne cmm_going
    lwz 10, {C_BUTTONS_NEW}(29)
    andi. 11, 10, {MINI_PUNCH_BUTTON}
    li 9, {MOVE_PUNCH}
    bne cmm_start
    andi. 11, 10, {MINI_MISSILE_BUTTON}
    li 9, {MOVE_MISSILES}
    bne cmm_start
    b cmm_out                       # (no golden bomb: the user, "remove the golden bomb")
cmm_start:
    stw 9, {C_MINI_MOVE}(29)
    li 10, 0
    stw 10, {C_MINI_T}(29)
    stw 10, {C_MINI_HIT}(29)
    li 10, -1                       # its animation from its start
    stw 10, {C_MINI_ANIM}(29)
    lwz 3, {T_MINI_BOMB_ANIM}(29)
    cmpwi 9, {MOVE_MISSILES}
    bne cmm_punch_anim
    lwz 3, {T_MINI_MISSILE_ANIM}(29)
cmm_punch_anim:
    cmpwi 9, {MOVE_PUNCH}
    bne cmm_anim
    lwz 10, {C_MINI_PUNCHES}(29)    # the left fist, then the right
    addi 11, 10, 1
    stw 11, {C_MINI_PUNCHES}(29)
    andi. 10, 10, 1
    lwz 3, {T_MINI_PUNCH_ANIM}(29)
    add 3, 3, 10
cmm_anim:
    bl coop_mini_anim
cmm_going:
    lwz 9, {C_MINI_T}(29)
    addi 9, 9, 1
    stw 9, {C_MINI_T}(29)
    lwz 10, {C_MINI_MOVE}(29)
    cmpwi 10, {MOVE_PUNCH}
    bne cmm_missiles
    lwz 11, {T_MINI_PUNCH_ACTION}(29)
    cmpw 9, 11
    bne cmm_punch_end
    bl coop_mini_punch_hit
    lwz 9, {C_MINI_T}(29)
cmm_punch_end:
    lwz 11, {T_MINI_PUNCH_FRAMES}(29)
    cmpw 9, 11
    blt cmm_out
    b cmm_done
cmm_missiles:
    cmpwi 10, {MOVE_MISSILES}
    bne cmm_bomb
    lwz 11, {T_MINI_MISSILE_ACTION}(29)
    cmpw 9, 11
    bne cmm_volley_end
    lwz 12, {COOP_FIRE}(31)         # Golden Clank fires them
    ori 12, 12, 1
    stw 12, {COOP_FIRE}(31)
cmm_volley_end:
    lwz 11, {T_MINI_MISSILE_FRAMES}(29)
    cmpw 9, 11
    blt cmm_out
    lwz 12, {C_BUTTONS}(29)         # Circle still held: another volley
    andi. 12, 12, {MINI_MISSILE_BUTTON}
    beq cmm_done
    li 9, 0
    stw 9, {C_MINI_T}(29)
    li 9, -1
    stw 9, {C_MINI_ANIM}(29)
    lwz 3, {T_MINI_MISSILE_ANIM}(29)
    bl coop_mini_anim
    b cmm_out
cmm_bomb:
    lwz 11, {T_MINI_BOMB_ACTION}(29)
    cmpw 9, 11
    bne cmm_bomb_end
    lwz 12, {COOP_FIRE}(31)
    ori 12, 12, 2
    stw 12, {COOP_FIRE}(31)
cmm_bomb_end:
    lwz 11, {T_MINI_BOMB_FRAMES}(29)
    cmpw 9, 11
    blt cmm_out
cmm_done:
    li 9, 0
    stw 9, {C_MINI_MOVE}(29)
    li 9, -1
    stw 9, {C_MINI_ANIM}(29)
cmm_out:
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_mini_punch_hit:                # (r29/r30) the punch strikes: crates, the nearest enemy, a star of lightning, the camera
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 28, 0x70(1)
    lfs 1, {C_MINI_YAW}(29)         # the fist: ahead of him and up
    bl {COS}
    lfs 0, {T_MINI_PUNCH_AHEAD}(29)
    lfs 2, {C_MINI_POS}(29)
    fmadds 2, 1, 0, 2
    stfs 2, {C_FIST}(29)
    lfs 1, {C_MINI_YAW}(29)
    bl {SIN}
    lfs 0, {T_MINI_PUNCH_AHEAD}(29)
    lfs 2, {C_MINI_POS} + 4(29)
    fmadds 2, 1, 0, 2
    stfs 2, {C_FIST} + 4(29)
    lfs 0, {C_MINI_POS} + 8(29)
    lfs 1, {T_MINI_PUNCH_UP}(29)
    fadds 0, 0, 1
    stfs 0, {C_FIST} + 8(29)
    lfs 0, {T_ONE}(29)
    stfs 0, {C_FIST} + 12(29)
    addi 3, 29, {C_FIST}
    lfs 1, {T_MINI_PUNCH_RADIUS}(29)
    bl {CRATE_SWEEP}
    addi 3, 29, {C_FIST}
    lfs 1, {T_MINI_PUNCH_RADIUS}(29)
    lfs 2, {T_RAM_REACH_Z}(29)
    bl coop_nearest_flat
    mr. 28, 3
    beq cmp_out
    lfs 1, {T_MINI_PUNCH_DAMAGE}(29)
    lwz 4, {T_PUNCH_FLAGS}(29)
    li 5, 0
    bl coop_hit
    addi 3, 29, {C_FIST}
    lwz 4, {T_RAM_BURST}(29)
    lwz 5, {T_RAM_BURST_FRAMES}(29)
    lfs 1, {T_RAM_BURST_R}(29)
    bl coop_burst
    lfs 1, {T_KICK}(29)
    lwz 3, {T_KICK_FRAMES}(29)
    bl coop_shake
cmp_out:
    ld 28, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_mini_ray:                      # (r29) the game's ray C_RAY_FROM -> C_RAY_TO, him left out -> r3 not 0 on a hit (RAY_HIT)
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    addi 3, 29, {C_RAY_FROM}
    addi 4, 29, {C_RAY_TO}
    li 5, 2
    lwz 6, {C_MINI}(29)
    li 7, 0
    bl {MINI_RAY}
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_mini_walk:                     # (r29/r30) the stick, a jump or the hover, walls, the floor, the leash, his heading
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0xa0(1)
    stfd 31, 0x70(1)
    stfd 30, 0x78(1)
    lfs 7, {T_ZERO}(29)             # f7, f8 = the wish: nothing while he punches or throws
    fmr 8, 7
    lwz 9, {C_MINI_MOVE}(29)
    cmpwi 9, {MOVE_PUNCH}
    beq cmw_grip
    cmpwi 9, {MOVE_BOMB}
    beq cmw_grip
    lfs 1, {C_STICK}(29)            # the stick, relative to the camera (as his flight takes it)
    lfs 2, {C_STICK} + 4(29)
    fmuls 3, 1, 1
    fmadds 3, 2, 2, 3
    fsqrts 3, 3
    lfs 0, {T_STICK_DEAD}(29)
    fcmpu 0, 3, 0
    blt cmw_grip
    lis 9, {CAMERA_STATE_HA}
    addi 9, 9, {CAMERA_STATE_LO}
    lfs 4, 0x350(9)
    lfs 5, 0x354(9)
    fmuls 6, 4, 4
    fmadds 6, 5, 5, 6
    fsqrts 6, 6
    lfs 0, {T_SMALL}(29)
    fcmpu 0, 6, 0
    blt cmw_grip
    fdivs 4, 4, 6
    fdivs 5, 5, 6
    fmuls 7, 4, 2
    fmadds 7, 5, 1, 7
    fmuls 8, 5, 2
    fnmsubs 8, 4, 1, 8
    lfs 0, {T_ONE}(29)
    fcmpu 0, 3, 0
    ble cmw_speed
    fdivs 7, 7, 3
    fdivs 8, 8, 3
cmw_speed:
    lfs 0, {T_MINI_SPEED}(29)
    fmuls 7, 7, 0
    fmuls 8, 8, 0
cmw_grip:
    lwz 9, {C_MINI_MOVE}(29)        # in a move he stands, as Giant Clank does (his moves set the target
    cmpwi 9, 0                      # speed 0; the user: "no moving when missiles"); the punch's lunge below
    beq cmw_wish
    lfs 7, {T_ZERO}(29)
    fmr 8, 7
cmw_wish:
    stfs 7, {C_MINI_WISH}(29)
    stfs 8, {C_MINI_WISH} + 4(29)
    lfs 0, {T_MINI_GRIP}(29)        # the velocity a part of the way to it
    lfs 1, {C_MINI_VEL}(29)
    fsubs 2, 7, 1
    fmadds 1, 2, 0, 1
    stfs 1, {C_MINI_VEL}(29)
    lfs 1, {C_MINI_VEL} + 4(29)
    fsubs 2, 8, 1
    fmadds 1, 2, 0, 1
    stfs 1, {C_MINI_VEL} + 4(29)
    lwz 9, {C_MINI_MOVE}(29)        # the punch's lunge
    cmpwi 9, {MOVE_PUNCH}
    bne cmw_jump
    lwz 9, {C_MINI_T}(29)
    lwz 10, {T_MINI_LUNGE_FROM}(29)
    cmpw 9, 10
    blt cmw_jump
    lwz 10, {T_MINI_LUNGE_TO}(29)
    cmpw 9, 10
    bge cmw_jump
    lfs 1, {C_MINI_YAW}(29)
    bl {COS}
    lfs 0, {T_MINI_LUNGE}(29)
    fmuls 1, 1, 0
    stfs 1, {C_MINI_VEL}(29)
    lfs 1, {C_MINI_YAW}(29)
    bl {SIN}
    lfs 0, {T_MINI_LUNGE}(29)
    fmuls 1, 1, 0
    stfs 1, {C_MINI_VEL} + 4(29)
cmw_jump:
    lwz 9, {C_MINI_AIR}(29)         # on the ground: Cross jumps
    cmpwi 9, 0
    bne cmw_air
    lwz 10, {C_BUTTONS_NEW}(29)
    andi. 10, 10, {MINI_JUMP_BUTTON}
    beq cmw_walls
    lfs 0, {T_MINI_JUMP}(29)
    stfs 0, {C_MINI_VEL} + 8(29)
    li 9, 1
    stw 9, {C_MINI_AIR}(29)
    lwz 9, {T_MINI_HOVER_FRAMES}(29)
    stw 9, {C_MINI_HOVER}(29)
    b cmw_walls
cmw_air:                            # in the air: falling, or hovering while Cross is held on the way down
    lfs 1, {C_MINI_VEL} + 8(29)
    lfs 0, {T_ZERO}(29)
    fcmpu 0, 1, 0
    bgt cmw_fall
    lwz 10, {C_BUTTONS}(29)
    andi. 10, 10, {MINI_JUMP_BUTTON}
    beq cmw_fall
    lwz 10, {C_MINI_HOVER}(29)
    cmpwi 10, 0
    ble cmw_fall
    addi 10, 10, -1
    stw 10, {C_MINI_HOVER}(29)
    lfs 1, {T_MINI_HOVER_FALL}(29)
    fneg 1, 1
    stfs 1, {C_MINI_VEL} + 8(29)
    b cmw_walls
cmw_fall:
    lfs 0, {T_MINI_GRAVITY}(29)
    lfs 2, {T_DT}(29)
    fnmsubs 1, 0, 2, 1
    stfs 1, {C_MINI_VEL} + 8(29)
cmw_walls:                          # a wall ahead stops him
    lfs 1, {C_MINI_VEL}(29)
    lfs 2, {C_MINI_VEL} + 4(29)
    fmuls 3, 1, 1
    fmadds 3, 2, 2, 3
    fsqrts 31, 3                    # f31 = his speed
    lfs 0, {T_SMALL}(29)
    fcmpu 0, 31, 0
    ble cmw_move
    lfs 0, {T_DT}(29)               # how far: this frame's way and T_MINI_WALL_REACH
    fmuls 4, 31, 0
    lfs 0, {T_MINI_WALL_REACH}(29)
    fadds 4, 4, 0
    fdivs 4, 4, 31
    lfs 0, {C_MINI_POS}(29)
    stfs 0, {C_RAY_FROM}(29)
    fmadds 0, 1, 4, 0
    stfs 0, {C_RAY_TO}(29)
    lfs 0, {C_MINI_POS} + 4(29)
    stfs 0, {C_RAY_FROM} + 4(29)
    fmadds 0, 2, 4, 0
    stfs 0, {C_RAY_TO} + 4(29)
    lfs 0, {C_MINI_POS} + 8(29)
    lfs 1, {T_MINI_WALL_UP}(29)
    fadds 0, 0, 1
    stfs 0, {C_RAY_FROM} + 8(29)
    stfs 0, {C_RAY_TO} + 8(29)
    lfs 0, {T_ONE}(29)
    stfs 0, {C_RAY_FROM} + 12(29)
    stfs 0, {C_RAY_TO} + 12(29)
    bl coop_mini_ray
    cmpwi 3, 0
    beq cmw_move
    li 9, 0
    stw 9, {C_MINI_VEL}(29)
    stw 9, {C_MINI_VEL} + 4(29)
    lfs 31, {T_ZERO}(29)
cmw_move:
    lfs 0, {T_DT}(29)               # the place
    li 7, 0
cmw_axis:
    addi 8, 7, {C_MINI_POS}
    lfsx 1, 29, 8
    addi 9, 7, {C_MINI_VEL}
    lfsx 2, 29, 9
    fmadds 1, 2, 0, 1
    stfsx 1, 29, 8
    addi 7, 7, 4
    cmpwi 7, 12
    blt cmw_axis
    lwz 9, {C_MINI_POS}(29)         # the floor: a ray down through him
    stw 9, {C_RAY_FROM}(29)
    stw 9, {C_RAY_TO}(29)
    lwz 9, {C_MINI_POS} + 4(29)
    stw 9, {C_RAY_FROM} + 4(29)
    stw 9, {C_RAY_TO} + 4(29)
    lfs 0, {C_MINI_POS} + 8(29)
    lfs 1, {T_MINI_PROBE_UP}(29)
    fadds 1, 0, 1
    stfs 1, {C_RAY_FROM} + 8(29)
    lfs 1, {T_MINI_PROBE_DOWN}(29)
    fsubs 1, 0, 1
    stfs 1, {C_RAY_TO} + 8(29)
    lfs 0, {T_ONE}(29)
    stfs 0, {C_RAY_FROM} + 12(29)
    stfs 0, {C_RAY_TO} + 12(29)
    bl coop_mini_ray
    cmpwi 3, 0
    beq cmw_up
    lis 9, {RAY_HIT_HA}
    addi 9, 9, {RAY_HIT_LO}
    lfs 1, 8(9)                     # f1 = the floor's height
    lfs 2, {C_MINI_POS} + 8(29)
    lfs 3, {C_MINI_VEL} + 8(29)
    lfs 0, {T_ZERO}(29)
    fcmpu 0, 3, 0                   # rising: in the air
    bgt cmw_up
    fsubs 4, 2, 1                   # f4 = how far above it
    lwz 9, {C_MINI_AIR}(29)         # walking on: down steps and slopes up to 0.4
    cmpwi 9, 0
    bne cmw_land
    lfs 0, {T_MINI_WALL_UP}(29)
    fadds 0, 0, 0
    fcmpu 0, 4, 0
    blt cmw_ground
cmw_land:
    lfs 0, {T_SMALL}(29)            # falling: landed when at or under it
    fadds 0, 0, 0
    fcmpu 0, 4, 0
    bgt cmw_up
cmw_ground:
    stfs 1, {C_MINI_POS} + 8(29)
    lfs 0, {T_ZERO}(29)
    stfs 0, {C_MINI_VEL} + 8(29)
    li 9, 0
    stw 9, {C_MINI_AIR}(29)
    b cmw_leash
cmw_up:
    lwz 9, {C_MINI_AIR}(29)
    addi 9, 9, 1
    stw 9, {C_MINI_AIR}(29)
cmw_leash:                          # too far from Ratchet, or fallen far below him: back beside him
    lfs 1, 0x80(30)
    lfs 0, {C_MINI_POS}(29)
    fsubs 1, 1, 0
    lfs 2, 0x84(30)
    lfs 0, {C_MINI_POS} + 4(29)
    fsubs 2, 2, 0
    fmuls 3, 1, 1
    fmadds 3, 2, 2, 3
    fsqrts 3, 3
    lfs 0, {T_MINI_LEASH}(29)
    fcmpu 0, 3, 0
    bgt cmw_back
    lfs 1, 0x88(30)
    lfs 0, {T_MINI_DROP}(29)
    fsubs 1, 1, 0
    lfs 2, {C_MINI_POS} + 8(29)
    fcmpu 0, 2, 1
    bge cmw_turn
cmw_back:
    bl coop_mini_beside
    b cmw_out
cmw_turn:                           # his heading to his way (not in a move)
    lwz 9, {C_MINI_MOVE}(29)
    cmpwi 9, 0
    bne cmw_out
    lfs 0, {T_HALF}(29)
    fcmpu 0, 31, 0
    blt cmw_out
    lfs 1, {C_MINI_VEL} + 4(29)
    lfs 2, {C_MINI_VEL}(29)
    bl coop_atan2
    lfs 2, {C_MINI_YAW}(29)
    bl {ANGLE_DIFF}
    lfs 0, {T_MINI_TURN}(29)
    lfs 2, {C_MINI_YAW}(29)
    fmadds 1, 1, 0, 2
    lfs 2, {T_ZERO}(29)
    bl {ANGLE_DIFF}
    stfs 1, {C_MINI_YAW}(29)
cmw_out:
    lfd 30, 0x78(1)
    lfd 31, 0x70(1)
    addi 1, 1, 0xa0
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_mini_body:                     # (r29) his moby at his place, turned, scaled; idle, walk or jump unless in a move
    lwz 3, {C_MINI}(29)
    cmpwi 3, 0
    beqlr
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 28, 0x70(1)
    mr 28, 3
    lwz 9, {C_MINI_POS}(29)
    stw 9, 0x10(28)
    lwz 9, {C_MINI_POS} + 4(29)
    stw 9, 0x14(28)
    lwz 9, {C_MINI_POS} + 8(29)
    stw 9, 0x18(28)
    li 9, 0
    stw 9, 0x40(28)
    stw 9, 0x44(28)
    lfs 1, {C_MINI_YAW}(29)
    lfs 0, {T_MINI_YAW_OFFSET}(29)
    fadds 1, 1, 0
    lfs 2, {T_ZERO}(29)
    bl {ANGLE_DIFF}
    stfs 1, 0x48(28)
    lfs 0, {T_MINI_SCALE}(29)
    stfs 0, 0x2c(28)
    lwz 9, {C_MINI_MOVE}(29)        # in a move: its animation runs
    cmpwi 9, 0
    bne cmb_out
    lwz 9, {C_MINI_AIR}(29)
    cmpwi 9, 3
    lwz 3, {T_MINI_JUMP_ANIM}(29)
    bgt cmb_anim
    lfs 1, {C_MINI_VEL}(29)
    lfs 2, {C_MINI_VEL} + 4(29)
    fmuls 3, 1, 1
    fmadds 3, 2, 2, 3
    fsqrts 3, 3
    lfs 0, {T_HALF}(29)
    lwz 3, {T_MINI_IDLE_ANIM}(29)
    fcmpu 0, 3, 0
    blt cmb_anim
    lfs 0, {T_MINI_WALK_RATE}(29)   # walking, at his speed
    fmuls 3, 3, 0
    stfs 3, 0x58(28)
    lwz 3, {T_MINI_WALK_ANIM}(29)
cmb_anim:
    bl coop_mini_anim
cmb_out:
    ld 28, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_mini_light:                    # (r29/r30, at the HUD hook) his gold: Ratchet's light times T_MINI_TINT_* (256ths)
    lwz 3, {C_MINI}(29)
    cmpwi 3, 0
    beqlr
    lwz 5, 0x2080(30)
    cmpwi 5, 0
    beqlr
    lwz 6, 0x38(5)                  # 00BBGGRR
    lwz 7, 0x3c(5)
    stw 7, 0x3c(3)
    li 8, 0                         # the new colour
    li 10, 0                        # the channel's shift
    addi 11, 29, {T_MINI_TINT_R}
clt_channel:
    srw 9, 6, 10
    andi. 9, 9, 0xff
    lwz 12, 0(11)
    mullw 9, 9, 12
    srwi 9, 9, 8
    cmpwi 9, 0xff
    ble clt_put
    li 9, 0xff
clt_put:
    slw 9, 9, 10
    or 8, 8, 9
    addi 10, 10, 8
    addi 11, 11, 4
    cmpwi 10, 24
    blt clt_channel
    rlwinm 6, 6, 0, 0, 7            # (its top byte kept)
    or 8, 8, 6
    stw 8, 0x38(3)
    blr

coop_mini_ride:                     # (r29/r30, before Ratchet's update) Ratchet gets on, rides or jumps off
    lwz 9, {C_RIDE}(29)
    cmpwi 9, 0
    bne cmr_riding
    lwz 9, {C_RIDE_WAIT}(29)        # not riding: getting on when he comes down over him
    cmpwi 9, 0
    ble cmr_may
    addi 9, 9, -1
    stw 9, {C_RIDE_WAIT}(29)
    b cmr_last
cmr_may:
    lwz 9, {HERO_ON_GROUND}(30)
    cmpwi 9, 0
    bne cmr_last
    lfs 1, 0x88(30)                 # coming down
    lfs 0, {C_RATCHET_Z}(29)
    fcmpu 0, 1, 0
    bge cmr_last
    lfs 0, {C_MINI_POS} + 8(29)     # over him
    lfs 2, {T_MOUNT_ABOVE}(29)
    fadds 0, 0, 2
    fcmpu 0, 1, 0
    blt cmr_last
    lfs 1, 0x80(30)                 # and near
    lfs 0, {C_MINI_POS}(29)
    fsubs 1, 1, 0
    lfs 2, 0x84(30)
    lfs 0, {C_MINI_POS} + 4(29)
    fsubs 2, 2, 0
    fmuls 3, 1, 1
    fmadds 3, 2, 2, 3
    fsqrts 3, 3
    lfs 0, {T_MOUNT_R}(29)
    fcmpu 0, 3, 0
    bgt cmr_last
    li 9, 1
    stw 9, {C_RIDE}(29)
cmr_riding:
    lis 10, {PAD_HA}                # his Cross: off he jumps, from up there
    addi 10, 10, {PAD_LO}
    lwz 9, 0xa4(10)
    andi. 9, 9, {P1_CROSS}
    beq cmr_hold
    li 9, 0
    stw 9, {C_RIDE}(29)
    lwz 9, {T_RIDE_WAIT}(29)
    stw 9, {C_RIDE_WAIT}(29)
    lwz 9, {C_DISMOUNT}(29)         # from behind the mini
    stw 9, 0x80(30)
    lwz 9, {C_DISMOUNT} + 4(29)
    stw 9, 0x84(30)
    lfs 0, {C_MINI_POS} + 8(29)     # (the seat's height: Giant Clank's model units times his scale)
    lfs 1, {T_RIDE_UP}(29)
    lfs 2, {T_MINI_SCALE}(29)
    fmadds 0, 1, 2, 0
    stfs 0, 0x88(30)
    b cmr_last
cmr_hold:                           # riding: where the mini Giant Clank stands, facing his way, the stick at rest
    li 9, 0
    stw 9, 8(10)
    stw 9, 0xc(10)
    stw 9, 0x48(10)
    stw 9, 0x4c(10)
    lwz 9, {C_MINI_POS}(29)
    stw 9, 0x80(30)
    lwz 9, {C_MINI_POS} + 4(29)
    stw 9, 0x84(30)
    lwz 9, {C_MINI_YAW}(29)
    stw 9, 0x98(30)
cmr_last:
    lwz 9, 0x88(30)
    stw 9, {C_RATCHET_Z}(29)
    blr

coop_ride_draw:                     # (r29/r30, at the HUD hook) Ratchet and what he carries hidden, the rider in his place
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 28, 0x70(1)
    std 27, 0x78(1)
    bl coop_ride_restore            # (a frame the mini's tick missed: kept once)
    lwz 9, {C_RIDE}(29)
    cmpwi 9, 0
    beq crd_out
    bl coop_rider_place
    lwz 3, 0x2080(30)               # his moby
    bl coop_ride_hide
    li 28, {RIDE_ATTACHED_COUNT}    # what he carries: two mobys at the start of each entry
    addi 27, 30, {RIDE_ATTACHED}
crd_entry:
    lwz 3, 0(27)
    bl coop_ride_hide
    lwz 3, 4(27)
    bl coop_ride_hide
    addi 27, 27, {RIDE_ATTACHED_SIZE}
    addic. 28, 28, -1
    bne crd_entry
    lwz 3, {RIDE_SINGLE_0}(30)
    bl coop_ride_hide
    lwz 3, {RIDE_SINGLE_1}(30)
    bl coop_ride_hide
    lwz 3, {RIDE_SINGLE_2}(30)
    bl coop_ride_hide
crd_out:
    ld 27, 0x78(1)
    ld 28, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_ride_hide:                     # (r3 a moby or 0; r29) not drawn this frame (draw distance 0); kept in
    cmpwi 3, 0                      # C_RIDE_KEPT, once a frame
    beqlr
    lwz 8, {C_RIDE_N}(29)
    cmpwi 8, {RIDE_KEPT_MAX}
    bgelr
    addi 7, 29, {C_RIDE_KEPT}
crh_seen:
    cmpwi 8, 0
    beq crh_keep
    lwz 9, 0(7)
    cmpw 9, 3
    beqlr                           # (in two of his lists: once)
    addi 7, 7, 12
    addi 8, 8, -1
    b crh_seen
crh_keep:
    stw 3, 0(7)
    lhz 9, 0x32(3)
    stw 9, 4(7)
    lwz 9, 0x24(3)
    stw 9, 8(7)
    lwz 9, {C_RIDE_N}(29)
    addi 9, 9, 1
    stw 9, {C_RIDE_N}(29)
    li 9, 0
    sth 9, 0x32(3)
    blr

coop_ride_restore:                  # (r29) what coop_ride_hide hid drawn again
    lwz 8, {C_RIDE_N}(29)
    addi 7, 29, {C_RIDE_KEPT}
crr_next:
    cmpwi 8, 0
    ble crr_done
    lwz 3, 0(7)
    lwz 9, 0x24(3)                  # (still the same moby)
    lwz 10, 8(7)
    cmpw 9, 10
    bne crr_skip
    lwz 9, 4(7)
    sth 9, 0x32(3)
crr_skip:
    addi 7, 7, 12
    addi 8, 8, -1
    b crr_next
crr_done:
    li 9, 0
    stw 9, {C_RIDE_N}(29)
    blr

coop_rider_tick:                    # (r29/r30, after coop_mini_ride) the rider made while Ratchet rides, gone when not
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lwz 3, {C_RIDER}(29)
    lwz 9, {C_RIDE}(29)
    cmpwi 9, 0
    bne crt_want
    bl coop_rider_delete
    b crt_out
crt_want:
    cmpwi 3, 0
    beq crt_spawn
    lwz 4, 0x24(3)                  # (still his: Ratchet's model)
    lwz 5, 0x2080(30)
    lwz 5, 0x24(5)
    cmpw 4, 5
    beq crt_place
crt_spawn:
    li 3, {CARRIER_CLASS}
    bl {SPAWN}
    stw 3, {C_RIDER}(29)
    cmpwi 3, 0
    beq crt_out
    lwz 4, 0x2080(30)               # Ratchet's model (scaled in coop_rider_place)
    lwz 5, 0x24(4)
    stw 5, 0x24(3)
    lwz 6, 0x2c(4)
    stw 6, 0x2c(3)
    lwz 8, {RIDER_ANIM_TABLE}(5)    # Quartu's pose in the model's table (only levels 0, 15 and 18 have it)
    cmpwi 8, 0
    bne crt_flags
    lis 8, {RIDER_ANIM_HA}
    addi 8, 8, {RIDER_ANIM_LO}
    stw 8, {RIDER_ANIM_TABLE}(5)
crt_flags:
    li 4, 0xff                      # in the moby loop at any distance, drawn
    stb 4, 0x30(3)
    li 4, 1
    stb 4, 0x31(3)
    li 4, {DRAW_DISTANCE}
    sth 4, 0x32(3)
    lhz 4, 0x34(3)
    rlwinm 4, 4, 0, {NOT_SKIP_MB}, {NOT_SKIP_ME}
    sth 4, 0x34(3)
    li 4, {RIDER_ANIM_SLOT}
    li 5, 0
    li 6, 0
    bl {MOBY_SET_ANIM}
crt_place:
    bl coop_rider_place
crt_out:
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_rider_place:                   # (r29/r30) the rider at the seat on the mini's back, turned with it, in Ratchet's light
    lwz 3, {C_RIDER}(29)
    cmpwi 3, 0
    beqlr
    lwz 4, {C_MINI}(29)
    cmpwi 4, 0
    beqlr
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x90(1)
    std 31, 0x88(1)
    mr 31, 3
    mr 3, 4                         # the seat goes with his animated back (the user: "he does not stick
    lwz 4, {T_RIDE_JOINT}(29)       # to the animated part of the model"): JOINT_POSITION of the joint
    addi 5, 1, 0x70                 # ending at bone 73, its way from his place times T_RIDE_JOINT_SCALE
    bl {JOINT_POSITION}             # (1: times the model's 0.75, as for Golden Clank's parts, sank him into
    lwz 3, {C_MINI}(29)             # the mini: 1.07 up, bone 73 is 1.46)
    lfs 3, {T_RIDE_JOINT_SCALE}(29)
    li 7, 0
crp_axis:
    add 8, 3, 7
    lfs 0, 0x10(8)
    addi 9, 1, 0x70
    lfsx 1, 9, 7
    fsubs 1, 1, 0
    fmadds 1, 1, 3, 0
    addi 9, 29, {C_RIDE_SEAT}
    stfsx 1, 9, 7
    addi 7, 7, 4
    cmpwi 7, 12
    blt crp_axis
    lfs 1, {C_MINI_YAW}(29)
    bl {COS}
    stfs 1, {C_TMP}(29)
    lfs 1, {C_MINI_YAW}(29)
    bl {SIN}
    lfs 2, {T_MINI_SCALE}(29)       # the seat in Giant Clank's model units, times his scale
    lfs 0, {T_RIDE_AHEAD}(29)
    fmuls 0, 0, 2
    lfs 3, {C_TMP}(29)
    lfs 4, {C_RIDE_SEAT}(29)
    fmadds 4, 3, 0, 4
    stfs 4, 0x10(31)
    lfs 4, {C_RIDE_SEAT} + 4(29)
    fmadds 4, 1, 0, 4
    stfs 4, 0x14(31)
    lfs 0, {T_DISMOUNT_BACK}(29)    # and where he jumps off from
    lfs 4, {C_MINI_POS}(29)
    fnmsubs 4, 3, 0, 4
    stfs 4, {C_DISMOUNT}(29)
    lfs 4, {C_MINI_POS} + 4(29)
    fnmsubs 4, 1, 0, 4
    stfs 4, {C_DISMOUNT} + 4(29)
    lfs 0, {T_RIDE_UP}(29)
    lfs 4, {C_RIDE_SEAT} + 8(29)
    fmadds 4, 0, 2, 4
    stfs 4, 0x18(31)
    lwz 4, {C_MINI}(29)             # turned as the mini is
    lwz 5, 0x40(4)
    stw 5, 0x40(31)
    lwz 5, 0x44(4)
    stw 5, 0x44(31)
    lwz 5, 0x48(4)
    stw 5, 0x48(31)
    lwz 4, 0x2080(30)
    lwz 5, 0x38(4)
    stw 5, 0x38(31)
    lfs 5, 0x2c(4)                  # his scale, as small to the mini as on Quartu
    lfs 6, {T_RIDE_SCALE}(29)
    fmuls 5, 5, 6
    fmuls 5, 5, 2
    stfs 5, 0x2c(31)
    ld 31, 0x88(1)
    addi 1, 1, 0x90
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_rider_delete:                  # (r29) the rider gone
    lwz 3, {C_RIDER}(29)
    cmpwi 3, 0
    beqlr
    li 9, 0
    stw 9, {C_RIDER}(29)
    lis 4, {HERO_HA}                # (still his: Ratchet's model)
    addi 4, 4, {HERO_LO}
    lwz 4, 0x2080(4)
    lwz 4, 0x24(4)
    lwz 5, 0x24(3)
    cmpw 4, 5
    bnelr
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    bl {MOBY_DELETE}
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr
"""