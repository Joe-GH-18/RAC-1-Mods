"""How a level 2 weapon and the experience are shown: the bar in the HUD, the QuickSelect and
the pause menu (with the experience in words in a taller ammunition box), the gold icons, the
gold weapon in Ratchet's hand and in the menus' models, "Gold" names, and the level-up's flash.
"""
from ..game import *  # noqa: F401,F403

# The bar. FILL_RECT(x0, y0, x1, y1, colour, 0); colours as the game's slider has them (0x803030f0
# for its filling, 0x80ffffff for its frame).
HUD_BAR_HOOK = 0xCECCC         # extsw r5, r3 in the QuickSelect's draw function 0xce170
HUD_BAR_HOOK_WORD = 0x7C6507B4
HUD_X, HUD_Y = 0x723938, 0x72393C
FILL_RECT = 0xCA72C
BAR_BELOW = 30                 # from the place of the HUD entry (the ammunition count is at +12)
BAR_WIDTH, BAR_HEIGHT = 60, 2
# The filling has the colour of the HUD's ammunition count (0x7244f8), on a faint dark strip.
BAR_FILL, BAR_FULL, BAR_BACK = 0x80E08060, 0x8020D0FF, 0x38000000
FADE = 0x5027BC                # (r3 colour, r4 colour, f1) -> the colour that far from the first to the second
# The HUD in play: 0xd56d8 updates and draws its 13 widgets (0x90 bytes each from 0x723b10; +0x14
# the draw function's descriptor). The ammunition count is the widget made with icon ICON_BASE +
# item; its draw function 0xd4838 writes "%d/%d" at AMMO_X + r30 + r27, AMMO_Y + r21 and is not
# run while the widget is hidden.
AMMO_BAR_HOOK = 0xD4DAC        # lwz r3, 0x58(r31) behind the count
AMMO_BAR_HOOK_WORD = 0x807F0058
AMMO_X, AMMO_Y = 0x724504, 0x724508
# The count is written with its right end at r27 (70, or 95 when the weapon holds 100 rounds or
# more: 0x7244ec, 0x7244f0) from the widget's x, which is about the right edge of the icon; the
# dark pill behind both ends 11 further on. The bar runs inside the pill from the icon to the
# end of the count, under it (placed with the user from screenshots).
AMMO_BAR_BELOW = 18
AMMO_BAR_LEFT, AMMO_BAR_SHORTER = 10, 7
ICON_BASE = 0xEA60
# The level-up itself, besides the message: a flash of the whole screen that fades out (drawn
# behind the HUD's widget loop, which runs every frame), the camera's own shake channel 0
# (CAMERA_STATE +0x160: strength, value, frames left, frames in all), and bolts that burst from
# the enemy and fly to Ratchet.
HUD_FLASH_HOOK = 0xD5A68       # ori r3, r30, 0
HUD_FLASH_HOOK_WORD = 0x63C30000
FLASH_FRAMES, FLASH_ALPHA, FLASH_COLOUR = 30, 0x50, 0x20D0FF     # an alpha of 0x80 hides the picture altogether
# The HUD's x = 0 is not the left edge of a wide screen: drawn from 0, the flash left a strip on
# the left uncovered.
FLASH_LEFT, FLASH_TOP, FLASH_RIGHT, FLASH_BOTTOM = -200, -40, 900, 640
# What tells a level 2 weapon from the others in the HUD: its icon is drawn in gold. The HUD's
# icons are textured quads from DRAW_QUAD (0xcbe60), which gives every one the colour 0x808080
# with its alpha at TINT_HOOK; ICON(widget, sprite, x, y, flags, alpha) draws an item's icon
# through it, and ICON_HOOK is the call for the ammunition widget's.
ICON = 0xCDEB8
ICON_HOOK = 0xD4C9C            # bl ICON in the ammunition widget's draw function
TINT_HOOK = 0xCBEF0            # or r4, r5, r8
# The QuickSelect draws its icons in a loop over its entries, 0x1c bytes each with the item at
# +0x18: the entry is at the pointer QUICK_LISTS[QUICK_LIST] plus r23 where it calls ICON.
QUICK_ICON_HOOK = 0xCEA9C      # bl ICON
QUICK_LISTS, QUICK_LIST = 0xA1C190, 0xA1C084
# The pause menu draws its tiles in several places (the grids' 0x144ec0, 0x13fd08, the ring of
# the QuickSelect page 0x149f88, ...), each with ICON_SPRITE(icon id, version) -> sprite and then
# either ICON_DRAW, which sets the colour itself, or 0xcc0f0, which goes through DRAW_QUAD. So
# the lookup notes whether the icon is one to tint, and the next quad of either kind is.
ICON_SPRITE_WORD = 0x3CA000A2  # lis r5, 0xa2, its first instruction
ICON_SPRITE_BACK = ICON_SPRITE + 4
MENU_TINT_HOOK = 0xCA1B8       # or r6, r6, r7
MENU_TINT_HOOK_WORD = 0x7CC63B78
TINT_HOOK_WORD = 0x7CA44378
TINT = 0x44C6FF                # tuned with the user until a blue tile came out as the game's gold tiles (0x44d8ff was too green, 2026-10-14)

