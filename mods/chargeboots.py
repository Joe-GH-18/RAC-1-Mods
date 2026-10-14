"""Charge Boots: RC2's charge dash, and a boost at the bolt cranks.

A port of RC2's charge state (hero state 0x7b, handler 0x83f5e8 in RC2.ppu.elf) built from
the RC1 counterparts of the functions it calls:
  * press R1 twice within 30 frames, from a ground state, to start; it keeps going while
    R1 is held and for at least 60 frames
  * 30 units/s for the first 60 frames, then 11.5 units/s; 100 units/s^2 up, 15 down
  * steering turns Ratchet relative to his own heading from smoothed stick left/right,
    1.22 rad/s at full stick, a tenth of that during the burst; no stick needed to dash
  * crates ahead are broken, and both feet leave RC2's two-layer trail
  * Ratchet hovers 0.17 above the ground on RC2's spring; there is no gravity and no fall,
    so off a ledge the spring lowers him at 7.5 units/s while the charge goes on
  * RC2's own transitions for the charge state and nothing else: it ends through the skid
    state (R1 released, a magnetic surface, an override animation), and running into a wall
    throws Ratchet back in the bump state, which RC1 has too (0x7a). No jump, no weapons or
    gadgets, no wrench
  * surfaces (ice, lava, water) act on the hovering Ratchet as they do in RC2
RC1 has no charge state, so the port runs in place of hero_update while a charge is active
and Ratchet is in the idle or walk state, and those two states' own transitions and the
weapon/gadget chooser are skipped meanwhile. A per-frame hook in front of hero_main runs the
trigger and RC2's transitions, and hides R1 from the game so Ratchet does not crouch.
The charge animation is RC2's own (Ratchet animation 139), embedded in the ELF, and so are
RC2's charge loop and end sounds (a cut-down copy of one RC2 level sound bank).
The Charge Boots are an entry of their own under Foot Items on the pause menu's Gadgets page,
owned from the start and put on by default. The confirm button there takes them off and puts
them on again, as it does with the Magneboots and Grindboots. While they are on, Ratchet wears
RC2's Charge Boots model (class 0xe70 with its texture, embedded) through RC1's foot slot
whenever the game does not want other boots there; taken off, there is no charge and no boost
at the bolt crank. The Grindboots keep their own model.
RC2's camera tuning for the charge is written to RC1's camera config struct.

Bolt crank boost (not in RC2)
-----------------------------
Double-tapping and holding R1 while Ratchet turns a bolt crank (hero state 0x3b, driven by the
crank's own update 0x32adf8) raises the crank's speed cap from 3.7 to 30 units/s (the charge's
burst speed), with the charge animation, sound and foot trails. Position and facing follow the
circle at once there.
"""
import functools
import os
import struct
import sys

from . import sweep
from .assets import asset, rc2_animation, rc2_sound_bank
from .game import *  # noqa: F401,F403

NAME = "chargeboots"
TITLE = "Charge Boots"
ABOUT = ("Tap R1 twice and hold it: RC2's charge dash, with its animation, sounds and boots model, as an item under "
         "Foot Items on the pause menu. At a bolt crank the same turns the crank at the speed of a charge.")
USES = (sweep,)

# Skid state transitions (RC1 0xc13dc, RC2 0x84e270): with the stick past 0.2 the skid goes on
# to idle or walk. RC2 first tests the lock timer +0x1e0 there (0x84e3d8) and stays in the skid
# while it runs; RC1's block has no such test. SKID_HOOK is the first instruction after RC1's
# stick test.
SKID_HOOK = 0xC14F0                # li r3, 0
# Bolt crank (moby update 0x32adf8, r30 = its variables, hero state 0x3b). The moby moves Ratchet
# round the bolt: the speed at variables +0x1c follows the stick with +-5.5 units/s^2 (table
# 0x32ad58 +0x54/+0x58) and is capped at 3.7 units/s (+0x5c) by the code at CRANK_HOOK, where
# f0 is the new speed, f13 becomes the cap and f11 is 1/60. Not in RC2: double-tapping and
# holding R1 at the crank raises the cap to CRANK_SPEED and drives the speed up
# to it, with the charge sound.
CRANK_HOOK = 0x32BBAC              # fmuls f13, f11, f20
CRANK_HOOK_WORD = 0xEDAB0532
STATE_CRANK = 0x3B
# The crank picks Ratchet's animation from the speed in the block CRANK_ANIM_HOOK..CRANK_ANIM_DONE
# (r28 = hero): 0x3f standing at the wrench, 0x40 pushing, 0x41 pushing fast, each set with
# hero_set_anim(id, 0, 14 frames). While boosting, that block is skipped and RC2's charge
# animation is kept on him instead; afterwards the pushing animation is put back.
CRANK_ANIM_HOOK = 0x32BC94         # lwz r3, 0x2080(r28)
CRANK_ANIM_HOOK_WORD = 0x807C2080
CRANK_ANIM_DONE = 0x32BDF0
CRANK_PUSH_ANIM, CRANK_ANIM_BLEND = 0x40, 14.0
# After the step along the tangent the crank pulls Ratchet back towards the point of its circle
# (radius 1.05, table +0x74) at his new angle: f26/f27 is the offset to that point, f25 its
# length, and the step taken is a spring's, limited to 7 units/s (+0x7c), loaded at
# CRANK_PULL_HOOK. A boosted step leaves the circle by more than that each frame, so while
# boosting the whole offset is taken.
CRANK_PULL_HOOK = 0x32C0A8         # lfs f1, -0x35c0(r29)
CRANK_PULL_HOOK_WORD = 0xC03DCA40
# Ratchet's yaw is turned towards the tangent (his angle on the circle +-pi/2) by at most
# 2 pi rad/s (table +0x0; f27 = 2 pi, f2 = the step per frame at CRANK_TURN_HOOK). A boosted
# crank goes round at about 30 rad/s, so his yaw fell behind and pointed anywhere, e.g. with
# his feet at the bolt. While boosting, the step may be a full turn.
CRANK_TURN_HOOK = 0x32C15C         # fmuls f2, f2, f27
CRANK_TURN_HOOK_WORD = 0xEC4206F2
CRANK_SPEED = 30.0                 # units/s: the burst speed of a charge
CRANK_ACCEL = 90.0                 # units/s^2
SKID_HOOK_WORD = 0x38600000

