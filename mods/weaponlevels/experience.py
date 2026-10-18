"""How a weapon earns its experience and reaches level 2.

Every kill that drops bolts goes through 0xfd8d0 (KILL_HOOK): the weapon in Ratchet's hand gets
the enemy's bolt value, unless the wrench killed it; the Decoy Glove and the Drone Device get
what dies while their decoys or drones are out, the Taunter what dies of the enemies it lured
(taunter.py), and the two bosses are worth half of what a weapon still needs. At the threshold
the weapon gets the game's gold version, or level 2 for the five without one, a message, the
level-up (fx.py) and its ammunition filled up.
"""
from ..game import *  # noqa: F401,F403

DAMAGE_RING = 0xA14C00         # 64 entries of 0x40 bytes: +0x24 flags, +0x2c damage, +0x34 target; moby +0xa4 = its entry
WRENCH_DAMAGE = 0x10000        # damage flag
KILL_HOOK = 0xFD8E0            # lhz r7, 0xb4(r3) in 0xfd8d0, behind its saving of the return address
KILL_HOOK_WORD = 0xA0E300B4
# The Decoy Glove kills nothing itself, so it is given what dies while one of its decoys stands:
# 0x2e7140 makes a decoy (class 0xcb, the gold one 0x76c) and 0x2e8af8 is its update, which notes
# the frame here. That function runs for other mobys too (in game it ran every frame for a player
# who does not own the glove), so the class is looked at.
DECOY_GLOVE = 0x19
DECOY_CLASS, GOLD_DECOY_CLASS = 0xCB, 0x76C
DECOY_HOOK = 0x2E8B18          # ori r31, r3, 0
DECOY_HOOK_WORD = 0x607F0000
DECOY_FRAMES = 3               # a decoy seen this many frames ago at most is standing
# The Drone Device's drones (class 0x1df, made by its fire function 0x39ac10, update 0x39b390)
# kill while Ratchet holds the wrench again (seen in game: item 8 in his hand), so the device is
# given what dies while drones are out, in the same way (DRONE_HOOK notes the frame in state
# +0x190); r4 is in use where the hook is.
DRONE_DEVICE, DRONE_CLASS = 0x18, 0x1DF
# The Drone Device at level 2 (the user's wish, 2026-10-14): gold drones, and twice as many. Its
# fire function launches drones until hero +0x1ff6 (the count, raised by the spawner 0x39a708 and
# lowered by a drone that goes) reaches 6, compared at the three DRONE_CAP_HOOKS; a level 2 device
# compares with DRONE_CAP_L2. Nothing keeps one slot per drone (the nine words at hero +0x1ffc
# are their targets), so more drones fit. The gold is the hand weapons' WEAPON_TINT (state
# +0x158), given to each drone at the top of its update (drone_seen).
DRONE_CAP_HOOKS = ((0x39AC74, 0x2C030006, "drone_cap3"), (0x39AE54, 0x2C1F0006, "drone_cap31"),
                   (0x39AE88, 0x2C1F0006, "drone_cap31"))
DRONE_CAP, DRONE_CAP_L2 = 6, 12
# Bosses (the user's pick, 2026-10-14) are worth half of what the weapon still needs for level 2,
# whatever their bolt value: the Blargian Snagglebeast on Umbris (level 7: bolt value 0) and the
# mutant on Blarg Station (level 6: 193). Both die through the bolt drop (the Snagglebeast at
# 0x1c7d40); their classes were picked out of the levels' gameplay files as the one large class of
# a single instance there (moby records of 0x78 bytes: +0x10 bolts, +0x18 class). Qwark and Drek
# were left out at the user's wish (neither dies through the bolt drop).
BOSS_SNAGGLEBEAST, BOSS_MUTANT = 0x452, 0x41B
DRONE_HOOK = 0x39B3C4          # ori r31, r3, 0
DRONE_HOOK_WORD = 0x607F0000

