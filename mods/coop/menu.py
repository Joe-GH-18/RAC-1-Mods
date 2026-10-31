"""The Clank Zapper: AI Clank switched on and off as a fourth entry of Back Packs on the pause
menu's Gadgets page (spec 2.1), the way mods/chargeboots/menu.py adds the Charge Boots to Foot
Items, and kept in the save.

The Back Packs grid (PACK_GRID, 1 x 3: Heli-Pack, Thruster-Pack, Hydro-Pack) is pointed at an
embedded table with a fourth entry (ZAPPER_TABLE) and made 1 x 4. The grid spreads its columns
over the widget's width: icon 0.45, margins 0.1 (0x144fc4), so four still fit the box the three
had (gaps of about 0.19 against 0.5), and the box is left as it is. The entry is recognised by
its address at the game's three places for an entry, hooks shared with the Charge Boots:
  * drawn always (coop_grid_entry) with its own icon (art/zapper_icon{0,1}.bin, drawn by
    tools/icon.py: Clank's head and a lightning bolt on the packs' yellow; the game has no Clank
    icon among its 56), the white version while AI Clank is on, as a worn item's
  * the confirm button switches AI Clank on and off (coop_grid_press), with the game's sound
  * its name and help text (coop_menu_text), the help saying which it is now; the text widget
    blanks the text of an item not owned, so its strings pass that test (coop_text_owned)
The icon is drawn the Charge Boots' way (mods/chargeboots/menu.py, "Icons"): its two textures go
into the graphics heap behind Clank's pixels (coop_install, which the entry calls itself: the menu
may come before Clank is first out), with texture entries of their own (ZAPPER_ICON_ENTRIES, +0
filled there); for the length of the one ICON_DRAW the Heli-Pack sprite's texture index
(ZAPPER_CARRIER) leads to a copy of the entry in ZAPPER_SLOTS. Not installed: the Tesla Claw's
lightning (ZAPPER_ICON).
Its item is 1, the Clank on Ratchet's back (class 0x259 in every level), for the model preview
(seen: Ratchet from the front, Clank behind him); the cursor goes onto an entry whatever its item.

The choice is kept in the save as AI_SAVE (u16, 1 = on), the lower half of the Magneboots' int in
the saved ammunition array (0x96c0ac + 4 * item): never held, no ammunition, 0 in a save made
without the mod (read in the user's, 2026-10-27), so the default is off. The weapon levels and
Golden Clank have the spare words of items 0 to 7.
"""
import os
import struct

from ..game import *  # noqa: F401,F403

PACK_GRID = 0x72A0E0
PACK_GRID_TABLE = 0x72A254
PACK_ENTRIES = bytes.fromhex("ea62 0000 0000 0002 0000  ea63 0000 0000 0003 0000  ea64 0000 0000 0004 0000")
ZAPPER_ICON, ZAPPER_ITEM = 0xEA73, 1
ZAPPER_CARRIER = 0xEA62            # the Heli-Pack's icon, whose sprite draws the Zapper's texture
ICON_FILES = ("zapper_icon0.bin", "zapper_icon1.bin")   # art/, drawn by tools/icon.py
ICON_ENTRY = bytes.fromhex("00000000 00018829 00010303 80000000 0000aae4 02063e80 00400040 00100000 00ff0000")   # a 64x64 item icon's (the Grindboots'), without its pixel offset
LEVEL_STRUCT = 0xA15F4C            # +0x1c the loaded level's texture table
MENU_HUD = 0xA1BFC0                # +0x20 the sprites' texture index words
AI_SAVE = 0x96C11E                 # 0x96c0ac + 4 * 0x1c (Magneboots) + 2
MENU = 0xA52BB0
GRID_ENTRY_HOOK = 0x1452BC         # lhz r3, 4(r30): top of the grid's drawing of one entry (r30; r22/r21 x, y, r26/r25 w, h)
GRID_ENTRY_HOOK_WORD = 0xA07E0004
GRID_ENTRY_NEXT = 0x1453F0         # behind the drawing of one entry
GRID_PRESS_HOOK = 0x142C10         # lhz r3, 6(r30): the confirm button on an entry (r30; r31 widget, r29 MENU)
GRID_PRESS_HOOK_WORD = 0xA07E0006
GRID_PRESS_DONE = 0x142D38
TEXT_HOOK = 0x140B10               # bl TEXT_LOOKUP in the text widget (r30; +0x34 its array of text ids)
TEXT_OWNED_HOOK = 0x140B38         # lbzx r4, r4, r25: behind the lookup, the item's owned byte (r29 the string);
TEXT_OWNED_HOOK_WORD = 0x7C84C8AE  # not owned, the string is replaced by an empty one (0x140b44)