CHARGE_BUTTON = 0x8        # R1, as in RC2
TAP_WINDOW = 30            # RC2: 30.5 frames between the two presses (chooser table 0x834b48 +0x1c)
STATE_IDLE, STATE_WALK, STATE_SKID, STATE_CROUCH = 0, 2, 3, 4
# RC2's transitions for the charge state (0x84dba8). There is no jump or fall among them.
#   * end through the skid state when hero +0x348 [RC1 +0x308, set while the Magneboots hold on
#     a magnetic surface] or +0x22b8 [RC1 +0x20a8, an override animation is playing] is set, or
#     R1 is released after MIN_FRAMES: end sound, +0x1e0 [RC1 +0x1c4, blocks jump and crouch
#     in the skid state] = 30 frames, set_state(3, 0), animation 6 blended over 11 frames
#   * otherwise, when the wall flag +0x287 [RC1 +0x257] is set and Ratchet either moved less
#     than 0.75 of his velocity (|+0x110| < 0.75 |+0xf0|, RC1 +0x100 and +0xe0) or the probe
#     finds a wall ahead: bump state 0x77. RC1's state 0x7a is the same state (9 units/s
#     backwards, 24 units/s^2, animation 0x29, back to idle when the animation is over); RC1
#     enters it from the long jump.
STATE_BUMP = 0x7A
SKID_LOCK = 30
SKID_ANIM, SKID_ANIM_BLEND = 6, 11.0
BUMP_RATIO = 0.75          # (transition table 0x84ac7c +0x28)
PROBE_HEIGHT = 1.0         # (+0xc)
PROBE_REACH = 1.25         # (+0x70)
# RC2's surface function treats a charging Ratchet within this height of the ground as standing
# on it (0x811548). RC1's counts the frames on the ground at hero +0x300, which stays 0 while
# he hovers.
GROUNDED_HEIGHT = 0.4

# RC2's charge animation is Ratchet animation 139 (set by RC2's set_state case 0x845fd8 with
# blend -2.0). Both games use the same 111-bone skeleton and animation format. At runtime the
# model's animation table (model+0x48) holds absolute pointers, and so do the frame pointers
# in each animation. RC1's table has 134 entries followed by zeroed space up to the mesh at
# +0x2e4 in every level, so slot 134 is free. The animation is loaded through the ELF's
# first unused PT_LOAD entry.
RC2_CHARGE_ANIM = 139
ANIM_SLOT = 134
ANIM_BLEND = -2.0

# RC2's charge sounds are Ratchet's model sound definitions 13 (looping, started on entry by
# RC2 0x82e9f4 with flags 4) and 9 (played once when the charge ends). A definition is 32 bytes;
# +0x18 is the loop type, +0x1a the sound index and +0x1c the bank handle at runtime.
# The index in the file is only the definition's own number: the level loader (RC2 0xb4af2c)
# replaces it per level through the table at engine.ps3 header +0x48: after an 8-byte header,
# one {u16 offset, u16 count} per model, pointing at 32-bit words: a bank word (-1 for Ratchet),
# then one level-bank sound index per definition. (RC1's lists have no bank word.) In RC2
# level 5 Ratchet's definitions 13 and 9 map to level-bank sounds 24 and 20; the two samples,
# a looping one of 0x1e20 bytes and a one-shot of 0x14b0 bytes, are in every RC2 level's bank.
# A cut-down copy of that level bank (all sound entries kept, only these two sounds' sample
# data) is embedded and loaded with the library's load-from-memory call, which the game's own
# loader wrapper 0x505b30 uses too. The loader relocates the bank in place, so it sits in a
# writable segment, with the two definitions, already carrying the mapped indices, in front.
# RC2 0x82e9f4 starts the loop again whenever its voice has ended or been taken over.
SOUND_BANK_LEVEL = 5
SOUND_DEFS = (bytes.fromhex("00000000000000000000000000000000000000000000000000000000" "00000000"),   # loop -> sound 24
              bytes.fromhex("00000000000000000000000000000000000000000000000000000000" "00000000"))   # end -> sound 20
SOUND_LOOP_FLAGS = 4
SOUND_BANK_OFF = 0x40          # bank offset inside the segment; must be 16-byte aligned
BANK_LOAD_FROM_MEM = 0x60AE8C  # (r3 bank image) -> handle, 0 on failure
STOP_VOICE = 0x15CDB0          # (r3 voice slot)

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
BOOTS_FILES = ("rc2_e70_model.bin", "rc2_e70_texentry.bin", "rc2_e70_texture.bin")
ITEM_MAGNEBOOTS = 0x1C
STATE_TYPE_GRIND = 0xF        # hero +0x208c
FOOT_REMEMBERED = 0x969C80    # the item the foot slot is meant to hold (0x969c7c + 4 * slot)
MODEL_SLOTS = 0xE0
CHARGE_CLASS = 0x7C0          # unused by all 19 levels (highest class id there: 0x7b5)
FOOT_SPAWN_HOOKS = (0x9261C, 0x92678)   # bl SPAWN for the left and the right boot in 0x921c0
MENU = 0xA52BB0
FOOT_GRID = 0x72A1B0
FOOT_GRID_TABLE = 0x72A290
FOOT_ICONS = (0xEA7D, 0xEA7C, 0xEA7D)   # Grindboots, Magneboots; the Charge Boots borrow the Grindboots' sprite
CHARGE_NAME = b"Charge Boots"
CHARGE_HELP = b"Tap \x15 twice and hold it to dash on the \x0cCharge Boots\x08."   # \x15: R1; \x0c..\x08: highlight
GRID_ENTRY_HOOK = 0x1452BC         # lhz r3, 4(r30): top of the grid's drawing of one entry (r30)
GRID_ENTRY_HOOK_WORD = 0xA07E0004
GRID_DRAW_ICON = 0x1453BC          # draws the entry's icon; r4 = 1 for the frame
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
TEXT_LOOKUP = 0x7B740              # (r3 text id) -> string
PREVIEW_CLASS_HOOK = 0x145DDC      # lwz r24, 0x10(r28): class of the item under the cursor
PREVIEW_CLASS_HOOK_WORD = 0x831C0010
PREVIEW_SPAWN_HOOK = 0x146008      # bl SPAWN for the preview's moby
PLAY_MODEL_SOUND = 0x15D12C        # (r3 definition index, r4 flags, r5 moby)
GRID_ENTRY_NEXT = 0x1453F0         # behind the drawing of one entry
HUD = 0xA1BFC0
ICON_FILES = ("charge_icon0.bin", "charge_icon1.bin")
ICON_ENTRY = bytes.fromhex("00000000 00018829 00010303 80000000 0000aae4 02063e80 00400040 00100000 00ff0000")   # the Grindboots icon's, without its pixel offset
MENU_FRAME_CLASS = 0x472
FOOT_BOX_ANIM = 0x26
FOOT_BOX_NARROW = (5303, 2394)     # root y and the corners' distance from it in the game's own pose
FOOT_BOX_WIDE = (4306, 3425)       # the Head Items box's

