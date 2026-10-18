"""RC2's Charge Boots model on Ratchet's feet: installed from the embedded data into the game's
heaps, and swapped in for the Grindboots' model whenever the Charge Boots are worn."""
import functools
import os
import struct
import sys

from ..game import *  # noqa: F401,F403
from ..rc2 import Extract
from .menu import *  # noqa: F401,F403

ART = os.path.join(os.path.dirname(os.path.abspath(__file__)), "art")

# Boots on Ratchet's feet. RC1's equipment-slot manager (0x85b30) handles four slots; slot 1 is
# the feet. It reads a requested item at hero +0x20b8 + 4*slot, keeps the item to go back to at
# +0x20f0 + 4*slot (0x26 = nothing) and restores it when +0x210c + 4*slot is set. The game
# requests the Grindboots (item 0x1d, two mobys of class 0xc3) this way while grinding.
#
# RC2's Charge Boots are item 0x36 -> two mobys of class 0xe70 (gadget tables: RC1 0x721000,
# 0x4c per item; RC2 0xd0 per item). That model and its 256x256 texture are embedded and
# installed once per boot:
#   * 0x20000 bytes are taken from the top of the main heap (0x90d7c8) and of the graphics heap
#     (0x90d7ec) by lowering their end pointers; model data has to be in memory the graphics
#     side can read (from the I/O base at [[0x8fa564] + 0x4a8]), which the ELF's own segments
#     are not
#   * the model is copied there and prepared by the game's own model fix-up 0xdbc38
#   * its two texture groups are pointed at an own texture entry (same 0x24-byte layout in
#     both games) whose pixels are in the graphics heap
# The model shares the model slot of class 0xc3 (CLASS_SLOT_MAP -> MODEL_TABLE): a moby takes its
# model pointer from that table when it is created (SPAWN), so the Charge Boots model is put
# there for the length of one SPAWN call and the level's own model is put back afterwards. Every
# frame the level's model is looked up again (a level load brings a new one), and the
# environment-mapped group is pointed at that level's texture table.
#
# The item table has no free row (ids 0..0x24 are all in use and other data follows it), so on
# Ratchet's feet the Charge Boots are the Grindboots item 0x1d with the other model: the two foot
# slot SPAWN calls (FOOT_SPAWN_HOOKS) pick the model by the foot mode in STATE and by whether he
# is grinding (state type 0xf, when the game itself asks for the Grindboots). When the boots on
# his feet have the wrong model for the moment, they are taken off, and the game or the port
# puts the right ones on.
#
ITEM_GRINDBOOTS = 0x1D
ITEM_NONE = 0x26
FOOT_REQUEST, FOOT_SAVED, FOOT_CURRENT = 0x20BC, 0x20F4, 0x1108
BOOT_CLASS = 0xC3
MODEL_FIXUP = 0xDBC38         # (r3 model, r6 class)
COPY = 0x50027C               # (r3 dst, r4 src, r5 size)
MAIN_HEAP, GRAPHICS_HEAP = 0x90D7C8, 0x90D7EC   # +8 and +0xc: end of the heap
GCM_PTR = 0x8FA564            # -> struct with +0x4ac graphics memory base
LEVEL = 0xA15F4C              # +0x1c texture table of the loaded level
BOOTS_RESERVE = 0x20000
ITEM_MAGNEBOOTS = 0x1C
STATE_TYPE_GRIND = 0xF        # hero +0x208c
FOOT_REMEMBERED = 0x969C80    # the item the foot slot is meant to hold (0x969c7c + 4 * slot)
CHARGE_CLASS = 0x7C0          # unused by all 19 levels (highest class id there: 0x7b5)
FOOT_SPAWN_HOOKS = (0x9261C, 0x92678)   # bl SPAWN for the left and the right boot in 0x921c0


