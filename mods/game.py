"""What the mods have in common: the game's functions and data, the room for new code and
state, the data segments, and the hook sites more than one mod uses.

Everything here is for Ratchet & Clank 1 HD, NPEA00385; addresses in square brackets are the
counterparts in RC2.ppu.elf.
"""
import struct

GAME = "NPEA00385"
ORIG_MD5 = "931eb96c62424cbb1120419ccf27a38d"     # the untouched, decrypted executable


def ha(v):
    """The upper half of an address for lis, to go with addi and lo()."""
    return ((v + 0x8000) >> 16) & 0xFFFF


def lo(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def pair(name, address):
    """The template fields NAME_HA and NAME_LO of an address that is not a constant of a module."""
    return {name + "_HA": ha(address), name + "_LO": lo(address)}


def floats(*values):
    return struct.pack(f">{len(values)}f", *values)


class Hook:
    """A game instruction that build.py replaces with a call (bl) of a mod's routine.

    site: its address. label: the routine. original: the function the instruction called, or the
    instruction word itself when it was no call; then the routine does what it did and returns.
    chain: the site is one that other mods hook too. Such a routine does not return or call the
    function itself: where it is done, at the label <label>_next, it has the line {CHAIN}, which
    becomes a branch to the next mod's routine for the site and, in the last one, to the function
    (or to the displaced instruction and back). The mods are chained in the order of mods.MODS.
    jump: the instruction becomes a jump (b) instead of a call, for sites in functions that do
    not save their return address. The routine does what the instruction did and jumps back to
    the one behind it itself.
    """

    def __init__(self, site, label, original, chain=False, jump=False):
        self.site, self.label, self.original, self.chain, self.jump = site, label, original, chain, jump


# Game functions and data
COLLECT = 0x5E598          # (r3 centre vec4, f1 radius, r5 flags, r6 ignore moby, r7 damage desc) -> count
RESULTS = 0xA14A00         # moby pointers written by COLLECT
IS_CRATE = 0x10AF88        # (r3 moby) -> class in 0x1f4..0x21c
DEAL_DAMAGE = 0x105C08     # (r3 target, r4 source, r5 flags, f1 damage, r7 pos vec4, r8 dir vec4)
VEC_SCALE = 0x5E822C       # (r3 out, r4 in, f1 scale)
HERO_MAIN = 0x8B778        # per-frame hero entry
HERO = 0x969CE0            # +0x80 position, +0x100 facing, +0x194 ground speed, +0x2080 hero moby
PAD = 0x964A40             # +0xa0 buttons held, +0xa4 buttons pressed this frame
CAMERA_STATE = 0x9513C0    # +0x160/+0x170 shake channels, +0x180 camera, +0x350 matrix [RC2 0x146e280]
COUNT_DOWN = 0x4FFF60      # (r3 int*)                                             [RC2 0x10d4ce0]
INT_TO_FLOAT = 0x502730    # (r3) -> f1                                            [RC2 0x10d74c0]
HERO_UPDATE = 0xAAEC0      # per-state hero update, called from HERO_MAIN at UPDATE_HOOK
HERO_SET_STATE = 0xB72B0   # (r3 state, r4 flag)
STICK_TARGET = 0x9B380     # (f1 scale, r4 mode): target speed/heading from the stick   [RC2 0x82cc30]
ROTATE_HERO = 0x9B9EC      # (f1, f2, f3 euler): rotate the hero's orientation           [RC2 0x812b6c]
APPROACH = 0x109AF0        # (r3 float*, f1 target, f2 step)                             [RC2 0xb68540]
BUILD_VELOCITY = 0x9C1B0   # (f1 heading clamp): velocity from speed and heading         [RC2 0x57758]
SPRING_STEP = 0x109A68     # (r3 velocity*, f1 distance, f2 stiffness, f3 damping, f4 max speed) [RC2 0xb68490]
VEC_ADD = 0x5E7F54         # (r3 out, r4 a, r5 b)                                        [RC2 0x11bce44]
JOINT_POS = 0xF1114        # (r3 moby, r4 joint, r5 out vec4)                            [RC2 0xb5964c]
TRAIL = 0x1349F0           # (r3 moby, r4 pos, r5 vec4, r6 descriptor, r7 = 1)           [RC2 0xba8ee8]
HERO_SET_ANIM = 0x85300    # (r3 animation id, r4, f1 blend)                             [RC2 0x81b170]
VEC_LENGTH = 0x5E8030      # (r3 vec) -> f1                                              [RC2 0x11bcf20]
WALL_PROBE = 0x88208       # (f1 height, f2 reach, r5 = 0) -> 1 when a wall is ahead; unused by RC1 itself [RC2 0x813788]
CHOOSER = 0xA30E0          # weapon/gadget use, called first by the transition function   [RC2 0x834b98]
SURFACE = 0x83AC8          # reactions to the surface under Ratchet (ice, lava, water)    [RC2 0x8114e8]
ANGLE_DIFF = 0x5025E0      # (f1, f2) -> f1 - f2 wrapped                          [RC2 0x10d7370]
SPAWN = 0xEFA28            # (r3 class) -> new moby, 0 when none is free
FRAME_COUNTER = 0xA10710   # frames since the level started                           [RC2 0x156b070]
SPAWN_BOLTS = 0xFCD60      # (r3 source moby, r4/r5 value range, r6 flags, r7)
ICON_SPRITE = 0xCA3E4      # (r3 icon id, r4 version) -> sprite
ICON_DRAW = 0xCA0F4        # (r3 sprite, x, y, w, h, alpha): an icon of the menus (see mods/chargeboots/menu.py)
ITEM_TABLE = 0x721000      # 0x4c bytes per item: +0 name text id, +4 the gold version's, +8 slot, +0x10/+0x14 classes
CLASS_SLOT_MAP = 0xA354C0  # byte per class id -> model slot
MODEL_TABLE = 0xA34C00     # model pointer per slot
PLAY_SOUND_DEF = 0x15CE18  # (r3 definition, r4 flags, r5 moby, r6 = 0, r7 = 0x400) -> voice slot or -1
PLAY_MODEL_SOUND = 0x15D12C  # (r3 definition index, r4 flags, r5 moby): a sound of the moby's model
TEXT_LOOKUP = 0x7B740      # (r3 text id) -> string
BOLT_FLY = 2               # SPAWN_BOLTS flag: the bolts fly to Ratchet at once
MENU_FRAME_CLASS = 0x472   # the pause menu's box frames, one animation of the model per box
MODEL_SLOTS = 0xE0         # the number of model slots (MODEL_TABLE); a slot from CLASS_SLOT_MAP is below it
# Voice table: 0x70 bytes per voice; +0x74 state (0 = free, 7 = queued), +0x78 definition,
# +0x88 moby to follow (set by RC1's play-model-sound 0x15d12c after PLAY_SOUND_DEF).
VOICES = 0x963760

# Hook sites more than one mod uses (Hook(..., chain=True)).
FRAME_HOOKS = (0x8C3FC, 0x955A0)   # both bl HERO_MAIN sites (in 0x8c3d0 and 0x954c8)
UPDATE_HOOK = 0x8B93C              # bl HERO_UPDATE in HERO_MAIN
# The transition function 0xbe228 [RC2 0x84adb0] runs checks common to all states, then switches
# on the state at TRANS_HOOK (r19 = hero) and leaves through TRANS_EXIT.
CHOOSER_HOOK = 0xBE2FC             # bl CHOOSER
TRANS_HOOK = 0xBE71C               # lwz r3, 0x2084(r19)
TRANS_HOOK_WORD = 0x80732084
TRANS_EXIT = 0xC81A8
SURFACE_HOOKS = (0x8C400, 0x955A4)  # both bl SURFACE sites, right after the bl HERO_MAIN ones
# Whatever drops bolts (a broken crate, a dead enemy) goes through 0xfd8d0, which works out their
# value and a flags word and calls SPAWN_BOLTS here.
BOLTS_HOOK = 0xFDCC8               # bl SPAWN_BOLTS

# Code: the mods' routines and constants go, one mod after the other, into the zero padding
# between the end of the R+X segment (0x6fd5e8) and 0x700000. A mod that no longer fits there
# goes behind the data of the segment FAR_CODE below, which is made executable for it; all of
# the game's code is within reach of a branch from there.
CAVE_START = 0x6FD600
SEG_END = 0x700000
# State: zero-initialised memory appended to the RW segment's bss (old end 0x1606310), shared by
# the mods as follows. tools/trace.py and tools/peek.py read and write it in a running game.
# Charge Boots:
#   +0 R1 last frame, +4 tap window, +8 charge frame counter (0 = off),
#   +0x10 the current skid ended a charge, +0x14 smoothed steering input,
#   +0x28 a bolt crank is being boosted,
#   +0x18 sound bank handle (0 = not loaded, -1 = failed), +0x1c loop voice slot + 1,
#   +0x20 play the end sound when the loop stops, +0x24 hover velocity,
#   +0x2c address of the installed Charge Boots model (0 = not installed)
# Box Breaker:
#   +0x30 frame of the last Box Breaker sweep, +0x34 crate whose bolts fly to Ratchet,
#   +0x40 the roll shake channel (strength, value, frames left, frames in all)
# Strafing [RC2 hero offsets]:
#   +0x50 timer, non-zero = strafing [+0x1454], +0x54 L2/R2 held this frame,
#   +0x58 direction of the stick: 0 left, 1 right, 2 forward, 3 back [+0x1457],
#   +0x5c moving backwards [+0x1456], +0x60 heading to move along [+0x1458],
#   +0x64 turn velocity kept between frames [+0x145c], +0x68/+0x6c reversal timers
#   [+0x146c/+0x146e], +0x70 body twist applied, +0x74 backwards animation applied,
#   +0x78 the current flip is a strafe flip [+0x52d]
# Charge Boots as an item:
#   +0x7c foot mode: 0 = Charge Boots on (the default), 1 = off, 2 = off and the Grindboots
#   put on in the menu, +0x80 the boots on Ratchet's feet were created with the Charge Boots
#   model, +0x84 put the Grindboots back on once his feet are bare, +0x88 the level's own
#   model of class 0xc3 (0 = not seen yet)
# Clank's dash:
#   +0x90 frame counter (0 = off), +0x94 vertical velocity per frame, +0x98 he is pitched,
#   +0x9c the wings' moby (0 = none), +0xc0/+0xc4 the two jets' mobys,
#   +0xc8 for tuning: the camera bump's squared distance as a float (0 = CLANK_CAMERA_BUMP),
#   +0xcc/+0xd0 his x and y a frame ago, +0xd4 frames into the bump (0 = not bumping),
#   +0xd8 he is past the top of the arc and levelling out
#   for tuning in a running game with tools/peek.py: +0xa0/+0xa4/+0xa8 offset of the wings in
#   his moby's axes (forward, left, up; set to CLANK_WINGS_OFFSET when they are created unless
#   +0xbc is non-zero), +0xb0 their animation (0 = CLANK_WINGS_ANIM), +0xb4 non-zero keeps them
#   on him all the time, +0xb8 their scale as a float (0 = as created)
# Weapon levels, all for tuning in a running game with tools/peek.py (0 = the built-in value):
#   +0x100/+0x104 added to the experience bar's x and y, +0x108/+0x10c its width and height,
#   +0x110/+0x114/+0x118 the colours of its filling, of a full bar and of its background,
#   +0x11c the message index the level-up message is shown with
#   +0x120/+0x124 added to the x and y of the bar in the HUD in play, +0x128 the colour of the
#   level-up flash (without alpha); and +0x130 the frames of that flash left, +0x134 the frame
#   in which a decoy was last seen standing
#   +0x138 the HUD quad being drawn is a level 2 weapon's icon, +0x13c for tuning: its colour
#   +0x144/+0x148 for tuning: the right and bottom edge of the level-up flash, +0x14c/+0x150 its
#   left and top edge
#   +0x154 the icon looked up last is to be drawn in gold by the menus
#   +0x158 for tuning: the colour of a level 2 weapon in his hand, +0x15c the frames of the
#   level-up left (see FX in mods/weaponlevels/fx.py)
#   +0x170/+0x174 for tuning: added to the x and y of the experience bar in the pause menu,
#   +0x178 added to the y of its experience in words, +0x17c for tuning: the colour of a level 2
#   Walloper's sparks (00BBGGRR), +0x180 added to the x of the experience in words in the menu,
#   +0x184 how much taller the menu's ammunition box is (pose units), +0x188 the height the
#   count is centred in, +0x18c the factor of a level 2 Visibomb's blast radius (float),
#   +0x190 the frame in which a drone of the Drone Device was last seen,
#   +0x1a0..+0x2a0 the enemies the Taunter lured (LURES in mods/weaponlevels/taunter.py)
STATE = 0x1606320
STATE_END = 0x16065C0

# Data: what a mod embeds is loaded through the ELF's three unused PT_LOAD entries (program
# header index, address). Each takes the data of all mods one after the other, 16-byte aligned:
# "ro" is read-only, "rw" writable (flags 6), "rw2" writable with the flags 0x6600006.
SEGMENTS = {"ro": (2, 0x1610000), "rw": (3, 0x1620000), "rw2": (4, 0x1630000)}
FAR_CODE = "ro"