# RC2 charge constants (float table 0x838f7c and transition table 0x84ac7c in RC2.ppu.elf)
MIN_FRAMES = 60            # releasing R1 only ends the charge after this many frames
BURST_FRAMES = 60          # burst speed and reduced steering for this long
ACCEL = 100.0              # units/s^2 towards a higher target        (+0x234)
DECEL = 15.0               # units/s^2 towards a lower target         (+0x158)
TURN_RATE = 1.2217         # rad/s at full stick                      (+0x7c)
BURST_TURN_SCALE = 0.1     #                                          (+0x1a0)
STEER_SMOOTH = 0.17        # per-frame approach of the steering input (+0xdc)
STEER_DEADZONE = 0.2
# Hover: RC2's handler springs Ratchet's height (hero +0x88) towards the ground height plus
# 0.17 with 0xb68728, instead of the walk state's gravity and ground-stick calls. RC1's ground
# height is hero +0x2d8, written every frame by the ground probe 0x7e5e8.
HOVER_HEIGHT = 0.17        # (+0xdc)
HOVER_STIFFNESS = 0.04     # (+0xe8)
HOVER_DAMPING = 0.3        # (+0x10c)
HOVER_MAX_SPEED = 7.5 / 60  # (+0x23c) per frame
HOVER_SNAP = 0.01          # snap when closer than max speed * this (RC2 0xb6871c)
# The ground probe leaves the ground height at 0.0 and the distance (+0x2dc) at 32.0 when it
# finds nothing below. Port safeguard: sink at the maximum speed then, whatever the altitude.
NO_GROUND = 0x42000000
DASH_SWEEP_AHEAD = 3.0     # crate sweep centre: hero+0xd0 + this * hero+0x100   (+0xac)
DASH_SWEEP_RADIUS = 0.57   #                                          (+0x240)
# Camera tuning written every charge frame. The struct is an array of 0xb0-byte configs with
# the same layout in both games (RC2 0x13188a0, RC1 0x721bd0).
CAMERA = 0x721BD0
CAMERA_FIELDS = ((0xA4, 0.017), (0xA8, 0.3), (0x204, 0.025), (0x208, 0.3), (0x2B4, 0.03), (0x2B8, 0.27))
CAMERA_TURN_GAIN = 27.0    # camera turn = clamp(yaw change * gain, +-limit)   (+0x3c, +0x54)
CAMERA_TURN_LIMIT = 1.7
CAMERA_TURN_FIELDS = (0x60, 0x278, 0x1C8)   # -turn, turn/2, turn/2
TRAIL_JOINTS = (0x16, 0x17)
TRAIL_VEC = (-5.0 / 60, 0.0, 0.0, 0.0)   # moby-local drift (RC2 table 0x84ac7c: +0x74 / 60, +0x1c)
TRAIL_DESCRIPTORS = (bytes.fromhex("40ff802000cf60000064004600000019"),   # RC2 0x1318590
                     bytes.fromhex("20ffff0000008000005a002d0000000f"))   # RC2 0x13185a0

# boots_tick(): install the Charge Boots model once, find the level's own boot model, and keep
# the right boots on Ratchet's feet for the foot mode.
# charge_spawn(r3 class, r4 = 0 or a word to set to 1): SPAWN with the Charge Boots model in the
#   boots' model slot. Without the model, or when the slot does not hold the model boots_tick saw
#   (a level was loaded since), it is a plain SPAWN and the word is left alone.
# boots_spawn: replaces bl SPAWN for the foot slot's two mobys.
BOOTS = """
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

# Replaces bl HERO_MAIN: charge trigger and end conditions in front of hero_main.
FRAME = """
frame:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 31, 0x70(1)
    std 30, 0x78(1)
    bl boots_tick
    bl foot_box
    lis 31, {STATE_HA}
    addi 31, 31, {STATE_LO}
    lis 30, {HERO_HA}
    addi 30, 30, {HERO_LO}
    lis 10, {PAD_HA}
    addi 10, 10, {PAD_LO}
    lwz 3, 0xa0(10)
    andi. 4, 3, {CHARGE_BUTTON}    # r4 = R1 held now
    lwz 5, 0(31)                    # r5 = held last frame
    stw 4, 0(31)
    lwz 12, 0x2084(30)              # r12 = hero state
    lwz 6, 8(31)                    # r6 = charge frame counter
    lwz 7, 0x7c(31)                 # Charge Boots taken off: no charge, no boost at the crank
    cmpwi 7, 0
    beq frame_boots_on
    li 7, 0
    stw 7, 4(31)
    stw 7, 0x28(31)
    cmpwi 6, 0
    ble frame_out
    bl charge_off
    b frame_out
frame_boots_on:
    cmpwi 6, 0
    ble frame_idle
    addi 6, 6, 1
    stw 6, 8(31)
    cmpwi 12, {STATE_IDLE}
    beq frame_charging
    cmpwi 12, {STATE_WALK}
    beq frame_charging
    cmpwi 12, {STATE_CROUCH}        # started from a crouch: the game stands him up first
    bne frame_stop                  # anything else (damage, a surface, a cutscene) took over
    cmpwi 4, 0
    bne frame_mask
    cmpwi 6, {MIN_FRAMES}
    ble frame_out
frame_stop:
    bl charge_off
    b frame_out

frame_charging:                     # RC2's transitions for the charge state
    lhz 7, 0x308(30)
    lbz 8, 0x20a8(30)
    or. 7, 7, 8
    bne frame_end
    cmpwi 4, 0
    bne frame_wall
    cmpwi 6, {MIN_FRAMES}
    ble frame_wall
