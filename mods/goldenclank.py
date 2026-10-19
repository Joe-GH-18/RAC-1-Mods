"""Golden Clank: bought with all 40 gold bolts in the gold weapons room, and gold from then on.

With the weapon levels, the gold weapons come from experience, so the gold weapons rooms (Novalis,
level 1, and the Gemlik Base, level 13) sell Golden Clank instead: under the dome where the Gold
Devastator stood, Clank turns slowly, in gold; standing in front of it, Ratchet is told the price,
all 40 gold bolts, and with all of them Circle buys him. From then on Clank on Ratchet's back and
his Heli-, Thruster- and Hydro-Pack are gold. (What Golden Clank can do comes next.)

The room. Each gold weapon is a moby of its own above a pedestal, classes 0x5b0..0x5b9 (one per
weapon, in the order of the item ids at 0x811cb0; 0x5b2 is the Devastator's), with the update
0x339b70, which also runs the pedestals (class 0x130): it shows the prompt and sells the weapon
(the price, 4 gold bolts, is the prompt system's: 0x4d3870 with the level's prompt records). A
display whose gold version is owned goes to state 0xfd, which the moby loop neither updates nor
draws. The mod skips the update of the displays (PEDESTAL_HOOK) and runs them itself from the
frame hook: all of them in state 0xfd, but the Devastator's, which gets the model of Clank on
Ratchet's back (class 0x259, in every level), turns and is gold, until Golden Clank is bought.
Nothing animates it (its update is skipped), so it is held in a pose of that model (POSE); without
one the model is drawn in its bind pose, the head apart from the body.

Gold bolts are 80 flag bytes at 0xa0ca34 (4 per planet); GOLD_BOLT_COUNT counts the set ones (the
pause menu's "%d of 40"). Collecting is all there is to them: the game takes 4 off the count for
each gold weapon owned. Golden Clank wants all 40 and takes them all the same way; the purchase is
a word of the save (OWNED, beside the Taunter's experience in item 1's ammunition int, which no
weapon uses).

A moby's colour (+0x38) is set again every frame by the level's lighting, so the gold goes on at
the HUD's hook, the last thing in the frame's update.
"""
from .game import *  # noqa: F401,F403

NAME = "goldenclank"
TITLE = "Golden Clank"
ABOUT = ("The gold weapons rooms sell Golden Clank for all 40 gold bolts (the gold weapons come from the weapon levels); "
         "Clank and his packs are gold from then on.")

ROOMS = (1, 13)                    # Novalis, Gemlik Base: PLANET
PEDESTAL_HOOK = 0x339B70           # stdu r1, -0x80(r1): the top of the displays' and pedestals' update
PEDESTAL_HOOK_WORD = 0xF821FF81
PEDESTAL_BACK = PEDESTAL_HOOK + 4
DISPLAY_FIRST, DISPLAY_COUNT = 0x5B0, 10
SHOW_CLASS = 0x5B2                 # the Gold Devastator's display: the one Ratchet faces in the room
HIDDEN = 0xFD                      # a display's state when its gold weapon is owned
CLANK_CLASS = 0x259                # Clank on Ratchet's back
GOLD_BOLT_COUNT = 0x11B1B4         # () -> gold bolts collected
ALL_GOLD_BOLTS = 40
OWNED = 0x96C0B2                   # u16 of the save: 1 = Golden Clank is bought (ammunition array + 6)
HERO_KIND, HERO_CLANK_MOBY, HERO_PACK_MOBY = 0x20A4, 0x1184, 0x1180
CIRCLE = 0x20                      # PAD bit
BORROWED_TEXT = 0x5301             # "Gold Weapon purchase" (the table has it twice; weaponlevels borrows 0x5302)
MESSAGE_INDEX = 0x92
BUY_SOUND = 24                     # Ratchet's sound definition 24, the weapon levels' level-up sound
GOLD = 0x0C64B0                    # 00BBGGRR, the weapon levels' gold
DISPLAY_SCALE = 0.3
DISPLAY_LIFT = 0.0                 # added to the display's height
POSE = (1, 2, 1, 1, 0.4)           # frame, next frame, their animations, the blend between them: folded, eyes to the front
FRAME_POINTERS = 0xEF74C           # (r3 moby): +0x68/+0x6c from the animations and frames at +0x50..+0x53
SPIN = 0.02                        # rad a frame
RANGE = 3.5                        # how near Ratchet has to be to the display (x and y)
SHAKE = (30, 0.25)                 # frames, strength of the camera shake at the purchase
TEXT_BUY = b"Press \x11 to buy \x0cGolden Clank\x08 for all 40 \x0cGold Bolts\x08"   # \x11: Circle; \x0c..\x08: highlight
TEXT_COST = b"\x0cGolden Clank\x08 costs all 40 \x0cGold Bolts\x08. You have %d."
TEXT_GOT = b"You got \x0cGolden Clank\x08!"
TEXT_ROOM = 64                     # the formatted text's buffer
# State block (game.py): +0x2a0 the display found this frame (0 = none), +0x2a4 the prompt is up,
# +0x2a8 the display's height as found; for tuning in a running game (0 = the built-in value):
# +0x2ac scale (float), +0x2b0 height above it (float), +0x2b4 turn a frame (float), +0x2b8 colour,
# +0x2bc/+0x2bd animation and frame of the pose, used when +0x2bf is not 0.
S_DISPLAY, S_PROMPT, S_BASE_Z = 0x2A0, 0x2A4, 0x2A8
S_SCALE, S_LIFT, S_SPIN, S_COLOUR = 0x2AC, 0x2B0, 0x2B4, 0x2B8
S_POSE_ANIM, S_POSE_FRAME, S_POSE_ON = 0x2BC, 0x2BD, 0x2BF

