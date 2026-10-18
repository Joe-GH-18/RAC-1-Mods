"""The level-up's effects besides the flash (display.py): gold puffs and smoke from the weapon,
the weapon white-hot, Ratchet glowing, the camera's shake and the sound. Its numbers are a block
of writable data (FX), so they can be tuned in a running game.
"""
from ..game import *  # noqa: F401,F403

# The level-up. Its numbers are one block of writable data (FX, see data()), so they can be
# changed in a running game with tools/peek.py; the constants cannot, it does not get through
# to them. The block: two sets of puffs of 0x38 bytes each, the smoke and the burst (+0 where
# from the weapon's origin, +0xc velocity, +0x1c f1, +0x20 scatter, +0x24 the two colours, +0x2c
# the two frame counts, +0x34 how many: a frame for the smoke, in all for the burst), then
#   +0x70 frames the level-up runs (smoke for all of them; counted down in the state block)
#   +0x74 frames the weapon takes from +0x78, the colour it starts with, to its own
#   +0x7c the colour Ratchet's moby is given for the first +0x80 frames (it eases back by itself)
#   +0x84/+0x88 the two sounds, as Ratchet's sound definition + 1 (0 = none; which of his 64
#   a level's sound bank holds differs), +0x8c the frame the second one plays in
#   +0x90 write a sound definition + 1 here to hear it, +0x94 write 1 to see the level-up again
#   +0x98 frames and +0x9c strength of the camera shake
#   +0xa0 frames and +0xa4 alpha at the start of the flash of the whole screen
#   +0xa8/+0xac kept while it runs: the weapon whose colour is not the mod's, and that colour
#   +0xb0 a third set, DAZE, above every enemy the Taunter has stunned (a frame each), then
#   +0xe8 STUN_FRAMES, +0xec STUN_ARRIVE (float), +0xf0 STUN_COOLDOWN, +0xf4 LURE_FRAMES
# The puffs are the game's own, the ones a breaking crate gives off:
# PUFF(position, velocity, colour AABBGGRR, second colour, -, frames, second frame count, -, 0, 0;
# f1, f2 = how far the velocity is scattered) makes one particle (type 0xb), or none in a frame
# that took long. What the numbers do, from screenshots of a running game: the puff is a soft
# ball of glow that is added to the picture and grows; the second colour is the one that shows
# most, and with an alpha of 0x18 and more a puff a frame is a solid yellow ball, with a darker
# tail above; f1 is the square of the distance it is drawn up to (at 40 nothing showed); the
# velocity is in units a frame.
PUFF = 0x123390
PUFFS = ">3f4f2f2I2iI"         # the layout of a set
SMOKE = ((0.0, 0.0, 0.5), (0.0, 0.0, 0.12), 400000.0, 0.05, (0x0820C8FF, 0x0520B8FF), (34, 35), 1)
BURST = ((0.0, 0.0, 0.3), (0.0, 0.0, 0.0), 400000.0, 0.18, (0x3060E0FF, 0x2840D0FF), (30, 35), 24)
LEVELUP_FRAMES = 100
WEAPON_FLASH = (40, 0xFFFFFF)          # frames, colour 00BBGGRR
HERO_GLOW = (0x40B0FF, 20)             # colour, frames
# The sound is Ratchet's sound definition 24, the user's choice by ear (tools/levels.py sound 24)
# after RC2's own were tried (see NOTES.md). All 19 levels' banks hold it.
SOUNDS = (24 + 1, 0, 12)
SHAKE = (40, 0.3)


