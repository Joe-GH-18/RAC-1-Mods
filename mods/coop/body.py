"""Clank's body: his model in every level, the moby that shows it, the Thruster-Pack's wings and
jets on him, and backpack Clank and the pack hidden on Ratchet meanwhile.

The model. Free Clank (class 0x57: 73 bones, 19 animations, 21 sounds) is only in levels 6 and
10, so his model and textures are embedded from the player's RC1 data (rc2data.level_model and
friends, level 6, sounds stripped: they play only where their bank is loaded) and installed once
per boot (coop_install): memory from the top of the main heap (the model, then its texture
entries) and of the graphics heap (the pixels), the game's model fix-up, and the mesh groups
pointed at the entries.

The moby (coop_body) is created as backpack Clank (class 0x259, in every level, no update of
its own) and given that model; with +0x30 = 0xff, +0x31 = 1, a draw distance at +0x32 and +0x34
bit 0x2 cleared the moby loop animates it and keeps its bounds. Its place, euler and scale are
set every frame (flight.py); its light (+0x38) is Ratchet's moby's, at the HUD hook.

Hiding (seen live 2026-10-26): a moby's draw distance +0x32 = 0 leaves it out of the picture,
and the game does not set it again for backpack Clank (hero +0x1184) or the pack (+0x1180), so
coop_hide keeps theirs (C_KEPT_*) and puts them back on docking. The red light of his antenna
still showed on Ratchet that way (the user), so the game's own hide bit (+0x34 0x1) is set too,
and their scale 0; it still showed: the light is a moby of its own (HERO_CLANK_LIGHT, class 0x4b4
at scale 0.001), whose draw distance is set to 0 as well.

The wings are the Thruster-Pack's device (class 0x260, animation 1 = wings out), placed from his
moby's matrix at T_WINGS_* (forward, left, up in his axes) at the HUD hook, as Clank's dash in
mods/clank.py places it on the playable Clank. Its two jets (class 0xa7, JET_SPAWN) have their own
update switched off (+0x20 = 5); each frame they get the device (variables +8), their draw
callback (DRAW_REGISTER(JET_DRAW): it insists on a device of class 0x260) and their particles
(JET_EMIT).
"""
from ..game import *  # noqa: F401,F403

CLANK_LEVEL, CLANK_CLASS = 6, 0x57         # free Clank's model, from his level
CARRIER_CLASS = 0x259                      # what the moby showing him is created as
CLASS_INFO = 0x71D1F0                      # model +0x2c of the game's models, filled at load
MODEL_FIXUP = 0xDBC38                      # (r3 model, r4 = 0, r5 = 0, r6 class)
COPY = 0x50027C                            # (r3 dst, r4 src, r5 size)
MAIN_HEAP, GRAPHICS_HEAP = 0x90D7C8, 0x90D7EC   # bump allocators: +8 and +0xc the end
GCM_PTR = 0x8FA564                         # -> +0x4ac the graphics memory base
MOBY_SET_ANIM = 0xFDDC0                    # (r3 moby, r4 animation, r5 = 0, r6 blend frames)
MOBY_DELETE = 0xEFB38                      # (r3 moby)
MANIP_REMOVE = 0xF0F1C                     # (r3 moby, r4 joint manipulator)
JOINT_POSITION = 0xF1114                   # (r3 moby, r4 joint of the model's list +0x1c, r5 vec4 out)
BANK_LOAD_FROM_MEM = 0x60AE8C               # (r3 bank image, 16-aligned, writable) -> handle, 0 on failure
MOBY_MOVED = 0xF31A8                       # (r3 moby): bounds from its place
DRAW_DISTANCE = 0x2000                     # moby +0x32 (u16); 0 = never drawn
SKIP_UPDATE = 0x2                          # moby +0x34: left out of the moby loop
HERO_KIND, HERO_CLANK_MOBY, HERO_PACK_MOBY = 0x20A4, 0x1184, 0x1180
HERO_CLANK_LIGHT = 0x118C        # backpack Clank's antenna light (class 0x4b4, scale 0.001; found 2026-10-27 among the mobys at his place)
HIDE_BIT = 0x1                  # moby +0x34: not drawn at all (the game's own hide, 0x7d5c0)
HERO_PACK_HIDDEN = 0x22D8       # not 0: the game hides the backpack mobys itself (+0x34 | 0x41 at their spawn, 0x921c0)
THRUSTER_CLASS, WINGS_ANIM, WINGS_DRAW = 0x260, 1, 0x20
JET_SPAWN = 0x2AA928                       # (r3 side) -> moby
JET_EMIT = 0x2A9F18                        # (r3 jet)
JET_DRAW = 0x70AD18                        # function descriptor of the flame's draw callback
DRAW_REGISTER = 0x6D7E0                    # (r3 function descriptor, r4 moby)
JET_OFF_STATE = 5
JET_VALUES = (0.0125, 0.2, 0.05, 0.025)    # variables +0x20..+0x2c of a lit jet
PUFF = 0x123390                            # the game's puff of glow (see mods/weaponlevels/fx.py)
# GRID_PLACE 0xf25f4 takes a moby's id out of a cell with no end test: an id not in the cell runs on
# through memory and writes where it finds it (the freeze on Drek's Fleet, NOTES.md). coop_grid_search
# stops at the cell's end and leaves that cell alone, counting it in C_GRID_MISS.
GRID_SEARCH_HOOK, GRID_SEARCH_HOOK_WORD = 0xF2764, 0x7C863814   # addc r4, r6, r7: the end of the cell's ids
GRID_FOUND, GRID_NEXT_CELL = 0xF278C, 0xF27E0