ZAPPER_NAME = b"Clank Zapper"
ZAPPER_HELP = (b"\x0cAI Clank\x08 is off. On, he fights when there is no Player 2.",   # \x0c..\x08: highlight
               b"\x0cAI Clank\x08 is on: he fights when there is no Player 2.")


def icon_pixels():
    return [open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "art", name), "rb").read() for name in ICON_FILES]


def menu_data():
    """The grid's table with the Clank Zapper behind the packs, the texts, the icon's texture entries
    and the room for their copies; -> bytes, offsets."""
    data = bytearray(PACK_ENTRIES + struct.pack(">HHHHH", ZAPPER_ICON, 0, 0, ZAPPER_ITEM, 0))
    data.extend(bytes(-len(data) % 4))
    offsets = {}
    for name, text in (("ZAPPER_NAME", ZAPPER_NAME), ("ZAPPER_HELP_OFF", ZAPPER_HELP[0]), ("ZAPPER_HELP_ON", ZAPPER_HELP[1])):
        offsets[name] = len(data)
        data.extend(text + b"\0")
        data.extend(bytes(-len(data) % 4))
    data.extend(bytes(-len(data) % 16))
    offsets["ZAPPER_ICON_ENTRIES"] = len(data)               # one per version
    data.extend(ICON_ENTRY * len(ICON_FILES))
    offsets["ZAPPER_SLOTS"] = len(data)                      # room for both at any of 0x24 offsets
    data.extend(bytes(len(ICON_ENTRY) * (len(ICON_FILES) + 1)))
    return bytes(data), offsets