# boots_tick(): install the Charge Boots model once, find the level's own boot model, and keep
# the right boots on Ratchet's feet for the foot mode.
# charge_spawn(r3 class, r4 = 0 or a word to set to 1): SPAWN with the Charge Boots model in the
#   boots' model slot. Without the model, or when the slot does not hold the model boots_tick saw
#   (a level was loaded since), it is a plain SPAWN and the word is left alone.
# boots_spawn: replaces bl SPAWN for the foot slot's two mobys.
BOOTS_A = """
boots_tick:
    stdu 1, -0x90(1)
    mflr 0
    std 0, 0xa0(1)
    std 31, 0x88(1)
    std 30, 0x80(1)
    std 29, 0x78(1)
    std 28, 0x70(1)
    lis 31, {STATE_HA}
    addi 31, 31, {STATE_LO}
    lis 30, {HERO_HA}
    addi 30, 30, {HERO_LO}
    lwz 29, 0x2c(31)                # r29 = installed model
    cmpwi 29, 0
    bne boots_installed

    lis 3, {MAIN_HEAP_HA}           # take memory from the top of both heaps
    addi 3, 3, {MAIN_HEAP_LO}
    lwz 29, 8(3)
    addis 29, 29, -{RESERVE_HI}
    stw 29, 8(3)
    stw 29, 0xc(3)
    lis 3, {GRAPHICS_HEAP_HA}
    addi 3, 3, {GRAPHICS_HEAP_LO}
    lwz 28, 8(3)
    addis 28, 28, -{RESERVE_HI}
    stw 28, 8(3)
    stw 28, 0xc(3)                  # r28 = pixels

    mr 3, 29                        # model, then the texture entry right behind it
    lis 4, {BOOTS_HA}
    addi 4, 4, {BOOTS_LO}
    lis 5, {MODEL_AND_ENTRY_HI}
    ori 5, 5, {MODEL_AND_ENTRY_LO}
    bl {COPY}
    mr 3, 28
    lis 4, {PIXELS_HA}
    addi 4, 4, {PIXELS_LO}
    lis 5, {PIXELS_SIZE_HI}
    ori 5, 5, {PIXELS_SIZE_LO}
    bl {COPY}

    lis 3, {GCM_PTR_HA}                 # the entry's offset is relative to the graphics memory base
    lwz 3, {GCM_PTR_LO}(3)
    lwz 3, 0x4ac(3)
    subf 3, 3, 28
    lis 4, {MODEL_SIZE_HI}
    ori 4, 4, {MODEL_SIZE_LO}
    add 28, 29, 4                   # r28 = texture entry
    stw 3, 0(28)
    lis 4, {ICON_PIXELS_HI}         # the two icons follow the boots' pixels
    ori 4, 4, {ICON_PIXELS_LO}
    add 3, 3, 4
    lis 4, {ICON_ENTRIES_HA}
    addi 4, 4, {ICON_ENTRIES_LO}
    stw 3, 0(4)
    addi 3, 3, {ICON_BYTES}
    stw 3, 0x24(4)

    mr 3, 29                        # the game's own fix-up turns the offsets into pointers
    li 4, 0
    li 5, 0
    li 6, {BOOT_CLASS}
    bl {MODEL_FIXUP}
    lwz 3, 0(29)                    # mesh
    lwz 4, 8(3)                     # texture groups: both use the embedded texture
    stw 28, 0(4)
    stw 28, 0x10(4)
    li 3, 0xff                      # RC1 models carry 0xff here, RC2's 0
    stb 3, 0xb(29)
    stw 29, 0x2c(31)

boots_installed:
    lis 3, {CLASS_SLOT_MAP_HA}           # the level's own model of class 0xc3
    addi 3, 3, {CLASS_SLOT_MAP_LO}
    lbz 4, {BOOT_CLASS}(3)
    cmplwi 4, {MODEL_SLOTS}
    bge boots_done
    stb 4, {CHARGE_CLASS}(3)        # CHARGE_CLASS names the same model slot
    slwi 4, 4, 2
    lis 5, {MODEL_TABLE_HA}
    addi 5, 5, {MODEL_TABLE_LO}
    lwzx 5, 5, 4
    cmpwi 5, 0
    beq boots_done
    cmpw 5, 29
    beq boots_wear
    stw 5, 0x88(31)
    lwz 3, 0x2c(5)                  # set on the original at load; copied as it is
    stw 3, 0x2c(29)
    lwz 3, 0(29)                    # the environment-mapped group uses the level's texture table
    lwz 3, 0xc(3)
    lis 4, {LEVEL_HA}
    addi 4, 4, {LEVEL_LO}
    lwz 4, 0x1c(4)
    stw 4, 0(3)

boots_wear:
    lwz 3, {FOOT_CURRENT}(30)       # r3 = item on his feet, r4 = made with the Charge Boots model,
    lwz 4, 0x80(31)                 # r5 = foot mode, r7 = state type
    lwz 5, 0x7c(31)
    lwz 7, 0x208c(30)
    cmpwi 3, {ITEM_GRINDBOOTS}
    bne boots_bare
    lis 6, {FOOT_REMEMBERED_HA}     # already being taken off?
    lwz 6, {FOOT_REMEMBERED_LO}(6)
    cmpwi 6, {ITEM_GRINDBOOTS}
    bne boots_done
    cmpwi 7, {STATE_TYPE_GRIND}     # grinding: the Grindboots' own model, and the game puts them on
    beq boots_want_grind
    cmpwi 5, 0
    bne boots_want_grind
    cmpwi 4, 0                      # Charge Boots on: their model
    bne boots_done
    b boots_off
boots_want_grind:
    cmpwi 4, 0
    beq boots_done
    cmpwi 7, {STATE_TYPE_GRIND}
    beq boots_off
    cmpwi 5, 2                      # the Grindboots were put on in the menu: they come back
    bne boots_off
    li 8, 1
    stw 8, 0x84(31)
boots_off:
    li 8, {ITEM_NONE}
    stw 8, {FOOT_REQUEST}(30)
    b boots_done

boots_bare:
    cmpwi 3, 0
    bne boots_done
    lwz 3, {FOOT_REQUEST}(30)
    cmpwi 3, 0
    bne boots_done
    lwz 8, 0x84(31)
    li 3, 0
    stw 3, 0x84(31)
    cmpwi 5, 0
    beq boots_auto
    cmpwi 5, 2
    bne boots_done
    cmpwi 8, 0
    beq boots_done
    b boots_request
boots_auto:
    lwz 3, 0x2084(30)               # Charge Boots on: worn whenever his feet are bare on the ground
    cmpwi 3, {STATE_IDLE}
    beq boots_request
    cmpwi 3, {STATE_WALK}
    bne boots_done
boots_request:
    li 3, {ITEM_GRINDBOOTS}
    stw 3, {FOOT_REQUEST}(30)
    li 3, 0                         # nothing to go back to: set_state (0xbdf78) restores the saved
    stw 3, {FOOT_SAVED}(30)         # item on every state change while the Grindboots are worn
boots_done:
    ld 28, 0x70(1)
    ld 29, 0x78(1)
    ld 30, 0x80(1)
    ld 31, 0x88(1)
    ld 0, 0xa0(1)
    mtlr 0
    addi 1, 1, 0x90
    blr
"""

