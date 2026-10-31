"""Lightning that lasts: bursts, rings, arcs and cages, drawn with the Tesla Claw's bolts.

Every effect of the mod is lightning (the user, 2026-10-26: "dont use the fog animation"; the
game's puffs were soft clouds). An effect takes one of FX_COUNT slots in the block (layout.py,
F_*) for some frames; coop_fx, once a frame, makes its bolts (coop_bolt: into BOLTS, drawn by
coop_bolt_draw at render time) with t going 0 -> 1 over its frames:
  FX_BURST  F_COUNT bolts from place A out in new random ways each frame (up rather than down),
            F_RADIUS * (0.3 + 0.7 t) long: a crackling star.
  FX_RING   a closed jagged ring about place A, its radius F_RADIUS * (T_RING_START ..1) by t, a
            little above A (T_RING_UP), each point moved out or in by up to T_RING_JITTER: the
            ground pound's shockwave.
coop_fx_add takes the next slot round (a full list loses its oldest effect).
"""
from ..game import *  # noqa: F401,F403

CODE = r"""
coop_fx_add:                        # (r3 kind, r4 frames, r5 place A or 0, r6 moby (or 0), r7 place B or 0, r8 count,
                                    #  f1 radius; r29) -> r3 = the slot
    lwz 9, {C_FX_NEXT}(29)
    addi 10, 9, 1
    stw 10, {C_FX_NEXT}(29)
    andi. 9, 9, {FX_COUNT} - 1
    slwi 9, 9, 6
    addi 9, 9, {FX}
    add 9, 9, 29
    stw 3, {F_KIND}(9)
    stw 4, {F_LEFT}(9)
    stw 4, {F_TOTAL}(9)
    stw 6, {F_MOBY}(9)
    stw 8, {F_COUNT}(9)
    stfs 1, {F_RADIUS}(9)
    cmpwi 5, 0
    beq cfa_b
    lwz 10, 0(5)
    stw 10, {F_A}(9)
    lwz 10, 4(5)
    stw 10, {F_A} + 4(9)
    lwz 10, 8(5)
    stw 10, {F_A} + 8(9)
cfa_b:
    cmpwi 7, 0
    beq cfa_out
    lwz 10, 0(7)
    stw 10, {F_B}(9)
    lwz 10, 4(7)
    stw 10, {F_B} + 4(9)
    lwz 10, 8(7)
    stw 10, {F_B} + 8(9)
cfa_out:
    mr 3, 9
    blr

coop_burst:                         # (r3 place, r4 bolts, r5 frames, f1 radius; r29) a burst there
    mr 8, 4
    mr 4, 5
    mr 5, 3
    li 3, {FX_BURST}
    li 6, 0
    li 7, 0
    b coop_fx_add

coop_fx:                            # (r29/r30, every frame) the effects' bolts
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x90(1)
    std 28, 0x70(1)
    std 27, 0x78(1)
    stfd 31, 0x80(1)
    li 27, 0
cfx_next:
    slwi 28, 27, 6
    addi 28, 28, {FX}
    add 28, 28, 29                  # r28 = the slot
    lwz 9, {F_KIND}(28)
    cmpwi 9, 0
    beq cfx_skip
    lwz 10, {F_LEFT}(28)
    addi 10, 10, -1
    stw 10, {F_LEFT}(28)
    cmpwi 10, 0
    bge cfx_go
    li 9, 0                         # done
    stw 9, {F_KIND}(28)
    b cfx_skip
cfx_go:
    lwz 11, {F_TOTAL}(28)           # t: 0 -> 1
    subf 9, 10, 11
    mr 10, 11
    bl coop_t
    fmr 31, 1
    lwz 9, {F_KIND}(28)
    cmpwi 9, {FX_BURST}
    bne cfx_ring
    bl coop_fx_burst
    b cfx_skip
cfx_ring:
    cmpwi 9, {FX_RING}
    bne cfx_skip
    bl coop_fx_ring
cfx_skip:
    addi 27, 27, 1
    cmpwi 27, {FX_COUNT}
    blt cfx_next
    lfd 31, 0x80(1)
    ld 27, 0x78(1)
    ld 28, 0x70(1)
    addi 1, 1, 0x90
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_bolt_from_to:                  # (r3 place A, r4 place B; r29) a bolt between them
    lwz 9, 0(3)
    stw 9, {C_BOLT_FROM}(29)
    lwz 9, 4(3)
    stw 9, {C_BOLT_FROM} + 4(29)
    lwz 9, 8(3)
    stw 9, {C_BOLT_FROM} + 8(29)
    lwz 9, 0(4)
    stw 9, {C_BOLT_TO}(29)
    lwz 9, 4(4)
    stw 9, {C_BOLT_TO} + 4(29)
    lwz 9, 8(4)
    stw 9, {C_BOLT_TO} + 8(29)
    b coop_bolt

coop_fx_burst:                      # (r28 the slot, f31 t; r29) its bolts out of place A
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x90(1)
    std 26, 0x70(1)
    stfd 30, 0x78(1)
    lfs 0, {T_ONE}(29)              # the length: radius * (0.3 + 0.7 t)
    lfs 1, {T_HALF}(29)
    fmuls 1, 1, 1                   # (0.25 ... 0.3)
    lfs 2, {T_ONE}(29)
    fsubs 2, 2, 1                   # 0.75
    fmadds 1, 2, 31, 1
    lfs 0, {F_RADIUS}(28)
    fmuls 30, 0, 1                  # f30 = the length
    lwz 26, {F_COUNT}(28)
cfb_one:
    cmpwi 26, 0
    ble cfb_out
    bl coop_rand
    stfs 1, {C_FXV}(29)
    bl coop_rand
    stfs 1, {C_FXV} + 4(29)
    bl coop_rand                    # up rather than down
    lfs 0, {T_HALF}(29)
    fmadds 1, 1, 0, 0
    stfs 1, {C_FXV} + 8(29)
    lfs 1, {C_FXV}(29)
    lfs 2, {C_FXV} + 4(29)
    lfs 3, {C_FXV} + 8(29)
    fmuls 4, 1, 1
    fmadds 4, 2, 2, 4
    fmadds 4, 3, 3, 4
    fsqrts 4, 4
    lfs 0, {T_SMALL}(29)
    fcmpu 0, 4, 0
    ble cfb_next
    fdivs 4, 30, 4                  # the way scaled to the length
    li 7, 0
cfb_axis:
    addi 8, 7, {F_A}
    lfsx 0, 28, 8
    addi 8, 7, {C_BOLT_FROM}
    stfsx 0, 29, 8
    addi 8, 7, {C_FXV}
    lfsx 5, 29, 8
    fmadds 0, 5, 4, 0
    addi 8, 7, {C_BOLT_TO}
    stfsx 0, 29, 8
    addi 7, 7, 4
    cmpwi 7, 12
    blt cfb_axis
    bl coop_bolt
cfb_next:
    addi 26, 26, -1
    b cfb_one
cfb_out:
    lfd 30, 0x78(1)
    ld 26, 0x70(1)
    addi 1, 1, 0x90
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_fx_ring:                       # (r28 the slot, f31 t; r29) a jagged ring about place A, growing with t
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0xa0(1)
    std 26, 0x70(1)
    std 25, 0x78(1)
    stfd 30, 0x80(1)
    lwz 9, {C_BOLT_N}(29)           # a bolt of its own: BOLT_POINTS points, the last the first
    cmpwi 9, {BOLT_MAX}
    bge cfr_out
    addi 10, 9, 1
    stw 10, {C_BOLT_N}(29)
    slwi 8, 9, 2
    addi 8, 8, {BOLT_COUNTS}
    li 11, {BOLT_POINTS}
    stwx 11, 29, 8
    mulli 26, 9, {BOLT_SIZE}
    addi 26, 26, {BOLTS}
    add 26, 26, 29                  # r26 = its points
    lfs 1, {T_RING_START}(29)       # the radius: F_RADIUS * (start + (1 - start) t)
    lfs 2, {T_ONE}(29)
    fsubs 2, 2, 1
    fmadds 1, 2, 31, 1
    lfs 0, {F_RADIUS}(28)
    fmuls 30, 0, 1
    li 25, 0
cfr_point:
    mr 9, 25
    li 10, {BOLT_POINTS} - 1
    bl coop_t
    lfs 0, {T_TWO_PI}(29)
    fmuls 1, 1, 0
    stfd 1, 0x60(1)
    bl {COS}
    stfs 1, {C_FXV}(29)
    lfd 1, 0x60(1)
    bl {SIN}
    stfs 1, {C_FXV} + 4(29)
    bl coop_rand                    # in or out a little
    lfs 0, {T_RING_JITTER}(29)
    lfs 2, {T_ONE}(29)
    fmadds 1, 1, 0, 2
    fmuls 1, 1, 30                  # f1 = this point's radius
    slwi 9, 25, 4
    add 9, 9, 26
    lfs 0, {F_A}(28)
    lfs 2, {C_FXV}(29)
    fmadds 0, 2, 1, 0
    stfs 0, 0(9)
    lfs 0, {F_A} + 4(28)
    lfs 2, {C_FXV} + 4(29)
    fmadds 0, 2, 1, 0
    stfs 0, 4(9)
    lfs 0, {F_A} + 8(28)
    lfs 2, {T_RING_UP}(29)
    fadds 0, 0, 2
    stfs 0, 8(9)
    lfs 0, {T_ONE}(29)
    stfs 0, 12(9)
    addi 25, 25, 1
    cmpwi 25, {BOLT_POINTS} - 1
    blt cfr_point
    slwi 9, 25, 4                   # closed: the last point is the first
    add 9, 9, 26
    lwz 10, 0(26)
    stw 10, 0(9)
    lwz 10, 4(26)
    stw 10, 4(9)
    lwz 10, 8(26)
    stw 10, 8(9)
    lwz 10, 12(26)
    stw 10, 12(9)
cfr_out:
    lfd 30, 0x80(1)
    ld 25, 0x78(1)
    ld 26, 0x70(1)
    addi 1, 1, 0xa0
    ld 0, 0x10(1)
    mtlr 0
    blr
"""