# The message. Text table: 16-byte entries {string, id, ..}, the pointer to it at TEXT_TABLE, their
# number at TEXT_COUNT. SHOW_MESSAGE(text id, message index) puts a help message up in place of the
# one showing; the index is that of its 8-byte record in the saved block 0xa1000c (+0 how often it
# was shown; 0xffff there keeps it from showing), 0x94 of them.
SHOW_MESSAGE = 0x7B4F0
MESSAGE_INDEX = 0x93           # the last record; taken to be unused
TEXT_TABLE = 0xA1A800
TEXT_COUNT = 0x7208B0
GOLD_TEXT = {0x0A: 0x53CB, 0x10: 0x53CC, 0x0F: 0x53CD, 0x14: 0x53CE, 0x11: 0x53CF,     # "You got the Gold Bomb Glove!" ...
             0x0B: 0x53D0, 0x19: 0x53D1, 0x13: 0x53D2, 0x09: 0x53D3, 0x15: 0x53D4}
BORROWED_TEXT = 0x5302
BOOST_TEXT = "Your \x0c{}\x08 reached level 2!"       # \x0c..\x08 highlights
BOOST_TEXT_SIZE = 48
ITEM_AMMO = 0x737D30                   # 24 bytes per item: +0xe what it holds

# xp_kill: replaces lhz r7, 0xb4(r3) at the top of the bolt drop 0xfd8d0 (r3 = the moby, r4, r5 and
#   the vector register v2 are still to be used by it); r30 = item, r11 -> its experience, r12 = the
#   experience.
LEVELS = """
xp_kill:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0xc0(1)
    std 3, 0x70(1)
    std 4, 0x78(1)
    std 5, 0x80(1)
    std 31, 0x98(1)
    std 30, 0xa0(1)
    li 9, 0xb0
    stvx 2, 1, 9
    mr 31, 3
    bl {IS_CRATE}
    cmpwi 3, 0
    bne xp_out
    lis 9, {HERO_HA}
    addi 9, 9, {HERO_LO}
    lbz 8, 0x20a4(9)                # Ratchet only
    cmpwi 8, 0
    bne xp_out
    lwz 30, {HAND_ITEM}(9)
    lbz 8, 0xa4(31)                 # the last damage it took: nothing for the weapon in his hand
    cmpwi 8, 0xff                   # when that was the wrench's
    beq xp_held
    lis 9, {DAMAGE_RING_HA}
    addi 9, 9, {DAMAGE_RING_LO}
    slwi 8, 8, 6
    add 9, 9, 8
    lwz 8, 0x34(9)
    cmpw 8, 31
    bne xp_held
    lwz 8, 0x24(9)
    andis. 8, 8, {WRENCH_HI}
    bne xp_decoy
xp_held:
    bl xp_award
xp_decoy:                           # a decoy is standing: the Decoy Glove gets the same, whatever killed it
    cmpwi 30, {DECOY_GLOVE}
    beq xp_taunt
    lis 9, {STATE_HA}
    addi 9, 9, {STATE_LO}
    lwz 8, 0x134(9)
    cmpwi 8, 0
    beq xp_taunt
    lis 10, {FRAME_COUNTER_HA}
    lwz 10, {FRAME_COUNTER_LO}(10)
    subf 10, 8, 10
    cmplwi 10, {DECOY_FRAMES}
    bgt xp_taunt
    li 30, {DECOY_GLOVE}
    bl xp_award
xp_taunt:                           # it was lured: the Taunter gets the same, unless it is in his hand
    mr 3, 31
    bl lure_find
    cmpwi 12, 0
    beq xp_drone
    lwz 8, 8(12)
    li 9, 0                         # the entry is free again
    stw 9, 0(12)
    stw 9, 8(12)
    stw 9, 0xc(12)
    lis 10, {FRAME_COUNTER_HA}
    lwz 10, {FRAME_COUNTER_LO}(10)
    subf 10, 8, 10
    lis 9, {FX_HA}
    addi 9, 9, {FX_LO}
    lwz 9, {FX_LURE_FRAMES}(9)
    cmplw 10, 9
    bgt xp_drone
    lis 9, {HERO_HA}
    addi 9, 9, {HERO_LO}
    lwz 8, {HAND_ITEM}(9)
    cmpwi 8, {TAUNTER}
    beq xp_drone
    li 30, {TAUNTER}
    bl xp_award
xp_drone:                           # drones are out: the Drone Device gets it, unless it is in his hand
    lis 9, {HERO_HA}
    addi 9, 9, {HERO_LO}
    lwz 8, {HAND_ITEM}(9)
    cmpwi 8, {DRONE_DEVICE}
    beq xp_out
    lis 9, {STATE_HA}
    addi 9, 9, {STATE_LO}
    lwz 8, 0x190(9)
    cmpwi 8, 0
    beq xp_out
    lis 10, {FRAME_COUNTER_HA}
    lwz 10, {FRAME_COUNTER_LO}(10)
    subf 10, 8, 10
    cmplwi 10, {DECOY_FRAMES}
    bgt xp_out
    li 30, {DRONE_DEVICE}
    bl xp_award
xp_out:
    li 9, 0xb0
    lvx 2, 1, 9
    ld 30, 0xa0(1)
    ld 31, 0x98(1)
    ld 5, 0x80(1)
    ld 4, 0x78(1)
    ld 3, 0x70(1)
    addi 1, 1, 0xc0
    ld 0, 0x10(1)
    mtlr 0
    lhz 7, 0xb4(3)                  # the displaced instruction
    blr

decoy_seen:                         # replaces ori r31, r3, 0 at the top of the update (r3 = the moby)
    lhz 11, 0xa6(3)
    cmpwi 11, {DECOY_CLASS}
    beq decoy_stamp
    cmpwi 11, {GOLD_DECOY_CLASS}
    bne decoy_out
decoy_stamp:
    lis 11, {FRAME_COUNTER_HA}
    lwz 11, {FRAME_COUNTER_LO}(11)
    lis 12, {STATE_HA}
    addi 12, 12, {STATE_LO}
    stw 11, 0x134(12)
decoy_out:
    ori 31, 3, 0                    # the displaced instruction
    blr

drone_seen:                         # replaces ori r31, r3, 0 in the drones' update (r3 = the moby; r4 in use)
    lhz 11, 0xa6(3)
    cmpwi 11, {DRONE_CLASS}
    bne drone_out
    lis 11, {FRAME_COUNTER_HA}
    lwz 11, {FRAME_COUNTER_LO}(11)
    lis 12, {STATE_HA}
    addi 12, 12, {STATE_LO}
    stw 11, 0x190(12)
    li 10, {DRONE_DEVICE}
@LEVEL2 drone_out@
    lis 12, {STATE_HA}
    addi 12, 12, {STATE_LO}
    lwz 12, 0x158(12)
    cmpwi 12, 0
    bne drone_gold
    lis 12, {WEAPON_TINT_HI}
    ori 12, 12, {WEAPON_TINT_LO}
drone_gold:
    stw 12, 0x38(3)
drone_out:
    ori 31, 3, 0                    # the displaced instruction
    blr

drone_cap3:                         # replace cmpwi r3/r31, 6 in the fire function (r0, r9 to r12 free)
    mflr 0
    bl drone_limit
    mtlr 0
    cmpw 3, 12
    blr
drone_cap31:
    mflr 0
    bl drone_limit
    mtlr 0
    cmpw 31, 12
    blr
drone_limit:                        # r12 = how many drones the device keeps out
    li 12, {DRONE_CAP}
    li 10, {DRONE_DEVICE}
@LEVEL2 dl_out@
    li 12, {DRONE_CAP_L2}
dl_out:
    blr

xp_award:                           # (r30 item, r31 the moby killed)
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    cmplwi 30, {LAST_ITEM}
    bgt xa_out
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    addi 10, 9, {P_XP_AT}
    lbzx 10, 10, 30
    cmpwi 10, {NO_WEAPON}
    beq xa_out
    lis 11, {AMMO_HA}
    addi 11, 11, {AMMO_LO}
    add 11, 11, 10
    lhz 12, 0(11)
    cmplwi 12, 0xffff               # at level 2 already
    beq xa_out
    lis 10, {GOLD_HA}
    addi 10, 10, {GOLD_LO}
    lbzx 8, 10, 30
    cmpwi 8, 0                      # gold already
    bne xa_out
    lhz 8, 0xa6(31)                 # a boss: half of what the weapon still needs
    cmpwi 8, {BOSS_SNAGGLEBEAST}
    beq xa_boss
    cmpwi 8, {BOSS_MUTANT}
    beq xa_boss
    lha 8, 0xb4(31)                 # what it is worth in bolts
    b xa_worth
xa_boss:
    addi 8, 9, {P_XP_NEEDED}
    slwi 7, 30, 1
    lhzx 8, 8, 7
    subf 8, 12, 8
    srawi 8, 8, 1
    cmpwi 8, 1
    bge xa_worth
    li 8, 1
xa_worth:
    cmpwi 8, 0
    ble xa_out
    add 12, 12, 8
    addi 8, 9, {P_XP_NEEDED}
    slwi 7, 30, 1
    lhzx 8, 8, 7
    cmplw 12, 8
    bge xp_level
    sth 12, 0(11)
    b xa_out
xp_level:
    mulli 8, 30, 0x4c               # the item has a second name: there is a gold version of it
    lis 7, {ITEM_TABLE_HA}
    addi 7, 7, {ITEM_TABLE_LO}
    add 7, 7, 8
    lwz 7, 4(7)
    cmpwi 7, 0
    beq xp_boost
    li 7, 1
    stbx 7, 10, 30
    li 12, 0
    sth 12, 0(11)
    addi 8, 9, {P_GOLD_TEXT}        # the game's own message for the gold version
    slwi 7, 30, 1
    lhzx 3, 8, 7
    b xp_tell
xp_boost:
    li 12, -1
    sth 12, 0(11)
    addi 8, 9, {P_BOOST_TEXT_AT}    # the borrowed text entry gets this weapon's text
    lbzx 8, 8, 30
    add 8, 8, 9
    addi 8, 8, {P_BOOST_TEXTS}
    lis 10, {TEXT_TABLE_HA}
    lwz 10, {TEXT_TABLE_LO}(10)
    lis 11, {TEXT_COUNT_HA}
    lwz 11, {TEXT_COUNT_LO}(11)
    cmpwi 11, 0
    ble xa_out
    mtctr 11
xp_find:
    lwz 12, 4(10)
    cmpwi 12, {BORROWED_TEXT}
    beq xp_found
    addi 10, 10, 16
    bdnz xp_find
    b xa_out
xp_found:
    stw 8, 0(10)
    li 3, {BORROWED_TEXT}
xp_tell:
    mulli 8, 30, 24                 # the weapon is filled up
    lis 7, {ITEM_AMMO_HA}
    addi 7, 7, {ITEM_AMMO_LO}
    add 7, 7, 8
    lhz 7, 0xe(7)
    cmpwi 7, 0
    beq xp_filled
    lis 9, {AMMO_HA}
    addi 9, 9, {AMMO_LO}
    slwi 8, 30, 2
    stwx 7, 9, 8
xp_filled:
    lis 4, {STATE_HA}
    addi 4, 4, {STATE_LO}
    lwz 4, 0x11c(4)
    cmpwi 4, 0
    bne xp_show
    li 4, {MESSAGE_INDEX}
xp_show:
    bl {SHOW_MESSAGE}
    bl celebrate
{BOLT_BURST}
xa_out:
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr
"""


# Bolts worth {LEVELUP_BOLTS} from the enemy (r31), with the last argument its own drop passes on.
BOLT_BURST = """
    mr 3, 31
    li 4, {LEVELUP_BOLTS}
    li 5, {LEVELUP_BOLTS}
    li 6, {BOLT_FLY}
    ld 7, 0xf0(1)                   # r5 as xp_kill kept it
    bl {SPAWN_BOLTS}
"""
