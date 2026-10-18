"""The Charge Boots as an item of their own under Foot Items on the pause menu's Gadgets page:
the grid's third entry, its name and help text, its model preview, its icon and the wider box."""
from ..game import *  # noqa: F401,F403

# Pause menu, Gadgets page (widgets from 0x729ec0): four grids of 10-byte entries {+0 icon,
# +2 icon variant, +4 kind, +6 item id}; a grid is {+0x3c cursor, +0x40 rows, +0x44 columns,
# +0x48 entries}. MENU +4 is the page (+0x40 its focused widget), +0x30 the item worn per slot:
# copied from the slots when the menu opens, and whatever differs when it closes is requested
# from the slot manager. The confirm button puts the entry's item into its slot's word, or 0 if
# it is there already (foot and head items). The grid draws an entry only when its item is
# unlocked, and framed when it is the one in its slot's word.
# The Foot Items grid (FOOT_GRID, 1 x 2: Grindboots, Magneboots) is pointed at an embedded
# table with a third entry and made 1 x 3. That entry is recognised by its address:
#   * drawn always, framed while the foot mode is 0 (GRID_ENTRY_HOOK)
#   * the confirm button toggles the foot mode and sets the slot's word (GRID_PRESS_HOOK)
#   * the name widget (item table as its text array) gets an embedded string (TEXT_HOOK)
#   * the model preview shows the Charge Boots: CHARGE_CLASS is a second class id for the
#     boots' model slot, so the preview sees another class than the Grindboots' and makes a new
#     moby (PREVIEW_CLASS_HOOK, PREVIEW_SPAWN_HOOK)
# and the Grindboots entry is not framed while the Charge Boots are on (both are item 0x1d).
#
# Icons: ICON_SPRITE(icon id, version) looks the id up in the list at HUD +0x1c ({id, versions,
# first sprite, -} per icon) and returns a sprite number; ICON_DRAW(sprite, x, y, w, h, alpha)
# takes the sprite's texture index from the words at HUD +0x20 and draws the entry at
# level texture table + 0x24 * index. Item icons are 64x64 DXT5 textures without mips, version 0
# a black shape (not in use), version 1 a white one (worn). The Charge Boots' two textures
# (tools/icon.py) go into the graphics heap behind the boots' texture. For the length of one
# ICON_DRAW call the Grindboots sprite's texture index is replaced by one that leads to an own
# entry: the index may be negative, and the entry is copied to the first address in ICON_SLOTS
# that is a whole number of entries away from the level's table.
#
# Size of a box on the menu pages: each of a page's 14 frames is a moby of class 0x472 playing
# one animation of that model (the page's animation ids are its first 14 words; the Foot Items
# box is 0x26, the Head Items box 0x25). The frame's update 0x1dbdb0 takes width and height from
# the positions of joints 1 to 3 against joint 0. In the animation's last frame, the pose that
# stays, the translations are 16-bit words: +0x38 the root's x, y, z and from +0x40 one
# {x, y, z, joint << 8} per corner. The Foot Items box has its root at y 5303 with the corners
# at +-2394, the wider boxes above it at 4306 with +-3425; foot_box writes those values into the
# Foot Items pose of the loaded level.
MENU = 0xA52BB0
FOOT_GRID = 0x72A1B0
FOOT_GRID_TABLE = 0x72A290
FOOT_ICONS = (0xEA7D, 0xEA7C, 0xEA7D)   # Grindboots, Magneboots; the Charge Boots borrow the Grindboots' sprite
CHARGE_NAME = b"Charge Boots"
CHARGE_HELP = b"Tap \x15 twice and hold it to dash on the \x0cCharge Boots\x08."   # \x15: R1; \x0c..\x08: highlight
GRID_ENTRY_HOOK = 0x1452BC         # lhz r3, 4(r30): top of the grid's drawing of one entry (r30)
GRID_ENTRY_HOOK_WORD = 0xA07E0004
GRID_SELECTED_HOOK = 0x14533C      # lwz r5, 0x30(r5): the slot's word, compared with the entry's item (r3)
GRID_SELECTED_HOOK_WORD = 0x80A50030
GRID_PRESS_HOOK = 0x142C10         # lhz r3, 6(r30): the confirm button on an entry (r30; r31 widget, r29 MENU)
GRID_PRESS_HOOK_WORD = 0xA07E0006
GRID_PRESS_DONE = 0x142D38
GRID_WORN_HOOK = 0x142C84          # lwz r6, 0x30(r6): the slot's word, compared with the item (r7)
GRID_WORN_HOOK_WORD = 0x80C60030
GRID_EQUIP_HOOK = 0x142D1C         # stwx r3, r4, r5: item r3 goes into the word of slot r5 / 4
GRID_EQUIP_HOOK_WORD = 0x7C64292E
TEXT_HOOK = 0x140B10               # bl TEXT_LOOKUP in the text widget (r30; +0x34 its array of text ids)
PREVIEW_CLASS_HOOK = 0x145DDC      # lwz r24, 0x10(r28): class of the item under the cursor
PREVIEW_CLASS_HOOK_WORD = 0x831C0010
PREVIEW_SPAWN_HOOK = 0x146008      # bl SPAWN for the preview's moby
GRID_ENTRY_NEXT = 0x1453F0         # behind the drawing of one entry
HUD = 0xA1BFC0
ICON_FILES = ("charge_icon0.bin", "charge_icon1.bin")   # art/, drawn by tools/icon.py
ICON_ENTRY = bytes.fromhex("00000000 00018829 00010303 80000000 0000aae4 02063e80 00400040 00100000 00ff0000")   # the Grindboots icon's, without its pixel offset
FOOT_BOX_ANIM = 0x26
FOOT_BOX_NARROW = (5303, 2394)     # root y and the corners' distance from it in the game's own pose
FOOT_BOX_WIDE = (4306, 3425)       # the Head Items box's