BOOTS_B = """
charge_spawn:
    stdu 1, -0x80(1)
    mflr 0
    std 0, 0x90(1)
    std 31, 0x78(1)
    std 30, 0x70(1)
    li 31, 0
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 30, 0x2c(11)
    cmpwi 30, 0
    beq cs_spawn
    lwz 12, 0x88(11)
    cmpwi 12, 0
    beq cs_spawn
    lis 11, {CLASS_SLOT_MAP_HA}
    addi 11, 11, {CLASS_SLOT_MAP_LO}
    lbz 11, {BOOT_CLASS}(11)
    slwi 11, 11, 2
    lis 31, {MODEL_TABLE_HA}
    addi 31, 31, {MODEL_TABLE_LO}
    add 31, 31, 11                  # r31 = the boots' entry of the model table
    lwz 11, 0(31)
    cmpw 11, 12
    beq cs_swap
    li 31, 0
    b cs_spawn
cs_swap:
    stw 30, 0(31)
    cmpwi 4, 0
    beq cs_spawn
    li 12, 1
    stw 12, 0(4)
cs_spawn:
    bl {SPAWN}
    cmpwi 31, 0
    beq cs_out
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x88(11)
    stw 12, 0(31)                   # the level's own model again
cs_out:
    ld 30, 0x70(1)
    ld 31, 0x78(1)
    ld 0, 0x90(1)
    mtlr 0
    addi 1, 1, 0x80
    blr

boots_spawn:
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    li 12, 0
    stw 12, 0x80(11)
    cmpwi 3, {BOOT_CLASS}
    bne bs_plain
    lwz 12, 0x7c(11)
    cmpwi 12, 0
    bne bs_plain
    lwz 12, 0x88(11)
    cmpwi 12, 0
    beq bs_plain
    lis 12, {HERO_HA}
    addi 12, 12, {HERO_LO}
    lwz 12, 0x208c(12)
    cmpwi 12, {STATE_TYPE_GRIND}
    beq bs_plain
    addi 4, 11, 0x80
    b charge_spawn
bs_plain:
    b {SPAWN}
"""


