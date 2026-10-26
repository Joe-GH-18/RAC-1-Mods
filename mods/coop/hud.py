"""What is set at the HUD hook, the last thing in a frame's update: backpack Clank and the pack
hidden while Clank is out, his light, the wings and jets placed on him."""
from ..game import *  # noqa: F401,F403

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
"""