# pedestal: jumped to from the top of the update (r3 = the moby; LR is the moby loop's).
# gc_frame: replaces bl HERO_MAIN; gc_tick(): the room, the prompt and the purchase.
# gc_say(r3 = a string): the borrowed text entry gets it, and it is shown.
# gc_hud: at the HUD's hook: the gold.
CODE = """
pedestal:
    lhz 11, 0xa6(3)
    addi 11, 11, -{DISPLAY_FIRST}
    cmplwi 11, {DISPLAY_LAST}       # (unsigned: a class below DISPLAY_FIRST is above it too)
    blelr                           # a display: run by gc_tick
pedestal_game:
    stdu 1, -0x80(1)                # the displaced instruction
    b {PEDESTAL_BACK}

gc_frame:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    bl gc_tick
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
gc_frame_next:
    {CHAIN}

gc_tick:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0xd0(1)
    std 31, 0x70(1)
    std 30, 0x78(1)
    std 29, 0x80(1)
    std 28, 0x88(1)
    std 27, 0x90(1)
    std 26, 0x98(1)
    std 25, 0xa0(1)
    lis 31, {STATE_HA}
    addi 31, 31, {STATE_LO}
    lis 30, {HERO_HA}
    addi 30, 30, {HERO_LO}
    lis 25, {POOL_HA}
    addi 25, 25, {POOL_LO}
    li 29, 0                        # the display, if one is found
    lis 9, {PLANET_HA}
    lwz 9, {PLANET_LO}(9)
    cmpwi 9, {ROOM_A}
    beq gt_room
    cmpwi 9, {ROOM_B}
    bne gt_found
gt_room:
    lis 9, {OWNED_HA}
    lhz 28, {OWNED_LO}(9)
    lis 9, {MOBY_ARRAY_HA}
    lwz 27, {MOBY_ARRAY_LO}(9)
gt_scan:                            # every display goes out but the one for Golden Clank
    lbz 9, 0x20(27)
    cmpwi 9, 0xff
    beq gt_found
    lhz 9, 0xa6(27)
    addi 9, 9, -{DISPLAY_FIRST}
    cmplwi 9, {DISPLAY_LAST}
    bgt gt_next
    cmpwi 9, {SHOW_OFF}
    bne gt_hide
    cmpwi 28, 0
    bne gt_hide
    mr 29, 27
    b gt_next
gt_hide:
    li 9, {HIDDEN}
    stb 9, 0x20(27)
gt_next:
    addi 27, 27, 0x100
    b gt_scan
gt_found:
    lwz 9, {S_DISPLAY}(31)
    stw 29, {S_DISPLAY}(31)
    cmpwi 29, 0
    beq gt_away
    cmpw 9, 29
    beq gt_known
    lfs 0, 0x18(29)                 # a new display: its height as found
    stfs 0, {S_BASE_Z}(31)
gt_known:
    li 9, 1                         # drawn and animated (its update is skipped)
    stb 9, 0x20(29)
    lis 9, {CLASS_SLOT_MAP_HA}
    addi 9, 9, {CLASS_SLOT_MAP_LO}
    lbz 9, {CLANK_CLASS}(9)
    cmplwi 9, {MODEL_SLOTS}
    bge gt_model
    slwi 9, 9, 2
    lis 10, {MODEL_TABLE_HA}
    addi 10, 10, {MODEL_TABLE_LO}
    lwzx 10, 10, 9
    cmpwi 10, 0
    beq gt_model
    stw 10, 0x24(29)
    lis 9, {POSE_HI}                # the pose: +0x50/+0x51 two frames, +0x52/+0x53 their animation
    ori 9, 9, {POSE_LO}
    stw 9, 0x50(29)
    lbz 9, {S_POSE_ON}(31)
    cmpwi 9, 0
    beq gt_pose
    lbz 9, {S_POSE_ANIM}(31)
    stb 9, 0x52(29)
    stb 9, 0x53(29)
    lbz 9, {S_POSE_FRAME}(31)
    stb 9, 0x50(29)
    stb 9, 0x51(29)
gt_pose:
    lfs 0, {P_POSE_BLEND}(25)
    stfs 0, 0x54(29)
    lfs 0, {P_POSE_SPEED}(25)
    stfs 0, 0x58(29)
    lfs 0, {P_POSE_EASE}(25)
    stfs 0, 0x5c(29)
    mr 3, 29
    bl {FRAME_POINTERS}
gt_model:
    lfs 1, {P_SCALE}(25)
    lwz 9, {S_SCALE}(31)
    cmpwi 9, 0
    beq gt_scale
    lfs 1, {S_SCALE}(31)
gt_scale:
    stfs 1, 0x2c(29)
    lfs 1, {P_LIFT}(25)
    lwz 9, {S_LIFT}(31)
    cmpwi 9, 0
    beq gt_lift
    lfs 1, {S_LIFT}(31)
gt_lift:
    lfs 0, {S_BASE_Z}(31)
    fadds 0, 0, 1
    stfs 0, 0x18(29)
    lfs 1, {P_SPIN}(25)
    lwz 9, {S_SPIN}(31)
    cmpwi 9, 0
    beq gt_spin
    lfs 1, {S_SPIN}(31)
gt_spin:
    lfs 0, 0x48(29)
    fadds 0, 0, 1
    lfs 1, {P_TWO_PI}(25)
    fcmpu 0, 0, 1
    blt gt_angle
    fsubs 0, 0, 1
gt_angle:
    stfs 0, 0x48(29)
    lbz 9, {HERO_KIND}(30)          # Ratchet only
    cmpwi 9, 0
    bne gt_away
    lfs 0, 0x80(30)                 # near enough?
    lfs 1, 0x10(29)
    fsubs 0, 0, 1
    fmuls 0, 0, 0
    lfs 1, 0x84(30)
    lfs 2, 0x14(29)
    fsubs 1, 1, 2
    fmadds 0, 1, 1, 0
    lfs 1, {P_RANGE2}(25)
    fcmpu 0, 0, 1
    bge gt_away
    lis 26, {PAD_HA}                # Circle is the mod's here, not the weapon's
    addi 26, 26, {PAD_LO}
    lwz 27, 0xa4(26)
    lwz 9, 0xa0(26)
    rlwinm 9, 9, 0, {CIRCLE_CLEAR_MB}, {CIRCLE_CLEAR_ME}
    stw 9, 0xa0(26)
    rlwinm 9, 27, 0, {CIRCLE_CLEAR_MB}, {CIRCLE_CLEAR_ME}
    stw 9, 0xa4(26)
    bl {GOLD_BOLT_COUNT}
    mr 28, 3
    lwz 9, {S_PROMPT}(31)
    cmpwi 9, 0
    bne gt_shown
    li 9, 1
    stw 9, {S_PROMPT}(31)
    cmpwi 28, {ALL_GOLD_BOLTS}
    blt gt_cost
    lis 3, {TEXT_BUY_HA}
    addi 3, 3, {TEXT_BUY_LO}
    bl gc_say
    b gt_shown
gt_cost:
    lis 3, {TEXT_BUFFER_HA}
    addi 3, 3, {TEXT_BUFFER_LO}
    lis 4, {TEXT_COST_HA}
    addi 4, 4, {TEXT_COST_LO}
    mr 5, 28
    bl {SPRINTF}
    lis 3, {TEXT_BUFFER_HA}
    addi 3, 3, {TEXT_BUFFER_LO}
    bl gc_say
gt_shown:
    andi. 9, 27, {CIRCLE}
    beq gt_done
    cmpwi 28, {ALL_GOLD_BOLTS}
    blt gt_done
    li 9, 1                         # bought
    lis 10, {OWNED_HA}
    sth 9, {OWNED_LO}(10)
    lis 3, {TEXT_GOT_HA}
    addi 3, 3, {TEXT_GOT_LO}
    bl gc_say
    li 3, {BUY_SOUND}
    li 4, 0
    lwz 5, 0x2080(30)
    bl {PLAY_MODEL_SOUND}
    lis 9, {CAMERA_STATE_HA}
    addi 9, 9, {CAMERA_STATE_LO}
    lfs 0, {P_SHAKE}(25)
    stfs 0, 0x160(9)
    li 10, {SHAKE_FRAMES}
    stw 10, 0x168(9)
    stw 10, 0x16c(9)
    b gt_done
gt_away:                            # not near it (or no display): the prompt goes
    lwz 9, {S_PROMPT}(31)
    cmpwi 9, 0
    beq gt_done
    li 9, 0
    stw 9, {S_PROMPT}(31)
    bl {CANCEL_MESSAGE}
gt_done:
    ld 25, 0xa0(1)
    ld 26, 0x98(1)
    ld 27, 0x90(1)
    ld 28, 0x88(1)
    ld 29, 0x80(1)
    ld 30, 0x78(1)
    ld 31, 0x70(1)
    addi 1, 1, 0xd0
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_say:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lis 10, {TEXT_TABLE_HA}
    lwz 10, {TEXT_TABLE_LO}(10)
    lis 11, {TEXT_COUNT_HA}
    lwz 11, {TEXT_COUNT_LO}(11)
    cmpwi 11, 0
    ble say_out
    mtctr 11
say_find:
    lwz 12, 4(10)
    cmpwi 12, {BORROWED_TEXT}
    beq say_found
    addi 10, 10, 16
    bdnz say_find
    b say_out
say_found:
    stw 3, 0(10)
    li 3, {BORROWED_TEXT}
    li 4, {MESSAGE_INDEX}
    bl {SHOW_MESSAGE}
say_out:
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

gc_hud:
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lis 12, {GOLD_HI}
    ori 12, 12, {GOLD_LO}
    lwz 9, {S_COLOUR}(11)
    cmpwi 9, 0
    beq gh_colour
    mr 12, 9
gh_colour:
    lis 9, {OWNED_HA}
    lhz 9, {OWNED_LO}(9)
    cmpwi 9, 0
    beq gh_display
    lis 10, {HERO_HA}
    addi 10, 10, {HERO_LO}
    lwz 9, {HERO_CLANK_MOBY}(10)
    cmpwi 9, 0
    beq gh_pack
    stw 12, 0x38(9)
gh_pack:
    lwz 9, {HERO_PACK_MOBY}(10)
    cmpwi 9, 0
    beq gc_hud_next
    stw 12, 0x38(9)
    b gc_hud_next
gh_display:
    lwz 9, {S_DISPLAY}(11)
    cmpwi 9, 0
    beq gc_hud_next
    stw 12, 0x38(9)
gc_hud_next:
    {CHAIN}
"""


