"""AI Clank ("the Clank Zapper that doesn't suck", docs/coop-clank-spec.md 2.6): with nobody at the
second pad and the AI chosen (C_AI_ON), coop_ai drives Clank in Player 2's place. It writes only
what a pad would (C_STICK, C_BUTTONS, C_BUTTONS_NEW), and C_TARGET, so he flies, zaps, rams and
docks with Player 2's moves, numbers and limits; a pad that comes back takes over at once.

- Out: docked, he leaves (Start) only when an enemy is within T_AI_QUIET of Ratchet (the user:
  "clank should only jump off, if enemies are nearby").
- Follow: the stick at rest, so the buddy slot holds him (flight.py).
- Moves (the user: "make clanks ai use more moves, he only uses the taser"), first that fits:
  - Pound: T_AI_CROWD enemies within T_AI_CROWD_RANGE of him on the ground plane: Triangle.
  - Protect: an enemy within T_AI_PROTECT of Ratchet is rammed (Square).
  - Engage: the nearest enemy within T_AI_ENGAGE of Ratchet is zapped (Circle held), at
    T_AI_DAMAGE of the zap's damage (coop_hit); within T_AI_RAM_REACH of Clank it is rammed after
    T_AI_ZAP_BURST frames of zapping (the user: "restrict the tesla shooting move ... so he starts
    dashing more"). A move he cannot pay or wait for falls back to the zap.
- Retreat: below T_AI_RETREAT energy he attacks nothing until T_AI_RESUME (C_AI bit AI_TIRED).
- Idle: no enemy within T_AI_QUIET of Ratchet for T_AI_IDLE frames ("go on after 5 seconds if no
  enemies are there"): he docks (Select held, T_DOCK_HOLD frames), Ratchet moving or not.
"""
from ..game import *  # noqa: F401,F403

AI_TIRED = 1                       # C_AI: below T_AI_RETREAT, until T_AI_RESUME