frame_end:
    bl charge_off
    li 3, 1
    stw 3, 0x20(31)                 # RC2 plays the end sound on this exit only
    stw 3, 0x10(31)
    li 3, {SKID_LOCK}
    stw 3, 0x1c4(30)
    li 3, {STATE_SKID}
    li 4, 0
    bl {HERO_SET_STATE}
    lis 5, {POOL_HA}
    addi 5, 5, {POOL_LO}
    lfs 1, {P_SKID_BLEND}(5)
    li 3, {SKID_ANIM}
    li 4, 4
    bl {HERO_SET_ANIM}
    b frame_out
frame_wall:
    lbz 7, 0x257(30)
    cmpwi 7, 0
    beq frame_mask
    addi 3, 30, 0x100
    bl {VEC_LENGTH}
    stfs 1, 0x60(1)
    addi 3, 30, 0xe0
    bl {VEC_LENGTH}
    lis 5, {POOL_HA}
    addi 5, 5, {POOL_LO}
    lfs 2, {P_BUMP_RATIO}(5)
    fmuls 1, 1, 2
    lfs 0, 0x60(1)
    fcmpu 0, 0, 1
    blt frame_bump
    lfs 1, {P_PROBE_HEIGHT}(5)
    lfs 2, {P_PROBE_REACH}(5)
    li 5, 0
    bl {WALL_PROBE}
    cmpwi 3, 0
    beq frame_mask
frame_bump:
    bl charge_off
    li 3, {STATE_BUMP}
    li 4, 1
    bl {HERO_SET_STATE}
    b frame_out

frame_idle:
    lwz 7, 0x28(31)                 # boosting a bolt crank: lasts while R1 is held there
    cmpwi 7, 0
    beq frame_no_crank
    cmpwi 12, {STATE_CRANK}
    bne frame_crank_off
    cmpwi 4, 0
    beq frame_crank_off
    bl charge_sound
    bl charge_trails
    b frame_mask
frame_crank_off:
    li 7, 0
    stw 7, 0x28(31)
    li 7, 1
    stw 7, 0x20(31)                 # end sound
frame_no_crank:
    cmpwi 12, {STATE_SKID}
    beq frame_tap
    li 7, 0
    stw 7, 0x10(31)
frame_tap:
    lwz 7, 4(31)                    # r7 = tap window
    cmpwi 7, 0
    ble frame_first
    addi 7, 7, -1
    stw 7, 4(31)
    cmpwi 4, 0
    beq frame_out
    cmpwi 5, 0
    bne frame_out
    cmpwi 12, {STATE_IDLE}          # RC2 only starts a charge from ground states
    beq frame_start
    cmpwi 12, {STATE_WALK}
    beq frame_start
    cmpwi 12, {STATE_CRANK}
    bne frame_not_crank
    li 7, 1
    stw 7, 0x28(31)
    li 7, 0
    stw 7, 4(31)
    b frame_mask
frame_not_crank:
    cmpwi 12, {STATE_CROUCH}
    bne frame_out
frame_start:
    li 6, 1                         # second press inside the window: start charging
    stw 6, 8(31)
    li 7, 0
    stw 7, 4(31)
    stw 7, 0x14(31)                 # steering input starts centred
    stw 7, 0x24(31)                 # hover at rest
frame_mask:
    lis 10, {PAD_HA}                # hide the button so the game does not crouch
    addi 10, 10, {PAD_LO}
    li 7, {BUTTON_MASK}
    lwz 3, 0xa0(10)
    and 3, 3, 7
    stw 3, 0xa0(10)
    lwz 3, 0xa4(10)
    and 3, 3, 7
    stw 3, 0xa4(10)
    b frame_out
frame_first:
    cmpwi 4, 0
    beq frame_out
    cmpwi 5, 0
    bne frame_out
    li 7, {TAP_WINDOW}              # first tap
    stw 7, 4(31)
frame_out:
    ld 30, 0x78(1)
    ld 31, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
frame_next:
    {CHAIN}

charge_off:                         # r31 = state block: the charge is over, RC2's camera tuning goes
    li 7, 0
    stw 7, 8(31)
{CAMERA_RESET}
    blr
"""

# The hooks that keep RC1's own idle/walk behaviour away from a charging Ratchet.
# chooser: replaces bl CHOOSER. RC2's chooser does nothing in the charge state's type.
# trans: replaces the load of the state in front of the transition switch. RC2's switch has
#   its own case for the charge state; its content runs in the frame hook above.
# skid: RC2's lock on leaving the skid by the stick, for the skid that ends a charge.
# surface: replaces bl SURFACE. Hovering close to the ground counts as standing on it.
GATES = """
chooser:
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 8(11)
    cmpwi 12, 0
    ble chooser_next
    li 3, 0
    blr
chooser_next:
    {CHAIN}

trans:
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 8(11)
    cmpwi 12, 0
    ble trans_next
    lwz 3, 0x2084(19)
    cmpwi 3, {STATE_IDLE}
    beq trans_skip
    cmpwi 3, {STATE_WALK}
    bne trans_next
trans_skip:
    b {TRANS_EXIT}
trans_next:
    {CHAIN}

crank:                              # replaces fmuls f13, f11, f20 (speed cap) in the bolt crank
    fmuls 13, 11, 20                # the displaced instruction
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x28(11)
    cmpwi 12, 0
    beqlr
    lis 11, {POOL_HA}
    addi 11, 11, {POOL_LO}
    lfs 13, {P_CRANK_MAX}(11)       # higher cap, and the speed runs up to it by itself
    lfs 1, {P_CRANK_ACCEL}(11)
    fadds 0, 0, 1
    stfs 0, 0x1c(30)
    blr

crank_pull:                         # replaces lfs f1, -0x35c0(r29): the step back onto the circle
    lfs 1, -0x35c0(29)              # the displaced instruction
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x28(11)
    cmpwi 12, 0
    beqlr
    fmr 1, 25
    blr

crank_turn:                         # replaces fmuls f2, f2, f27: the largest yaw step
    fmuls 2, 2, 27                  # the displaced instruction
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x28(11)
    cmpwi 12, 0
    beqlr
    fmr 2, 27
    blr

crank_anim:                         # replaces lwz r3, 0x2080(r28) in front of the crank's animation choice
    lwz 3, 0x2080(28)               # the displaced instruction
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x28(11)
    lbz 4, 0x53(3)
    lis 11, {POOL_HA}
    addi 11, 11, {POOL_LO}
    cmpwi 12, 0
    bne crank_anim_boost
    cmpwi 4, {ANIM_SLOT}
    bnelr
    li 3, {CRANK_PUSH_ANIM}         # the boost is over: back to pushing
    li 4, 0
    lfs 1, {P_CRANK_BLEND}(11)
    bl {HERO_SET_ANIM}
    b {CRANK_ANIM_DONE}