# The weapon in his hand is the moby at hero +0x1090. Its colour (moby +0x38, 00BBGGRR; what the
# level gives its mobys is about 0x29 a channel) is set to the hero moby's again in every frame
# (seen in a running game with the R.Y.N.O. and the Devastator; the code that does it was not
# found), so a level 2 weapon without a gold version gets its gold from the HUD's update, which
# is the last thing in the frame's update 0x166fb0, behind the hero and the mobys. Not every
# weapon gets it back: the gold Blaster, left at another colour by the level-up's flash, kept
# it, so the flash puts back what it found.
HAND_MOBY = 0x1090
WEAPON_TINT = 0x0C64B0           # picked from screenshots of the R.Y.N.O. in a running game

# The pause menu's Weapons page shows the weapon under the cursor in a box of its own (0x145d28)
# and Ratchet holding the one in his hand slot (0x14f828). Both make a moby for it when the item
# changes, give it the colour 0x202020 and, for an owned gold version, the game's gold look
# (0x8d7e8); the colour stays as set while the moby lives (seen in a running game). So the five
# without a gold version get WEAPON_TINT right there, as in his hand (r29 the item, r24 or r28
# the moby).
PREVIEW_GOLD_HOOK = 0x1460AC   # lis r3, 0x95 behind the gold look in 0x145d28
FIGURE_GOLD_HOOK = 0x14FA5C    # lis r3, 0x70 behind the gold look in 0x14f828
PREVIEW_GOLD_HOOK_WORD = 0x3C600095
FIGURE_GOLD_HOOK_WORD = 0x3C600070
# The experience in the menu: the Weapons page's box with the ammunition count (widget 0x72a620,
# draw function 0x147334: +0x20/+0x24 its width and height, r25 = 24 * the item under the cursor,
# nothing drawn for one not owned) writes the count centred in the box with 0x6a510 and then
# calls the empty 0x6d708; there the bar goes under the count, centred.
MENU_BAR_HOOK = 0x1475F0       # bl 0x6d708
MENU_TEXT_DONE = 0x6D708
MENU_BAR_WIDTH = 120
# The ammunition box is made MENU_BOX_GROW taller (in the units of the frame's pose: about 47.6
# a unit of the menu) and the count kept in its top MENU_COUNT_H; under it the bar (MENU_BAR_Y
# from the top) and the experience in words ("XP 340/1500", or "Level 2" in the full bar's
# colour), drawn as the count is: DRAW_TEXT(r3 the box as halfwords {top, bottom, left, right,
# centre x, centre y, 0, 0, 0x10, 3}, r4 colour, r5 the string, r6 -1), in the widget's
# coordinates. (Drawn in another box's place it does not show.) A box's size is that of its frame:
# the frame's update writes it into the widget (+0x20/+0x24) in every frame from the last pose of
# the frame's animation, joints 1 to 3 against joint 0 (see FOOT_BOX in mods/chargeboots/menu.py; the
# pose's fourth corner, joint 4 at +0x58, is the bottom left one and has to move with them);
# the ammunition box's is animation MENU_BOX_ANIM. The numbers were placed in a running game
# (state +0x170 to +0x188).
SPRINTF = 0x5CD2A8
DRAW_TEXT = 0x6A510
MENU_TEXT_COLOUR = 0x80FEA888  # the count's
XP_TEXT, XP_TEXT_MAX_TEXT = b"XP %d/%d", b"Level 2"
XP_TEXT_MAX = len(XP_TEXT) + 1
MENU_COUNT_HOOK = 0x147598     # lwz r3, 0x24(r31)
MENU_COUNT_HOOK_WORD = 0x807F0024
MENU_BOX_ANIM = 0x20
MENU_BOX_ANIM_OFF = 0x48 + 4 * MENU_BOX_ANIM
MENU_BOX_X, MENU_BOX_Y, MENU_BOX_HALF_W, MENU_BOX_HALF_H = 6233, -7790, 5261, 762   # the game's pose
MENU_BOX_GROW = 952            # 20 units
MENU_COUNT_H = 32              # the box's own height
MENU_BAR_Y = 28
MENU_XP_Y, MENU_XP_X, MENU_XP_HEIGHT = 33, 0, 16
MENU_XP_HEIGHT_HALF = MENU_XP_HEIGHT // 2

