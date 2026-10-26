"""Controller 2.

The pad read 0x11e2d4 (called from 0x12284, 0x1313c, 0xe14a0, 0xe14bc, 0xe14f8, 0xe1528) loops
the ports 0..3: for each it calls the pad driver's virtual function +0x10 (r3 = *PAD_DRIVER,
r4 = the port, r5 = the port's block at PORTS + port * PORT_SIZE; the driver is 0x4ec160:
cellPadGetInfo2, then cellPadGetData), which sets the block's +0x9c (and +0x458) to 1 when the
port delivered data and to 0 when not; the first block with +0x9c set is copied whole to PAD and
the loop ends. So with Player 1 on port 0 the other ports are never read.

coop_pad, at the read's epilogue (r28 = the port it took, 4 when none), reads the ports after
Player 1's the same way, once per frame (FRAME_COUNTER), and the first that delivers is Player
2's: its block, laid out as PAD, goes to STATE + COOP_PAD (0 = none). The block's own button
words are kept by the driver (0x4eb6e8 with the block's history), and the mod keeps its own
"pressed this frame" of the held word as well (C_PRESSED), for the case they are not filled
the same way as PAD's.
"""
from ..game import *  # noqa: F401,F403

PAD_DRIVER = 0x902EDC          # -> the pad driver object; its vtable +0x10 reads one port
PORTS = 0x965540               # the ports' blocks, PORT_SIZE bytes each, laid out as PAD
PORT_SIZE = 0x564
PORT_COUNT = 4
PORT_ACTIVE = 0x9C             # set by the driver when the port delivered data
PAD_HELD = 0xA0
PAD_READ_HOOK = 0x11E3A0       # ld r0, 0xa0(r1): the pad read's epilogue
PAD_READ_HOOK_WORD = 0xE80100A0

CODE = r"""
# coop_pad: replaces ld r0, 0xa0(r1) in the pad read's epilogue (r28 = the port the game took,
# 4 = none, r29 = PORTS; the epilogue restores r28..r31 behind it, so they are free here).
coop_pad:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    std 2, 0x28(1)
    lis 31, {COOP_HA}
    addi 31, 31, {COOP_LO}
    lis 11, {FRAME_COUNTER_HA}
    lwz 11, {FRAME_COUNTER_LO}(11)
    lwz 12, {C_READ}(31)
    cmpw 11, 12
    beq cp_done                         # read once a frame
    stw 11, {C_READ}(31)
    lwz 12, {C_READS}(31)
    addi 12, 12, 1
    stw 12, {C_READS}(31)
    li 30, 0
    addi 28, 28, 1                      # the ports after Player 1's
cp_port:
    cmpwi 28, {PORT_COUNT}
    bge cp_found
    mulli 4, 28, {PORT_SIZE}
    add 30, 29, 4
    clrldi 30, 30, 32
    lis 3, {PAD_DRIVER_HA}
    lwz 3, {PAD_DRIVER_LO}(3)
    mr 4, 28
    mr 5, 30
    lwz 6, 0(3)
    lwz 6, 0x10(6)
    lwz 7, 0(6)
    lwz 2, 4(6)
    mtctr 7
    bctrl
    ld 2, 0x28(1)
    lwz 3, {PORT_ACTIVE}(30)
    cmpwi 3, 0
    bne cp_found
    li 30, 0
    addi 28, 28, 1
    b cp_port
cp_found:
    lis 12, {STATE_HA}
    addi 12, 12, {STATE_LO}
    stw 30, {COOP_PAD}(12)
    li 11, 0
    cmpwi 30, 0
    beq cp_held
    lwz 11, {PAD_HELD}(30)
    stw 28, {C_PORT}(31)
cp_held:
    lwz 12, {C_HELD}(31)
    andc 12, 11, 12
    stw 11, {C_HELD}(31)
    stw 12, {C_PRESSED}(31)
cp_done:
    ld 0, 0x80(1)
    addi 1, 1, 0x70
    mtlr 0
    ld 0, 0xa0(1)                       # the displaced instruction
    blr
"""