CODE = r"""
coop_ai:                            # (r29/r30/r31) AI Clank's stick and buttons; C_DRIVER = DRIVER_AI
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x90(1)
    std 28, 0x70(1)
    std 27, 0x78(1)
    std 26, 0x80(1)
    li 9, {DRIVER_AI}
    stw 9, {C_DRIVER}(29)
    li 9, 0
    stw 9, {C_STICK}(29)
    stw 9, {C_STICK} + 4(29)
    stw 9, {C_BUTTONS}(29)
    stw 9, {C_BUTTONS_NEW}(29)
    addi 3, 30, 0x80                # anything near Ratchet? (r28)
    lfs 1, {T_AI_QUIET}(29)
    li 4, 0
    li 5, 0
    bl coop_nearest
    mr 28, 3
    lis 9, {FRAME_COUNTER_HA}       # quiet: the frames since an enemy was last near (by the game's
    lwz 9, {FRAME_COUNTER_LO}(9)    # counter: this runs several times a frame)
    cmpwi 28, 0
    beq cai_quiet
    stw 9, {C_STILL}(29)
cai_quiet:
    lwz 10, {C_STILL}(29)
    subf 27, 10, 9                  # (r27: frames quiet)
    lwz 9, {C_AI}(29)               # tired below T_AI_RETREAT, rested again at T_AI_RESUME
    lfs 1, {C_ENERGY}(29)
    lfs 0, {T_AI_RETREAT}(29)
    fcmpu 0, 1, 0
    bge cai_rested
    ori 9, 9, {AI_TIRED}
cai_rested:
    lfs 0, {T_AI_RESUME}(29)
    fcmpu 0, 1, 0
    blt cai_energy
    li 10, {AI_TIRED}
    andc 9, 9, 10
cai_energy:
    stw 9, {C_AI}(29)
    lwz 9, {C_MODE}(29)
    cmpwi 9, {MODE_DOCKED}
    beq cai_docked
    cmpwi 9, {MODE_FLY}
    bne cai_out
    cmpwi 28, 0                     # flying: quiet for T_AI_IDLE frames, back on his back
    bne cai_fight
    lwz 10, {T_AI_IDLE}(29)
    cmpw 27, 10
    blt cai_out
    li 9, {BUTTON_SELECT}
    stw 9, {C_BUTTONS}(29)
    b cai_out
cai_fight:
    lwz 9, {C_AI}(29)
    andi. 9, 9, {AI_TIRED}
    bne cai_out
    lwz 9, {C_PUNCH}(29)            # in a ram or a pound: let it run
    lwz 10, {C_POUND}(29)
    or. 9, 9, 10
    bne cai_out
    lwz 9, {C_POUND_WAIT}(29)       # the pound ready and paid for?
    cmpwi 9, 0
    bgt cai_protect
    lfs 1, {C_ENERGY}(29)
    lfs 0, {T_POUND_COST}(29)
    fcmpu 0, 1, 0
    blt cai_protect
    lfs 1, {T_AI_CROWD_RANGE}(29)   # a group under him
    bl coop_ai_crowd
    lwz 10, {T_AI_CROWD}(29)
    cmpw 3, 10
    blt cai_protect
    li 9, {BUTTON_POUND}
    stw 9, {C_BUTTONS}(29)
    stw 9, {C_BUTTONS_NEW}(29)
    b cai_out
cai_protect:
    addi 3, 30, 0x80                # protect: one close to Ratchet is rammed
    lfs 1, {T_AI_PROTECT}(29)
    li 4, 0
    li 5, 0
    bl coop_nearest
    cmpwi 3, 0
    beq cai_engage
    stw 3, {C_TARGET}(29)
    b cai_ram
cai_engage:
    addi 3, 30, 0x80                # engage: the nearest within reach of Ratchet
    lfs 1, {T_AI_ENGAGE}(29)
    li 4, 0
    li 5, 0
    bl coop_nearest
    cmpwi 3, 0
    beq cai_out
    stw 3, {C_TARGET}(29)
    mr 26, 3
    addi 3, 26, 0x10                # within T_AI_RAM_REACH: rammed after a short burst of zapping
    bl coop_distance
    lfs 0, {T_AI_RAM_REACH}(29)
    fcmpu 0, 1, 0
    bgt cai_zap
    lwz 9, {C_ZAP}(29)
    lwz 10, {T_AI_ZAP_BURST}(29)
    cmpw 9, 10
    blt cai_zap
cai_ram:
    lwz 9, {C_PUNCH_WAIT}(29)       # (ready and paid for, else the zap)
    cmpwi 9, 0
    bgt cai_zap
    lfs 1, {C_ENERGY}(29)
    lfs 0, {T_COST_PUNCH}(29)
    fcmpu 0, 1, 0
    blt cai_zap
    li 9, {BUTTON_PUNCH}
    stw 9, {C_BUTTONS}(29)
    stw 9, {C_BUTTONS_NEW}(29)
    b cai_out
cai_zap:
    li 9, {BUTTON_ZAP}
    stw 9, {C_BUTTONS}(29)
    lwz 10, {C_ZAP}(29)
    cmpwi 10, 0
    bne cai_out
    stw 9, {C_BUTTONS_NEW}(29)
    b cai_out
cai_docked:                         # docked: out only when an enemy is near
    cmpwi 28, 0
    beq cai_out
cai_join:
    li 9, {BUTTON_START}
    stw 9, {C_BUTTONS_NEW}(29)
cai_out:
    ld 26, 0x80(1)
    ld 27, 0x78(1)
    ld 28, 0x70(1)
    addi 1, 1, 0x90
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_ai_crowd:                      # (f1 reach on the ground plane; r29) -> r3 = the enemies so near him
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x90(1)
    std 28, 0x70(1)
    std 27, 0x78(1)
    std 26, 0x80(1)
    stfd 31, 0x88(1)
    fmr 31, 1
    li 26, 0
    lis 27, {MOBY_LIST_HA}
    addi 27, 27, {MOBY_LIST_LO} - 4
cac_next:
    lwzu 28, 4(27)
    cmpwi 28, 0
    beq cac_out
    mr 3, 28
    bl coop_enemy
    cmpwi 3, 0
    beq cac_next
    lfs 1, 0x10(28)
    lfs 0, {C_POS}(29)
    fsubs 1, 1, 0
    lfs 2, 0x14(28)
    lfs 0, {C_POS} + 4(29)
    fsubs 2, 2, 0
    fmuls 1, 1, 1
    fmadds 1, 2, 2, 1
    fsqrts 1, 1
    fcmpu 0, 1, 31
    bgt cac_next
    addi 26, 26, 1
    b cac_next
cac_out:
    mr 3, 26
    lfd 31, 0x88(1)
    ld 26, 0x80(1)
    ld 27, 0x78(1)
    ld 28, 0x70(1)
    addi 1, 1, 0x90
    ld 0, 0x10(1)
    mtlr 0
    blr
"""