# The names. TEXT_LOOKUP(text id) -> string is what the QuickSelect, the menus and the vendor get
# an item's name with (191 callers); the game's gold versions have a text of their own (item
# table +4), these five have not, so their name is put together: "Gold " and the game's name in
# the language it runs in, in a buffer for each.
TEXT_LOOKUP_WORD = 0x3CA00097  # lis r5, 0x97, its first instruction
TEXT_LOOKUP_BACK = TEXT_LOOKUP + 4
NAME_TEXT = {0x0D: 0x4E50, 0x0E: 0x4E51, 0x12: 0x4E45, 0x17: 0x4E4E, 0x18: 0x4E42}   # item table +0
NAME_PREFIX = b"Gold "
NAME_SIZE = 48


# The bar. bar(r3 item, r4 x, r5 y, r6 = x is the bar's centre, not its left end, r7 = width or 0
#   for BAR_WIDTH, f1 = how far the HUD element is faded in): r31 = the filled width, r30 = pool, r29 = state block, f31 = fade; on
#   the stack: 0x98 colour, 0xa0 width, 0xa8 x0, 0xb0 y0, 0xb8 y1, 0xc8 r6.
# hud_bar: replaces extsw r5, r3 in the QuickSelect (r3 = the item of the entry, r18/r28 = its place).
# ammo_bar: replaces lwz r3, 0x58(r31) behind the ammunition count of the HUD in play (r31 = the
#   widget, +0 its icon, ICON_BASE + item; r30/r27 and r21 = where the count is; f30 = fade).
# hud_flash: replaces ori r3, r30, 0 behind the HUD's loop over its widgets (r31 = they are drawn):
#   it counts the flash's frames. A rectangle drawn there did not show in game, so the flash is
#   drawn from ammo_bar, with the ammunition widget, which is on screen when a weapon is used.
BAR = """
bar:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0xe0(1)
    std 31, 0x80(1)
    std 30, 0x88(1)
    std 29, 0x90(1)
    stfd 31, 0xd0(1)
    fmr 31, 1
    std 4, 0xa8(1)
    std 5, 0xb0(1)
    std 6, 0xc8(1)
    std 7, 0xa0(1)
    cmplwi 3, {LAST_ITEM}
    bgt hb_out
    lis 30, {POOL_HA}
    addi 30, 30, {POOL_LO}
    addi 10, 30, {P_XP_AT}
    lbzx 10, 10, 3
    cmpwi 10, {NO_WEAPON}
    beq hb_out
    lis 11, {AMMO_HA}
    addi 11, 11, {AMMO_LO}
    lhzx 31, 11, 10                 # the experience
    slwi 12, 3, 1
    addi 11, 30, {P_XP_NEEDED}
    lhzx 12, 11, 12                 # what level 2 takes
    lis 11, {GOLD_HA}
    addi 11, 11, {GOLD_LO}
    lbzx 11, 11, 3
    lis 29, {STATE_HA}
    addi 29, 29, {STATE_LO}
    ld 9, 0xa0(1)
    cmpwi 9, 0
    bgt hb_width
@TUNE 9 0x108 BAR_WIDTH@
hb_width:
    cmpwi 11, 0
    bne hb_full
    cmplwi 31, 0xffff
    beq hb_full
    mullw 31, 31, 9
    divwu 31, 31, 12
@TUNE 11 0x110 BAR_FILL@
    b hb_place
hb_full:
    mr 31, 9
@TUNE 11 0x114 BAR_FULL@
hb_place:
    std 11, 0x98(1)
    std 9, 0xa0(1)
    ld 10, 0xa8(1)
    ld 6, 0xc8(1)
    cmpwi 6, 0
    beq hb_left
    srawi 8, 9, 1
    subf 10, 8, 10
hb_left:
    ld 8, 0xb0(1)
@TUNE 7 0x10c BAR_HEIGHT@
    add 7, 8, 7
    std 10, 0xa8(1)
    std 7, 0xb8(1)
@TUNE 4 0x118 BAR_BACK@
    extsw 4, 4                      # the background, faded as the HUD is
    clrlwi 3, 4, 8
    fmr 1, 31
    bl {FADE}
    mr 7, 3
    ld 3, 0xa8(1)
    ld 4, 0xb0(1)
    ld 9, 0xa0(1)
    add 5, 3, 9
    ld 6, 0xb8(1)
    extsw 3, 3
    extsw 4, 4
    extsw 5, 5
    extsw 6, 6
    clrldi 7, 7, 32
    li 8, 0
    bl {FILL_RECT}
    cmpwi 31, 0
    ble hb_out
    ld 4, 0x98(1)
    extsw 4, 4
    clrlwi 3, 4, 8
    fmr 1, 31
    bl {FADE}
    mr 7, 3
    ld 3, 0xa8(1)
    ld 4, 0xb0(1)
    add 5, 3, 31
    ld 6, 0xb8(1)
    extsw 3, 3
    extsw 4, 4
    extsw 5, 5
    extsw 6, 6
    clrldi 7, 7, 32
    li 8, 0
    bl {FILL_RECT}
hb_out:
    lfd 31, 0xd0(1)
    ld 29, 0x90(1)
    ld 30, 0x88(1)
    ld 31, 0x80(1)
    addi 1, 1, 0xe0
    ld 0, 0x10(1)
    mtlr 0
    blr

hud_bar:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 3, 0x70(1)
    std 4, 0x78(1)
    lis 9, {STATE_HA}
    addi 9, 9, {STATE_LO}
    lis 4, {HUD_X_HA}
    lwz 4, {HUD_X_LO}(4)
    add 4, 4, 18
    lwz 8, 0x100(9)
    add 4, 4, 8
    lis 5, {HUD_Y_HA}
    lwz 5, {HUD_Y_LO}(5)
    add 5, 5, 28
    addi 5, 5, {BAR_BELOW}
    lwz 8, 0x104(9)
    add 5, 5, 8
    li 6, 1                         # centred as the count is
    li 7, 0
    lis 8, {POOL_HA}
    addi 8, 8, {POOL_LO}
    lfs 1, {P_ONE}(8)
    bl bar
    ld 4, 0x78(1)
    ld 3, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    extsw 5, 3                      # the displaced instruction
    blr

menu_bar:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 30, 0x70(1)
    bl box_grow
    li 9, 24
    divwu 30, 25, 9                 # the item
    mr 3, 30
    lis 9, {STATE_HA}
    addi 9, 9, {STATE_LO}
    lwz 4, 0x20(31)
    srawi 4, 4, 1
    lwz 8, 0x170(9)
    add 4, 4, 8
    li 5, {MENU_BAR_Y}
    lwz 8, 0x174(9)
    add 5, 5, 8
    li 6, 1
    li 7, {MENU_BAR_WIDTH}
    lis 8, {POOL_HA}
    addi 8, 8, {POOL_LO}
    lfs 1, {P_ONE}(8)
    bl bar
    mr 4, 30
    bl xp_words
    bl {MENU_TEXT_DONE}
    ld 30, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

# box_grow: the ammunition box's frame MENU_BOX_GROW taller at its bottom (the last pose of
#   animation MENU_BOX_ANIM of the menu frames' model, recognised by its width and x).
box_grow:
    lis 3, {CLASS_SLOT_MAP_HA}
    addi 3, 3, {CLASS_SLOT_MAP_LO}
    lbz 4, {MENU_FRAME_CLASS}(3)
    cmplwi 4, {MODEL_SLOTS}
    bgelr
    slwi 4, 4, 2
    lis 5, {MODEL_TABLE_HA}
    addi 5, 5, {MODEL_TABLE_LO}
    lwzx 5, 5, 4
    cmpwi 5, 0
    beqlr
    lwz 5, {MENU_BOX_ANIM_OFF}(5)
    cmpwi 5, 0
    beqlr
    lbz 4, 0x10(5)                  # frames
    slwi 4, 4, 2
    add 4, 4, 5
    lwz 4, 0x18(4)                  # the last pose
    lha 6, 0x3a(4)
    cmpwi 6, {MENU_BOX_X}
    bnelr
    lha 6, 0x42(4)
    cmpwi 6, {MENU_BOX_HALF_W}
    bnelr
    lis 9, {STATE_HA}
    addi 9, 9, {STATE_LO}
    lwz 6, 0x184(9)
    cmpwi 6, 0
    bne bg_set
    li 6, {MENU_BOX_GROW}
bg_set:
    srawi 6, 6, 1                   # half of it to the half height, as much down for the centre
    addi 7, 6, {MENU_BOX_HALF_H}
    sth 7, 0x44(4)
    sth 7, 0x4c(4)
    neg 7, 7
    sth 7, 0x54(4)
    sth 7, 0x5c(4)
    neg 6, 6
    addi 6, 6, {MENU_BOX_Y}
    sth 6, 0x3c(4)
    blr

# menu_count: replaces lwz r3, 0x24(r31) where the count's box is set up: the count stays in
#   the top MENU_COUNT_H of the taller box.
menu_count:
    lwz 3, 0x24(31)                 # the displaced instruction
    lis 9, {STATE_HA}
    addi 9, 9, {STATE_LO}
    lwz 10, 0x188(9)
    cmpwi 10, 0
    bne mc_set
    li 10, {MENU_COUNT_H}
mc_set:
    cmpw 10, 3
    bgelr
    mr 3, 10
    blr

xp_words:                           # (r4 item, r31 the box's widget)
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0xe0(1)
    std 29, 0xc8(1)
    std 30, 0xd0(1)
    mr 30, 4
    cmplwi 30, {LAST_ITEM}
    bgt mx_done
    lis 8, {POOL_HA}
    addi 8, 8, {POOL_LO}
    addi 9, 8, {P_XP_AT}
    lbzx 10, 9, 30
    cmpwi 10, {NO_WEAPON}
    beq mx_done
    lis 9, {AMMO_HA}
    addi 9, 9, {AMMO_LO}
    lhzx 5, 9, 10
    lis 9, {GOLD_HA}
    addi 9, 9, {GOLD_LO}
    lbzx 11, 9, 30
    cmpwi 11, 0
    bne mx_max
    cmplwi 5, 0xffff
    beq mx_max
    slwi 12, 30, 1
    addi 9, 8, {P_XP_NEEDED}
    lhzx 6, 9, 12
    addi 4, 8, {P_XP_TEXTS}
    lis 29, {MENU_TEXT_COLOUR_HI}
    ori 29, 29, {MENU_TEXT_COLOUR_LO}
    b mx_print
mx_max:
    addi 4, 8, {P_XP_TEXTS}
    addi 4, 4, {XP_TEXT_MAX}
    lis 29, {BAR_FULL_HI}
    ori 29, 29, {BAR_FULL_LO}
mx_print:
    addi 3, 1, 0x70
    bl {SPRINTF}
    li 0, 0                         # where: see MENU_XP_X/MENU_XP_Y
    std 0, 0xa0(1)
    std 0, 0xa8(1)
    std 0, 0xb0(1)
    lis 9, {STATE_HA}
    addi 9, 9, {STATE_LO}
    lwz 5, 0x178(9)
    addi 5, 5, {MENU_XP_Y}
    sth 5, 0xa0(1)
    addi 6, 5, {MENU_XP_HEIGHT}
    sth 6, 0xa2(1)
    lwz 7, 0x180(9)
    addi 7, 7, {MENU_XP_X}
    sth 7, 0xa4(1)
    lwz 4, 0x20(31)
    add 8, 4, 7
    sth 8, 0xa6(1)
    srawi 4, 4, 1
    add 4, 4, 7
    sth 4, 0xa8(1)
    addi 6, 5, {MENU_XP_HEIGHT_HALF}
    sth 6, 0xaa(1)
    li 4, 0x10
    sth 4, 0xb0(1)
    li 4, 3
    sth 4, 0xb2(1)
    addi 3, 1, 0xa0
    clrldi 4, 29, 32
    addi 5, 1, 0x70
    li 6, -1
    bl {DRAW_TEXT}
mx_done:
    ld 29, 0xc8(1)
    ld 30, 0xd0(1)
    addi 1, 1, 0xe0
    ld 0, 0x10(1)
    mtlr 0
    blr

ammo_bar:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lwz 3, 0(31)
    lis 8, {ICON_BASE_HI}
    ori 8, 8, {ICON_BASE_LO}
    subf 3, 8, 3
    lis 9, {STATE_HA}
    addi 9, 9, {STATE_LO}
    lis 4, {AMMO_X_HA}
    lwz 4, {AMMO_X_LO}(4)
    add 4, 4, 30
    addi 4, 4, {AMMO_BAR_LEFT}
    lwz 8, 0x120(9)
    add 4, 4, 8
    lis 5, {AMMO_Y_HA}
    lwz 5, {AMMO_Y_LO}(5)
    add 5, 5, 21
    addi 5, 5, {AMMO_BAR_BELOW}
    lwz 8, 0x124(9)
    add 5, 5, 8
    li 6, 0
    addi 7, 27, -{AMMO_BAR_SHORTER}
    fmr 1, 30
    bl bar
    bl flash
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    lwz 3, 0x58(31)                 # the displaced instruction
    blr

hud_flash:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    cmpwi 31, 0
    beq hf_out
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x130(11)               # frames of the flash left: it fades with them
    cmpwi 12, 0
    ble hf_out
    addi 12, 12, -1
    stw 12, 0x130(11)
hf_out:
    bl weapon_gold
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    ori 3, 30, 0                    # the displaced instruction
    blr

weapon_gold:                        # r31 = the weapon, r30 = its colour, r29 = it is to be set, r28 = FX
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x90(1)
    std 31, 0x70(1)
    std 30, 0x78(1)
    std 29, 0x80(1)
    std 28, 0x88(1)
    lis 28, {FX_HA}
    addi 28, 28, {FX_LO}
    lis 12, {HERO_HA}
    addi 12, 12, {HERO_LO}
    lbz 10, 0x20a4(12)
    cmpwi 10, 0
    bne wg_out
    lis 9, {STATE_HA}
    addi 9, 9, {STATE_LO}
    lwz 8, 0x15c(9)                 # frames of a level-up left (r8)
    lwz 7, 0x70(28)
    subf 7, 8, 7                   # r7 = frames into it
    cmpwi 8, 0
    ble wg_weapon
    lwz 10, 0x80(28)                # Ratchet glows
    cmpw 7, 10
    bge wg_weapon
    lwz 9, 0x2080(12)
    lwz 10, 0x7c(28)
    stw 10, 0x38(9)
wg_weapon:
    lwz 31, {HAND_MOBY}(12)
    cmpwi 31, 0
    beq wg_out
    lwz 10, {HAND_ITEM}(12)
    cmplwi 10, {LAST_ITEM}
    bgt wg_out
    li 29, 0
@NOGOLD2 wg_other@
    li 29, 1                        # a level 2 weapon without a gold version: gold
    lis 9, {STATE_HA}
    addi 9, 9, {STATE_LO}
    lwz 30, 0x158(9)
    cmpwi 30, 0
    bne wg_flash
    lis 30, {WEAPON_TINT_HI}
    ori 30, 30, {WEAPON_TINT_LO}
    b wg_flash
wg_other:                           # any other weapon has its own colour, which is kept through a level-up
    cmpwi 8, 0
    bgt wg_keep
    li 0, 0
    stw 0, 0xa8(28)
    b wg_out
wg_keep:
    lwz 9, 0xa8(28)
    cmpw 9, 31
    beq wg_kept
    stw 31, 0xa8(28)
    lwz 9, 0x38(31)
    stw 9, 0xac(28)
wg_kept:
    lwz 30, 0xac(28)
    li 29, 1
wg_flash:                           # in the first frames of a level-up: on its way there from the flash's colour
    cmpwi 8, 0
    ble wg_set
    lwz 6, 0x74(28)
    cmpw 7, 6
    bge wg_set
    subf 7, 7, 6                    # frames of it to go
    lwz 3, 0x78(28)
    li 5, 0
    li 12, 0
wg_mix:                             # byte by byte
    srw 9, 3, 5
    andi. 9, 9, 0xff
    srw 10, 30, 5
    andi. 10, 10, 0xff
    subf 9, 10, 9
    mullw 9, 9, 7
    divw 9, 9, 6
    add 9, 9, 10
    slw 9, 9, 5
    or 12, 12, 9
    addi 5, 5, 8
    cmpwi 5, 24
    blt wg_mix
    mr 30, 12
wg_set:
    cmpwi 29, 0
    beq wg_out
    stw 30, 0x38(31)
wg_out:
    ld 28, 0x88(1)
    ld 29, 0x80(1)
    ld 30, 0x78(1)
    ld 31, 0x70(1)
    addi 1, 1, 0x90
    ld 0, 0x10(1)
    mtlr 0
    blr

flash:                              # the level-up flash, while its frames run
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 29, 0x70(1)
    lis 29, {STATE_HA}
    addi 29, 29, {STATE_LO}
    lwz 9, 0x130(29)
    cmpwi 9, 0
    ble flash_out
    lis 8, {FX_HA}
    addi 8, 8, {FX_LO}
    lwz 10, 0xa4(8)
    mullw 9, 9, 10
    lwz 10, 0xa0(8)
    divw 9, 9, 10
    slwi 9, 9, 24
@TUNE 7 0x128 FLASH_COLOUR@
    clrlwi 7, 7, 8
    or 7, 7, 9
    clrldi 7, 7, 32
@TUNE 3 0x14c FLASH_LEFT@
@TUNE 4 0x150 FLASH_TOP@
    extsw 3, 3
    extsw 4, 4
@TUNE 5 0x144 FLASH_RIGHT@
@TUNE 6 0x148 FLASH_BOTTOM@
    li 8, 0
    bl {FILL_RECT}
flash_out:
    ld 29, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr
"""