CODE = r"""
coop_cursor_on_zapper:              # cr0 eq when the page's focused grid has its cursor on the entry; uses r11, r12
    lis 11, {MENU_HA}
    addi 11, 11, {MENU_LO}
    lwz 11, 4(11)
    cmpwi 11, 0
    beq ccz_no
    lwz 11, 0x40(11)
    cmpwi 11, 0
    beq ccz_no
    lwz 12, 0x3c(11)
    mulli 12, 12, 10
    lwz 11, 0x48(11)
    add 11, 11, 12
    lis 12, {ZAPPER_ENTRY_HI}
    ori 12, 12, {ZAPPER_ENTRY_LO}
    cmplw 11, 12
    blr
ccz_no:
    cmpwi 11, 1
    blr

coop_grid_entry:                    # (in place of lhz r3, 4(r30)) the Clank Zapper's icon, white while on
    lis 12, {ZAPPER_ENTRY_HI}
    ori 12, 12, {ZAPPER_ENTRY_LO}
    cmplw 30, 12
    bne coop_grid_entry_next
    stdu 1, -0x90(1)
    std 31, 0x88(1)
    std 30, 0x80(1)
    std 29, 0x78(1)
    lis 29, {COOP_HA}
    addi 29, 29, {COOP_LO}
    bl coop_install                 # (Clank's model, and with it the icon's pixels: once per boot)
    bl coop_preview                 # (the model preview: our Clank zapping while the cursor is here)
    lis 4, {AI_SAVE_HA}             # r31 = version: 1 while on
    lhz 31, {AI_SAVE_LO}(4)
    andi. 31, 31, 1
    lwz 9, {C_MODEL}(29)
    li 29, 0                        # r29 = the sprite's texture index word, once replaced
    cmpwi 9, 0
    bne cge_own
    lis 3, 0                        # not installed: the Tesla Claw's lightning
    ori 3, 3, {ZAPPER_ICON}
    mr 4, 31
    bl {ICON_SPRITE}
    mr 30, 3
    b cge_draw
cge_own:
    lis 3, 0
    ori 3, 3, {ZAPPER_CARRIER}
    mr 4, 31
    bl {ICON_SPRITE}
    mr 30, 3                        # r30 = sprite
    lis 10, {ZAPPER_ICON_ENTRIES_HA}
    addi 10, 10, {ZAPPER_ICON_ENTRIES_LO}
    lis 12, {LEVEL_STRUCT_HA}
    addi 12, 12, {LEVEL_STRUCT_LO}
    lwz 12, 0x1c(12)                # r12 = the level's texture table
    lis 11, {ZAPPER_SLOTS_HA}
    addi 11, 11, {ZAPPER_SLOTS_LO}
    cmplw 12, 11
    ble cge_draw
    subf 9, 11, 12
    li 7, 0x24
    divwu 8, 9, 7
    mullw 6, 8, 7
    subf 6, 6, 9
    add 11, 11, 6                   # r11 = table - 0x24 * r8, inside ZAPPER_SLOTS
    neg 8, 8
    mulli 6, 31, 0x24               # this version's entry
    add 11, 11, 6
    add 10, 10, 6
    add 8, 8, 31                    # r8 = its index
    li 6, 9
    mtctr 6
cge_copy:
    lwz 6, 0(10)
    stw 6, 0(11)
    addi 10, 10, 4
    addi 11, 11, 4
    bdnz cge_copy
    lis 10, {MENU_HUD_HA}
    addi 10, 10, {MENU_HUD_LO}
    lwz 10, 0x20(10)
    slwi 6, 30, 2
    add 29, 10, 6
    lwz 6, 0(29)
    stw 6, 0x70(1)
    stw 8, 0(29)
cge_draw:
    mr 3, 30
    mr 4, 22                        # position and size as the game passes them at 0x1453d8
    mr 5, 21
    mr 6, 26
    mr 7, 25
    li 8, 0x80
    bl {ICON_DRAW}
    cmpwi 29, 0
    beq cge_out
    lwz 6, 0x70(1)
    stw 6, 0(29)
cge_out:
    ld 29, 0x78(1)
    ld 30, 0x80(1)
    ld 31, 0x88(1)
    addi 1, 1, 0x90
    b {GRID_ENTRY_NEXT}
coop_grid_entry_next:
    {CHAIN}

coop_grid_press:                    # (in place of lhz r3, 6(r30)) the confirm button: AI Clank on or off
    lis 12, {ZAPPER_ENTRY_HI}
    ori 12, 12, {ZAPPER_ENTRY_LO}
    cmplw 30, 12
    bne coop_grid_press_next
    li 3, 0                         # the game's own sound and input delay for a confirmed entry
    li 4, 0x11
    lwz 5, 0x14(31)
    bl {PLAY_MODEL_SOUND}
    li 3, 10
    stw 3, 0x144(29)
    lis 11, {AI_SAVE_HA}
    lhz 12, {AI_SAVE_LO}(11)
    xori 12, 12, 1
    andi. 12, 12, 1
    sth 12, {AI_SAVE_LO}(11)
    b {GRID_PRESS_DONE}
coop_grid_press_next:
    {CHAIN}

coop_text_owned:                    # (in place of lbzx r4, r4, r25) the entry's strings count as owned
    lbzx 4, 4, 25                   # the displaced instruction
    lis 12, {ZAPPER_NAME_HA}
    addi 12, 12, {ZAPPER_NAME_LO}
    cmplw 29, 12
    bltlr
    lis 12, {ZAPPER_HELP_ON_HA}
    addi 12, 12, {ZAPPER_HELP_ON_LO}
    cmplw 29, 12
    bgtlr
    li 4, 1
    blr

coop_menu_text:                     # (in place of bl TEXT_LOOKUP) the entry's name and help
    lwz 12, 0x34(30)
    lis 11, {ITEM_TABLE_HA}
    addi 11, 11, {ITEM_TABLE_LO}
    subf 12, 11, 12
    cmplwi 12, 0x4c                 # a widget that reads its text ids out of the item table
    bge coop_menu_text_next
    mflr 0
    bl coop_cursor_on_zapper
    mtlr 0
    bne coop_menu_text_next
    lwz 12, 0x34(30)
    lis 11, {ITEM_TABLE_HA}
    addi 11, 11, {ITEM_TABLE_LO}
    lis 3, {ZAPPER_NAME_HA}
    addi 3, 3, {ZAPPER_NAME_LO}
    cmplw 12, 11
    beqlr
    lis 3, {ZAPPER_HELP_OFF_HA}
    addi 3, 3, {ZAPPER_HELP_OFF_LO}
    lis 11, {AI_SAVE_HA}
    lhz 11, {AI_SAVE_LO}(11)
    cmpwi 11, 0
    beqlr
    lis 3, {ZAPPER_HELP_ON_HA}
    addi 3, 3, {ZAPPER_HELP_ON_LO}
    blr
coop_menu_text_next:
    {CHAIN}
"""