def hooks(args):
    return [Hook(PEDESTAL_HOOK, "pedestal", PEDESTAL_HOOK_WORD, jump=True),
            *(Hook(site, "gc_frame", HERO_MAIN, chain=True) for site in FRAME_HOOKS),
            Hook(HUD_HOOK, "gc_hud", HUD_HOOK_WORD, chain=True)]


def data(args):
    def texts(vaddr):
        return TEXT_BUY + b"\0" + TEXT_COST + b"\0" + TEXT_GOT + b"\0" + bytes(TEXT_ROOM)
    return [("rw", "texts", texts)]


def pool(args):
    return dict(SCALE=DISPLAY_SCALE, LIFT=DISPLAY_LIFT, SPIN=SPIN, TWO_PI=6.283185307179586,
                RANGE2=RANGE * RANGE, SHAKE=SHAKE[1], POSE_BLEND=POSE[4], POSE_SPEED=1.0, POSE_EASE=0.1)


def parts(args):
    return [CODE]


def fields(args, addr):
    at = addr["texts"]
    cost = at + len(TEXT_BUY) + 1
    got = cost + len(TEXT_COST) + 1
    buffer = got + len(TEXT_GOT) + 1
    bit = 31 - (CIRCLE.bit_length() - 1)        # rlwinm keeps bits mb..me (big-endian numbering): all but CIRCLE
    return dict(**pair("TEXT_BUY", at), **pair("TEXT_COST", cost), **pair("TEXT_GOT", got), **pair("TEXT_BUFFER", buffer),
                ROOM_A=ROOMS[0], ROOM_B=ROOMS[1], DISPLAY_LAST=DISPLAY_COUNT - 1, SHOW_OFF=SHOW_CLASS - DISPLAY_FIRST,
                POSE_HI=POSE[0] << 8 | POSE[1], POSE_LO=POSE[2] << 8 | POSE[3],
                GOLD_HI=GOLD >> 16, GOLD_LO=GOLD & 0xFFFF, SHAKE_FRAMES=SHAKE[0],
                CIRCLE_CLEAR_MB=(bit + 1) % 32, CIRCLE_CLEAR_ME=(bit - 1) % 32)