# icon_gold: replaces bl ICON for the ammunition widget (r3): a level 2 weapon's icon is tinted.
# quick_icon: the same for an entry of the QuickSelect.
# icon_lookup: jumped to from the top of ICON_SPRITE (r3 = icon id); menu_tint: replaces
#   or r6, r6, r7 in ICON_DRAW, its own place for the colour (r7 and r9 are free there).
# tint: replaces or r4, r5, r8 in DRAW_QUAD, where r5 is the alpha and r8 the grey.
ICONS = """
quick_icon:
    lis 10, {QUICK_LISTS_HA}
    lwz 10, {QUICK_LISTS_LO}(10)
    lis 11, {QUICK_LIST_HA}
    lwz 11, {QUICK_LIST_LO}(11)
    slwi 11, 11, 2
    lwzx 10, 10, 11
    add 10, 10, 23
    lwz 10, 0x18(10)
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    cmplwi 10, {LAST_ITEM}
    bgt qi_draw
@NOGOLD2 qi_draw@
    lis 12, {STATE_HA}
    addi 12, 12, {STATE_LO}
    li 11, 1
    stw 11, 0x138(12)
qi_draw:
    bl {ICON}
    lis 12, {STATE_HA}
    addi 12, 12, {STATE_LO}
    li 11, 0
    stw 11, 0x138(12)
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

icon_gold:
    lwz 10, 0(3)
    lis 11, {ICON_BASE_HI}
    ori 11, 11, {ICON_BASE_LO}
    subf 10, 11, 10
icon_item:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    cmplwi 10, {LAST_ITEM}
    bgt ig_draw
@LEVEL2 ig_draw@
    lis 12, {STATE_HA}
    addi 12, 12, {STATE_LO}
    li 11, 1
    stw 11, 0x138(12)
ig_draw:
    bl {ICON}
    lis 12, {STATE_HA}
    addi 12, 12, {STATE_LO}
    li 11, 0
    stw 11, 0x138(12)
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

icon_lookup:
    lis 12, {STATE_HA}
    addi 12, 12, {STATE_LO}
    li 11, 0
    stw 11, 0x154(12)
    lis 11, {ICON_BASE_HI}
    ori 11, 11, {ICON_BASE_LO}
    subf 10, 11, 3
    cmplwi 10, {LAST_ITEM}
    bgt il_out
@NOGOLD2 il_out@
    li 11, 1
    stw 11, 0x154(12)
il_out:
    lis 5, 0xa2                     # the displaced instruction
    b {ICON_SPRITE_BACK}

menu_tint:
    or 6, 6, 7                      # the displaced instruction
    lis 7, {STATE_HA}
    addi 7, 7, {STATE_LO}
    lwz 9, 0x154(7)
    cmpwi 9, 0
    beqlr
    li 9, 0
    stw 9, 0x154(7)
    lwz 9, 0x13c(7)
    cmpwi 9, 0
    bne menu_tint_set
    lis 9, {TINT_HI}
    ori 9, 9, {TINT_LO}
menu_tint_set:
    rlwinm 6, 6, 0, 0, 7
    or 6, 6, 9
    blr

preview_gold:
    lis 3, 0x95                     # the displaced instruction
    mr 12, 24
    b model_gold
figure_gold:
    lis 3, 0x70                     # the displaced instruction
    mr 12, 28
model_gold:
    mr 10, 29
    cmplwi 10, {LAST_ITEM}
    bgtlr
@NOGOLD2 mg_out@
    lis 11, {WEAPON_TINT_HI}
    ori 11, 11, {WEAPON_TINT_LO}
    stw 11, 0x38(12)
mg_out:
    blr
"""

