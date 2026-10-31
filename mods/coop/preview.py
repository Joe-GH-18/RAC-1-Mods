"""The Clank Zapper's preview on the pause menu (the user: "in the showcase in the menu, where clank
zapper is selected ... can it feature clank shooting small lightning out of his antenna?").

The Gadgets page's big preview (PREVIEW_WIDGET, read live 2026-10-27) shows the item under the
cursor on Ratchet. Its draw (0x1454d0) draws only the mobys in its own list, up to PREVIEW_SLOTS
of them from +0x44 (0 Ratchet, 1 the item, then what he wears), each unless its byte at +0xa4 +
the slot is set: a moby of the world placed there was never drawn (tried first). While the cursor
is on the Zapper, coop_preview puts a Clank of its own into slot 1, the item's (the game rewrites
the others each frame: put into a free one he was never drawn). The game's item (for the Zapper's
item 1 the backpack Clank on his back) is kept aside in C_PREV_ITEM with its update (+0x74) off:
left on, it ran after the menu had closed and deleted Ratchet, and crashed reading his joints. If
the menu lets go of its list first, coop_preview_gone deletes the item itself. It sets the other slots' bytes
(kept in C_PREV_FLAGS) and their mobys' draw distance to 0 (Ratchet was drawn all the same with
his byte set; 0xff, the preview's own, afterwards). Its Clank is made as his flying body is (CARRIER_CLASS with Clank's
installed model) and set up as the preview's own are (PREVIEW_SETUP; position w 1; an update of
its own, coop_preview_update, which the menu runs), stands where Ratchet stands at T_PREV_SCALE,
turned T_PREV_YAW from Ratchet's facing, in his light, animation T_PREV_ANIM, with T_PREV_ARCS
small bolts out of his antenna's tip (coop_antenna) to random places within T_PREV_ARC_R (with
T_PREV_JITTER and T_PREV_SEGMENTS in place of the zap's, coop_preview_swap), new every 2 draws.
The ways that draw the zap in play do not reach the menu: its render (0x6c558 -> 0x13ca68) never
runs DRAW_REGISTER's callbacks (0x6bb78); the zap's ribbon drawn after the menu's mobys
(MENU_RENDER_HOOK) is covered by the panels drawn after them. So the bolts are drawn flat after
the panels (coop_preview_flat at T_PREV_AT 1, MENU_PANELS_HOOK), each piece projected from the
menu's camera (T_PREV_CX/CY/FX/FY, fitted 2026-10-29 with T_PREV_MARK 1 on his antenna and feet).
The game is paused in the menu (no frame counter), so the bolts' randomness counts the draws
(C_PREV_T). Off the entry, or the menu closed (coop_frame runs again: coop_preview_late), the
game's list and flags are put back and he goes.
"""
from ..game import *  # noqa: F401,F403

PREVIEW_WIDGET = 0x72A384          # the Gadgets page's model preview: +0x44 its mobys (Ratchet, the item, ...), +0xa4 a byte each: not drawn
PREVIEW_SLOTS = 24
MOBY_DRAW = 0xF1934                # (r3 moby, r4 1): queued for the render
MENU_RENDER_HOOK = 0x13D150        # bl MOBY_RENDER in the menu's draw 0x13ca68: the mobys the widgets queued, drawn
MOBY_RENDER = 0xF1974
# After the mobys the menu's draw draws its second pass of widgets (those without flag 0x2 at
# +0x10: the panels), then each widget's extras (0x13c5e8); both are followed by a call of an empty
# function (the PS2's leftovers): places to draw the bolts after the panels (T_PREV_AT 1 or 2).
MENU_PANELS_HOOK, MENU_STUB_A = 0x13D17C, 0x6D704
MENU_DRAWN_HOOK, MENU_STUB_B = 0x13D1C0, 0x6D708
MOBY_FINISH = 0xF30A0              # (r3 moby) the end of a moby's update, from its matrix
PREVIEW_SETUP = 0xF1EA0            # (r3 moby, r4 0x202020, r5 0xe, r6 0xe, r7 0): what the preview does to each moby it makes