crank_anim_boost:
    lwz 5, 0x24(3)
    lis 6, {ANIM_HA}
    addi 6, 6, {ANIM_LO}
    stw 6, {ANIM_TABLE_OFF}(5)
    cmpwi 4, {ANIM_SLOT}
    beq crank_anim_done
    li 3, {ANIM_SLOT}
    li 4, 0
    lfs 1, {P_ANIM_BLEND}(11)
    bl {HERO_SET_ANIM}
crank_anim_done:
    b {CRANK_ANIM_DONE}

skid:                               # replaces li r3, 0 behind the skid block's stick test
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x10(11)
    cmpwi 12, 0
    beq skid_on
    lwz 12, 0x1c4(19)
    cmpwi 12, 0
    beq skid_on
    b {TRANS_EXIT}
skid_on:
    li 3, 0                         # the displaced instruction
    blr

surface:
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 8(11)
    cmpwi 12, 0
    ble surface_plain
    lis 11, {HERO_HA}
    addi 11, 11, {HERO_LO}
    lwz 12, 0x2084(11)
    cmplwi 12, {STATE_WALK}
    bgt surface_plain
    cmpwi 12, 1
    beq surface_plain
    lwz 12, 0x300(11)
    cmpwi 12, 0
    bne surface_plain
    lis 12, {POOL_HA}
    addi 12, 12, {POOL_LO}
    lfs 13, {P_GROUNDED}(12)
    lfs 0, 0x2dc(11)
    fabs 0, 0
    fcmpu 0, 0, 13
    bge surface_plain
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    li 12, 1
    stw 12, 0x300(11)
    bl surface_next
    lis 11, {HERO_HA}
    addi 11, 11, {HERO_LO}
    li 12, 0
    stw 12, 0x300(11)
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr
surface_plain:
surface_next:
    {CHAIN}
"""

# Replaces bl HERO_UPDATE: while charging in the idle or walk state, run the port of RC2's
# charge handler instead of the normal state handler.
UPDATE = """
update:
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 8(11)
    cmpwi 12, 0
    ble update_normal
    lis 11, {HERO_HA}
    addi 11, 11, {HERO_LO}
    lwz 12, 0x2084(11)
    cmpwi 12, {STATE_IDLE}
    beq charge_update
    cmpwi 12, {STATE_WALK}
    beq charge_update
update_normal:
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x28(11)
    cmpwi 12, 0
    bne update_tail
    lwz 12, 0x1c(11)
    cmpwi 12, 0
    beq update_tail
    mflr 0                          # the charge is over: stop the loop sound
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 31, 0x70(1)
    mr 31, 11
    mulli 4, 12, 0x70               # only if the voice is still the loop's
    lis 5, {VOICES_HA}
    addi 5, 5, {VOICES_LO}
    add 5, 5, 4
    lwz 6, 0x8(5)
    lis 7, {SOUND_HA}
    addi 7, 7, {SOUND_LO}
    cmpw 6, 7
    bne update_stopped
    addi 3, 12, -1
    bl {STOP_VOICE}
update_stopped:
    li 0, 0
    stw 0, 0x1c(31)
    lwz 3, 0x20(31)
    cmpwi 3, 0
    beq update_unwind
    stw 0, 0x20(31)
    lis 3, {SOUND_HA}
    addi 3, 3, {SOUND_LO}
    addi 3, 3, 0x20                 # the end sound's definition
    li 4, 0
    lis 5, {HERO_HA}
    addi 5, 5, {HERO_LO}
    lwz 5, 0x2080(5)
    li 6, 0
    li 7, 0x400
    bl {PLAY_SOUND_DEF}
update_unwind:
    ld 31, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
update_tail:
update_next:
    {CHAIN}

charge_update:
    stdu 1, -0xf0(1)
    mflr 0
    std 0, 0x100(1)
    std 31, 0xe8(1)
    std 30, 0xe0(1)
    std 29, 0xd8(1)
    stfd 31, 0xc8(1)
    stfd 30, 0xc0(1)
    stfd 29, 0xb8(1)
    lis 31, {HERO_HA}
    addi 31, 31, {HERO_LO}
    lis 30, {STATE_HA}
    addi 30, 30, {STATE_LO}
    lis 29, {POOL_HA}
    addi 29, 29, {POOL_LO}

    lwz 3, 0x2080(31)               # keep RC2's charge animation on Ratchet
    lwz 4, 0x24(3)                  # r4 = model
    lis 5, {ANIM_HA}
    addi 5, 5, {ANIM_LO}
    stw 5, {ANIM_TABLE_OFF}(4)
    lbz 5, 0x53(3)                  # current animation id
    cmpwi 5, {ANIM_SLOT}
    beq cu_anim_set
    li 3, {ANIM_SLOT}
    li 4, 0
    lfs 1, {P_ANIM_BLEND}(29)
    bl {HERO_SET_ANIM}
cu_anim_set:
    li 3, 0                         # hero_set_anim leaves +0xa9c set until the walk handler's
    stw 3, 0xa9c(31)                # animation code clears it, and that handler does not run here

    bl charge_sound

    lfs 1, {P_ONE}(29)              # stick -> target speed and heading, as the walk state does
    li 4, 0
    bl {STICK_TARGET}

    lwz 3, 8(30)                    # target speed and steering scale for this phase
    lfs 31, {P_CRUISE}(29)
    lfs 30, {P_ONE}(29)
    cmpwi 3, {BURST_FRAMES}
    bgt cu_target
    lfs 31, {P_BURST}(29)
    lfs 30, {P_BURST_TURN}(29)
cu_target:
    stfs 31, 0x190(31)

    lfs 1, 0x1d20(31)               # steering input: smoothed -stick_x, clamped to +-1
    fneg 1, 1
    lfs 2, {P_STEER_SMOOTH}(29)
    addi 3, 30, 0x14
    bl {APPROACH}
    lfs 1, 0x14(30)
    lfs 2, {P_ONE}(29)
    fcmpu 0, 1, 2
    ble cu_clamp_low
    fmr 1, 2