# The Charge Boots entry of the Gadgets page (see the comment above ITEM_GRINDBOOTS).
# cursor_on_boots: cr0 eq when the page's focused grid has its cursor on the entry; uses r11, r12.
BOOTS_MENU = """
cursor_on_boots:
    lis 11, {MENU_HA}
    addi 11, 11, {MENU_LO}
    lwz 11, 4(11)
    cmpwi 11, 0
    beq cob_no
    lwz 11, 0x40(11)
    cmpwi 11, 0
    beq cob_no
    lwz 12, 0x3c(11)
    mulli 12, 12, 10
    lwz 11, 0x48(11)
    add 11, 11, 12
    lis 12, {CHARGE_ENTRY_HI}
    ori 12, 12, {CHARGE_ENTRY_LO}
    cmplw 11, 12
    blr
cob_no:
    cmpwi 11, 1
    blr

grid_entry:                         # replaces lhz r3, 4(r30)
    lis 12, {CHARGE_ENTRY_HI}
    ori 12, 12, {CHARGE_ENTRY_LO}
    cmplw 30, 12
    beq grid_entry_boots
    lhz 3, 4(30)                    # the displaced instruction
    blr
grid_entry_boots:                   # the game's two calls for an icon, with the Charge Boots' texture
    stdu 1, -0x90(1)
    std 31, 0x88(1)
    std 30, 0x80(1)
    std 29, 0x78(1)
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x7c(11)
    li 31, 0                        # r31 = version: 1 while they are on
    cmpwi 12, 0
    bne geb_sprite
    li 31, 1
geb_sprite:
    lis 3, 0
    ori 3, 3, {CHARGE_ICON}
    mr 4, 31
    bl {ICON_SPRITE}
    mr 30, 3                        # r30 = sprite
    li 29, 0                        # r29 = the sprite's texture index word, once replaced
    lis 10, {ICON_ENTRIES_HA}
    addi 10, 10, {ICON_ENTRIES_LO}
    lwz 12, 0(10)                   # no pixels yet: the Grindboots' icon
    cmpwi 12, 0
    beq geb_draw
    lis 12, {LEVEL_HA}
    addi 12, 12, {LEVEL_LO}
    lwz 12, 0x1c(12)                # r12 = the level's texture table
    lis 11, {ICON_SLOTS_HI}
    ori 11, 11, {ICON_SLOTS_LO}
    cmplw 12, 11
    ble geb_draw
    subf 9, 11, 12
    li 7, 0x24
    divwu 8, 9, 7
    mullw 6, 8, 7
    subf 6, 6, 9
    add 11, 11, 6                   # r11 = table - 0x24 * r8, inside ICON_SLOTS
    neg 8, 8
    mulli 6, 31, 0x24               # this version's entry
    add 11, 11, 6
    add 10, 10, 6
    add 8, 8, 31                    # r8 = its index
    li 6, 9
    mtctr 6
geb_copy:
    lwz 6, 0(10)
    stw 6, 0(11)
    addi 10, 10, 4
    addi 11, 11, 4
    bdnz geb_copy
    lis 10, {HUD_HA}
    addi 10, 10, {HUD_LO}
    lwz 10, 0x20(10)
    slwi 6, 30, 2
    add 29, 10, 6
    lwz 6, 0(29)
    stw 6, 0x70(1)
    stw 8, 0(29)
geb_draw:
    mr 3, 30
    mr 4, 22                        # position and size as the game passes them at 0x1453d8
    mr 5, 21
    mr 6, 26
    mr 7, 25
    li 8, 0x80
    bl {ICON_DRAW}
    cmpwi 29, 0
    beq geb_out
    lwz 6, 0x70(1)
    stw 6, 0(29)
geb_out:
    ld 29, 0x78(1)
    ld 30, 0x80(1)
    ld 31, 0x88(1)
    addi 1, 1, 0x90
    b {GRID_ENTRY_NEXT}

grid_selected:                      # replaces lwz r5, 0x30(r5); r3 = the entry's item
    lwz 5, 0x30(5)                  # the displaced instruction
    cmpwi 3, {ITEM_GRINDBOOTS}
    bnelr
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x7c(11)
    cmpwi 12, 0
    bnelr
    li 5, -1                        # the item 0x1d in the slot is the Charge Boots
    blr

grid_worn:                          # replaces lwz r6, 0x30(r6); r7 = the item confirmed
    lwz 6, 0x30(6)                  # the displaced instruction
    cmpwi 7, {ITEM_GRINDBOOTS}
    bnelr
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x7c(11)
    cmpwi 12, 0
    bnelr
    li 6, -1
    blr

grid_equip:                         # replaces stwx r3, r4, r5
    stwx 3, 4, 5                    # the displaced instruction
    cmpwi 5, 4
    bnelr
    lis 11, {STATE_HA}              # other boots are put on: the Charge Boots are off
    addi 11, 11, {STATE_LO}
    li 12, 1
    cmpwi 3, {ITEM_GRINDBOOTS}
    bne grid_equip_store
    li 12, 2
grid_equip_store:
    stw 12, 0x7c(11)
    blr

grid_press:                         # replaces lhz r3, 6(r30)
    lis 12, {CHARGE_ENTRY_HI}
    ori 12, 12, {CHARGE_ENTRY_LO}
    cmplw 30, 12
    beq grid_press_boots
    lhz 3, 6(30)                    # the displaced instruction
    blr
grid_press_boots:
    li 3, 0                         # the game's own sound and input delay for a confirmed entry
    li 4, 0x11
    lwz 5, 0x14(31)
    bl {PLAY_MODEL_SOUND}
    li 3, 10
    stw 3, 0x144(29)
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x7c(11)
    cmpwi 12, 0
    li 3, 0                         # taken off: nothing in the foot slot
    li 12, 1
    beq grid_press_store
    li 3, {ITEM_GRINDBOOTS}         # put on
    li 12, 0
grid_press_store:
    stw 12, 0x7c(11)
    stw 3, 0x34(29)
    b {GRID_PRESS_DONE}

menu_text:                          # replaces bl TEXT_LOOKUP
    lwz 12, 0x34(30)
    lis 11, {ITEM_TABLE_HA}
    addi 11, 11, {ITEM_TABLE_LO}
    subf 12, 11, 12
    cmplwi 12, 0x4c                 # a widget that reads its text ids out of the item table
    bge menu_text_plain
    mflr 0
    bl cursor_on_boots
    mtlr 0
    bne menu_text_plain
    lwz 12, 0x34(30)
    lis 11, {ITEM_TABLE_HA}
    addi 11, 11, {ITEM_TABLE_LO}
    lis 3, {CHARGE_NAME_HA}
    addi 3, 3, {CHARGE_NAME_LO}
    cmplw 12, 11
    beqlr
    lis 3, {CHARGE_HELP_HA}
    addi 3, 3, {CHARGE_HELP_LO}
    blr
menu_text_plain:
    b {TEXT_LOOKUP}

preview_class:                      # replaces lwz r24, 0x10(r28); cr1 is in use there
    lwz 24, 0x10(28)                # the displaced instruction
    mflr 0
    bl cursor_on_boots
    mtlr 0
    bnelr
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x88(11)
    cmpwi 12, 0
    beqlr
    li 24, {CHARGE_CLASS}
    blr

preview_spawn:                      # replaces bl SPAWN
    cmpwi 3, {CHARGE_CLASS}
    bne preview_spawn_plain
    li 4, 0
    b charge_spawn
preview_spawn_plain:
    b {SPAWN}
"""

FOOT_BOX = """
foot_box:                           # the Foot Items box as wide as the ones above it
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
    lwz 5, {FOOT_BOX_ANIM_OFF}(5)
    cmpwi 5, 0
    beqlr
    lbz 4, 0x10(5)                  # frames
    cmpwi 4, 0
    beqlr
    slwi 4, 4, 2
    add 4, 4, 5
    lwz 4, 0x18(4)                  # the last frame
    lhz 6, 0x3a(4)
    cmplwi 6, {FOOT_BOX_OLD_Y}
    bnelr
    lhz 6, 0x42(4)
    cmplwi 6, {FOOT_BOX_OLD_HALF}
    bnelr
    li 6, {FOOT_BOX_NEW_Y}
    sth 6, 0x3a(4)
    li 6, {FOOT_BOX_NEW_HALF}
    sth 6, 0x42(4)
    sth 6, 0x52(4)
    neg 6, 6
    sth 6, 0x4a(4)
    sth 6, 0x5a(4)
    blr
"""
