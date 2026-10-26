"""What is set at the HUD hook, the last thing in a frame's update: backpack Clank and the pack
hidden while Clank is out, his light, the wings and jets placed on him, the lightning's draw
callback; and Player 2's HUD, drawn there as the Weapon levels draw their flash.

The HUD itself is drawn behind the game's widgets in the HUD's draw (0xd5c20, HUD_DRAW_HOOK):
HUD_HOOK is in its update (0xd56d8 calls the widgets' updates, their +0x14; the draws are +0x18),
where whatever was drawn never showed (a 600 x 400 magenta rectangle, 2026-10-26).
While Player 2 is in, a badge top left (T_HUD_X/Y): "P2 CLANK" in Clank's blue and his
energy under it as a bar (T_BAR_*: its back, the energy in blue, gold when full, red-orange below
the ram's cost); "P2 DOCKED" in grey on Ratchet's back, "P2 GIANT ARMS" in gold while Player 2
fires Giant Clank's arms (COOP_PILOT). And the messages (coop_msg: C_MSG, the texts MESSAGES in
layout.py), centred at T_MSG_X/Y for T_MSG_FRAMES, fading over the last T_MSG_FADE: Player 2
joined, Clank docked, and each combo's name. Not drawn in the game's scenes (SCENE_FLAG).

Text: HUD_TEXT 0x70130(x, y, colour, string, -1) is the HUD's own (the ammunition count's, with a
shadow drawn a unit down and right first); it ends the text at x, measured with the font's widths
(FONT_WIDTHS, the u8 at +3 of a character's 4 bytes) unless FONT_FLAG is set (then 0x6ccc4 with
the other font's FONT_WIDTHS_B). coop_text measures it the same way to start or centre it.
FILL_RECT 0xca72c(x0, y0, x1, y1, colour, 0) fills the bar.
"""
from ..game import *  # noqa: F401,F403

HUD_DRAW_HOOK = 0xD5CD0        # lis r28, 0xa1 behind the widgets' draws in the HUD's draw 0xd5c20
HUD_DRAW_HOOK_WORD = 0x3F8000A1
HUD_TEXT = 0x70130             # (r3 x of the end, r4 y, r5 colour, r6 string, r7 -1)
FONT_FLAG = 0x159C351          # u8: the other font
FONT_WIDTHS, FONT_WIDTHS_B = 0x7368B0, 0x737390
TEXT_WIDTH = 0x6CCC4           # (r3 string, r4 -1, r5 widths) -> r3, the other font's
FILL_RECT = 0xCA72C            # (r3 x0, r4 y0, r5 x1, r6 y1, r7 colour, r8 0)