cu_clamp_low:
    fneg 2, 2
    fcmpu 0, 1, 2
    bge cu_clamped
    fmr 1, 2
cu_clamped:
    stfs 1, 0x14(30)
    lfs 2, 0x229c(31)               # stick magnitude
    lfs 3, {P_TURN}(29)
    fmuls 29, 3, 2
    fmuls 29, 29, 1
    fmuls 29, 29, 30                # f29 = yaw change this frame
    fabs 2, 2
    lfs 3, {P_DEADZONE}(29)
    fcmpu 0, 2, 3
    ble cu_speed
    lfs 1, {P_ZERO}(29)
    fmr 2, 1
    fmr 3, 29
    bl {ROTATE_HERO}

cu_speed:
    lfs 1, 0x190(31)                # speed approaches the target
    lfs 3, 0x194(31)
    lfs 2, {P_ACCEL}(29)
    fcmpu 0, 1, 3
    bgt cu_approach
    lfs 2, {P_DECEL}(29)
cu_approach:
    addi 3, 31, 0x194
    bl {APPROACH}
    lfs 1, {P_BIG}(29)              # velocity along the hero's own heading
    bl {BUILD_VELOCITY}

    lfs 1, 0x2d8(31)                # hover: spring the height towards ground + 0.17
    lfs 2, {P_HOVER}(29)
    fadds 30, 1, 2                  # f30 = target height
    lfs 2, 0x88(31)
    lwz 3, 0x2dc(31)
    xoris 3, 3, {NO_GROUND_HI}
    cmpwi 3, 0
    bne cu_hover
    lfs 1, {P_BIG}(29)
    fsubs 30, 2, 1
cu_hover:
    fsubs 1, 30, 2
    addi 3, 30, 0x24
    lfs 2, {P_HOVER_K}(29)
    lfs 3, {P_HOVER_D}(29)
    lfs 4, {P_HOVER_MAX}(29)
    bl {SPRING_STEP}
    lfs 1, 0x88(31)
    lfs 2, 0x24(30)
    fadds 1, 1, 2
    stfs 1, 0x88(31)
    fsubs 2, 30, 1
    fabs 2, 2
    lfs 3, {P_HOVER_SNAP}(29)
    fcmpu 0, 2, 3
    bge cu_crates
    stfs 30, 0x88(31)
    li 3, 0
    stw 3, 0x24(30)

cu_crates:
    addi 3, 1, 0x70                 # break crates ahead
    addi 4, 31, 0x100
    lfs 1, {P_AHEAD}(29)
    bl {VEC_SCALE}
    addi 3, 1, 0x70
    mr 4, 3
    addi 5, 31, 0xd0
    bl {VEC_ADD}
    addi 3, 1, 0x70
    lfs 1, {P_DASH_RADIUS}(29)
    bl {CRATE_SWEEP}

    bl charge_trails

    lis 4, {CAMERA_HA}              # RC2's camera tuning for the charge
    addi 4, 4, {CAMERA_LO}
{CAMERA_SET}
    lfs 1, {P_CAM_GAIN}(29)         # the camera swings with the steering
    fmuls 1, 29, 1
    lfs 2, {P_CAM_LIMIT}(29)
    fcmpu 0, 1, 2
    ble cu_cam_low
    fmr 1, 2
cu_cam_low:
    fneg 2, 2
    fcmpu 0, 1, 2
    bge cu_cam_clamped
    fmr 1, 2
cu_cam_clamped:
    fneg 2, 1
    stfs 2, {CAM_TURN_A}(4)
    lfs 2, {P_HALF}(29)
    fmuls 1, 1, 2
    stfs 1, {CAM_TURN_B}(4)
    stfs 1, {CAM_TURN_C}(4)

    lfd 29, 0xb8(1)
    lfd 30, 0xc0(1)
    lfd 31, 0xc8(1)
    ld 29, 0xd8(1)
    ld 30, 0xe0(1)
    ld 31, 0xe8(1)
    ld 0, 0x100(1)
    mtlr 0
    addi 1, 1, 0xf0
    blr

charge_sound:                       # keep the charge loop playing on Ratchet
    stdu 1, -0x80(1)
    mflr 0
    std 0, 0x90(1)
    std 31, 0x78(1)
    std 30, 0x70(1)
    lis 31, {HERO_HA}
    addi 31, 31, {HERO_LO}
    lis 30, {STATE_HA}
    addi 30, 30, {STATE_LO}
    lwz 3, 0x18(30)                 # sound: load the embedded bank once
    cmpwi 3, 0
    bne cu_bank_known
    lis 3, {SOUND_HA}
    addi 3, 3, {SOUND_LO}
    addi 3, 3, {SOUND_BANK_OFF}
    bl {BANK_LOAD_FROM_MEM}
    cmpwi 3, 0
    bne cu_bank_ok
    li 3, -1
cu_bank_ok:
    stw 3, 0x18(30)
    lis 4, {SOUND_HA}
    addi 4, 4, {SOUND_LO}
    stw 3, 0x1c(4)                  # both definitions point at the bank
    stw 3, 0x3c(4)
cu_bank_known:
    cmpwi 3, 0
    blt cu_sound_done
    lis 3, {SOUND_HA}               # r3 = the loop's definition
    addi 3, 3, {SOUND_LO}
    lwz 4, 0x1c(30)                 # (re)start the loop unless its voice is still playing it
    cmpwi 4, 0
    beq cu_sound_start
    mulli 4, 4, 0x70
    lis 5, {VOICES_HA}
    addi 5, 5, {VOICES_LO}
    add 5, 5, 4
    lbz 6, 0x4(5)                   # voice state: r5 = voice + 0x70, as the index is slot + 1
    cmpwi 6, 0
    beq cu_sound_start
    lwz 6, 0x8(5)
    cmpw 6, 3
    beq cu_sound_done
cu_sound_start:
    li 4, {SOUND_LOOP_FLAGS}
    lwz 5, 0x2080(31)
    li 6, 0
    li 7, 0x400
    bl {PLAY_SOUND_DEF}
    addi 4, 3, 1
    stw 4, 0x1c(30)
    cmpwi 3, 0
    blt cu_sound_done
    mulli 4, 4, 0x70                # the voice follows Ratchet, as with RC1's play-model-sound
    lis 5, {VOICES_HA}
    addi 5, 5, {VOICES_LO}
    add 5, 5, 4
    lwz 6, 0x2080(31)
    stw 6, 0x18(5)