CODE = r"""
coop_grid_search:                   # (jumped to) r6 the cell's ids, r7 their bytes, r31 the moby
    addc 4, 6, 7
    clrldi 4, 4, 32
    lwz 8, 0xac(31)
    mr 5, 6
cgs_next:
    cmplw 5, 4
    bge cgs_none
    lhz 7, 0(5)
    extsh 7, 7
    cmpw 7, 8
    beq cgs_found
    addi 5, 5, 2
    b cgs_next
cgs_found:
    addi 6, 5, 2
    b {GRID_FOUND}
cgs_none:
    lis 9, {COOP_HA}
    addi 9, 9, {COOP_LO}
    lwz 8, {C_GRID_MISS}(9)
    addi 8, 8, 1
    stw 8, {C_GRID_MISS}(9)
    b {GRID_NEXT_CELL}

coop_install:                       # (r29) Clank's model, once per boot
    lwz 3, {C_MODEL}(29)
    cmpwi 3, 0
    bnelr
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x90(1)
    std 30, 0x70(1)
    std 28, 0x78(1)
    std 27, 0x80(1)
    lis 3, {MAIN_HEAP_HA}           # memory from the top of both heaps
    addi 3, 3, {MAIN_HEAP_LO}
    lwz 30, 8(3)
    addis 30, 30, -{MODEL_RESERVE_HI}
    stw 30, 8(3)
    stw 30, 0xc(3)                  # r30 = the model, then its texture entries
    lis 3, {GRAPHICS_HEAP_HA}
    addi 3, 3, {GRAPHICS_HEAP_LO}
    lwz 28, 8(3)
    addis 28, 28, -{PIXELS_RESERVE_HI}
    stw 28, 8(3)
    stw 28, 0xc(3)                  # r28 = the pixels
    mr 3, 30
    lis 4, {CLANK_MODEL_HA}
    addi 4, 4, {CLANK_MODEL_LO}
    lis 5, {MODEL_SIZE_HI}
    ori 5, 5, {MODEL_SIZE_LO}
    bl {COPY}
    lis 27, {MODEL_SIZE_HI}
    ori 27, 27, {MODEL_SIZE_LO}
    add 27, 30, 27                  # r27 = the entries
    mr 3, 27
    lis 4, {CLANK_TEXTURES_HA}
    addi 4, 4, {CLANK_TEXTURES_LO} + 8
    li 5, {ENTRIES_SIZE}
    bl {COPY}
    mr 3, 28
    lis 4, {CLANK_PIXELS_HA}
    addi 4, 4, {CLANK_PIXELS_LO}
    lis 5, {PIXELS_SIZE_HI}
    ori 5, 5, {PIXELS_SIZE_LO}
    bl {COPY}
    lis 3, {GCM_PTR_HA}             # an entry's +0 is relative to the graphics memory base
    lwz 3, {GCM_PTR_LO}(3)
    lwz 3, 0x4ac(3)
    subf 3, 3, 28
    lis 4, {ZAPPER_PIXELS_HI}       # the Clank Zapper's menu icons follow his pixels (menu.py)
    ori 4, 4, {ZAPPER_PIXELS_LO}
    add 4, 3, 4
    lis 5, {ZAPPER_ICON_ENTRIES_HA}
    addi 5, 5, {ZAPPER_ICON_ENTRIES_LO}
    stw 4, 0(5)
    addi 4, 4, 0x1000
    stw 4, 0x24(5)
    li 4, {ENTRY_COUNT}
    mtctr 4
    mr 4, 27
ci_entry:
    lwz 5, 0(4)
    add 5, 5, 3
    stw 5, 0(4)
    addi 4, 4, 0x24
    bdnz ci_entry
    mr 3, 30                        # the game's own fix-up turns the offsets into pointers
    li 4, 0
    li 5, 0
    li 6, {CLANK_CLASS}
    bl {MODEL_FIXUP}
    lwz 3, 0(30)                    # each mesh group gets its texture's entry
    lwz 3, 8(3)
    lis 4, {CLANK_TEXTURES_HA}
    addi 4, 4, {CLANK_TEXTURES_LO}
    lbz 5, 0(4)
    mtctr 5
ci_group:
    lbzu 5, 1(4)
    mulli 5, 5, 0x24
    add 5, 27, 5
    stw 5, 0(3)
    addi 3, 3, 0x10
    bdnz ci_group
    lis 3, {CLASS_INFO_HA}
    addi 3, 3, {CLASS_INFO_LO}
    stw 3, 0x2c(30)
    stw 30, {C_MODEL}(29)
    ld 27, 0x80(1)
    ld 28, 0x78(1)
    ld 30, 0x70(1)
    addi 1, 1, 0x90
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_body:                          # (r3 = 1 wanted, 0 not; r29) -> r3 = the body, 0 = none
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 28, 0x70(1)
    mr 28, 3
    lwz 3, {C_BODY}(29)
    cmpwi 3, 0
    beq cb_none
    lwz 4, 0x24(3)                  # still ours?
    lwz 5, {C_MODEL}(29)
    cmpw 4, 5
    beq cb_have
    li 3, 0
    stw 3, {C_BODY}(29)
    stw 3, {MANIPS_ON}(29)          # (the moby went with its list)
cb_none:
    cmpwi 28, 0
    beq cb_out
    bl coop_install
    li 3, {CARRIER_CLASS}
    bl {SPAWN}
    cmpwi 3, 0
    beq cb_out                      # no moby free: again next frame
    stw 3, {C_BODY}(29)
    lwz 4, {C_MODEL}(29)
    stw 4, 0x24(3)
    li 4, 0xff                      # updated at any distance
    stb 4, 0x30(3)
    li 4, 1
    stb 4, 0x31(3)
    li 4, {DRAW_DISTANCE}
    sth 4, 0x32(3)
    lhz 4, 0x34(3)                  # and by the moby loop
    rlwinm 4, 4, 0, {NOT_SKIP_MB}, {NOT_SKIP_ME}
    sth 4, 0x34(3)
    lfs 0, {T_SCALE}(29)
    stfs 0, 0x2c(3)
    li 4, -1
    stw 4, {C_ANIM}(29)
    bl coop_limbs_on
    lwz 3, {C_BODY}(29)
    b cb_out
cb_have:
    cmpwi 28, 0
    bne cb_out
    bl coop_limbs_off
    lwz 3, {C_BODY}(29)
    bl {MOBY_DELETE}                # not wanted any more
    li 3, 0
    stw 3, {C_BODY}(29)
    li 4, -1
    stw 4, {C_ANIM}(29)
cb_out:
    ld 28, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_limbs_on:                      # (r3 = his new body; r29): his limbs' manipulators linked into its list
    lwz 9, {T_LIMBS_HIDE}(29)
    cmpwi 9, 0
    beqlr
    lwz 9, {MANIPS_ON}(29)
    cmpwi 9, 0
    bnelr                           # (never twice: a ring froze the game once)
    li 7, 0
cl_one:
    slwi 9, 7, 2
    addi 9, 9, {T_LIMB_0}
    lwzx 11, 29, 9                  # the bone, < 0 none
    cmpwi 11, 0
    blt cl_next
    slwi 9, 7, 6
    addi 9, 9, {MANIPS}
    add 8, 29, 9                    # r8 = the manipulator: weight 1, no turn, scale 0
    li 10, 0
    li 12, 0x10
    mtctr 12
cl_clear:
    addi 12, 12, -1                 # (cleared word by word)
    slwi 6, 12, 2
    stwx 10, 8, 6
    bdnz cl_clear
    slwi 11, 11, 6
    addis 11, 11, 0x7000
    stw 11, 4(8)
    li 10, 1
    stb 10, 1(8)
    stb 10, 3(8)
    lfs 0, {T_ONE}(29)
    stfs 0, 0xc(8)
    stfs 0, 0x1c(8)
    lwz 10, 0x64(3)
    stw 10, 8(8)
    stw 8, 0x64(3)
cl_next:
    addi 7, 7, 1
    cmpwi 7, {LIMBS}
    blt cl_one
    li 9, 1
    stw 9, {MANIPS_ON}(29)
    blr

coop_limbs_off:                     # (r3 = his body; r29): the manipulators out of its list again
    lwz 9, {MANIPS_ON}(29)
    cmpwi 9, 0
    beqlr
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 28, 0x70(1)
    std 27, 0x78(1)
    mr 28, 3
    li 27, 0
clo_one:
    slwi 9, 27, 2
    addi 9, 9, {T_LIMB_0}
    lwzx 11, 29, 9
    cmpwi 11, 0
    blt clo_next
    mr 3, 28
    slwi 4, 27, 6
    addi 4, 4, {MANIPS}
    add 4, 4, 29
    bl {MANIP_REMOVE}
clo_next:
    addi 27, 27, 1
    cmpwi 27, {LIMBS}
    blt clo_one
    li 9, 0
    stw 9, {MANIPS_ON}(29)
    ld 27, 0x78(1)
    ld 28, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_anim:                          # (r3 = an animation of his; r29): set when it changes
    lwz 4, {C_ANIM}(29)
    cmpw 4, 3
    beqlr
    lwz 5, {C_BODY}(29)
    cmpwi 5, 0
    beqlr
    stw 3, {C_ANIM}(29)
    mr 4, 3
    mr 3, 5
    li 5, 0
    lwz 6, {T_ANIM_BLEND}(29)
    b {MOBY_SET_ANIM}

coop_hide:                          # (r3 = 1 hide backpack Clank and the pack, 0 show them again; r29/r30)
    lwz 9, {HERO_CLANK_LIGHT}(30)   # his antenna's light (class 0x4b4, at scale 0.001 a red dot all the same):
    cmpwi 9, 0                      # its draw distance 0 while hidden, kept in C_KEPT_LIGHT
    beq ch_lit
    lwz 10, {C_KEPT_LIGHT_MOBY}(29)
    cmpwi 3, 0
    beq ch_light_on
    cmpw 10, 9
    beq ch_light_off
    stw 9, {C_KEPT_LIGHT_MOBY}(29)
    lhz 10, 0x32(9)
    stw 10, {C_KEPT_LIGHT}(29)
ch_light_off:
    li 10, 0
    sth 10, 0x32(9)
    b ch_lit
ch_light_on:
    cmpw 10, 9
    bne ch_lit
    lwz 10, {C_KEPT_LIGHT}(29)
    sth 10, 0x32(9)
    li 10, 0
    stw 10, {C_KEPT_LIGHT_MOBY}(29)
ch_lit:
    lwz 9, {HERO_CLANK_MOBY}(30)
    addi 10, 29, {C_KEPT_CLANK}
    addi 12, 29, {C_KEPT_SCALES}
    lwz 8, {C_HIDDEN}(29)
    stw 3, {C_HIDDEN}(29)
    li 7, 2
ch_one:
    cmpwi 9, 0
    beq ch_next
    cmpwi 3, 0
    beq ch_show
    lhz 11, 0x34(9)                 # hide: the game's own hide bit too (the antenna's red light is
    ori 11, 11, {HIDE_BIT}          # drawn without regard to the draw distance)
    sth 11, 0x34(9)
    lfs 0, 0x2c(9)                  # and scale 0 (the light still showed with the bit): its scale kept
    lfs 1, {T_ZERO}(29)
    fcmpu 0, 0, 1
    beq ch_scaled
    stfs 0, 0(12)
    stfs 1, 0x2c(9)
ch_scaled:
    lhz 11, 0x32(9)                 # and keep its draw distance (a new moby brings its own)
    cmpwi 11, 0
    beq ch_next
    sth 11, 0(10)
    li 11, 0
    sth 11, 0x32(9)
    b ch_next
ch_show:
    cmpwi 8, 0                      # only once, after hiding
    beq ch_next
    lwz 11, 0(12)                   # its scale back
    cmpwi 11, 0
    beq ch_unscaled
    stw 11, 0x2c(9)
    li 11, 0
    stw 11, 0(12)
ch_unscaled:
    lhz 11, {HERO_PACK_HIDDEN}(30)  # the hide bit off, unless the game hides the pack itself
    cmpwi 11, 0
    bne ch_shown
    lhz 11, 0x34(9)
    rlwinm 11, 11, 0, 0, 30
    sth 11, 0x34(9)
ch_shown:
    lhz 11, 0(10)
    cmpwi 11, 0
    bne ch_put
    li 11, {WINGS_DRAW}
ch_put:
    sth 11, 0x32(9)
ch_next:
    lwz 9, {HERO_PACK_MOBY}(30)
    addi 10, 29, {C_KEPT_PACK}
    addi 12, 12, 4
    addic. 7, 7, -1
    bne ch_one
    blr

coop_wings:                         # (r3 = 1 wanted, 0 not; r29/r30): the device and its jets
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 28, 0x70(1)
    mr 28, 3
    lwz 3, {C_WINGS}(29)
    cmpwi 28, 0
    beq cw_off
    cmpwi 3, 0
    bne cw_out
    li 3, {THRUSTER_CLASS}
    bl {SPAWN}
    cmpwi 3, 0
    beq cw_out
    stw 3, {C_WINGS}(29)
    li 4, 0xff                      # in the moby loop at any distance, as his body (with +0x34 bit 0x2
    stb 4, 0x30(3)                  # it was never animated and kept the joints of its first frame)
    lhz 4, 0x34(3)
    rlwinm 4, 4, 0, {NOT_SKIP_MB}, {NOT_SKIP_ME}
    sth 4, 0x34(3)
    li 4, 1
    stb 4, 0x31(3)
    li 4, {WINGS_DRAW}
    sth 4, 0x32(3)
    lwz 5, 0x2080(30)
    ld 6, 0x38(5)
    std 6, 0x38(3)
    li 4, {WINGS_ANIM}
    li 5, 0
    li 6, 6
    bl {MOBY_SET_ANIM}
    li 3, 0
    bl {JET_SPAWN}
    stw 3, {C_JET_L}(29)
    bl coop_jet_init
    li 3, 1
    bl {JET_SPAWN}
    stw 3, {C_JET_R}(29)
    bl coop_jet_init
    b cw_out
cw_off:
    cmpwi 3, 0
    beq cw_out
    bl {MOBY_DELETE}
    lwz 3, {C_JET_L}(29)
    cmpwi 3, 0
    beq cw_second
    bl {MOBY_DELETE}
cw_second:
    lwz 3, {C_JET_R}(29)
    cmpwi 3, 0
    beq cw_done
    bl {MOBY_DELETE}
cw_done:
    li 3, 0
    stw 3, {C_WINGS}(29)
    stw 3, {C_JET_L}(29)
    stw 3, {C_JET_R}(29)
cw_out:
    ld 28, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_jet_init:                      # (r3 = a new jet or 0; r29): its own update switched off
    cmpwi 3, 0
    beqlr
    li 4, {JET_OFF_STATE}
    stb 4, 0x20(3)
    lwz 4, 0x78(3)
    lwz 5, {C_WINGS}(29)
    stw 5, 8(4)
    lis 6, {POOL_HA}
    addi 6, 6, {POOL_LO}
    lwz 5, {P_JET_VALUES}(6)
    stw 5, 0x20(4)
    lwz 5, {P_JET_VALUES} + 4(6)
    stw 5, 0x24(4)
    lwz 5, {P_JET_VALUES} + 8(6)
    stw 5, 0x28(4)
    lwz 5, {P_JET_VALUES} + 12(6)
    stw 5, 0x2c(4)
    blr

coop_place:                         # (r29/r30, at the HUD hook): his light, the wings on him, the jets burning
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 28, 0x70(1)
    lwz 9, {C_BODY}(29)
    cmpwi 9, 0
    beq cpl_out
    lwz 5, 0x2080(30)               # Ratchet's light
    cmpwi 5, 0
    beq cpl_wings
    ld 6, 0x38(5)
    std 6, 0x38(9)
cpl_wings:
    lwz 10, {C_WINGS}(29)
    cmpwi 10, 0
    beq cpl_out
    cmpwi 5, 0
    beq cpl_rows
    ld 6, 0x38(5)
    std 6, 0x38(10)
cpl_rows:
    bl coop_wings_put
    lwz 28, {C_JET_L}(29)
    bl coop_jet
    lwz 28, {C_JET_R}(29)
    bl coop_jet
cpl_out:
    ld 28, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_wings_put:                     # (r29) the device on his back: his rows and euler, placed at T_WINGS_* in his axes
    lwz 9, {C_BODY}(29)
    lwz 10, {C_WINGS}(29)
    cmpwi 9, 0
    beqlr
    cmpwi 10, 0
    beqlr
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    li 6, 0                         # his euler turned by T_WINGS_ROLL/PITCH/YAW, kept within -pi..pi
cwp_turn:                           # (the moby loop builds its rows from it)
    std 6, 0x50(1)
    std 9, 0x60(1)
    std 10, 0x68(1)
    addi 7, 6, 0x40
    lfsx 1, 9, 7
    addi 7, 6, {T_WINGS_ROLL}
    lfsx 0, 29, 7
    fadds 1, 1, 0
    lfs 2, {T_ZERO}(29)
    bl {ANGLE_DIFF}
    ld 10, 0x68(1)
    ld 9, 0x60(1)
    ld 6, 0x50(1)
    addi 7, 6, 0x40
    stfsx 1, 10, 7
    addi 6, 6, 4
    cmpwi 6, 12
    blt cwp_turn
    std 9, 0x60(1)
    std 10, 0x68(1)
    lwz 3, {T_JOINT_TORSO}(29)      # from his torso as it moves with his animation
    addi 4, 29, {C_JOINT_AT}
    bl coop_joint
    ld 10, 0x68(1)
    ld 9, 0x60(1)
    lfs 1, {T_WINGS_AHEAD}(29)      # the offset, along his axes
    lfs 2, {T_WINGS_LEFT}(29)
    lfs 3, {T_WINGS_UP}(29)
    li 7, 0
cwp_axis:
    add 8, 9, 7
    addi 6, 7, {C_JOINT_AT}
    lfsx 0, 29, 6
    lfs 4, 0xc0(8)
    fmadds 0, 4, 1, 0
    lfs 4, 0xd0(8)
    fmadds 0, 4, 2, 0
    lfs 4, 0xe0(8)
    fmadds 0, 4, 3, 0
    add 8, 10, 7
    stfs 0, 0x10(8)
    addi 7, 7, 4
    cmpwi 7, 12
    blt cwp_axis
    lwz 6, 0x1c(9)
    stw 6, 0x1c(10)
    lfs 0, {T_WINGS_SCALE}(29)
    lfs 1, {T_ZERO}(29)
    fcmpu 0, 0, 1
    beq cwp_moved
    stfs 0, 0x2c(10)
cwp_moved:
    mr 3, 10
    bl {MOBY_MOVED}
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_joint:                         # (r3 = a joint of his model's list, r4 = out vec4; r29) where it is now:
    mflr 0                          # his place + (JOINT_POSITION less his place) * T_JOINT_SCALE
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 28, 0x70(1)
    mr 28, 4
    mr 4, 3
    lwz 3, {C_BODY}(29)
    mr 5, 28
    bl {JOINT_POSITION}
    lwz 9, {C_BODY}(29)
    lfs 1, {T_JOINT_SCALE}(29)
    li 7, 0
cjt_axis:
    add 8, 9, 7
    lfs 0, 0x10(8)
    lfsx 2, 28, 7
    fsubs 2, 2, 0
    fmadds 2, 2, 1, 0
    stfsx 2, 28, 7
    addi 7, 7, 4
    cmpwi 7, 12
    blt cjt_axis
    lfs 0, {T_ONE}(29)
    stfs 0, 12(28)
    ld 28, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_jet:                           # (r28 = a jet or 0; r29): it burns this frame
    cmpwi 28, 0
    beqlr
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lwz 4, 0x78(28)
    lwz 5, {C_WINGS}(29)
    stw 5, 8(4)
    addi 6, 29, {T_JET_0}           # its flame: as he flies, or as he boosts (or rams)
    lwz 5, {C_BOOST}(29)
    lwz 7, {C_PUNCH}(29)
    or. 5, 5, 7
    beq cj_values
    addi 6, 29, {T_JET_BOOST_0}
cj_values:
    lwz 5, 0(6)
    stw 5, 0x20(4)
    lwz 5, 4(6)
    stw 5, 0x24(4)
    lwz 5, 8(6)
    stw 5, 0x28(4)
    lwz 5, 12(6)
    stw 5, 0x2c(4)
    lis 3, {JET_DRAW_HA}
    addi 3, 3, {JET_DRAW_LO}
    mr 4, 28
    bl {DRAW_REGISTER}
    mr 3, 28
    bl {JET_EMIT}
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_forget:                        # (r29) a new level: the mobys went with the old one
    li 9, 0
    stw 9, {C_MINI}(29)
    stw 9, {C_RIDE}(29)
    stw 9, {C_RIDE_N}(29)            # (what was hidden, and the rider, went too)
    stw 9, {C_RIDER}(29)
    stw 9, {MANIPS_ON}(29)
    stw 9, {C_BODY}(29)
    stw 9, {C_WINGS}(29)
    stw 9, {C_JET_L}(29)
    stw 9, {C_JET_R}(29)
    stw 9, {C_MODE}(29)
    stw 9, {C_TIMER}(29)
    stw 9, {C_HIDDEN}(29)
    stw 9, {C_TARGET}(29)
    stw 9, {C_ZAP}(29)
    stw 9, {C_PUNCH}(29)
    stw 9, {C_POUND}(29)
    stw 9, {C_BOOST}(29)
    stw 9, {C_SWELL}(29)
    li 9, -1
    stw 9, {C_ANIM}(29)
    lis 10, {PREVIEW_WIDGET_HA}     # the menu's preview Clank went too (a game loaded from the menu): the
    addi 10, 10, {PREVIEW_WIDGET_LO}  # preview's own bytes back, no moby touched
    lwz 9, {C_PREV_KEPT}(29)
    cmpwi 9, 0
    beq cfg_prev
    li 12, 0
cfg_flag:
    addi 11, 12, {C_PREV_FLAGS}
    lbzx 9, 29, 11
    addi 11, 12, 0xa4
    stbx 9, 10, 11
    addi 12, 12, 1
    cmpwi 12, {PREVIEW_SLOTS}
    blt cfg_flag
cfg_prev:
    lwz 9, 0x48(10)                 # (ours left in the item's slot)
    lwz 11, {C_PREV}(29)
    cmpw 9, 11
    bne cfg_out
    li 9, 0
    stw 9, 0x48(10)
cfg_out:
    li 9, 0
    stw 9, {C_PREV}(29)
    stw 9, {C_PREV_ITEM}(29)
    stw 9, {C_PREV_KEPT}(29)
    stw 9, {C_PREV_BOLTS}(29)
    blr

coop_puffs:                         # (r3 = a set of puffs in the block, r4 = where: 3 floats) the game's puffs of glow
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0xb0(1)
    std 28, 0x98(1)
    std 27, 0xa0(1)
    std 26, 0xa8(1)
    mr 28, 3
    mr 26, 4
    lwz 27, 0x34(28)
cp_next:
    cmpwi 27, 0
    ble cp_out
    li 7, 0
cp_axis:
    lfsx 0, 26, 7
    lfsx 1, 28, 7
    fadds 0, 0, 1
    addi 8, 7, 0x80
    stfsx 0, 1, 8
    addi 7, 7, 4
    cmpwi 7, 12
    blt cp_axis
    lfs 0, 0x18(28)
    stfs 0, 0x8c(1)
    addi 3, 1, 0x80
    addi 4, 28, 0xc
    lwz 5, 0x24(28)
    lwz 6, 0x28(28)
    li 7, 0
    lwz 8, 0x2c(28)
    lwz 9, 0x30(28)
    li 10, 0
    li 0, 0
    std 0, 0x70(1)
    std 0, 0x78(1)
    lfs 1, 0x1c(28)
    lfs 2, 0x20(28)
    bl {PUFF}
    addi 27, 27, -1
    b cp_next
cp_out:
    ld 26, 0xa8(1)
    ld 27, 0xa0(1)
    ld 28, 0x98(1)
    addi 1, 1, 0xb0
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_sound:                         # (r3 = a sound, < 0 none; r29, r30): it plays at Ratchet. Below 0x100 one of
    cmpwi 3, 0                      # Ratchet's sound definitions, below SOUND_OURS class << 8 | a definition of that
    bltlr                           # class's model in this level (none if it is not loaded or has fewer), from
    lwz 5, 0x2080(30)               # SOUND_OURS the picked sound of slot k (sounds.json), from SOUND_BANK the
    cmpwi 5, 0                      # level bank's sound n
    beqlr
    lwz 6, 0x24(5)                  # r6 = the model: Ratchet's
    lis 7, 1                        # (SOUND_OURS)
    cmpw 3, 7
    bge cs_ours
    cmplwi 3, 0x100
    blt cs_model
    srwi 6, 3, 8                    # or the class's
    clrlwi 3, 3, 24
    cmplwi 6, 0x800
    bgelr
    lis 7, {CLASS_SLOT_MAP_HA}
    addi 7, 7, {CLASS_SLOT_MAP_LO}
    lbzx 6, 7, 6
    cmplwi 6, {MODEL_SLOTS}
    bgelr
    slwi 6, 6, 2
    lis 7, {MODEL_TABLE_HA}
    addi 7, 7, {MODEL_TABLE_LO}
    lwzx 6, 7, 6
cs_model:
    cmpwi 6, 0
    beqlr
    lbz 7, 0xd(6)                   # (as PLAY_MODEL_SOUND: the definitions at +0x28, +0xd of them)
    cmpw 3, 7
    bgelr
    lwz 7, 0x28(6)
    cmpwi 7, 0
    beqlr
    slwi 3, 3, 5
    add 3, 3, 7
    li 4, 0
    li 6, 0
    li 7, 0x400
    b {PLAY_SOUND_DEF}
cs_ours:                            # a definition of ours for a sound of the level's bank (the bank Ratchet's
    lwz 6, 0x28(6)                  # definitions play from), as one of his one-shots
    cmpwi 6, 0
    beqlr
    lwz 8, 0x1c(6)                  # r8 = the level bank's handle, r10 = the volume
    lwz 10, {T_SOUND_VOLUME}(29)
    subf 9, 7, 3                    # r9 = the bank's sound
    lis 7, 2                        # (SOUND_BANK)
    cmpw 3, 7
    bge cs_bank
    cmplwi 9, {SOUND_SLOTS}         # a slot: its volume and its sound on this level
    bgelr
    slwi 11, 9, 2
    addi 12, 11, {SOUND_VOLUMES}
    lwzx 10, 29, 12
    addi 12, 11, {SOUND_SLOT_BANK}  # from a bank of our own (one the level lacks): its handle
    lwzx 12, 29, 12
    cmpwi 12, 0
    beq cs_level
    slwi 12, 12, 2
    addi 12, 12, {C_OWN_BANKS} - 4
    lwzx 8, 29, 12
    cmpwi 8, 0
    blelr
cs_level:
    lis 11, {PLANET_HA}
    lwz 11, {PLANET_LO}(11)
    cmplwi 11, {LEVEL_COUNT}
    bgelr
    mulli 9, 9, {LEVEL_COUNT}
    add 9, 9, 11
    slwi 9, 9, 1
    addi 9, 9, {SOUND_TABLE}
    lhzx 9, 29, 9
    cmplwi 9, {SOUND_NONE}
    beqlr
    b cs_def
cs_bank:
    subf 9, 7, 3
cs_def:
    lwz 11, {C_SOUND_NEXT}(29)      # r3 = the next of our definitions
    addi 12, 11, 1
    stw 12, {C_SOUND_NEXT}(29)
    andi. 11, 11, {SOUND_DEFS} - 1
    slwi 11, 11, 5
    addi 11, 11, {C_SOUND_DEFS}
    add 3, 29, 11
    li 11, 0
    stw 11, 0(3)
    stw 11, 8(3)
    stw 11, 0x10(3)
    stw 11, 0x14(3)
    lis 11, 0x4280                  # (range 64)
    stw 11, 4(3)
    stw 10, 0xc(3)
    li 11, 2
    sth 11, 0x18(3)
    sth 9, 0x1a(3)
    stw 8, 0x1c(3)
    li 4, 0
    li 6, 0
    li 7, 0x400
    b {PLAY_SOUND_DEF}

coop_banks:                         # (r29) OWN_BANKS loaded, once (the loader relocates a bank in place)
    lwz 9, {C_BANKS_IN}(29)
    cmpwi 9, 0
    bnelr
    li 9, 1
    stw 9, {C_BANKS_IN}(29)
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
{OWN_BANKS_LOAD}
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

coop_sound_try:                     # (r29, r30) C_SOUND_TRY, a sound plus 1 (tools/coop.py sound), played once
    lwz 3, {C_SOUND_TRY}(29)
    cmpwi 3, 0
    beqlr
    li 9, 0
    stw 9, {C_SOUND_TRY}(29)
    addi 3, 3, -1
    b coop_sound
"""