CODE = r"""
coop_preview:                       # (r29) the Zapper under the cursor: our Clank zapping in place of the game's preview
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 28, 0x70(1)
    std 27, 0x78(1)
    lis 9, {FRAME_COUNTER_HA}
    lwz 9, {FRAME_COUNTER_LO}(9)
    stw 9, {C_PREV_FRAME}(29)
    lwz 9, {T_PREV_ON}(29)
    cmpwi 9, 0
    beq cpv_off
    lwz 9, {C_MODEL}(29)
    cmpwi 9, 0
    beq cpv_off
    bl coop_cursor_on_zapper
    bne cpv_off
    lis 28, {PREVIEW_WIDGET_HA}
    addi 28, 28, {PREVIEW_WIDGET_LO}
    lwz 27, 0x44(28)                # r27 = the game's Ratchet
    cmpwi 27, 0
    beq cpv_off
    lwz 9, {C_PREV_KEPT}(29)        # the slots' bytes kept once, then all but the item's set
    cmpwi 9, 0
    bne cpv_flags
    li 9, 1
    stw 9, {C_PREV_KEPT}(29)
    li 10, 0
cpv_keep:
    addi 11, 10, 0xa4
    lbzx 9, 28, 11
    addi 11, 10, {C_PREV_FLAGS}
    stbx 9, 29, 11
    addi 10, 10, 1
    cmpwi 10, {PREVIEW_SLOTS}
    blt cpv_keep
cpv_flags:
    li 10, 0
cpv_flag:
    li 9, 1
    addi 11, 10, 0xa4
    stbx 9, 28, 11
    slwi 11, 10, 2                  # and its moby's draw distance 0 (Ratchet was drawn all the same)
    addi 11, 11, 0x44
    lwzx 12, 28, 11
    cmpwi 12, 0
    beq cpv_flag_next
    lwz 9, {C_PREV}(29)
    cmpw 12, 9
    beq cpv_flag_next
    li 9, 0
    sth 9, 0x32(12)
cpv_flag_next:
    addi 10, 10, 1
    cmpwi 10, {PREVIEW_SLOTS}
    blt cpv_flag
    lwz 3, {C_PREV}(29)             # ours (still ours?)
    cmpwi 3, 0
    beq cpv_spawn
    lwz 4, 0x24(3)
    lwz 5, {C_MODEL}(29)
    cmpw 4, 5
    beq cpv_have
cpv_spawn:
    li 3, {CARRIER_CLASS}
    bl {SPAWN}
    cmpwi 3, 0
    beq cpv_out
    stw 3, {C_PREV}(29)
    lwz 4, {C_MODEL}(29)
    stw 4, 0x24(3)
    li 4, 0xff                      # as the preview's own (0x14601c..0x146034, 0x1460b8)
    stb 4, 0x30(3)
    sth 4, 0x32(3)
    li 4, 0
    stb 4, 0x31(3)
    stb 4, 0x20(3)
    sth 4, 0x34(3)
    lwz 9, {C_PREV_DESC}(29)        # an update of its own: the menu draws only mobys it updated
    cmpwi 9, 0
    bne cpv_desc
    bl coop_preview_desc
cpv_desc:
    lwz 3, {C_PREV}(29)
    addi 4, 29, {C_PREV_DESC}
    stw 4, 0x74(3)
    lwz 3, {C_PREV}(29)             # set up as the preview's own are (0x146038..0x146058)
    lis 4, 0x20
    ori 4, 4, 0x2020
    li 5, 0xe
    li 6, 0xe
    li 7, 0
    bl {PREVIEW_SETUP}
    lwz 3, {C_PREV}(29)
    lwz 4, {T_PREV_ANIM}(29)
    li 5, 0
    li 6, 0
    bl {MOBY_SET_ANIM}
    lwz 3, {C_PREV}(29)
cpv_have:
    lis 10, {PREVIEW_WIDGET_HA}     # in the item's slot (the game rewrites the others each frame)
    addi 10, 10, {PREVIEW_WIDGET_LO}
    lwz 9, 0x48(10)
    cmpw 9, 3
    beq cpv_slotted
    stw 9, {C_PREV_ITEM}(29)        # the game's item kept aside, its update off meanwhile (out of the
    cmpwi 9, 0                      # list it ran after the menu had deleted Ratchet, and crashed)
    beq cpv_put
    lwz 11, 0x74(9)
    stw 11, {C_PREV_ITEM_UPD}(29)
    li 11, 0
    stw 11, 0x74(9)
cpv_put:
    stw 3, 0x48(10)
cpv_slotted:
    li 9, 0
    stb 9, 0xa5(10)
    mr 28, 3                        # r28 = ours: where Ratchet stands, turned, scaled, in his light
    lfs 0, 0x10(27)
    stfs 0, 0x10(28)
    lfs 0, 0x14(27)
    stfs 0, 0x14(28)
    lfs 0, 0x18(27)
    lfs 1, {T_PREV_UP}(29)
    fadds 0, 0, 1
    stfs 0, 0x18(28)
    lfs 0, {T_ONE}(29)              # (w 1: with 0 he was not drawn)
    stfs 0, 0x1c(28)
    lfs 0, {T_ZERO}(29)
    stfs 0, 0x40(28)
    stfs 0, 0x44(28)
    lfs 0, 0x48(27)
    lfs 1, {T_PREV_YAW}(29)
    fadds 0, 0, 1
    lfs 1, {T_PI}(29)               # (kept within -pi..pi)
    fcmpu 0, 0, 1
    ble cpv_yaw
    lfs 1, {T_TWO_PI}(29)
    fsubs 0, 0, 1
cpv_yaw:
    stfs 0, 0x48(28)
    lfs 0, {T_PREV_SCALE}(29)
    stfs 0, 0x2c(28)
    lwz 9, 0x38(27)
    stw 9, 0x38(28)
    mr 3, 28                        # its bounds from its place (the moby loop is not run in the menu)
    bl {MOBY_MOVED}
    li 9, 0                         # the bolts: new every 2 draws
    stw 9, {C_BOLT_N}(29)
    lwz 9, {C_PREV_T}(29)
    addi 9, 9, 1
    stw 9, {C_PREV_T}(29)
    srwi 9, 9, 1
    lis 10, 0x9e37
    ori 10, 10, 0x79b1
    mullw 9, 9, 10
    stw 9, {C_BOLT_SEED}(29)
    stw 9, {C_SEED}(29)
    lwz 27, {C_BODY}(29)            # coop_antenna works on C_BODY: ours for the moment
    stw 28, {C_BODY}(29)
    addi 3, 29, {C_PREV_TIP}
    bl coop_antenna
    stw 27, {C_BODY}(29)
    bl coop_preview_swap
    lwz 27, {T_PREV_ARCS}(29)
cpv_arc:
    cmpwi 27, 0
    ble cpv_arcs_made
    bl coop_rand
    lfs 0, {T_PREV_ARC_R}(29)
    lfs 2, {C_PREV_TIP}(29)
    fmadds 1, 1, 0, 2
    stfs 1, {C_PREV_END}(29)
    bl coop_rand
    lfs 0, {T_PREV_ARC_R}(29)
    lfs 2, {C_PREV_TIP} + 4(29)
    fmadds 1, 1, 0, 2
    stfs 1, {C_PREV_END} + 4(29)
    bl coop_rand                    # (up rather than down)
    fabs 1, 1
    lfs 0, {T_PREV_ARC_R}(29)
    lfs 2, {C_PREV_TIP} + 8(29)
    fmadds 1, 1, 0, 2
    stfs 1, {C_PREV_END} + 8(29)
    addi 3, 29, {C_PREV_TIP}
    addi 4, 29, {C_PREV_END}
    bl coop_bolt_from_to
    addi 27, 27, -1
    b cpv_arc
cpv_arcs_made:
    bl coop_preview_swap
cpv_draw:
    li 9, 1                         # the bolts drawn flat over the menu (coop_preview_flat)
    stw 9, {C_PREV_BOLTS}(29)
    b cpv_out
cpv_off:
    bl coop_preview_gone
cpv_out:
    ld 27, 0x78(1)
    ld 28, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_preview_panels_drawn:          # (in place of the menu's bl MENU_STUB_A, an empty function) both passes of
    li 4, 1                         # widgets drawn: the bolts here if T_PREV_AT is 1
    b coop_preview_bolts

coop_preview_menu_drawn:            # (in place of bl MENU_STUB_B, empty) the widgets' extras drawn too: if T_PREV_AT is 2
    li 4, 2
    b coop_preview_bolts

coop_preview_bolts:                 # (r4 = the place in the menu's draw) our Clank's bolts, if T_PREV_AT names it
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 29, 0x70(1)
    lis 29, {COOP_HA}
    addi 29, 29, {COOP_LO}
    lwz 9, {T_PREV_AT}(29)
    cmpw 9, 4
    bne cpb_out
    lwz 9, {C_PREV_BOLTS}(29)
    cmpwi 9, 0
    beq cpb_out
    lwz 9, {C_PREV}(29)
    cmpwi 9, 0
    beq cpb_out
    bl coop_preview_flat
cpb_out:
    ld 29, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_preview_swap:                  # (r29) the zap's jitter and segments exchanged with the preview's (twice: back)
    lwz 9, {T_BOLT_JITTER}(29)
    lwz 10, {T_PREV_JITTER}(29)
    stw 10, {T_BOLT_JITTER}(29)
    stw 9, {T_PREV_JITTER}(29)
    lwz 9, {T_BOLT_SEGMENTS}(29)
    lwz 10, {T_PREV_SEGMENTS}(29)
    stw 10, {T_BOLT_SEGMENTS}(29)
    stw 9, {T_PREV_SEGMENTS}(29)
    blr

coop_preview_flat:                  # (r29) the bolts of BOLTS drawn flat (FILL_RECT, as the menu fills its boxes):
    mflr 0                          # each piece projected into the preview's box (coop_preview_project) and drawn
    std 0, 0x10(1)                  # as squares T_PREV_STEP apart, a glow pass, then the core
    stdu 1, -0xb0(1)
    std 31, 0x70(1)
    std 30, 0x78(1)
    std 28, 0x80(1)
    std 27, 0x88(1)
    std 26, 0x90(1)
    std 25, 0x98(1)
    li 28, 0                        # r28 = the pass
cpf_pass:
    li 27, 0                        # r27 = the bolt
cpf_bolt:
    lwz 9, {C_BOLT_N}(29)
    cmpw 27, 9
    bge cpf_next_pass
    slwi 9, 27, 2
    addi 9, 9, {BOLT_COUNTS}
    lwzx 26, 29, 9                  # r26 = its points left
    mulli 31, 27, {BOLT_SIZE}
    addi 31, 31, {BOLTS}
    add 31, 31, 29                  # r31 = the point
cpf_piece:
    cmpwi 26, 2
    blt cpf_next_bolt
    mr 3, 31                        # C_PREV_SEG = its start on the screen, then the step to the next
    bl coop_preview_project
    stfs 1, {C_PREV_SEG}(29)
    stfs 2, {C_PREV_SEG} + 4(29)
    addi 3, 31, 0x10
    bl coop_preview_project
    lfs 3, {C_PREV_SEG}(29)
    fsubs 1, 1, 3
    stfs 1, {C_PREV_SEG} + 8(29)
    lfs 3, {C_PREV_SEG} + 4(29)
    fsubs 2, 2, 3
    stfs 2, {C_PREV_SEG} + 12(29)
    fabs 3, 1                       # squares: the longer way across over T_PREV_STEP
    fabs 4, 2
    fcmpu 0, 3, 4
    bge cpf_long
    fmr 3, 4
cpf_long:
    lfs 0, {T_PREV_STEP}(29)
    fdivs 3, 3, 0
    fctiwz 3, 3
    stfd 3, 0xa0(1)
    lwz 30, 0xa4(1)
    addi 30, 30, 1                  # r30 = steps (at most 64)
    cmplwi 30, 64
    ble cpf_steps
    li 30, 64
cpf_steps:
    mr 3, 30
    bl {INT_TO_FLOAT}
    lfs 2, {C_PREV_SEG} + 8(29)
    fdivs 2, 2, 1
    stfs 2, {C_PREV_SEG} + 8(29)
    lfs 2, {C_PREV_SEG} + 12(29)
    fdivs 2, 2, 1
    stfs 2, {C_PREV_SEG} + 12(29)
    li 25, 0
cpf_dot:
    cmpw 25, 30
    bge cpf_piece_next
    lfs 1, {C_PREV_SEG}(29)
    lfs 2, {C_PREV_SEG} + 4(29)
    bl coop_preview_dot
    lfs 1, {C_PREV_SEG}(29)
    lfs 0, {C_PREV_SEG} + 8(29)
    fadds 1, 1, 0
    stfs 1, {C_PREV_SEG}(29)
    lfs 1, {C_PREV_SEG} + 4(29)
    lfs 0, {C_PREV_SEG} + 12(29)
    fadds 1, 1, 0
    stfs 1, {C_PREV_SEG} + 4(29)
    addi 25, 25, 1
    b cpf_dot
cpf_piece_next:
    addi 31, 31, 0x10
    addi 26, 26, -1
    b cpf_piece
cpf_next_bolt:
    addi 27, 27, 1
    b cpf_bolt
cpf_next_pass:
    addi 28, 28, 1
    cmpwi 28, 2
    blt cpf_pass
    lwz 9, {T_PREV_MARK}(29)        # for lining up: big dots at his antenna's tip and his feet
    cmpwi 9, 0
    beq cpf_out
    addi 3, 29, {C_PREV_TIP}
    bl coop_preview_project
    li 28, 2
    bl coop_preview_dot
    lwz 3, {C_PREV}(29)
    addi 3, 3, 0x10
    bl coop_preview_project
    li 28, 2
    bl coop_preview_dot
cpf_out:
    ld 25, 0x98(1)
    ld 26, 0x90(1)
    ld 27, 0x88(1)
    ld 28, 0x80(1)
    ld 30, 0x78(1)
    ld 31, 0x70(1)
    addi 1, 1, 0xb0
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_preview_project:               # (r3 a point, r29) -> f1, f2 its place on the screen: from the menu's camera
    lis 9, {CAMERA_STATE_HA}        # (the preview's: place +0x140, view axis +0x350, left +0x360, up +0x370) at
    addi 9, 9, {CAMERA_STATE_LO}    # depth d, left l, up u: T_PREV_CX - T_PREV_FX l / d, T_PREV_CY - T_PREV_FY u / d
    lfs 1, 0(3)
    lfs 0, 0x140(9)
    fsubs 1, 1, 0
    lfs 2, 4(3)
    lfs 0, 0x144(9)
    fsubs 2, 2, 0
    lfs 3, 8(3)
    lfs 0, 0x148(9)
    fsubs 3, 3, 0
    lfs 0, 0x350(9)                 # f4 = d
    fmuls 4, 1, 0
    lfs 0, 0x354(9)
    fmadds 4, 2, 0, 4
    lfs 0, 0x358(9)
    fmadds 4, 3, 0, 4
    lfs 0, 0x360(9)                 # f5 = l
    fmuls 5, 1, 0
    lfs 0, 0x364(9)
    fmadds 5, 2, 0, 5
    lfs 0, 0x368(9)
    fmadds 5, 3, 0, 5
    lfs 0, 0x370(9)                 # f6 = u
    fmuls 6, 1, 0
    lfs 0, 0x374(9)
    fmadds 6, 2, 0, 6
    lfs 0, 0x378(9)
    fmadds 6, 3, 0, 6
    lfs 0, {T_SMALL}(29)            # (behind the camera: at it)
    fcmpu 0, 4, 0
    bge cpp_ahead
    fmr 4, 0
cpp_ahead:
    fdivs 5, 5, 4
    fdivs 6, 6, 4
    lfs 0, {T_PREV_FX}(29)
    lfs 1, {T_PREV_CX}(29)
    fnmsubs 1, 5, 0, 1
    lfs 0, {T_PREV_FY}(29)
    lfs 2, {T_PREV_CY}(29)
    fnmsubs 2, 6, 0, 2
    blr

coop_preview_dot:                   # (f1 x, f2 y, r28 = 0 glow, 1 core, 2 mark; r29) a square there: T_PREV_DOT_H + 4 r28
    mflr 0                          # its half size, T_PREV_DOT_COLOUR + 4 r28 its colour
    std 0, 0x10(1)
    stdu 1, -0xb0(1)
    slwi 9, 28, 2
    addi 10, 9, {T_PREV_DOT_H}
    lfsx 0, 29, 10
    fsubs 3, 1, 0
    fctiwz 3, 3
    stfd 3, 0x70(1)
    fsubs 3, 2, 0
    fctiwz 3, 3
    stfd 3, 0x78(1)
    fadds 3, 1, 0
    fctiwz 3, 3
    stfd 3, 0x80(1)
    fadds 3, 2, 0
    fctiwz 3, 3
    stfd 3, 0x88(1)
    addi 10, 9, {T_PREV_DOT_COLOUR}
    lwzx 7, 29, 10
    lwz 3, 0x74(1)
    lwz 4, 0x7c(1)
    lwz 5, 0x84(1)
    lwz 6, 0x8c(1)
    li 8, 0
    bl {FILL_RECT}
    addi 1, 1, 0xb0
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_preview_desc:                  # (r29) C_PREV_DESC made: the address of the trampoline behind the bl, and this TOC
    mflr 10
    bl cpd_got
    b coop_preview_update
cpd_got:
    mflr 9
    stw 9, {C_PREV_DESC}(29)
    stw 2, {C_PREV_DESC} + 4(29)
    mtlr 10
    blr

coop_preview_update:                # (r3 = our Clank) his update: finished from his matrix, as the preview's item is (0x150d54)
    b {MOBY_FINISH}

coop_preview_gone:                  # (r29) the game's list and flags back, ours away
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lis 10, {PREVIEW_WIDGET_HA}
    addi 10, 10, {PREVIEW_WIDGET_LO}
    lwz 9, {C_PREV_KEPT}(29)
    cmpwi 9, 0
    beq cpg_list
    li 9, 0
    stw 9, {C_PREV_KEPT}(29)
    li 12, 0
cpg_flag:
    addi 11, 12, {C_PREV_FLAGS}
    lbzx 9, 29, 11
    addi 11, 12, 0xa4
    stbx 9, 10, 11
    slwi 11, 12, 2                  # the draw distance the preview gives its mobys (0x14602c)
    addi 11, 11, 0x44
    lwzx 4, 10, 11
    cmpwi 4, 0
    beq cpg_flag_next
    lwz 9, {C_PREV}(29)
    cmpw 4, 9
    beq cpg_flag_next
    li 9, 0xff
    sth 9, 0x32(4)
cpg_flag_next:
    addi 12, 12, 1
    cmpwi 12, {PREVIEW_SLOTS}
    blt cpg_flag
cpg_list:
    li 9, 0
    stw 9, {C_PREV_BOLTS}(29)
    lwz 3, {C_PREV}(29)
    cmpwi 3, 0
    beq cpg_out
    li 9, 0
    stw 9, {C_PREV}(29)
    lwz 4, {C_PREV_ITEM}(29)        # r4 = the game's item, its update back
    stw 9, {C_PREV_ITEM}(29)
    cmpwi 4, 0
    beq cpg_updated
    lwz 9, {C_PREV_ITEM_UPD}(29)
    stw 9, 0x74(4)
    li 9, 0xff                      # (and seen again)
    sth 9, 0x32(4)
cpg_updated:
    lwz 9, 0x48(10)
    cmpw 9, 3
    bne cpg_dropped
    stw 4, 0x48(10)                 # still in the slot: the item back in it, ours away
    bl cpg_delete
    b cpg_out
cpg_dropped:                        # the menu let go of its list (closed): the item it never saw goes too
    stw 4, {C_TMP}(29)
    bl cpg_delete
    lwz 3, {C_TMP}(29)
    cmpwi 3, 0
    beq cpg_out
    lbz 9, 0x20(3)
    cmpwi 9, 0x80
    bge cpg_out
    bl {MOBY_DELETE}
    b cpg_out
cpg_delete:                         # (r3 ours) away, unless already deleted (+0x20 0xfd/0xfe then, 0xefb70)
    lbz 9, 0x20(3)
    cmpwi 9, 0x80
    bgelr
    lwz 4, 0x24(3)
    lwz 5, {C_MODEL}(29)
    cmpw 4, 5
    bnelr
    lwz 4, 0x74(3)
    addi 5, 29, {C_PREV_DESC}
    cmpw 4, 5
    bnelr
    b {MOBY_DELETE}
cpg_out:
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_preview_late:                  # (r29, every frame of play) the menu closed with ours out: away with him
    lwz 9, {C_PREV}(29)
    lwz 10, {C_PREV_KEPT}(29)
    or. 9, 9, 10
    beqlr
    lis 9, {FRAME_COUNTER_HA}
    lwz 9, {FRAME_COUNTER_LO}(9)
    lwz 10, {C_PREV_FRAME}(29)
    subf 9, 10, 9
    cmplwi 9, 2
    blelr
    b coop_preview_gone
"""