cu_sound_done:
    ld 30, 0x70(1)
    ld 31, 0x78(1)
    ld 0, 0x90(1)
    mtlr 0
    addi 1, 1, 0x80
    blr

charge_trails:
    stdu 1, -0xc0(1)
    mflr 0
    std 0, 0xd0(1)
    std 31, 0xb8(1)
    std 29, 0xb0(1)
    lis 31, {HERO_HA}
    addi 31, 31, {HERO_LO}
    lis 29, {POOL_HA}
    addi 29, 29, {POOL_LO}
    lwz 3, 0x2080(31)               # trails from both feet, two layers each
    li 4, {JOINT_A}
    addi 5, 1, 0x80
    bl {JOINT_POS}
    lwz 3, 0x2080(31)
    li 4, {JOINT_B}
    addi 5, 1, 0x90
    bl {JOINT_POS}
    addi 4, 1, 0x80
    addi 6, 29, {P_TRAIL_A}
    bl cu_trail
    addi 4, 1, 0x80
    addi 6, 29, {P_TRAIL_B}
    bl cu_trail
    addi 4, 1, 0x90
    addi 6, 29, {P_TRAIL_A}
    bl cu_trail
    addi 4, 1, 0x90
    addi 6, 29, {P_TRAIL_B}
    bl cu_trail
    ld 29, 0xb0(1)
    ld 31, 0xb8(1)
    ld 0, 0xd0(1)
    mtlr 0
    addi 1, 1, 0xc0
    blr

cu_trail:                           # (r4 position, r6 descriptor)
    lwz 3, 0x2080(31)
    addi 5, 29, {P_TRAIL_VEC}
    li 7, 1
    b {TRAIL}
"""

# RC2's camera tuning: written every frame of a charge, and cleared when it ends.
UPDATE = UPDATE.replace("{CAMERA_SET}", "\n".join(
    f"    lfs 0, {{P_CAM_{off:X}}}(29)\n    stfs 0, {off}(4)" for off, _ in CAMERA_FIELDS))
FRAME = FRAME.replace("{CAMERA_RESET}", "    lis 8, {CAMERA_HA}\n    addi 8, 8, {CAMERA_LO}\n    li 7, 0\n" + "\n".join(
    f"    stw 7, {off}(8)" for off in [off for off, _ in CAMERA_FIELDS] + list(CAMERA_TURN_FIELDS)))


def charge_sound_bank():
    """RC2's level sound bank cut down to the two charge sounds (see assets.rc2_sound_bank)."""
    return rc2_sound_bank(SOUND_BANK_LEVEL, SOUND_DEFS, "rc2_charge_sounds.bin")


@functools.lru_cache(None)
def boots_data(vaddr):
    """The embedded Charge Boots: model, texture entry, padding, pixels, the Foot Items table and
    the menu strings, for the address vaddr; and the sizes and addresses the code needs."""
    model, entry, pixels = (asset("boots", name) for name in BOOTS_FILES)
    icons = [asset("boots", name) for name in ICON_FILES]
    icon_pixels = len(pixels)                                # offset of the first icon from the boots' texture
    if icon_pixels % 0x80 or len({len(icon) for icon in icons}) != 1:
        sys.exit("icon textures do not line up")
    pixels += b"".join(icons)
    if len(model) % 16 or len(model) + len(entry) + 0x10 > BOOTS_RESERVE or len(pixels) > BOOTS_RESERVE:
        sys.exit("boots data does not fit its reservation")
    model = bytearray(model)
    mesh = struct.unpack_from(">I", model, 0)[0]
    groups = struct.unpack_from(">I", model, mesh + 8)[0]
    struct.pack_into(">I", model, groups, 0)             # texture ids: any valid one for the fix-up,
    struct.pack_into(">I", model, groups + 0x10, 0)      # they are replaced by the entry afterwards
    blob = bytes(model) + entry + bytes(-(len(model) + len(entry)) % 16)
    pixels_at = vaddr + len(blob)
    blob += pixels + bytes(-len(pixels) % 16)
    foot_table = vaddr + len(blob)
    items = (ITEM_GRINDBOOTS, ITEM_MAGNEBOOTS, ITEM_GRINDBOOTS)      # the third entry is the Charge Boots
    blob += b"".join(struct.pack(">5H", icon, 0, 0, item, 0) for icon, item in zip(FOOT_ICONS, items))
    charge_entry = foot_table + 10 * (len(items) - 1)
    name = vaddr + len(blob)
    blob += CHARGE_NAME + b"\0"
    text = vaddr + len(blob)
    blob += CHARGE_HELP + b"\0"
    blob += bytes(-len(blob) % 4)
    icon_entries = vaddr + len(blob)                   # one texture entry per icon version
    blob += ICON_ENTRY * len(icons)
    icon_slots = vaddr + len(blob)                     # room for both entries at any of 0x24 offsets
    blob += bytes(len(ICON_ENTRY) * (len(icons) + 1))
    return blob, dict(
        FOOT_TABLE=foot_table, FOOT_COLUMNS=len(items), CHARGE_ENTRY_HI=charge_entry >> 16, CHARGE_ENTRY_LO=charge_entry & 0xFFFF,
        CHARGE_NAME_HA=ha(name), CHARGE_NAME_LO=lo(name), CHARGE_HELP_HA=ha(text), CHARGE_HELP_LO=lo(text),
        ICON_ENTRIES_HA=ha(icon_entries), ICON_ENTRIES_LO=lo(icon_entries),
        ICON_SLOTS_HI=icon_slots >> 16, ICON_SLOTS_LO=icon_slots & 0xFFFF,
        ICON_PIXELS_HI=icon_pixels >> 16, ICON_PIXELS_LO=icon_pixels & 0xFFFF, ICON_BYTES=len(icons[0]),
        MODEL_AND_ENTRY_HI=(len(model) + len(entry)) >> 16, MODEL_AND_ENTRY_LO=(len(model) + len(entry)) & 0xFFFF,
        MODEL_SIZE_HI=len(model) >> 16, MODEL_SIZE_LO=len(model) & 0xFFFF,
        PIXELS_HA=ha(pixels_at), PIXELS_LO=lo(pixels_at),
        PIXELS_SIZE_HI=len(pixels) >> 16, PIXELS_SIZE_LO=len(pixels) & 0xFFFF)