# levelup_frame: replaces bl HERO_MAIN; fx_tick(): the level-up's frame (r31 = state block, r30 =
#   the weapon, r29 = hero, r28 = FX, r26 = frames into it); puffs(r3 = a set): its puffs from
#   the weapon r30 (the position is at 0x80 on the stack); celebrate(): start a level-up.
FX = """
levelup_frame:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    bl fx_tick
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
levelup_frame_next:
    {CHAIN}

fx_tick:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0xa0(1)
    std 31, 0x70(1)
    std 30, 0x78(1)
    std 29, 0x80(1)
    std 28, 0x88(1)
    std 26, 0x90(1)
    lis 31, {STATE_HA}
    addi 31, 31, {STATE_LO}
    lis 29, {HERO_HA}
    addi 29, 29, {HERO_LO}
    lis 28, {FX_HA}
    addi 28, 28, {FX_LO}
    lwz 3, 0x90(28)                 # a sound to hear
    li 0, 0
    stw 0, 0x90(28)
    bl fx_sound
    lwz 3, 0x94(28)                 # the level-up again
    cmpwi 3, 0
    beq fx_run
    li 0, 0
    stw 0, 0x94(28)
    bl celebrate
fx_run:
    bl daze_tick
    lwz 9, 0x15c(31)
    cmpwi 9, 0
    ble fx_out
    lwz 26, 0x70(28)
    subf 26, 9, 26
    addi 9, 9, -1
    stw 9, 0x15c(31)
    lbz 10, 0x20a4(29)
    cmpwi 10, 0
    bne fx_out
    cmpwi 26, 0
    bne fx_second
    lwz 3, 0x84(28)
    bl fx_sound
    b fx_glow
fx_second:
    lwz 10, 0x8c(28)
    cmpw 26, 10
    bne fx_glow
    lwz 3, 0x88(28)
    bl fx_sound
fx_glow:
    lwz 30, {HAND_MOBY}(29)
    cmpwi 30, 0
    beq fx_out
    cmpwi 26, 0
    bne fx_smoke
    addi 3, 28, 0x38
    bl puffs
fx_smoke:
    mr 3, 28
    bl puffs
fx_out:
    ld 26, 0x90(1)
    ld 28, 0x88(1)
    ld 29, 0x80(1)
    ld 30, 0x78(1)
    ld 31, 0x70(1)
    addi 1, 1, 0xa0
    ld 0, 0x10(1)
    mtlr 0
    blr

fx_sound:                           # (r3 = one of Ratchet's sound definitions + 1, or 0)
    cmpwi 3, 0
    beqlr
    addi 3, 3, -1
    li 4, 0
    lwz 5, 0x2080(29)
    b {PLAY_MODEL_SOUND}

celebrate:
    lis 9, {STATE_HA}
    addi 9, 9, {STATE_LO}
    lis 10, {FX_HA}
    addi 10, 10, {FX_LO}
    lwz 8, 0xa0(10)
    stw 8, 0x130(9)
    lwz 8, 0x70(10)
    stw 8, 0x15c(9)
    lis 9, {CAMERA_STATE_HA}
    addi 9, 9, {CAMERA_STATE_LO}
    lfs 0, 0x9c(10)
    stfs 0, 0x160(9)
    lwz 8, 0x98(10)
    stw 8, 0x168(9)
    stw 8, 0x16c(9)
    blr

puffs:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0xb0(1)
    std 28, 0x98(1)
    std 27, 0xa0(1)
    mr 28, 3
    lwz 27, 0x34(28)
pf_next:
    cmpwi 27, 0
    ble pf_out
    lfs 0, 0x10(30)
    lfs 1, 0(28)
    fadds 0, 0, 1
    stfs 0, 0x80(1)
    lfs 0, 0x14(30)
    lfs 1, 4(28)
    fadds 0, 0, 1
    stfs 0, 0x84(1)
    lfs 0, 0x18(30)
    lfs 1, 8(28)
    fadds 0, 0, 1
    stfs 0, 0x88(1)
    lfs 0, 0x1c(30)
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
    b pf_next
pf_out:
    ld 27, 0xa0(1)
    ld 28, 0x98(1)
    addi 1, 1, 0xb0
    ld 0, 0x10(1)
    mtlr 0
    blr
"""