TINT_QUADS = """
tint:
    or 4, 5, 8                      # the displaced instruction
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x138(11)
    cmpwi 12, 0
    bne tint_do
    lwz 12, 0x154(11)               # or the icon a menu looked up last
    cmpwi 12, 0
    beqlr
    li 12, 0
    stw 12, 0x154(11)
tint_do:
    lwz 12, 0x13c(11)
    cmpwi 12, 0
    bne tint_set
    lis 12, {TINT_HI}
    ori 12, 12, {TINT_LO}
tint_set:
    rlwinm 4, 4, 0, 0, 7            # the alpha stays
    or 4, 4, 12
    blr
"""


# gold_name: jumped to from the top of TEXT_LOOKUP (r3 = text id; a leaf function, so everything
#   volatile is free).
GOLD_NAME = """
gold_name:
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    addi 10, 9, {P_NAMES}           # for each of the five: u16 text id, u8 place of its experience, u8 number
    li 11, {NAME_COUNT}
    mtctr 11
gn_next:
    lhz 12, 0(10)
    cmpw 12, 3
    beq gn_found
    addi 10, 10, 4
    bdnz gn_next
gn_plain:
    lis 5, 0x97                     # the displaced instruction
    b {TEXT_LOOKUP_BACK}
gn_found:
    lbz 11, 2(10)
    lis 12, {AMMO_HA}
    addi 12, 12, {AMMO_LO}
    lhzx 11, 12, 11
    cmplwi 11, 0xffff
    bne gn_plain
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    lbz 11, 3(10)
    std 11, 0x70(1)
    lis 5, 0x97
    bl {TEXT_LOOKUP_BACK}           # the game's name
    ld 11, 0x70(1)
    mulli 11, 11, {NAME_SIZE}
    lis 12, {NAME_BUFFERS_HA}
    addi 12, 12, {NAME_BUFFERS_LO}
    add 12, 12, 11
    addi 10, 12, {NAME_PREFIX_END}  # behind the prefix
    addi 3, 3, -1
    li 11, {NAME_ROOM}
    mtctr 11
gn_copy:
    lbzu 9, 1(3)
    stbu 9, 1(10)
    cmpwi 9, 0
    beq gn_done
    bdnz gn_copy
    li 9, 0
    stb 9, 1(10)
gn_done:
    mr 3, 12
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr
"""