def options(ap):
    ap.add_argument("--burst-speed", type=float, default=30.0, help="units/s for the first second of a charge (RC2: 30)")
    ap.add_argument("--cruise-speed", type=float, default=11.5, help="units/s after that (RC2: 11.5)")
    ap.add_argument("--crank-speed", type=float, default=CRANK_SPEED, help="units/s at a boosted bolt crank (the game's own: 3.7)")


def hooks(args):
    return [
        *(Hook(site, "frame", HERO_MAIN, chain=True) for site in FRAME_HOOKS),
        *(Hook(site, "surface", SURFACE, chain=True) for site in SURFACE_HOOKS),
        Hook(UPDATE_HOOK, "update", HERO_UPDATE, chain=True), Hook(CHOOSER_HOOK, "chooser", CHOOSER, chain=True),
        Hook(TRANS_HOOK, "trans", TRANS_HOOK_WORD, chain=True), Hook(SKID_HOOK, "skid", SKID_HOOK_WORD),
        Hook(CRANK_HOOK, "crank", CRANK_HOOK_WORD), Hook(CRANK_ANIM_HOOK, "crank_anim", CRANK_ANIM_HOOK_WORD),
        Hook(CRANK_PULL_HOOK, "crank_pull", CRANK_PULL_HOOK_WORD), Hook(CRANK_TURN_HOOK, "crank_turn", CRANK_TURN_HOOK_WORD),
        *(Hook(site, "boots_spawn", SPAWN) for site in FOOT_SPAWN_HOOKS),
        Hook(GRID_ENTRY_HOOK, "grid_entry", GRID_ENTRY_HOOK_WORD), Hook(GRID_SELECTED_HOOK, "grid_selected", GRID_SELECTED_HOOK_WORD),
        Hook(GRID_PRESS_HOOK, "grid_press", GRID_PRESS_HOOK_WORD), Hook(GRID_WORN_HOOK, "grid_worn", GRID_WORN_HOOK_WORD),
        Hook(GRID_EQUIP_HOOK, "grid_equip", GRID_EQUIP_HOOK_WORD), Hook(TEXT_HOOK, "menu_text", TEXT_LOOKUP),
        Hook(PREVIEW_CLASS_HOOK, "preview_class", PREVIEW_CLASS_HOOK_WORD), Hook(PREVIEW_SPAWN_HOOK, "preview_spawn", SPAWN)]


def words(args, addr):
    """The Foot Items grid: three columns, from the embedded table."""
    boots = boots_data(addr["boots"])[1]
    return {FOOT_GRID + 0x44: (struct.pack(">I", 2), struct.pack(">I", boots["FOOT_COLUMNS"])),
            FOOT_GRID + 0x48: (struct.pack(">I", FOOT_GRID_TABLE), struct.pack(">I", boots["FOOT_TABLE"]))}


def data(args):
    return [("ro", "anim", lambda vaddr: rc2_animation(RC2_CHARGE_ANIM, vaddr)),
            ("rw", "sound", lambda vaddr: SOUND_DEFS[0] + SOUND_DEFS[1] + charge_sound_bank()),
            ("rw2", "boots", lambda vaddr: boots_data(vaddr)[0])]


def pool(args):
    return dict(
        ZERO=0.0, ONE=1.0, HALF=0.5, BIG=99999.0,
        BURST=args.burst_speed / 60, CRUISE=args.cruise_speed / 60,       # speeds are per frame
        ACCEL=ACCEL / 3600, DECEL=DECEL / 3600, TURN=TURN_RATE / 60, BURST_TURN=BURST_TURN_SCALE,
        STEER_SMOOTH=STEER_SMOOTH, DEADZONE=STEER_DEADZONE, AHEAD=DASH_SWEEP_AHEAD, DASH_RADIUS=DASH_SWEEP_RADIUS,
        ANIM_BLEND=ANIM_BLEND, HOVER=HOVER_HEIGHT, HOVER_K=HOVER_STIFFNESS, HOVER_D=HOVER_DAMPING,
        HOVER_MAX=HOVER_MAX_SPEED, HOVER_SNAP=HOVER_MAX_SPEED * HOVER_SNAP, SKID_BLEND=SKID_ANIM_BLEND,
        BUMP_RATIO=BUMP_RATIO, PROBE_HEIGHT=PROBE_HEIGHT, PROBE_REACH=PROBE_REACH, GROUNDED=GROUNDED_HEIGHT,
        CRANK_MAX=args.crank_speed / 60, CRANK_ACCEL=CRANK_ACCEL / 3600, CRANK_BLEND=CRANK_ANIM_BLEND,
        CAM_GAIN=CAMERA_TURN_GAIN, CAM_LIMIT=CAMERA_TURN_LIMIT, **{f"CAM_{off:X}": value for off, value in CAMERA_FIELDS},
        TRAIL_VEC=TRAIL_VEC, TRAIL_A=TRAIL_DESCRIPTORS[0], TRAIL_B=TRAIL_DESCRIPTORS[1])


def parts(args):
    return [BOOTS, BOOTS_MENU, FRAME, GATES, UPDATE]


def fields(args, addr):
    return dict(
        **pair("ANIM", addr["anim"]), **pair("SOUND", addr["sound"]), **pair("BOOTS", addr["boots"]),
        **boots_data(addr["boots"])[1],
        ANIM_TABLE_OFF=0x48 + 4 * ANIM_SLOT, BUTTON_MASK=~CHARGE_BUTTON, NO_GROUND_HI=NO_GROUND >> 16,
        CAM_TURN_A=CAMERA_TURN_FIELDS[0], CAM_TURN_B=CAMERA_TURN_FIELDS[1], CAM_TURN_C=CAMERA_TURN_FIELDS[2],
        JOINT_A=TRAIL_JOINTS[0], JOINT_B=TRAIL_JOINTS[1], RESERVE_HI=BOOTS_RESERVE >> 16, CHARGE_ICON=FOOT_ICONS[2],
        FOOT_BOX_ANIM_OFF=0x48 + 4 * FOOT_BOX_ANIM, FOOT_BOX_OLD_Y=FOOT_BOX_NARROW[0], FOOT_BOX_OLD_HALF=FOOT_BOX_NARROW[1],
        FOOT_BOX_NEW_Y=FOOT_BOX_WIDE[0], FOOT_BOX_NEW_HALF=FOOT_BOX_WIDE[1])