@functools.lru_cache(None)
def boots_data(vaddr):
    """The embedded Charge Boots: model, texture entry, padding, pixels (RC2's, then the menu
    icons), the Foot Items table and the menu strings, for the address vaddr, as pieces (see
    mods/rc2.py); and the sizes and addresses the code needs."""
    model, entry, pixels = Extract("boots_model"), Extract("boots_texture_entry"), Extract("boots_pixels")
    icons = [open(os.path.join(ART, name), "rb").read() for name in ICON_FILES]
    icon_pixels = len(pixels)                                # offset of the first icon from the boots' texture
    if icon_pixels % 0x80 or len({len(icon) for icon in icons}) != 1:
        sys.exit("icon textures do not line up")
    pixel_size = len(pixels) + sum(map(len, icons))
    if len(model) % 16 or len(model) + len(entry) + 0x10 > BOOTS_RESERVE or pixel_size > BOOTS_RESERVE:
        sys.exit("boots data does not fit its reservation")
    pieces = [model, entry, bytes(-(len(model) + len(entry)) % 16)]
    size = len(model) + len(entry) + len(pieces[-1])
    pixels_at = vaddr + size
    pieces += [pixels, *icons, bytes(-pixel_size % 16)]
    size += pixel_size + len(pieces[-1])
    blob = bytearray()                                       # the mod's own tables behind them
    tables = vaddr + size
    foot_table = tables + len(blob)
    items = (ITEM_GRINDBOOTS, ITEM_MAGNEBOOTS, ITEM_GRINDBOOTS)      # the third entry is the Charge Boots
    blob += b"".join(struct.pack(">5H", icon, 0, 0, item, 0) for icon, item in zip(FOOT_ICONS, items))
    charge_entry = foot_table + 10 * (len(items) - 1)
    name = tables + len(blob)
    blob += CHARGE_NAME + b"\0"
    text = tables + len(blob)
    blob += CHARGE_HELP + b"\0"
    blob += bytes(-len(blob) % 4)
    icon_entries = tables + len(blob)                  # one texture entry per icon version
    blob += ICON_ENTRY * len(icons)
    icon_slots = tables + len(blob)                    # room for both entries at any of 0x24 offsets
    blob += bytes(len(ICON_ENTRY) * (len(icons) + 1))
    return pieces + [bytes(blob)], dict(
        FOOT_TABLE=foot_table, FOOT_COLUMNS=len(items), CHARGE_ENTRY_HI=charge_entry >> 16, CHARGE_ENTRY_LO=charge_entry & 0xFFFF,
        CHARGE_NAME_HA=ha(name), CHARGE_NAME_LO=lo(name), CHARGE_HELP_HA=ha(text), CHARGE_HELP_LO=lo(text),
        ICON_ENTRIES_HA=ha(icon_entries), ICON_ENTRIES_LO=lo(icon_entries),
        ICON_SLOTS_HI=icon_slots >> 16, ICON_SLOTS_LO=icon_slots & 0xFFFF,
        ICON_PIXELS_HI=icon_pixels >> 16, ICON_PIXELS_LO=icon_pixels & 0xFFFF, ICON_BYTES=len(icons[0]),
        MODEL_AND_ENTRY_HI=(len(model) + len(entry)) >> 16, MODEL_AND_ENTRY_LO=(len(model) + len(entry)) & 0xFFFF,
        MODEL_SIZE_HI=len(model) >> 16, MODEL_SIZE_LO=len(model) & 0xFFFF,
        PIXELS_HA=ha(pixels_at), PIXELS_LO=lo(pixels_at),
        PIXELS_SIZE_HI=pixel_size >> 16, PIXELS_SIZE_LO=pixel_size & 0xFFFF)