CODE = r"""
coop_hud:                           # at HUD_HOOK (r30, r31 are the HUD's: kept)
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 29, 0x70(1)
    std 30, 0x78(1)
    lis 29, {COOP_HA}
    addi 29, 29, {COOP_LO}
    lis 30, {HERO_HA}
    addi 30, 30, {HERO_LO}
    lwz 3, {C_MODE}(29)
    cmpwi 3, {MODE_DOCKED}
    beq chd_hide
    li 3, 1
chd_hide:
    bl coop_hide
    lwz 3, {C_MODE}(29)
    cmpwi 3, {MODE_DOCKED}
    beq chd_out
    bl coop_place
    bl coop_bolt_show
chd_out:
    ld 30, 0x78(1)
    ld 29, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
coop_hud_next:
    {CHAIN}

# coop_hud_draw: replaces lis r28, 0xa1 behind the HUD draw's loop over its widgets' draw
# functions (0xd5c20): drawing is open there (r28 is set by the displaced instruction itself).
coop_hud_draw:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 29, 0x70(1)
    std 30, 0x78(1)
    lis 29, {COOP_HA}
    addi 29, 29, {COOP_LO}
    lis 30, {HERO_HA}
    addi 30, 30, {HERO_LO}
    bl coop_draw_hud
    ld 30, 0x78(1)
    ld 29, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    lis 28, 0xa1                    # the displaced instruction
    blr

coop_msg:                           # (r3 a message, MSG_*; r29) it shows from now
    stw 3, {C_MSG}(29)
    lwz 9, {T_MSG_FRAMES}(29)
    stw 9, {C_MSG_LEFT}(29)
    blr

coop_text_width:                    # (r3 a string) -> r3 its width as HUD_TEXT measures it
    lis 9, {FONT_FLAG_HA}
    lbz 9, {FONT_FLAG_LO}(9)
    cmpwi 9, 0
    bne ctw_other
    lis 10, {FONT_WIDTHS_HA}
    addi 10, 10, {FONT_WIDTHS_LO}
    li 11, 0
ctw_next:
    lbz 9, 0(3)
    cmpwi 9, 0
    beq ctw_out
    slwi 9, 9, 2
    add 9, 9, 10
    lbz 8, 3(9)
    extsb 8, 8
    add 11, 11, 8
    addi 3, 3, 1
    b ctw_next
ctw_out:
    mr 3, 11
    blr
ctw_other:
    li 4, -1
    lis 5, {FONT_WIDTHS_B_HA}
    addi 5, 5, {FONT_WIDTHS_B_LO}
    b {TEXT_WIDTH}

coop_text:                          # (r3 x, r4 y, r5 colour, r6 string, r7 0 from x, 1 centred on x) with its shadow
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x90(1)
    std 31, 0x70(1)
    std 28, 0x78(1)
    std 27, 0x80(1)
    std 26, 0x88(1)
    mr 31, 6
    mr 28, 4
    mr 27, 5
    std 3, 0x60(1)
    std 7, 0x68(1)
    mr 3, 6
    bl coop_text_width
    ld 7, 0x68(1)
    ld 4, 0x60(1)
    cmpwi 7, 0
    beq ctx_from
    srawi 3, 3, 1                   # centred: it ends half its width right of x
ctx_from:
    add 26, 4, 3                    # r26 = where it ends
    addi 3, 26, 1                   # the shadow: black, as transparent as the text
    addi 4, 28, 1
    clrrwi 5, 27, 24
    mr 6, 31
    li 7, -1
    bl {HUD_TEXT}
    mr 3, 26
    mr 4, 28
    mr 5, 27
    mr 6, 31
    li 7, -1
    bl {HUD_TEXT}
    ld 26, 0x88(1)
    ld 27, 0x80(1)
    ld 28, 0x78(1)
    ld 31, 0x70(1)
    addi 1, 1, 0x90
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_rect:                          # (r3 x0, r4 y0, r5 x1, r6 y1, r7 colour)
    li 8, 0
    b {FILL_RECT}

coop_draw_hud:                      # (r29/r30) the badge and the message
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x90(1)
    std 31, 0x70(1)
    std 28, 0x78(1)
    std 27, 0x80(1)
    lis 31, {STATE_HA}
    addi 31, 31, {STATE_LO}
    lis 9, {SCENE_FLAG_HA}          # not in the game's scenes
    lwz 9, {SCENE_FLAG_LO}(9)
    cmpwi 9, 0
    bne cdh_out
    lwz 9, {C_DRIVER}(29)
    cmpwi 9, {DRIVER_P2}
    bne cdh_message
    li 28, {BADGE_DOCKED}           # the badge: its text and colour
    lwz 27, {T_HUD_GREY}(29)
    lwz 9, {COOP_PILOT}(31)
    cmpwi 9, 0
    beq cdh_out_q
    li 28, {BADGE_PILOT}
    lwz 27, {T_HUD_GOLD}(29)
    b cdh_badge
cdh_out_q:
    lwz 9, {C_MODE}(29)
    cmpwi 9, {MODE_DOCKED}
    beq cdh_badge
    li 28, {BADGE_OUT}
    lwz 27, {T_HUD_BLUE}(29)
cdh_badge:
    lwz 3, {T_HUD_X}(29)
    lwz 4, {T_HUD_Y}(29)
    mr 5, 27
    addi 6, 28, -1
    mulli 6, 6, {TEXT_SIZE}
    addi 6, 6, {TEXTS}
    add 6, 6, 29
    li 7, 0
    bl coop_text
    lwz 3, {T_HUD_X}(29)            # the bar: its back
    lwz 4, {T_HUD_Y}(29)
    lwz 9, {T_BAR_BELOW}(29)
    add 4, 4, 9
    lwz 5, {T_BAR_W}(29)
    add 5, 5, 3
    lwz 6, {T_BAR_H}(29)
    add 6, 6, 4
    lwz 7, {T_HUD_BACK}(29)
    bl coop_rect
    lfs 1, {C_ENERGY}(29)           # the energy: its width, its colour
    lfs 2, {T_ENERGY_MAX}(29)
    fdivs 1, 1, 2
    lwz 9, {T_BAR_W}(29)
    stw 9, {C_TMP} + 0x14(29)
    lis 9, 0x4330
    stw 9, {C_TMP} + 0x10(29)
    lfd 2, {C_TMP} + 0x10(29)
    li 9, 0
    stw 9, {C_TMP} + 0x14(29)
    lfd 3, {C_TMP} + 0x10(29)
    fsub 2, 2, 3
    fmul 1, 1, 2
    fctiwz 1, 1
    stfd 1, {C_TMP} + 0x10(29)
    lwz 28, {C_TMP} + 0x14(29)      # r28 = the filled width
    cmpwi 28, 0
    ble cdh_message
    lwz 27, {T_HUD_BLUE}(29)
    lfs 1, {C_ENERGY}(29)
    lfs 2, {T_ENERGY_MAX}(29)
    fcmpu 0, 1, 2
    blt cdh_low
    lwz 27, {T_HUD_GOLD}(29)
    b cdh_fill
cdh_low:
    lfs 2, {T_COST_PUNCH}(29)
    fcmpu 0, 1, 2
    bge cdh_fill
    lwz 27, {T_HUD_LOW}(29)
cdh_fill:
    lwz 3, {T_HUD_X}(29)
    lwz 4, {T_HUD_Y}(29)
    lwz 9, {T_BAR_BELOW}(29)
    add 4, 4, 9
    add 5, 3, 28
    lwz 6, {T_BAR_H}(29)
    add 6, 6, 4
    mr 7, 27
    bl coop_rect
cdh_message:
    lwz 9, {C_MSG_LEFT}(29)         # the message, fading at its end
    cmpwi 9, 0
    ble cdh_out
    addi 9, 9, -1
    stw 9, {C_MSG_LEFT}(29)
    lwz 3, {C_MSG}(29)
    cmpwi 3, 1
    blt cdh_out
    cmpwi 3, {BADGE_OUT} - 1
    bgt cdh_out
    lwz 27, {T_HUD_GOLD}(29)
    lwz 10, {T_MSG_FADE}(29)
    cmpw 9, 10
    bge cdh_say
    slwi 9, 9, 7                    # alpha 0x80 * left / fade
    divw 9, 9, 10
    clrlwi 27, 27, 8
    slwi 9, 9, 24
    or 27, 27, 9
cdh_say:
    lwz 6, {C_MSG}(29)
    addi 6, 6, -1
    mulli 6, 6, {TEXT_SIZE}
    addi 6, 6, {TEXTS}
    add 6, 6, 29
    lwz 3, {T_MSG_X}(29)
    lwz 4, {T_MSG_Y}(29)
    mr 5, 27
    li 7, 1
    bl coop_text
cdh_out:
    ld 27, 0x80(1)
    ld 28, 0x78(1)
    ld 31, 0x70(1)
    addi 1, 1, 0x90
    ld 0, 0x10(1)
    mtlr 0
    blr
"""
