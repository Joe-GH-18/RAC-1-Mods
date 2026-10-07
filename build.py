#!/usr/bin/env python3
"""Box Breaker and Charge Boots for Ratchet & Clank 1 HD (NPEA00385).

Box Breaker
-----------
The hyper-strike is hero state 0x14. When it lands, hero_update (0xaaec0) sweeps a 0.4 unit
sphere at 0xb01f4 and damages whatever is inside. That call is redirected into a cave that
runs the original sweep and then a crate-only sweep with a large radius, built from the same
calls the game itself uses for its crate-only sweeps.
As in RC2, the strike shakes the screen when the wrench comes down (RC2 0x83d640): RC2's third
camera shake channel, a roll about the view axis that RC1's camera does not have, is ported and
started with RC2's values. Not in RC2: the bolts of crates that break within 35 frames of the
sweep fly to Ratchet at once, through the bolt spawner's own flag for that.

Charge Boots
------------
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

Strafing
--------
A port of RC2's strafing. RC2 keeps a timer at hero +0x1454 that is 1 while L2 or R2 is held
(hero_main 0x816aa0) and tests it in its hero code; RC1's hero code is the older version of the
same functions, so each of those branches is inserted at the matching RC1 instruction:
  * walking (RC2 0x83ee6c, RC1 0xb1630): Ratchet turns to the camera's yaw and moves along the
    stick's heading (RC2 0x82c238), with RC2's damping when left and right are reversed
  * standing: holding the button turns him to the camera (idle -> walk, RC2 0x84bd80), and the
    walk state lasts until he is aligned (RC2 0x84d770); letting the stick go while strafing
    takes him straight to idle at 1.5 units/s at most (RC2 0x84d7f0) instead of RC1's skid
  * moving sideways twists the body through the two joint controllers RC2 uses for it
    (RC2 0x830a5c); moving backwards plays RC2's backwards walk (RC2 0x836018). That is
    Ratchet animation 0x14 in RC2; RC1 has its skid there, so RC2's is embedded
  * jump with the stick held sideways or back: RC1's own flip state 0xb, chosen and aimed by the
    strafe direction as in RC2 (0x835e64, 0x833698, 0x83388c, 0x848810, 0x82f91c)
  * in the air he keeps facing the camera and moves along the stick's heading (RC2 0x83007c,
    0x8429e4)
In RC1, L2 does what L1 does (first-person view) and R2 what R1 does (crouch). While Ratchet is
on foot (states up to 0x15) the two buttons are taken out of the pad's button words every frame,
so they only strafe; in other states (vehicles, the hover with its own L2/R2 strafe) they are
left alone. Strafing is off while RC1's magnetic-surface flag (hero +0x20b3) is set.
Ratchet speeds up and slows down on the ground as in RC2: 18 and 20 units/s^2 instead of RC1's
7.5 and 8.5, with RC2's three rules for speed while he turns in the walk state
(--rc1-acceleration keeps RC1's).
Not ported: RC2's reads of the timer in 0x82e4b0 (speed bookkeeping), 0x817c68 (a counter of
strafing frames), 0x812e28 (resets hero +0x1e8) and 0x819898 (first-person mode sets the timer).

Bolt crank boost (not in RC2)
-----------------------------
Double-tapping and holding R1 while Ratchet turns a bolt crank (hero state 0x3b, driven by the
crank's own update 0x32adf8) raises the crank's speed cap from 3.7 to 30 units/s (the charge's burst speed), with the
charge animation, sound and foot trails. Position and facing follow the circle at once there.

Clank's thruster dash (not in the games)
----------------------------------------
While the player is Clank (hero +0x20a4 = 1; his idle and walk states are 0x43 and 0x44), R1
held, the stick pushed and X pressed on the ground start a dash: he turns to the stick's
heading at once and makes Ratchet's Thruster-Pack long jump (state 0x10) with Ratchet's own
numbers: 11.5 units/s reached at 44 units/s^2, launched after 5 frames to a height of 0.4
under a gravity of 8.5 units/s^2 (0.6 s in the air, about 7 units), breaking the crates
ahead of him as that jump does. The camera is given the state type of a jump meanwhile, and
a wall that stops him, or the camera in his way, throws him back as the game's bump state
(0x7a) throws Ratchet, done here with Clank's hit animation. It ends when he
touches the ground, at his run speed. Meanwhile he is pitched forward by 90 degrees (hero
euler y, hero +0x94, turned in over 6 frames and back out afterwards), holds his fall
animation, and carries the Thruster-Pack's device (class 0x260, loaded in every level) with
its wings out: a moby of its own that takes his moby's position and matrix every frame.
Like the charge it runs in place of hero_update with the state left
as it is, and that state's transitions are skipped meanwhile, so X does not jump. Movement
The pack's two jets burn meanwhile: the game's own jet mobys, driven from here, and Ratchet's Thruster-Pack sound plays when it starts.


Usage
-----
    .venv/bin/python build.py              build build/EBOOT.elf from the untouched RC1.ppu.elf
    .venv/bin/python build.py --install    ... and copy it over RPCS3's EBOOT.BIN (the file there
                                           is kept once as EBOOT.BIN.bak); restart RPCS3 afterwards
    .venv/bin/python build.py --export patches/boxbreaker-npea00385.bbpatch
                                           ... and write the changes as a patch file; patch.py
                                           applies it to the same executable without any of
                                           this file's dependencies
    .venv/bin/python build.py --help       tuning options (radius, speeds) and paths
    SHOW=1 .venv/bin/python build.py       also print the disassembly of the cave
The input ELF is found through tools/ppu.py (environment variable RC1_ELF overrides the path),
the installation target through RPCS3_EBOOT.
"""
import argparse
import hashlib
import os
import re
import shutil
import struct
import sys

import capstone
import keystone

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from ppu import RC1_ELF, Elf, show  # noqa: E402

ASSETS = os.path.join(ROOT, "assets")                # the RC2 data the build embeds, kept with the source
DEFAULT_OUT = os.path.join(ROOT, "build", "EBOOT.elf")
# RPCS3 boots EBOOT.BIN of the installed game, and takes a plain ELF there.
RPCS3_EBOOT = os.environ.get("RPCS3_EBOOT") or os.path.expanduser(
    "~/.config/rpcs3/dev_hdd0/game/NPEA00385/USRDIR/EBOOT.BIN")

ORIG_MD5 = "931eb96c62424cbb1120419ccf27a38d"

# Game functions and data
COLLECT = 0x5E598          # (r3 centre vec4, f1 radius, r5 flags, r6 ignore moby, r7 damage desc) -> count
RESULTS = 0xA14A00         # moby pointers written by COLLECT
IS_CRATE = 0x10AF88        # (r3 moby) -> class in 0x1f4..0x21c
DEAL_DAMAGE = 0x105C08     # (r3 target, r4 source, r5 flags, f1 damage, r7 pos vec4, r8 dir vec4)
VEC_SCALE = 0x5E822C       # (r3 out, r4 in, f1 scale)
HERO_MAIN = 0x8B778        # per-frame hero entry
HERO = 0x969CE0            # +0x80 position, +0x100 facing, +0x194 ground speed, +0x2080 hero moby
PAD = 0x964A40             # +0xa0 buttons held, +0xa4 buttons pressed this frame
EXPLOSIVE_CRATE = 0x1F5

# Box Breaker screen shake. RC2's hyper-strike handler tests, behind its sweep (0x83d640), whether
# the animation frame (hero +0xc38, RC1 +0xaa8) has just passed 25.7 (the step it made is at
# +0xc3c, RC1 +0xaac). With the Box Breaker owned it then starts camera shake channel 2: strength
# 0.1 for frames(30), and it zeroes channel 0's length. RC1's handler has no such block;
# STRIKE_FX_HOOK is the first instruction behind RC1's sweep, reached on every frame of the state.
# A channel is {+0 strength, +4 current value, +8 frames left, +0xc frames in all}. Both games
# run channels 0 and 1 (camera struct +0x160, +0x170; they move the camera along its up and view
# axes) from the camera update, RC1 0x53550 / RC2 0xb00910, with RC1 0x528e8 / RC2 0xaff858.
# RC2 has a third one at +0x180 that rolls the camera matrix (RC2 +0x370, RC1 +0x350) about the
# view axis: value = strength * sin(freq * (t - 10)) * (left / all)^3 * min(6 t, 1), used as the
# sine of half the roll angle. RC1 keeps its camera pointer at +0x180, so the ported channel
# lives in STATE; SHAKE_HOOK is the call for channel 1, and the port runs right behind it.
STRIKE_FX_HOOK = 0xB01FC           # lwz r3, 0x198(r25)
STRIKE_FX_HOOK_WORD = 0x80790198
STRIKE_FRAME = 25.7                # (RC2 hero table 0x838f7c +0x19c)
SHAKE_STRENGTH = 0.1               # (+0x1a0)
SHAKE_FRAMES = 30
SHAKE_HOOK = 0x53724               # bl SHAKE_CHANNEL with r3 = camera +0x170, r4 = 1
SHAKE_CHANNEL = 0x528E8            # (r3 channel, r4 index)                               [RC2 0xaff858]
CAMERA_STATE = 0x9513C0            # +0x160/+0x170 shake channels, +0x180 camera, +0x350 matrix [RC2 0x146e280]
SHAKE_FREQ = 2001.0 * 0.01745329238474369   # rad/s (RC2 global 0x131eaf4 times table 0xaff81c +0x24)
SHAKE_PHASE = 10.5                 # (+0x34) truncated after scaling: starts 10 s into the wave
SHAKE_RAMP = 6.0                   # (+0x2c)
SIN_TERMS = (-0.16666656732559204, 0.008333025500178337, -0.0001980741071747616, 2.601886990305502e-06)
PI = 3.141592502593994
TIME_SCALE = 0x71F410              # 1.0; the games scale frame counts with it             [RC2 0x1328c4c]
FRAMES = 0x5E7E18                  # (r3 frames) -> frames at the current time scale       [RC2 0x11bcd28]
COUNT_DOWN = 0x4FFF60              # (r3 int*)                                             [RC2 0x10d4ce0]
INT_TO_FLOAT = 0x502730            # (r3) -> f1                                            [RC2 0x10d74c0]
WRAP_ANGLE = 0x502648              # (f1) -> f1 in -pi..pi                                 [RC2 0x10d73d8]
QUAT_TO_MATRIX = 0x501AB0          # (r3 quaternion, r4 out)                               [RC2 0x10d6840]
MATRIX_MULTIPLY = 0x5014D4         # (r3 out, r4 a, r5 b)                                  [RC2 0x10d6264]

# Bolts. A crate that breaks calls CRATE_BREAK_FX (debris, sound) and then 0x3a4da0, which drops
# its contents; bolts come from 0xfd8d0, which works out a flags word and calls SPAWN_BOLTS at
# BOLTS_HOOK. Flag 2 makes 0x242738 hand every new bolt to 0x240f38, the function the bolt update
# uses when a bolt comes into reach: the bolt goes into its fly-to-Ratchet state. The game sets
# the flag itself, e.g. when it is short of mobys. The strike hook stamps the frame of the Box
# Breaker sweep; a crate that breaks within BOX_WINDOW frames of it (RC2 keeps its Box Breaker
# running for frames(35), hero +0x224) is remembered at CRATE_BREAK_HOOKS (r3 = the crate), and
# its bolts get the flag.
CRATE_BREAK_HOOKS = (0x3A6F58, 0x3A7820, 0x3A7FE0)   # all three bl CRATE_BREAK_FX sites
CRATE_BREAK_FX = 0x3A5468
BOLTS_HOOK = 0xFDCC8               # bl SPAWN_BOLTS
SPAWN_BOLTS = 0xFCD60              # (r3 source moby, r4/r5 value range, r6 flags, r7)
BOLT_FLY = 2
BOX_WINDOW = 35
FRAME_COUNTER = 0xA10710           # [RC2 0x156b070]

# More game functions used by the Charge Boots port
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

# Hook sites: address -> expected original word
STRIKE_HOOK = 0xB01F4              # bl COLLECT in the state 0x14 landing code
FRAME_HOOKS = (0x8C3FC, 0x955A0)   # both bl HERO_MAIN sites (in 0x8c3d0 and 0x954c8)
UPDATE_HOOK = 0x8B93C              # bl HERO_UPDATE in HERO_MAIN
# The transition function 0xbe228 [RC2 0x84adb0] runs checks common to all states, then switches
# on the state at TRANS_HOOK (r19 = hero) and leaves through TRANS_EXIT.
CHOOSER_HOOK = 0xBE2FC             # bl CHOOSER
TRANS_HOOK = 0xBE71C               # lwz r3, 0x2084(r19)
TRANS_HOOK_WORD = 0x80732084
TRANS_EXIT = 0xC81A8
SURFACE_HOOKS = (0x8C400, 0x955A4)  # both bl SURFACE sites, right after the bl HERO_MAIN ones
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

# Strafing (see the docstring). Hook sites in RC1, each with the RC2 address it corresponds to.
STRAFE_LAST_STATE = 0x15           # on foot: idle, walk, skid, crouch, the jump states, the wrench
JOINTS = 0x721BD0                  # joint controllers, 0xb0 bytes each: +0x68 angle, +0xa4/+0xa8 rates [RC2 0x13188a0]
WALK_QUICK_HOOK = 0xB16C4          # lis r27, 0x72: in front of the quick-turn flags      [RC2 0x83ef38]
WALK_QUICK_HOOK_WORD = 0x3F600072
WALK_QUICK_SKIP = 0xB1734
WALK_TURN_HOOK = 0xB1804           # lfs f29, 0x14(r26): in front of the turn             [RC2 0x83f1f0]
WALK_TURN_HOOK_WORD = 0xC3BA0014
WALK_TURN_DONE = 0xB1990
WALK_VEL_HOOK = 0xB1A48            # lhz r3, 0x3b8(r25): in front of the velocity         [RC2 0x83f4c0]
WALK_VEL_HOOK_WORD = 0xA07903B8
WALK_VEL_DONE = 0xB1A7C
IDLE_ALIGN_HOOK = 0xBF464          # lfs f1, 0x30(r25): idle -> walk by the stick         [RC2 0x84bd80]
IDLE_ALIGN_HOOK_WORD = 0xC0390030
IDLE_ALIGN_BACK = 0xBF468
IDLE_TO_WALK = 0xBF47C
WALK_ALIGN_HOOK = 0xC0974          # lfs f1, 0x80(r25): walk -> idle by the stick         [RC2 0x84d770]
WALK_ALIGN_HOOK_WORD = 0xC0390080
WALK_ALIGN_BACK = 0xC0978
WALK_STAYS = 0xC0B50
WALK_TO_IDLE = 0xC0AB8             # the walk block's own way to idle, behind its wait     [RC2 0x84d7e0]
STRAFE_STOP_SPEED = 1.5            # units/s kept when the stick is let go                 (RC2 table 0x84ac7c +0x4c)
FLIP_TYPE_HOOK = 0xA1D9C           # bl STICK_TARGET in the flip type function 0xa1d70    [RC2 0x833698]
FLIP_TYPE_EXIT = 0xA1E3C           # r3 = type
FLIP_TIME_HOOK = 0xA1ECC           # bl STICK_TARGET in 0xa1e78                           [RC2 0x83386c]
FLIP_TIME_TAIL = 0xA1F68           # r31 = type
JUMP_CHOICE_HOOK = 0xA49F0         # cmpwi r31, 0 in the jump chooser 0xa4950             [RC2 0x835e64]
JUMP_CHOICE_HOOK_WORD = 0x2C1F0000
JUMP_CHOICE_FLIP = 0xA49D8         # set_state(0xb, 1), return 1
LEAN_HOOK = 0x9F31C                # lwz r3, 0x2084(r31) at the top of the lean function  [RC2 0x830a5c]
LEAN_HOOK_WORD = 0x807F2084
LEAN_EXIT = 0x9FBA8
WALK_ANIM_HOOK = 0xA4AEC           # lis r4, 0xa in the walk animation chooser 0xa4a60    [RC2 0x836018]
WALK_ANIM_HOOK_WORD = 0x3C80000A
WALK_ANIM_RATE = 0xA4D48
WALK_ANIM_EXIT = 0xA4E08
FLIP_HEADING_HOOK = 0xBB84C        # lfs f1, 0x180(r27) in set_state's flip entry         [RC2 0x8487e0]
FLIP_HEADING_HOOK_WORD = 0xC03B0180
FLIP_SPEED_HOOK = 0xBB888          # stfs f27, 0x458(r27)                                 [RC2 0x848814]
FLIP_SPEED_HOOK_WORD = 0xD37B0458
FLIP_AIR_HOOK = 0x9E5C0            # lhz r4, 0x41e(r31) in the air function 0x9de38       [RC2 0x82f91c]
FLIP_AIR_HOOK_WORD = 0xA09F041E
FLIP_AIR_DONE = 0x9E658
AIR_TURN_HOOK = 0x9EC5C            # lis r3, 0xa: in front of the default air turn        [RC2 0x83007c]
AIR_TURN_HOOK_WORD = 0x3C60000A
AIR_TURNED_HOOK = 0x9ECBC          # stfs f1, 0x188(r31): behind it                       [RC2 0x830120]
AIR_TURNED_HOOK_WORD = 0xD03F0188
JUMP_VEL_HOOK = 0xB465C            # lfs f1, 0x128(r26) in the jump handler               [RC2 0x8429e4]
JUMP_VEL_HOOK_WORD = 0xC03A0128
APPROACH_ANGLE = 0x10A050          # (r3 angle*, f1 target, f2, f3, f4, r5 velocity*, r9 = 0) [RC2 0xb68d98]
ANGLE_DIFF = 0x5025E0              # (f1, f2) -> f1 - f2 wrapped                          [RC2 0x10d7370]
ANGLE_GAP = 0x5026A0               # (f1, f2) -> |f1 - f2| wrapped                        [RC2 0x10d7430]
# RC2's numbers. Turn (table 0x82c220): reversal factors -0.25 and (4 - frames) * 0.25 over 5
# frames, approach-angle arguments 0.037, 0.25 and 12.2173 rad/s. Alignment thresholds
# (transition table 0x84ac7c +0x18, +0x48). Body twist rates (0x8308f8). Backwards walk
# (0x835f70): blend 11.5 frames, rate = speed * 25 within 0.7..2.2, 7.5 frames back to the gait
# animation. Flip (0x844784 +0x194, 0x82f2c0 +0x3c/+0x48/+0x4c): starts at 5 units/s, then
# towards max(5 * stick, 2) units/s at 37 units/s^2.
STRAFE_REVERSE = -0.25
STRAFE_REVERSE_FRAMES = 5
STRAFE_TURN = (0.037, 0.25, 12.217304229736328 / 60)
STRAFE_ALIGN_IDLE = 0.1745329201221466
STRAFE_ALIGN_WALK = 0.03490658476948738
STRAFE_TWIST = (0.037, 0.27, 0.025)
STRAFE_TWIST_STICK = 0.15
STRAFE_BACK_BLEND, STRAFE_GAIT_BLEND = 11.0, 7.0
# The backwards walk is Ratchet animation 0x14 in RC2 (30 frames). All other ids up to 133 have
# the frame counts of RC1's, but RC1's 0x14 is the 14-frame skid its walk -> skid transition
# sets (0xc0a54). RC2's is embedded behind the charge animation and gets the next free slot.
RC2_BACK_ANIM = 0x14
BACK_SLOT = 135
# Ground acceleration. The hero table (r26 = 0xaaafc in hero_update) has 7.5 at +0x2a8 and 8.5 at
# +0x298, units/s^2 for speeding up and slowing down; six handlers read the pair (walk at
# 0xb199c). RC2's table has 18 and 20 for the same reads (+0x1fc, +0x200; walk at 0x83f3ac) and
# kept the 8.5 at +0x204 for one more read, a speed threshold (RC2 0x83e888, RC1 0xb0f3c).
HERO_TABLE = 0xAAAFC
GROUND_ACCEL = (0x2A8, 7.5, 18.0)       # offset, RC1, RC2
GROUND_DECEL = (0x298, 8.5, 20.0)
SPEED_THRESHOLD_HOOK = 0xB0F3C     # lfs f1, 0x298(r26)
SPEED_THRESHOLD_HOOK_WORD = 0xC03A0298
# Speed while turning, in the walk handler (RC1 0xb1630, r25 = hero, r26 = table; RC2 0x83ee6c).
# "Turn" is the angle left to the stick's heading (hero +0x188, RC2 +0x1a8), "stick" its
# deflection (+0x229c, RC2 +0x24b8); the quick-turn flag is the u16 at +0x3be (RC2 byte +0x40f).
#   * The factor on the acceleration (f31, 1 by default). RC1 0xb1898: with +0x20a8 set it is
#     1 - 0.55 * turn, otherwise 0 when the stick is under 0.8 and the turn over 30 degrees.
#     RC2 0x83f2d8: 0 when the turn is over 45 degrees, unless the stick is at 0.9 or more and
#     either +0x22ba [RC1 +0x20aa] is clear or the quick-turn flag is set. WALK_FACTOR_HOOK is the
#     first instruction of RC1's block and WALK_FACTOR_DONE the first one behind it.
#   * RC2 0x83f33c, not in RC1: during a quick turn the target speed is at most
#     5.95 - 5.5 * turn / pi units/s. WALK_CAP_HOOK is the instruction behind the lean calls.
#   * RC2 0x83f400, not in RC1: with the stick under 0.75 and the turn over 35 degrees the target
#     speed is multiplied by 1 - 0.4 * turn. WALK_SLOW_HOOK is where the target speed is loaded
#     for the approach.
# The rest of that code is the same in both games (quick turn: target times 2.618 - turn within
# 0.2..1, slowing at 17 units/s^2).
WALK_FACTOR_HOOK = 0xB1898         # lbz r3, 0x20a8(r25)
WALK_FACTOR_HOOK_WORD = 0x887920A8
WALK_FACTOR_DONE = 0xB18F0         # expects f1 = stick
WALK_FACTOR_STICK, WALK_FACTOR_TURN = 0.8999999761581421, 0.7853981852531433
WALK_CAP_HOOK = 0xB1998            # lis r28, 0x72
WALK_CAP_HOOK_WORD = 0x3F800072
WALK_CAP_SPEED, WALK_CAP_PER_TURN = 5.95, 5.5 * 0.31830987334251404    # (RC2 table +0x220, +0x40 times +0x224)
WALK_SLOW_HOOK = 0xB1A08           # lfs f3, 0x190(r25)
WALK_SLOW_HOOK_WORD = 0xC0790190
WALK_SLOW_STICK, WALK_SLOW_TURN, WALK_SLOW_RATE = 0.75, 0.6108652353286743, 0.4   # (0x83f404, 0x83f430, table +0x70)
STRAFE_BACK_RATE = (25.0, 0.7, 2.2)
STRAFE_FLIP_STICK = 0.9            # jump -> flip above this stick deflection             (RC2 0x835e7c)
STRAFE_FLIP_AIM_STICK = 0.3        # the flip follows the strafe heading above this       (RC2 0x848838)
STRAFE_FLIP_SPEED = (5.0 / 60, 2.0 / 60, 37.0 / 3600)

# Clank's dash. Hero +0x20a4 is the character: 0 Ratchet, 1 Clank (set by 0x86b60, which hands the
# hero to a level moby), 2 Giant Clank. Traced on level 6: idle 0x43, walk 0x44 (3.0 units/s),
# fall 0x45, jump 0x49 (about 1 unit high), punch 0x51; R1 does nothing for him.
HERO_CLANK = 1
STATE_CLANK_IDLE, STATE_CLANK_WALK = 0x43, 0x44
CLANK_BUTTON, CLANK_JUMP_BUTTON = 0x8, 0x40     # R1 held, X pressed
CLANK_DASH_STICK = 0.5         # stick deflection that counts as moving
# Ratchet's Thruster-Pack long jump: set_state's entry for state 0x10 (0xbb17c, table 0xb70d0)
# fills the jump parameters the air code works from. 0x9d6b0 launches him with the vertical
# speed sqrt(2 * height * gravity) (height hero +0x430, gravity +0x4a0) and takes the gravity
# off every frame; the handler (0xb4674) moves the ground speed to the target +0x3f4 by +0x480
# when speeding up. Not copied: the 5 frames he waits before the launch (+0x420) and the extra
# height while X is held (+0x48c).
THRUST_SPEED = 11.5            # units/s    (table +0x180 -> hero +0x3f4)
THRUST_HEIGHT = 0.4            # units      (+0x1c -> +0x430)
THRUST_GRAVITY = 8.5           # units/s^2  (+0x188 -> +0x4a0)
THRUST_ACCEL = 44.0            # units/s^2  (+0x18c -> +0x480)
CLANK_RUN_SPEED = 3.0          # units/s, traced
THRUST_DELAY = 5               # frames before the launch (hero +0x420 = frames(5))
# The long jump's crate sweep (handler, 0xb4a64): from frame 9 on while the animation's frame is
# under 28, crates within THRUST_SWEEP_RADIUS of the point 0.8 ahead of and 0.3 above Ratchet
# (0x84180 with his matrix) take the same wrench damage the cave's crate_sweep deals. Clank's
# matrix is pitched meanwhile, so here the point is built from his position and yaw.
THRUST_SWEEP_FROM = 8
THRUST_SWEEP_AHEAD, THRUST_SWEEP_UP, THRUST_SWEEP_RADIUS = 0.8, 0.3, 0.9      # hero table +0x248, +0x14c, +0x20c
COS, SIN = 0x5E8078, 0x5E8128  # (f1 angle) -> f1; the jump handler builds a heading from them (0xb4570)
# The camera: its code reads the hero's state type (+0x208c, 10 functions) and +0x2284 (13), not
# the state. set_state's jump group (0xba7fc) sets them to 4 and 0x50 for every jump; the dash
# leaves Clank in his idle or walk state, so it sets the two itself, and the set_state that
# ends it puts back his own.
STATE_TYPE_JUMP, CAMERA_JUMP = 4, 0x50
# Running into a wall: Ratchet's long jump goes to the bump state 0x7a when the wall flag is set
# and he moved less than half his velocity (0xc4400). That state throws him back at 9 units/s,
# slowing at 24 units/s^2 (see STATE_BUMP). Using the state itself for Clank went wrong in game
# (2026-10-06): the test with hero +0x100 let him press on the wall for 19 to 25 frames, sunk to
# 0.3 above the floor, before it fired, and from there he hung through the bump and seconds of
# his fall state. So the bump is done here, inside the dash: it starts on the first frame after
# the delay in which the wall flag is set and he covered less than half his speed (measured from
# his position), throws him back with the game's two numbers under a gravity of its own, levels
# him, and plays the animation his hurt state 0x46 sets (set_state 0xbd0e8: hero_set_anim(6, 3,
# -3.0), 22 frames). It lasts at least those 22 frames and until he is on the ground.
THRUST_BUMP_RATIO = 0.5
BUMP_SPEED, BUMP_DECEL = 9.0, 24.0             # (set_state table 0xb70d0 +0x1dc; handler 0xb0c58)
CLANK_BUMP_GRAVITY = 30.0      # units/s^2, not from the game
CLANK_BUMP_FRAMES, CLANK_BUMP_MAX_FRAMES = 22, 60
CLANK_BUMP_ANIM, CLANK_BUMP_ANIM_FLAGS = 6, 3
CLANK_BUMP_ANIM_BLEND = -3.0   # (set_state table 0xb70d0 +0x40)
# Not in the game: the same bump when he flies into the camera, asked for by the user. Taken
# to mean its position (camera struct +0x140): within this distance on the ground plane and
# moving towards it.
# Traced: the camera starts 2.5 to 4 units from him and backs off as he comes, so he never gets
# nearer than about 0.95; a first threshold of 1.0 fired once in six dashes at it. At Ratchet's
# speed it keeps 2.2 to 2.3 away and 1.6 fired once as well.
CLANK_CAMERA_BUMP = 2.4
CLANK_BUMP_ANIM, CLANK_BUMP_ANIM_FLAGS = 6, 3
CLANK_BUMP_ANIM_BLEND = -3.0   # (set_state table 0xb70d0 +0x40)
# Earlier versions ran at 0.55 of Ratchet's lengths (his run speed over Ratchet's), then at 1.2
# times that speed with a longer time in the air; on 2026-10-06 the user asked for Ratchet's own
# parameters.
# The Thruster-Pack's sound: the air code plays Ratchet's model sound 1 at one frame of a jump
# when the Thruster-Pack is worn (0x9e4f4, 0x9d7e8). Here it is played from Ratchet's model's
# definitions on Clank's moby when the dash starts.
THRUSTER_SOUND = 1
# The pose. The Thruster-Pack on Ratchet is two mobys (0x921c0): the Clank on his back, class
# 0x259 at hero +0x1184, and the device, class 0x260 at hero +0x1180, created with
# SPAWN(class), moby +0x31 = 1, +0x32 = 0x20 and the hero moby's 8 bytes at +0x38. The device has
# 9 animations: 0 one frame (stowed), 1 ten frames, 2 one frame, 3-8 the ones hero_set_anim's
# helper 0x850f8 picks through the table 0x723120 for idle fidgets.
THRUSTER_CLASS = 0x260
CLANK_WINGS_ANIM = 1           # the wings out, as seen in game
# Read in game on Ratchet with the Heli-Pack: the device and the Clank on his back have the same
# position and matrix, so the device is modelled in that Clank's frame. The playable Clank
# (class 0x57) is a larger model with longer legs, and his origin is at his feet. This offset
# (forward, left, up in his axes) was set with the user in a running game, at the device's own
# scale (0.25; smaller ones were tried and dropped). It puts the device's root bone, which is
# 0.174 behind and 0.031 above its origin, on his spine 0.39 above his feet.
CLANK_WINGS_OFFSET = (0.174, 0.0, 0.359)   # confirmed by the user ("looks good now")
MOBY_SET_ANIM = 0xFDDC0        # (r3 moby, r4 animation, r5 = 0, r6 blend frames)
MOBY_DELETE = 0xEFB38          # (r3 moby)
# The Thruster-Pack's jets are two mobys of class 0xa7 that 0x921c0 creates with the device
# through JET_SPAWN(0) and (1). Their update 0x2aa9c0 is a state machine on moby +0x20 (1 off,
# 2 lighting, 3 on, 4 going out) that deletes the moby when Ratchet's backpack is not the
# Thruster-Pack and lights it by Ratchet's state, so it is no use for Clank; with +0x20 = 5 it
# does nothing. What it does every frame while on is done here instead: variables +8 = the
# device, DRAW_REGISTER(JET_DRAW, jet) (the flame, drawn at the device's joints; it insists on
# class 0x260), +0x20 = 0.0125 and JET_EMIT(jet) (the particles). Variables +4 is 0 or 1 for
# the side, +0x20..+0x2c the four values the lit state starts with.
JET_SPAWN = 0x2AA928           # (r3 side) -> moby
JET_EMIT = 0x2A9F18            # (r3 jet)
JET_DRAW = 0x70AD18            # function descriptor of the flame's draw callback 0x2a94c8
DRAW_REGISTER = 0x6D7E0        # (r3 function descriptor, r4 moby): draw callback for this frame
JET_OFF_STATE = 5
JET_VALUES = (0.0125, 0.2, 0.05, 0.025)    # variables +0x20, +0x24, +0x28, +0x2c (0x2aad68)
MOBY_MOVED = 0xF31A8           # (r3 moby): bounding sphere and the like from its position; 363 callers
STATE_CLANK_FALL = 0x45
CLANK_DASH_ANIM = 4            # the animation traced in his fall state
CLANK_DASH_ANIM_BLEND = 6.0
CLANK_PITCH = 3.141592502593994 / 2
CLANK_PITCH_FRAMES = 6
CLANK_DASH_MIN_FRAMES = THRUST_DELAY + 8   # the landing test starts after this many frames
CLANK_DASH_MAX_FRAMES = 150    # past this the dash is over wherever he is, and the game lets him fall
# Landing. Traced on 2026-10-07: coming down, he stops 0.30 above the ground (hero +0x2d8) with
# the wall flag set and the frames-off-the-ground counter +0x30e still running, and is held there
# for as long as the dash stands in for his own state code; every dash ended in the wall bump
# there, and the bump then hung at that height until its last frame. So the dash and the bump
# land him themselves: going down within this height of a ground the probe found (its distance
# +0x2dc is 32 without one), he is put on the ground and into his idle state.
# Second trace the same day (102 dashes): 85 landed so, 17 did not: on the frame of the landing,
# still pitched, he was back at 0.28 with the wall flag set, the idle state became his fall state
# 0x45, and that hung there for 2.7 s and more (once 38 s). The bump, which levels him first,
# comes down to the ground without that. So the pitch is what makes the floor a wall for him
# (taken to be the wall probes turning with him), and the landing levels him at once.
CLANK_LAND_HEIGHT = 0.34
CLANK_LAND_NO_GROUND = 31.0
# Third trace: with the pitch set level on the landing frame all three dashes still ended 0.28 up
# in the fall state, and the height there was just one more frame of his descent, so writing his
# z does nothing either. What does come down is the bump (to -0.14 against the ground reading,
# level, on the dash's own gravity). So a landing is a phase of the dash now: for up to this many
# frames it levels him and takes him down as the bump does, moving on at his run speed, and hands
# over to his idle state once the frames-off-the-ground counter is 0.
CLANK_SETTLE_FRAMES = 20
# Fourth trace: that phase did not free him either. Two of three dashes met the floor at 0.30
# while still pitched (wall flag on the first frame of the phase) and stayed there, level, for
# all 20 frames and then in his own states (18 s in the fall state, 1.5 s in the walk state);
# the third, over ground falling away, never met it and came down to 0.00 in 7 frames. So the
# contact made while pitched is what holds him, whatever he does afterwards, and the dash now
# keeps him from making it: from the top of the arc (vertical speed below 0) the pitch goes back
# to level, six frames in which he is still 0.37 or more up, and he lands level, on the dash's own
# speed and gravity as Ratchet's long jump does, when he is within CLANK_TOUCH_HEIGHT of the ground.
CLANK_TOUCH_HEIGHT = 0.05
# The cause, read from a stuck Clank on 2026-10-07 (contact point straight under him on the
# ground, hero +0x224 = 0.02 where it is 0.45 when he stands): the hero's collision sphere sits
# +0x224 above his feet (radius +0x234 = 0.30 for Clank), and 0x84978, called every frame from
# hero_main, moves +0x224 towards +0x22c. It sets +0x22c per character (Clank 0.45), but in
# state type 4, a jump, past the launch delay, it takes hero +0x434 instead, a jump parameter
# that Ratchet's set_state fills and that is 0 for a Clank who has not jumped. The dash sets
# state type 4 for the camera, so his sphere sank to his feet and rested on the floor with him
# 0.30 up. The same function leaves +0x224 alone while the sphere touches something under him,
# which is why he stayed there through his own states until a jump. The dash now writes his own
# height to +0x434 and +0x224 on every frame.
CLANK_SPHERE_HEIGHT = 0x3EE66667   # 0.45, the word 0x84978 stores to +0x22c for hero type 1
# Fifth trace and the user's word on it (2026-10-07): levelling early "looks worse" and one dash
# of 33 still stuck, level, so none of the three readings above (pitch on the landing frame, a
# landing phase, the contact made while pitched) is the cause. Back to the first landing: pitched
# all the way down, landed by clank_grounded at CLANK_LAND_HEIGHT, the pitch going back over
# CLANK_PITCH_FRAMES afterwards. CLANK_TOUCH_HEIGHT and CLANK_SETTLE_FRAMES are unused.

# Caves sit in the zero padding between the end of the R+X segment (0x6fd5e8) and 0x700000.
CAVE_START = 0x6FD600
SEG_END = 0x700000
# Zero-initialised state appended to the RW segment's bss (old end 0x1606310):
#   +0 R1 last frame, +4 tap window, +8 charge frame counter (0 = off),
#   +0x10 the current skid ended a charge, +0x14 smoothed steering input,
#   +0x28 a bolt crank is being boosted,
#   +0x18 sound bank handle (0 = not loaded, -1 = failed), +0x1c loop voice slot + 1,
#   +0x20 play the end sound when the loop stops, +0x24 hover velocity,
#   +0x2c address of the installed Charge Boots model (0 = not installed),
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
STATE = 0x1606320
STATE_END = 0x1606400

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
ANIM_VADDR = 0x1610000
ANIM_PHDR = 2

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
SOUND_BANK_LEVEL = 5
SOUND_DEFS = (bytes.fromhex("00000000000000000000000000000000000000000000000000000000" "00000000"),   # loop -> sound 24
              bytes.fromhex("00000000000000000000000000000000000000000000000000000000" "00000000"))   # end -> sound 20
SOUND_LOOP_FLAGS = 4
SOUND_VADDR = 0x1620000
SOUND_PHDR = 3
SOUND_BANK_OFF = 0x40          # bank offset inside the segment; must be 16-byte aligned
BANK_LOAD_FROM_MEM = 0x60AE8C  # (r3 bank image) -> handle, 0 on failure
PLAY_SOUND_DEF = 0x15CE18      # (r3 definition, r4 flags, r5 moby, r6 = 0, r7 = 0x400) -> voice slot or -1
STOP_VOICE = 0x15CDB0          # (r3 voice slot)
# Voice table: 0x70 bytes per voice; +0x74 state (0 = free, 7 = queued), +0x78 definition,
# +0x88 moby to follow (set by RC1's play-model-sound 0x15d12c after PLAY_SOUND_DEF).
# RC2 0x82e9f4 starts the loop again whenever its voice has ended or been taken over.
VOICES = 0x963760

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
CLASS_SLOT_MAP = 0xA354C0     # byte per class id -> model slot
MODEL_TABLE = 0xA34C00        # model pointer per slot
MODEL_FIXUP = 0xDBC38         # (r3 model, r6 class)
COPY = 0x50027C               # (r3 dst, r4 src, r5 size)
MAIN_HEAP, GRAPHICS_HEAP = 0x90D7C8, 0x90D7EC   # +8 and +0xc: end of the heap
GCM_PTR = 0x8FA564            # -> struct with +0x4ac graphics memory base
LEVEL = 0xA15F4C              # +0x1c texture table of the loaded level
BOOTS_RESERVE = 0x20000
BOOTS_VADDR = 0x1630000       # embedded: model, texture entry, pixels
BOOTS_PHDR = 4
BOOTS_FILES = ("rc2_e70_model.bin", "rc2_e70_texentry.bin", "rc2_e70_texture.bin")
ITEM_MAGNEBOOTS = 0x1C
STATE_TYPE_GRIND = 0xF        # hero +0x208c
FOOT_REMEMBERED = 0x969C80    # the item the foot slot is meant to hold (0x969c7c + 4 * slot)
MODEL_SLOTS = 0xE0
CHARGE_CLASS = 0x7C0          # unused by all 19 levels (highest class id there: 0x7b5)
SPAWN = 0xEFA28               # (r3 class) -> new moby, 0 when none is free
FOOT_SPAWN_HOOKS = (0x9261C, 0x92678)   # bl SPAWN for the left and the right boot in 0x921c0
ITEM_TABLE = 0x721000         # 0x4c bytes per item: +0 name text id, +8 slot, +0x10/+0x14 classes
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
ICON_SPRITE = 0xCA3E4
ICON_DRAW = 0xCA0F4
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

# crate_sweep(r3 = centre vec4*, f1 = radius): damage every crate in the sphere.
SWEEP = """
crate_sweep:
    stdu 1, -0xb0(1)
    mflr 0
    std 0, 0xc0(1)
    std 31, 0xa8(1)
    std 30, 0xa0(1)
    std 29, 0x98(1)
    std 28, 0x90(1)
    stfs 1, 0x80(1)
    mr 28, 3
    lis 31, {HERO_HA}
    addi 31, 31, {HERO_LO}
    lis 29, {POOL_HA}
    addi 29, 29, {POOL_LO}
    addi 3, 1, 0x70         # hit direction = 7 * hero+0x100, as the game's own crate sweeps do
    addi 4, 31, 0x100
    lfs 1, {P_SEVEN}(29)
    bl {VEC_SCALE}
    mr 3, 28
    lfs 1, 0x80(1)
    li 5, 0
    lwz 6, 0x2080(31)
    li 7, 0
    bl {COLLECT}
    mr 30, 3
    lis 28, {RESULTS_HA}
    addi 28, 28, {RESULTS_LO}
sweep_loop:
    cmpwi 30, 0
    ble sweep_done
    lwz 3, 0(28)
    bl {IS_CRATE}
    cmpwi 3, 0
    beq sweep_next
    lwz 3, 0(28)
{SKIP_EXPLOSIVE}
    lwz 4, 0x2080(31)
    lis 5, 1                # 0x10000: wrench damage
    lfs 1, {P_ONE}(29)
    addi 7, 31, 0x80
    addi 8, 1, 0x70
    bl {DEAL_DAMAGE}
sweep_next:
    addi 28, 28, 4
    addi 30, 30, -1
    b sweep_loop
sweep_done:
    ld 28, 0x90(1)
    ld 29, 0x98(1)
    ld 30, 0xa0(1)
    ld 31, 0xa8(1)
    ld 0, 0xc0(1)
    mtlr 0
    addi 1, 1, 0xb0
    blr
"""

SKIP_EXPLOSIVE = """
    lhz 4, 0xa6(3)
    cmpwi 4, {EXPLOSIVE_CRATE}
    beq sweep_next
"""

# Replaces the hyper-strike's bl COLLECT: original sweep, then the Box Breaker sweep.
STRIKE = """
strike:
    stdu 1, -0x70(1)
    mflr 0
    std 0, 0x80(1)
    bl {COLLECT}            # arguments untouched
    lis 3, {HERO_HA}
    addi 3, 3, {HERO_LO}
    addi 3, 3, 0x80
    lis 4, {POOL_HA}
    addi 4, 4, {POOL_LO}
    lfs 1, {P_BOX_RADIUS}(4)
    bl crate_sweep
    lis 3, {FRAME_HA}               # the frame of the sweep, for the bolts
    lwz 3, {FRAME_LO}(3)
    lis 4, {STATE_HA}
    addi 4, 4, {STATE_LO}
    stw 3, 0x30(4)
    ld 0, 0x80(1)
    mtlr 0
    addi 1, 1, 0x70
    blr
"""

# strike_fx: replaces lwz r3, 0x198(r25) behind the hyper-strike's sweep (r25 = hero).
# shake: replaces bl SHAKE_CHANNEL for channel 1 in the camera update, then runs RC2's channel 2.
# crate_break: replaces bl CRATE_BREAK_FX (r3 = the crate).
# bolts: replaces bl SPAWN_BOLTS (r3 = source moby, r6 = flags).
BOX = """
strike_fx:
    lis 11, {POOL_HA}
    addi 11, 11, {POOL_LO}
    lfs 0, 0xaa8(25)                # has the animation just passed the frame of the hit?
    lfs 13, {P_STRIKE_FRAME}(11)
    fcmpu 0, 0, 13
    ble sfx_out
    fsubs 0, 0, 13
    lfs 13, 0xaac(25)
    fcmpu 0, 0, 13
    bgt sfx_out
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lfs 0, {P_SHAKE}(11)
    lis 12, {STATE_HA}
    addi 12, 12, {STATE_LO}
    stfs 0, 0x40(12)
    li 3, {SHAKE_FRAMES}
    bl {FRAMES}
    lis 12, {STATE_HA}
    addi 12, 12, {STATE_LO}
    stw 3, 0x48(12)
    lis 12, {CAMERA_STATE_HA}
    addi 12, 12, {CAMERA_STATE_LO}
    li 3, 0
    stw 3, 0x16c(12)                # RC2 zeroes channel 0's length here
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
sfx_out:
    lwz 3, 0x198(25)                # the displaced instruction
    blr

shake:
    stdu 1, -0x100(1)
    mflr 0
    std 0, 0x110(1)
    std 31, 0xf8(1)
    std 30, 0xf0(1)
    std 29, 0xe8(1)
    stfd 31, 0xe0(1)
    stfd 30, 0xd8(1)
    bl {SHAKE_CHANNEL}              # arguments untouched
    lis 30, {STATE_HA}
    addi 30, 30, {STATE_LO}
    addi 30, 30, 0x40               # r30 = the channel
    lis 29, {CAMERA_STATE_HA}
    addi 29, 29, {CAMERA_STATE_LO}
    lis 31, {POOL_HA}
    addi 31, 31, {POOL_LO}
    lwz 3, 0x180(29)                # camera type 6 cancels a shake
    cmpwi 3, 0
    beq shake_run
    lhz 3, 0x86(3)
    cmpwi 3, 6
    bne shake_run
    li 3, 0
    stw 3, 8(30)
    stw 3, 0xc(30)
    b shake_out
shake_run:
    lwz 3, 8(30)
    cmpwi 3, 0
    bne shake_on
    stw 3, 0xc(30)
    b shake_out
shake_on:
    lwz 4, 0xc(30)                  # frames in all = the most frames left ever seen
    cmpw 4, 3
    bge shake_length
    mr 4, 3
shake_length:
    stw 4, 0xc(30)
    addi 3, 30, 8
    bl {COUNT_DOWN}
    lwz 3, 8(30)
    bl {INT_TO_FLOAT}
    fmr 31, 1
    lwz 3, 0xc(30)
    bl {INT_TO_FLOAT}
    fdivs 31, 31, 1
    fmuls 1, 31, 31
    fmuls 31, 1, 31                 # f31 = (left / all)^3
    lwz 3, 0xc(30)
    lwz 4, 8(30)
    subf 3, 4, 3
    bl {INT_TO_FLOAT}               # frames since the start
    lis 3, {TIME_SCALE_HA}
    lfs 5, {TIME_SCALE_LO}(3)
    lfs 2, {P_SIXTY}(31)
    fmuls 2, 5, 2
    fdivs 1, 1, 2                   # f1 = t, seconds since the start
    lfs 3, {P_SHAKE_PHASE}(31)
    fmuls 3, 5, 3
    fctidz 3, 3
    fcfid 3, 3
    frsp 3, 3
    lfs 6, {P_SHAKE_FREQ}(31)
    fmuls 3, 3, 6
    lfs 2, {P_SHAKE_RAMP}(31)
    fmuls 2, 1, 2
    fmsubs 1, 6, 1, 3               # angle = freq * (t - 10)
    lfs 4, {P_ONE}(31)
    fsub 3, 4, 2
    fsel 30, 3, 2, 4                # f30 = min(6 t, 1)
    bl {WRAP_ANGLE}
    lfs 4, {P_PI}(31)               # sine: fold into -pi/2..pi/2, then the series
    fsubs 2, 4, 1
    fneg 4, 4
    fsubs 3, 4, 1
    fsub 5, 1, 2
    fsel 1, 5, 2, 1
    fsub 2, 3, 1
    fsel 1, 2, 3, 1
    fmuls 3, 1, 1
    fmuls 4, 3, 1
    fmuls 5, 3, 4
    lfs 6, {P_SIN3}(31)
    fmadds 1, 4, 6, 1
    fmuls 4, 3, 5
    lfs 6, {P_SIN5}(31)
    fmadds 1, 5, 6, 1
    fmuls 3, 3, 4
    lfs 6, {P_SIN7}(31)
    fmadds 1, 4, 6, 1
    lfs 6, {P_SIN9}(31)
    fmadds 1, 3, 6, 1
    lfs 2, 0(30)
    fmuls 1, 2, 1
    fmuls 1, 1, 31
    fmuls 1, 1, 30
    stfs 1, 4(30)

    addi 4, 29, 0x350               # quaternion about the view axis (RC2 0xb6fc60): axis * value, sqrt(1 - value^2)
    lfs 2, 0(4)
    lfs 3, 4(4)
    lfs 4, 8(4)
    fmuls 5, 3, 3
    fmadds 5, 2, 2, 5
    fmadds 5, 4, 4, 5
    fsqrts 5, 5
    lfs 6, {P_ZERO}(31)
    fmr 7, 6
    fcmpu 0, 5, 6
    beq shake_axis
    fdivs 7, 1, 5
shake_axis:
    fmuls 2, 2, 7
    fmuls 3, 3, 7
    fmuls 4, 4, 7
    stfs 2, 0x70(1)
    stfs 3, 0x74(1)
    stfs 4, 0x78(1)
    lfs 6, {P_ONE}(31)
    fnmsubs 1, 1, 1, 6
    fsqrts 1, 1
    stfs 1, 0x7c(1)
    addi 3, 1, 0x70
    addi 4, 1, 0x80
    bl {QUAT_TO_MATRIX}
    addi 3, 29, 0x350               # camera matrix = roll * camera matrix
    addi 4, 1, 0x80
    mr 5, 3
    bl {MATRIX_MULTIPLY}
shake_out:
    lfd 30, 0xd8(1)
    lfd 31, 0xe0(1)
    ld 29, 0xe8(1)
    ld 30, 0xf0(1)
    ld 31, 0xf8(1)
    ld 0, 0x110(1)
    mtlr 0
    addi 1, 1, 0x100
    blr

crate_break:
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    li 0, 0
    lwz 12, 0x30(11)                # frame of the last Box Breaker sweep
    cmpwi 12, 0
    beq cb_store
    lis 10, {FRAME_HA}
    lwz 10, {FRAME_LO}(10)
    subf 10, 12, 10
    cmplwi 10, {BOX_WINDOW}
    bgt cb_store
    mr 0, 3
cb_store:
    stw 0, 0x34(11)
    b {CRATE_BREAK_FX}

bolts:
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x34(11)
    cmpwi 12, 0
    beq bolts_run
    cmpw 12, 3
    bne bolts_run
    li 12, 0
    stw 12, 0x34(11)
    ori 6, 6, {BOLT_FLY}
bolts_run:
    b {SPAWN_BOLTS}
"""

# Strafing: one routine per hook site, named after what RC2 does there.
STRAFE = """
strafe_frame:                       # replaces bl HERO_MAIN when the Charge Boots are not built
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    bl strafe_tick
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    b {HERO_MAIN}

strafe_tick:                        # the timer [RC2 0x816ac4], direction and backwards flag [RC2 0x82cf70]
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lis 10, {PAD_HA}
    addi 10, 10, {PAD_LO}
    lis 9, {HERO_HA}
    addi 9, 9, {HERO_LO}
    lwz 3, 0xa0(10)
    lwz 12, 0x2084(9)
    lwz 5, 0x50(11)
    andi. 4, 3, 3                   # L2 | R2
    beq st_release
    cmplwi 12, {STRAFE_LAST_STATE}
    bgt st_release
    lbz 6, 0x20b3(9)
    cmpwi 6, 0
    bne st_release
    li 6, -4                        # on foot the two buttons only strafe: hide them from the game
    and 3, 3, 6
    stw 3, 0xa0(10)
    lwz 7, 0xa4(10)
    and 7, 7, 6
    stw 7, 0xa4(10)
    stw 4, 0x54(11)
    cmpwi 5, 1
    bge st_state
    li 5, 1
    b st_state
st_release:
    li 4, 0
    stw 4, 0x54(11)
    cmpwi 5, 0
    ble st_state
    addi 5, 5, -1
st_state:
    cmpwi 12, 0x10
    bne st_timer
    li 5, 0
st_timer:
    stw 5, 0x50(11)
    li 6, 0
    cmpwi 5, 0
    bne st_dir
    stw 6, 0x5c(11)
    lwz 7, 0x70(11)                 # strafing is over: undo the body twist
    cmpwi 7, 0
    beqlr
    stw 6, 0x70(11)
    lis 10, {JOINTS_HA}
    addi 10, 10, {JOINTS_LO}
    stw 6, 0x68(10)
    stw 6, 0x118(10)
    blr
st_dir:
    lis 10, {POOL_HA}
    addi 10, 10, {POOL_LO}
    lfs 1, 0x1d20(9)                # stick x, y: the angle atan2(y, x) falls into one of four quarters
    lfs 2, 0x1d24(9)
    fabs 3, 1
    fabs 4, 2
    lfs 0, {P_ZERO}(10)
    li 7, 1
    fadds 5, 3, 4
    fcmpu 0, 5, 0
    beq st_dir_done
    li 7, 3
    fcmpu 0, 2, 3
    bgt st_dir_done
    li 7, 1
    fcmpu 0, 1, 4
    bgt st_dir_done
    li 7, 0
    fneg 5, 1
    fcmpu 0, 5, 4
    bgt st_dir_done
    li 7, 2
st_dir_done:
    stw 7, 0x58(11)
    cmpwi 7, 3
    bne st_flag
    lfs 5, 0x229c(9)
    lfs 0, {P_TWIST_STICK}(10)
    fcmpu 0, 5, 0
    ble st_flag
    li 6, 1
st_flag:
    stw 6, 0x5c(11)
    blr

strafe_turn:                        # [RC2 0x82c238] face the camera, keep the stick's heading to move along
    stdu 1, -0x80(1)
    mflr 0
    std 0, 0x90(1)
    std 31, 0x78(1)
    std 30, 0x70(1)
    std 29, 0x68(1)
    stfd 31, 0x60(1)
    lis 31, {HERO_HA}
    addi 31, 31, {HERO_LO}
    lis 30, {STATE_HA}
    addi 30, 30, {STATE_LO}
    lis 29, {POOL_HA}
    addi 29, 29, {POOL_LO}
    lfs 1, 0x1d20(31)               # with the stick let go the heading is his own yaw, while the stick's length
    lfs 2, 0x1d24(31)               # +0x229c takes some frames to fall and keeps him walking: keep the last
    fabs 1, 1                       # heading then, or he runs forwards out of a strafe backwards
    fabs 2, 2
    fadds 1, 1, 2
    lfs 0, {P_ZERO}(29)
    fcmpu 0, 1, 0
    beq turn_heading_kept
    lfs 1, 0x180(31)
    stfs 1, 0x60(30)
turn_heading_kept:
    addi 3, 30, 0x68
    bl {COUNT_DOWN}
    addi 3, 30, 0x6c
    bl {COUNT_DOWN}
    lfs 31, {P_ONE}(29)             # f31 = speed factor
    lbz 4, 0x20a4(31)
    cmpwi 4, 0
    bne turn_speed
    lwz 4, 0x58(30)
    cmpwi 4, 0
    bne turn_right
    li 5, {STRAFE_REVERSE_FRAMES}   # left: within 5 frames of going right the speed is reversed and quartered
    stw 5, 0x6c(30)
    lwz 5, 0x68(30)
    cmpwi 5, 0
    beq turn_speed
    lfs 31, {P_REVERSE}(29)
    b turn_speed
turn_right:
    cmpwi 4, 1
    bne turn_speed
    li 5, {STRAFE_REVERSE_FRAMES}   # right: within 5 frames of going left it ramps up from 0
    lwz 3, 0x6c(30)
    stw 5, 0x68(30)
    cmpwi 3, 0
    beq turn_speed
    bl {INT_TO_FLOAT}
    lfs 2, {P_FOUR}(29)
    fsubs 1, 2, 1
    lfs 2, {P_QUARTER}(29)
    fmuls 31, 1, 2
turn_speed:
    lfs 1, 0x194(31)
    fmuls 1, 1, 31
    stfs 1, 0x194(31)
    lis 4, {CAMERA_STATE_HA}
    addi 4, 4, {CAMERA_STATE_LO}
    lfs 1, 0x158(4)                 # the camera's yaw becomes the heading to turn to
    stfs 1, 0x180(31)
    lfs 2, 0x64(30)
    stfs 2, 0x184(31)
    lfs 2, {P_TURN_A}(29)
    lfs 3, {P_QUARTER}(29)
    lfs 4, {P_TURN_C}(29)
    addi 3, 31, 0x98
    addi 5, 31, 0x184
    li 9, 0
    bl {APPROACH_ANGLE}
    li 3, 0
    stw 3, 0x188(31)
    lfs 1, 0x184(31)
    stfs 1, 0x64(30)
    stw 3, 0x184(31)
    lfd 31, 0x60(1)
    ld 29, 0x68(1)
    ld 30, 0x70(1)
    ld 31, 0x78(1)
    ld 0, 0x90(1)
    mtlr 0
    addi 1, 1, 0x80
    blr

strafe_align:                       # [RC2 0x82c184] (f1 angle) -> 1 while the button is held and he is not yet facing the camera
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 3, 0x54(11)
    cmpwi 3, 0
    beqlr
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    stfs 1, 0x70(1)
    lis 4, {HERO_HA}
    addi 4, 4, {HERO_LO}
    lfs 1, 0x98(4)
    lis 4, {CAMERA_STATE_HA}
    addi 4, 4, {CAMERA_STATE_LO}
    lfs 2, 0x158(4)
    bl {ANGLE_GAP}
    lfs 2, 0x70(1)
    li 3, 0
    fcmpu 0, 2, 1
    bgt align_out
    li 3, 1
align_out:
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

walk_quick:                         # replaces lis r27, 0x72: no quick-turn flags while strafing
    lis 27, 0x72
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x50(11)
    cmpwi 12, 0
    beqlr
    b {WALK_QUICK_SKIP}

walk_turn:                          # replaces lfs f29, 0x14(r26)
    lfs 29, 0x14(26)
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x50(11)
    cmpwi 12, 0
    bne walk_turn_strafe
    lfs 0, 0x98(25)                 # not strafing: the heading to move along is his own
    stfs 0, 0x60(11)
    blr
walk_turn_strafe:
    fmr 31, 29
    bl strafe_turn
    b {WALK_TURN_DONE}

walk_vel:                           # replaces lhz r3, 0x3b8(r25)
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x50(11)
    cmpwi 12, 0
    bne walk_vel_strafe
    lhz 3, 0x3b8(25)
    blr
walk_vel_strafe:
    lfs 1, 0x60(11)
    bl {BUILD_VELOCITY}
    b {WALK_VEL_DONE}

idle_align:                         # replaces lfs f1, 0x30(r25)
    lis 11, {POOL_HA}
    addi 11, 11, {POOL_LO}
    lfs 1, {P_ALIGN_IDLE}(11)
    bl strafe_align
    cmpwi 3, 0
    bne idle_align_walk
    lfs 1, 0x30(25)
    b {IDLE_ALIGN_BACK}
idle_align_walk:
    b {IDLE_TO_WALK}

walk_align:                         # replaces lfs f1, 0x80(r25)
    lis 11, {POOL_HA}
    addi 11, 11, {POOL_LO}
    lfs 1, {P_ALIGN_WALK}(11)
    bl strafe_align
    cmpwi 3, 0
    bne walk_align_stay
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x50(11)
    cmpwi 12, 0
    beq walk_align_plain
    lfs 1, 0x80(25)
    lfs 2, 0x229c(19)
    fcmpu 0, 2, 1
    bge walk_align_plain
    lis 11, {POOL_HA}               # strafing and the stick let go: to idle with the speed capped, as RC2's
    addi 11, 11, {POOL_LO}          # walk does [RC2 0x84d7f0]; RC1's own way is the skid state 3
    lfs 1, {P_STOP_SPEED}(11)
    lfs 2, 0x194(19)
    fcmpu 0, 2, 1
    ble walk_align_coast
    fmr 2, 1
walk_align_coast:                   # RC1's idle carries the speed on along his facing, RC2's along the way he
    lfs 0, {P_ZERO}(11)             # went: keep the part of it that he made forwards (+0x168 of +0x164), so
    lfs 3, 0x164(19)                # that a strafe backwards or sideways ends on the spot
    fcmpu 0, 3, 0
    ble walk_align_still
    fcmpu 0, 2, 0
    ble walk_align_still
    lfs 4, 0x168(19)
    fdivs 4, 4, 3
    fmuls 0, 2, 4
walk_align_still:
    stfs 0, 0x194(19)
    b {WALK_TO_IDLE}
walk_align_plain:
    lfs 1, 0x80(25)
    b {WALK_ALIGN_BACK}
walk_align_stay:
    b {WALK_STAYS}

flip_type:                          # replaces bl STICK_TARGET: the flip's type is the strafe direction
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x50(11)
    cmpwi 12, 0
    bne flip_type_strafe
    b {STICK_TARGET}
flip_type_strafe:
    lwz 3, 0x58(11)
    b {FLIP_TYPE_EXIT}

flip_time:                          # the same in the function that also gives the jump buffer time
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x50(11)
    cmpwi 12, 0
    bne flip_time_strafe
    b {STICK_TARGET}
flip_time_strafe:
    lwz 31, 0x58(11)
    b {FLIP_TIME_TAIL}

jump_choice:                        # replaces cmpwi r31, 0: strafing with the stick pushed anywhere but forward flips
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x50(11)
    cmpwi 12, 0
    beq jump_choice_plain
    lwz 12, 0x58(11)
    cmpwi 12, 2
    beq jump_choice_plain
    lis 11, {HERO_HA}
    addi 11, 11, {HERO_LO}
    lfs 0, 0x229c(11)
    lis 11, {POOL_HA}
    addi 11, 11, {POOL_LO}
    lfs 13, {P_FLIP_STICK}(11)
    fcmpu 0, 0, 13
    ble jump_choice_plain
    b {JUMP_CHOICE_FLIP}
jump_choice_plain:
    cmpwi 31, 0
    blr

lean:                               # replaces lwz r3, 0x2084(r31): the body twist of a sideways strafe
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lis 10, {JOINTS_HA}
    addi 10, 10, {JOINTS_LO}
    lis 9, {POOL_HA}
    addi 9, 9, {POOL_LO}
    lwz 12, 0x50(11)
    cmpwi 12, 0
    beq lean_off
    lfs 0, 0x229c(31)
    lfs 13, {P_TWIST_STICK}(9)
    fcmpu 0, 0, 13
    ble lean_off
    lwz 12, 0x2084(31)
    cmpwi 12, 0xb
    beq lean_off
    lwz 12, 0x5c(11)
    cmpwi 12, 0
    bne lean_off
    li 12, 1
    stw 12, 0x70(11)
    lfs 0, {P_TWIST_A}(9)
    stfs 0, 0xa4(10)
    lfs 0, {P_TWIST_B}(9)
    stfs 0, 0xa8(10)
    stfs 0, 0x158(10)
    lfs 0, {P_TWIST_C}(9)
    stfs 0, 0x154(10)
    std 30, 0x98(1)                 # the function has not saved r30 yet; its exit restores it
    mr 30, 10
    lfs 1, 0x60(11)
    lfs 2, 0x98(31)
    bl {ANGLE_DIFF}
    stfs 1, 0x68(30)
    fneg 1, 1
    stfs 1, 0x118(30)
    b {LEAN_EXIT}
lean_off:
    lwz 12, 0x70(11)
    cmpwi 12, 0
    beq lean_plain
    li 12, 0
    stw 12, 0x70(11)
    stw 12, 0x68(10)
    stw 12, 0x118(10)
lean_plain:
    lwz 3, 0x2084(31)
    blr

walk_anim:                          # replaces lis r4, 0xa: the backwards walk
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lis 10, {POOL_HA}
    addi 10, 10, {POOL_LO}
    lwz 12, 0x50(11)
    cmpwi 12, 0
    beq walk_anim_off
    lwz 12, 0x5c(11)
    cmpwi 12, 0
    beq walk_anim_off
    li 12, 1
    stw 12, 0x74(11)
    lwz 3, 0x2080(31)
    lwz 4, 0x24(3)                  # RC2's animation in its slot of the model's table
    lis 5, {BACK_ANIM_HA}
    addi 5, 5, {BACK_ANIM_LO}
    stw 5, {BACK_TABLE_OFF}(4)
    lbz 3, 0x53(3)
    cmpwi 3, {BACK_SLOT}
    beq walk_anim_rate
    li 3, {BACK_SLOT}
    li 4, 0
    lfs 1, {P_BACK_BLEND}(10)
    bl {HERO_SET_ANIM}
walk_anim_rate:
    lis 10, {POOL_HA}
    addi 10, 10, {POOL_LO}
    lfs 1, 0x194(31)
    lfs 2, {P_BACK_RATE}(10)
    fmuls 1, 1, 2
    lfs 2, {P_BACK_MIN}(10)
    fcmpu 0, 1, 2
    bge walk_anim_min
    fmr 1, 2
walk_anim_min:
    lfs 2, {P_BACK_MAX}(10)
    fcmpu 0, 1, 2
    ble walk_anim_max
    fmr 1, 2
walk_anim_max:
    stfs 1, 0xa90(31)
    b {WALK_ANIM_EXIT}
walk_anim_off:
    lwz 12, 0x74(11)
    cmpwi 12, 0
    beq walk_anim_plain
    li 12, 0
    stw 12, 0x74(11)
    lwz 3, 0x2088(31)               # back to the animation of the current gait
    addi 3, 3, 3
    li 4, 0
    lfs 1, {P_GAIT_BLEND}(10)
    bl {HERO_SET_ANIM}
    b {WALK_ANIM_RATE}
walk_anim_plain:
    lis 4, 0xa
    blr

flip_heading:                       # replaces lfs f1, 0x180(r27): a strafe flip goes along the strafe heading
    lfs 1, 0x180(27)
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    li 12, 0
    stw 12, 0x78(11)
    lwz 12, 0x50(11)
    cmpwi 12, 0
    beqlr
    lis 12, {POOL_HA}
    addi 12, 12, {POOL_LO}
    lfs 0, 0x229c(27)
    lfs 13, {P_FLIP_AIM}(12)
    fcmpu 0, 0, 13
    blelr
    li 12, 1
    stw 12, 0x78(11)
    lfs 1, 0x60(11)
    blr

flip_speed:                         # replaces stfs f27, 0x458(r27): its starting speed, and no carried momentum
    stfs 27, 0x458(27)
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x78(11)
    cmpwi 12, 0
    beqlr
    lis 12, {POOL_HA}
    addi 12, 12, {POOL_LO}
    lfs 0, {P_FLIP_SPEED}(12)
    stfs 0, 0x458(27)
    stfs 27, 0x454(27)
    blr

flip_air:                           # replaces lhz r4, 0x41e(r31): the speed of a strafe flip follows the stick
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x78(11)
    cmpwi 12, 0
    bne flip_air_strafe
    lhz 4, 0x41e(31)
    blr
flip_air_strafe:
    lis 11, {POOL_HA}
    addi 11, 11, {POOL_LO}
    lfs 1, 0x229c(31)
    lfs 2, {P_FLIP_SPEED}(11)
    fmuls 1, 1, 2
    lfs 2, {P_FLIP_SPEED_MIN}(11)
    fcmpu 0, 1, 2
    bge flip_air_target
    fmr 1, 2
flip_air_target:
    lfs 2, {P_FLIP_ACCEL}(11)
    addi 3, 31, 0x458
    bl {APPROACH}
    lfs 1, 0x164(31)
    stfs 1, 0x194(31)
    b {FLIP_AIR_DONE}

air_turn:                           # replaces lis r3, 0xa: in the air he turns to the camera, the stick gives the heading to move along
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x50(11)
    cmpwi 12, 0
    beq air_turn_plain
    lfs 0, 0x1d20(31)               # as in strafe_turn: no stick, no new heading
    lfs 13, 0x1d24(31)
    fabs 0, 0
    fabs 13, 13
    fadds 0, 0, 13
    lis 12, {POOL_HA}
    addi 12, 12, {POOL_LO}
    lfs 13, {P_ZERO}(12)
    fcmpu 0, 0, 13
    beq air_turn_kept
    lfs 0, 0x180(31)
    stfs 0, 0x60(11)
air_turn_kept:
    lis 11, {CAMERA_STATE_HA}
    addi 11, 11, {CAMERA_STATE_LO}
    lfs 0, 0x158(11)
    stfs 0, 0x180(31)
air_turn_plain:
    lis 3, 0xa
    blr

air_turned:                         # replaces stfs f1, 0x188(r31)
    stfs 1, 0x188(31)
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x50(11)
    cmpwi 12, 0
    beqlr
    lfs 0, 0x60(11)
    stfs 0, 0x180(31)
    blr

speed_threshold:                    # replaces lfs f1, 0x298(r26): this read keeps RC1's 8.5, as RC2's does
    lis 11, {POOL_HA}
    addi 11, 11, {POOL_LO}
    lfs 1, {P_SPEED_THRESHOLD}(11)
    blr

walk_factor:                        # replaces lbz r3, 0x20a8(r25) and the block it starts; f30 = 0, f31 = 1
    lis 11, {POOL_HA}
    addi 11, 11, {POOL_LO}
    lfs 1, 0x229c(25)
    lfs 2, 0x188(25)
    fabs 2, 2
    fabs 0, 1
    lfs 13, {P_FACTOR_STICK}(11)
    fcmpu 0, 0, 13
    blt walk_factor_turn
    lbz 12, 0x20aa(25)
    cmpwi 12, 0
    beq walk_factor_done
    lhz 12, 0x3be(25)
    cmpwi 12, 0
    bne walk_factor_done
walk_factor_turn:
    lfs 13, {P_FACTOR_TURN}(11)
    fcmpu 0, 2, 13
    ble walk_factor_done
    fmr 31, 30
walk_factor_done:
    b {WALK_FACTOR_DONE}

walk_cap:                           # replaces lis r28, 0x72
    lis 28, 0x72                    # the displaced instruction
    lhz 12, 0x3be(25)
    cmpwi 12, 0
    beqlr
    lis 11, {POOL_HA}
    addi 11, 11, {POOL_LO}
    lfs 0, 0x188(25)
    fabs 0, 0
    lfs 13, {P_CAP_PER_TURN}(11)
    fmuls 0, 0, 13
    lfs 13, {P_CAP_SPEED}(11)
    fsubs 0, 13, 0
    lfs 13, {P_ZERO}(11)
    fcmpu 0, 0, 13
    bge walk_cap_set
    fmr 0, 13
walk_cap_set:
    lfs 13, 0x190(25)
    fcmpu 0, 13, 0
    blelr
    stfs 0, 0x190(25)
    blr

walk_slow:                          # replaces lfs f3, 0x190(r25); f1 and f2 hold the steps
    lis 11, {POOL_HA}
    addi 11, 11, {POOL_LO}
    lfs 0, 0x229c(25)
    fabs 0, 0
    lfs 13, {P_SLOW_STICK}(11)
    fcmpu 0, 0, 13
    bge walk_slow_done
    lfs 0, 0x188(25)
    fabs 0, 0
    lfs 13, {P_SLOW_TURN}(11)
    fcmpu 0, 0, 13
    ble walk_slow_done
    lfs 13, {P_SLOW_RATE}(11)
    fmuls 0, 0, 13
    lfs 13, {P_ONE}(11)
    fsubs 0, 13, 0
    lfs 13, {P_ZERO}(11)
    fcmpu 0, 0, 13
    bge walk_slow_set
    fmr 0, 13
walk_slow_set:
    lfs 13, 0x190(25)
    fmuls 0, 13, 0
    stfs 0, 0x190(25)
walk_slow_done:
    lfs 3, 0x190(25)                # the displaced instruction
    blr

jump_vel:                           # replaces lfs f1, 0x128(r26): the velocity goes along the strafe heading
    lfs 1, 0x128(26)
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x50(11)
    cmpwi 12, 0
    beqlr
    lfs 1, 0x60(11)
    blr
"""

# Replaces bl HERO_MAIN: charge trigger and end conditions, then tail-calls HERO_MAIN.
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
    lis 3, {GFX_HEAP_HA}
    addi 3, 3, {GFX_HEAP_LO}
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

    lis 3, {GCM_HA}                 # the entry's offset is relative to the graphics memory base
    lwz 3, {GCM_LO}(3)
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
    lis 3, {CLASS_MAP_HA}           # the level's own model of class 0xc3
    addi 3, 3, {CLASS_MAP_LO}
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
    lis 3, {CLASS_MAP_HA}
    addi 3, 3, {CLASS_MAP_LO}
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
    lis 11, {CLASS_MAP_HA}
    addi 11, 11, {CLASS_MAP_LO}
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

FRAME = """
frame:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 31, 0x70(1)
    std 30, 0x78(1)
    bl boots_tick
    bl foot_box
    bl strafe_tick
    bl clank_tick
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
    b {HERO_MAIN}

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
    lwz 10, 0x90(11)                # Clank's dash
    or 12, 12, 10
    cmpwi 12, 0
    ble chooser_run
    li 3, 0
    blr
chooser_run:
    b {CHOOSER}

trans_clank:                        # Clank's dash: none of his idle/walk transitions (jump, punch, fall)
    cmpwi 3, {STATE_CLANK_IDLE}
    beq trans_skip
    cmpwi 3, {STATE_CLANK_WALK}
    beq trans_skip
    blr

trans:
    lwz 3, 0x2084(19)               # the displaced instruction
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x90(11)
    cmpwi 12, 0
    bgt trans_clank
    lwz 12, 8(11)
    cmpwi 12, 0
    blelr
    cmpwi 3, {STATE_IDLE}
    beq trans_skip
    cmpwi 3, {STATE_WALK}
    bnelr
trans_skip:
    b {TRANS_EXIT}

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
    lwz 12, 0x9c(11)                # Clank's wings follow him once hero_main has moved him
    cmpwi 12, 0
    beq surface_charge
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    bl clank_wings
    bl clank_jets
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
surface_charge:
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
    bl {SURFACE}
    lis 11, {HERO_HA}
    addi 11, 11, {HERO_LO}
    li 12, 0
    stw 12, 0x300(11)
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr
surface_plain:
    b {SURFACE}
"""

# Replaces bl HERO_UPDATE: while charging in the idle or walk state, run the port of RC2's
# charge handler instead of the normal state handler.
UPDATE = """
update:
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x90(11)
    cmpwi 12, 0
    bgt clank_update
update_charge:
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
    b {HERO_UPDATE}

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
    bl crate_sweep

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

# Clank's dash. clank_tick runs in the frame hook in front of hero_main: it keeps the frame
# counter and starts a dash. clank_update runs in place of hero_update while the counter runs.
CLANK = """
clank_tick:                         # r31 = state block, r30 = hero in all of this part
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 31, 0x70(1)
    std 30, 0x78(1)
    lis 31, {STATE_HA}
    addi 31, 31, {STATE_LO}
    lis 30, {HERO_HA}
    addi 30, 30, {HERO_LO}
    lbz 12, 0x20a4(30)
    cmpwi 12, {HERO_CLANK}
    bne ct_off
    lwz 12, 0x2084(30)
    cmpwi 12, {STATE_CLANK_IDLE}
    beq ct_ground
    cmpwi 12, {STATE_CLANK_WALK}
    bne ct_off                      # anything else (damage, a fall, a cutscene) took over
ct_ground:
    lwz 9, 0x90(31)
    cmpwi 9, 0
    ble ct_idle
    addi 9, 9, 1
    stw 9, 0x90(31)
    b ct_out
ct_idle:
    bl clank_unpitch
    lwz 3, 0xb4(31)
    cmpwi 3, 0
    beq ct_plain
    bl clank_wings_on
    b ct_trigger
ct_plain:
    bl clank_wings_off
ct_trigger:
    lis 8, {PAD_HA}
    addi 8, 8, {PAD_LO}
    lwz 7, 0xa0(8)
    andi. 7, 7, {CLANK_BUTTON}
    beq ct_out
    lwz 7, 0xa4(8)
    andi. 7, 7, {CLANK_JUMP_BUTTON}
    beq ct_out
    lhz 7, 0x30e(30)                # frames off the ground
    cmpwi 7, 0
    bne ct_out
    lis 8, {POOL_HA}
    addi 8, 8, {POOL_LO}
    lfs 0, {P_CLANK_STICK}(8)
    lfs 1, 0x229c(30)
    fcmpu 0, 1, 0
    blt ct_out
    li 9, 1
    stw 9, 0x90(31)
    lfs 0, {P_CLANK_LIFT}(8)
    stfs 0, 0x94(31)
    li 9, 0
    stw 9, 0xd4(31)
    stw 9, 0xd8(31)
    b ct_out
ct_off:
    li 9, 0
    stw 9, 0x90(31)
    stw 9, 0xd4(31)
    stw 9, 0xd8(31)
    bl clank_unpitch
    bl clank_wings_off
ct_out:
    ld 30, 0x78(1)
    ld 31, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

clank_unpitch:                      # the pitch goes back to level, CLANK_PITCH_FRAMES for all of it
    lwz 3, 0x98(31)
    cmpwi 3, 0
    beqlr
    lis 8, {POOL_HA}
    addi 8, 8, {POOL_LO}
    lfs 0, 0x94(30)
    lfs 1, {P_CLANK_PITCH_STEP}(8)
    lfs 2, {P_ZERO}(8)
    fcmpu 0, 0, 2
    bgt cup_down
    blt cup_up
    b cup_level
cup_down:
    fsubs 0, 0, 1
    fcmpu 0, 0, 2
    bgt cup_store
    b cup_level
cup_up:
    fadds 0, 0, 1
    fcmpu 0, 0, 2
    blt cup_store
cup_level:
    fmr 0, 2
    li 3, 0
    stw 3, 0x98(31)
cup_store:
    stfs 0, 0x94(30)
    blr

clank_wings_on:                     # the Thruster-Pack's device, created as 0x921c0 creates Ratchet's
    lwz 3, 0x9c(31)
    cmpwi 3, 0
    bnelr
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    li 3, {THRUSTER_CLASS}
    bl {SPAWN}
    cmpwi 3, 0
    beq cwn_out
    stw 3, 0x9c(31)
    lwz 4, 0xbc(31)
    cmpwi 4, 0
    bne cwn_placed
    lis 5, {POOL_HA}
    addi 5, 5, {POOL_LO}
    lwz 4, {P_CLANK_WINGS_AT}(5)
    stw 4, 0xa0(31)
    lwz 4, {P_CLANK_WINGS_AT} + 4(5)
    stw 4, 0xa4(31)
    lwz 4, {P_CLANK_WINGS_AT} + 8(5)
    stw 4, 0xa8(31)
cwn_placed:
    li 4, 1
    stb 4, 0x31(3)
    li 4, 0x20
    sth 4, 0x32(3)
    lwz 5, 0x2080(30)
    ld 6, 0x38(5)
    std 6, 0x38(3)
    lwz 4, 0xb0(31)
    cmpwi 4, 0
    bne cwn_anim
    li 4, {CLANK_WINGS_ANIM}
cwn_anim:
    li 5, 0
    li 6, {CLANK_PITCH_FRAMES}
    bl {MOBY_SET_ANIM}
    li 3, 0
    bl {JET_SPAWN}
    stw 3, 0xc0(31)
    bl clank_jet_init
    li 3, 1
    bl {JET_SPAWN}
    stw 3, 0xc4(31)
    bl clank_jet_init
cwn_out:
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

clank_wings_off:
    lwz 3, 0x9c(31)
    cmpwi 3, 0
    beqlr
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    bl {MOBY_DELETE}
    li 3, 0
    stw 3, 0x9c(31)
    lwz 3, 0xc0(31)
    cmpwi 3, 0
    beq cwf_second
    bl {MOBY_DELETE}
cwf_second:
    lwz 3, 0xc4(31)
    cmpwi 3, 0
    beq cwf_done
    bl {MOBY_DELETE}
cwf_done:
    li 3, 0
    stw 3, 0xc0(31)
    stw 3, 0xc4(31)
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

clank_sound:                        # Ratchet's Thruster-Pack sound, on Clank
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lis 4, {CLASS_MAP_HA}           # Ratchet's model: class 0
    lbz 4, {CLASS_MAP_LO}(4)
    slwi 4, 4, 2
    lis 5, {MODEL_TABLE_HA}
    addi 5, 5, {MODEL_TABLE_LO}
    lwzx 4, 5, 4
    cmpwi 4, 0
    beq cks_out
    lbz 5, 0xd(4)                   # its sound definitions: count, then 32 bytes each
    cmpwi 5, {THRUSTER_SOUND}
    ble cks_out
    lwz 3, 0x28(4)
    cmpwi 3, 0
    beq cks_out
    addi 3, 3, {THRUSTER_SOUND_OFF}
    li 4, 0
    lwz 5, 0x2080(30)
    li 6, 0
    li 7, 0x400
    bl {PLAY_SOUND_DEF}
    cmpwi 3, 0
    blt cks_out
    addi 4, 3, 1                    # the voice follows him, as with the game's play-model-sound
    mulli 4, 4, 0x70
    lis 5, {VOICES_HA}
    addi 5, 5, {VOICES_LO}
    add 5, 5, 4
    lwz 6, 0x2080(30)
    stw 6, 0x18(5)
cks_out:
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

clank_jet_init:                     # r3 = a new jet or 0: its own update is switched off
    cmpwi 3, 0
    beqlr
    li 4, {JET_OFF_STATE}
    stb 4, 0x20(3)
    lwz 4, 0x78(3)
    lwz 5, 0x9c(31)
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

clank_jets:                         # the jets burn while he dashes
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 31, 0x70(1)
    std 30, 0x78(1)
    lis 31, {STATE_HA}
    addi 31, 31, {STATE_LO}
    lwz 3, 0x90(31)
    cmpwi 3, 0
    ble cj_out
    lwz 30, 0xc0(31)
    bl clank_jet
    lwz 30, 0xc4(31)
    bl clank_jet
cj_out:
    ld 30, 0x78(1)
    ld 31, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

clank_jet:                          # r30 = jet or 0
    cmpwi 30, 0
    beqlr
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lwz 4, 0x78(30)
    lwz 5, 0x9c(31)
    stw 5, 8(4)
    lis 6, {POOL_HA}
    addi 6, 6, {POOL_LO}
    lwz 5, {P_JET_VALUES}(6)
    stw 5, 0x20(4)
    lis 3, {JET_DRAW_HA}
    addi 3, 3, {JET_DRAW_LO}
    mr 4, 30
    bl {DRAW_REGISTER}
    mr 3, 30
    bl {JET_EMIT}
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

clank_wings:                        # the wings take his moby's matrix, rotation and position
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 10, 0x9c(11)
    cmpwi 10, 0
    beqlr
    lis 9, {HERO_HA}
    addi 9, 9, {HERO_LO}
    lwz 9, 0x2080(9)
    cmpwi 9, 0
    beqlr
    li 0, 12
    mtctr 0
    addi 7, 9, 0xbc
    addi 8, 10, 0xbc
cw_copy:
    lwzu 6, 4(7)
    stwu 6, 4(8)
    bdnz cw_copy
    lwz 6, 0x40(9)
    stw 6, 0x40(10)
    lwz 6, 0x44(9)
    stw 6, 0x44(10)
    lwz 6, 0x48(9)
    stw 6, 0x48(10)
    lfs 1, 0xa0(11)                 # the offset, along his axes
    lfs 2, 0xa4(11)
    lfs 3, 0xa8(11)
    lfs 0, 0x10(9)
    lfs 4, 0xc0(9)
    fmadds 0, 4, 1, 0
    lfs 4, 0xd0(9)
    fmadds 0, 4, 2, 0
    lfs 4, 0xe0(9)
    fmadds 0, 4, 3, 0
    stfs 0, 0x10(10)
    lfs 0, 0x14(9)
    lfs 4, 0xc4(9)
    fmadds 0, 4, 1, 0
    lfs 4, 0xd4(9)
    fmadds 0, 4, 2, 0
    lfs 4, 0xe4(9)
    fmadds 0, 4, 3, 0
    stfs 0, 0x14(10)
    lfs 0, 0x18(9)
    lfs 4, 0xc8(9)
    fmadds 0, 4, 1, 0
    lfs 4, 0xd8(9)
    fmadds 0, 4, 2, 0
    lfs 4, 0xe8(9)
    fmadds 0, 4, 3, 0
    stfs 0, 0x18(10)
    lwz 6, 0x1c(9)
    stw 6, 0x1c(10)
    lwz 6, 0xb8(11)
    cmpwi 6, 0
    beq cw_moved
    stw 6, 0x2c(10)
cw_moved:
    mr 3, 10                        # as the game does after moving an attached moby (0x8cb6c):
    b {MOBY_MOVED}                  # without it the bounding sphere stays empty and it is never drawn

clank_update:                       # r11 = state block
    lis 10, {HERO_HA}
    addi 10, 10, {HERO_LO}
    lwz 12, 0x2084(10)
    cmpwi 12, {STATE_CLANK_IDLE}
    beq cl_run
    cmpwi 12, {STATE_CLANK_WALK}
    bne update_charge
cl_run:
    stdu 1, -0xb0(1)
    mflr 0
    std 0, 0xc0(1)
    std 31, 0xa8(1)
    std 30, 0xa0(1)
    std 29, 0x98(1)
    mr 31, 11
    mr 30, 10
    lis 29, {POOL_HA}
    addi 29, 29, {POOL_LO}

    lis 3, {CLANK_SPHERE_HI}        # his collision sphere stays at its own height (see CLANK_SPHERE_HEIGHT)
    ori 3, 3, {CLANK_SPHERE_LO}
    stw 3, 0x434(30)
    stw 3, 0x224(30)

    lwz 3, 0xd4(31)
    cmpwi 3, 0
    bgt cl_bumping
    lfs 1, 0x80(30)                 # ground covered since the last frame, squared
    lfs 2, 0xcc(31)
    fsubs 1, 1, 2
    lfs 3, 0x84(30)
    lfs 4, 0xd0(31)
    fsubs 3, 3, 4
    fmuls 5, 1, 1
    fmadds 5, 3, 3, 5
    stfs 5, 0x80(1)
    lwz 3, 0x80(30)
    stw 3, 0xcc(31)
    lwz 3, 0x84(30)
    stw 3, 0xd0(31)
    lwz 3, 0x90(31)
    cmpwi 3, 1
    bne cl_move
    lfs 1, {P_ONE}(29)              # first frame: turn to the stick's heading, as the walk
    li 4, 0                         # state would over the next frames
    bl {STICK_TARGET}
    lfs 1, 0x180(30)
    lfs 2, 0x98(30)
    bl {ANGLE_DIFF}
    fmr 3, 1
    lfs 1, {P_ZERO}(29)
    fmr 2, 1
    bl {ROTATE_HERO}
    li 3, {CLANK_DASH_ANIM}
    li 4, 0
    lfs 1, {P_CLANK_ANIM_BLEND}(29)
    bl {HERO_SET_ANIM}
    bl clank_wings_on
    bl clank_sound
    li 3, {STATE_TYPE_JUMP}         # the camera follows as it does a jump
    stw 3, 0x208c(30)
    li 3, {CAMERA_JUMP}
    stw 3, 0x2284(30)
cl_move:
    li 3, 0                         # as in the charge: hero_set_anim's flag would block his jump
    stw 3, 0xa9c(30)
    lfs 1, {P_CLANK_PITCH}(29)
    lfs 2, {P_CLANK_PITCH_STEP}(29)
    addi 3, 30, 0x94
    bl {APPROACH}
    li 3, 1
    stw 3, 0x98(31)

    lfs 1, {P_CLANK_SPEED}(29)
    stfs 1, 0x190(30)
    lfs 2, {P_CLANK_ACCEL}(29)
    addi 3, 30, 0x194
    bl {APPROACH}
    lfs 1, {P_BIG}(29)              # velocity along his own heading
    bl {BUILD_VELOCITY}
    lwz 3, 0x90(31)
    cmpwi 3, {THRUST_DELAY}         # he leaves the ground after this many frames
    ble cl_sweep
    lfs 1, 0x94(31)                 # launch speed, less the gravity every frame
    stfs 1, 0xe8(30)
    lfs 2, {P_CLANK_GRAVITY}(29)
    fsubs 1, 1, 2
    stfs 1, 0x94(31)
cl_sweep:
    lwz 3, 0x90(31)
    cmpwi 3, {THRUST_SWEEP_FROM}
    ble cl_landing
    lfs 1, 0x98(30)                 # crates around the point ahead of him
    bl {COS}
    lfs 2, {P_SWEEP_AHEAD}(29)
    lfs 3, 0x80(30)
    fmadds 1, 1, 2, 3
    stfs 1, 0x70(1)
    lfs 1, 0x98(30)
    bl {SIN}
    lfs 2, {P_SWEEP_AHEAD}(29)
    lfs 3, 0x84(30)
    fmadds 1, 1, 2, 3
    stfs 1, 0x74(1)
    lfs 1, 0x88(30)
    lfs 2, {P_SWEEP_UP}(29)
    fadds 1, 1, 2
    stfs 1, 0x78(1)
    lwz 3, 0x8c(30)
    stw 3, 0x7c(1)
    addi 3, 1, 0x70
    lfs 1, {P_SWEEP_RADIUS}(29)
    bl crate_sweep
cl_landing:
    lwz 3, 0x90(31)
    cmpwi 3, {THRUST_DELAY}
    ble cl_no_wall
    cmpwi 3, {CLANK_DASH_MIN_FRAMES}
    ble cl_air
    bl clank_grounded               # going down and near the ground: landed, still pitched as the user wants it
    cmpwi 3, 0
    bne cl_land
cl_air:
    lis 4, {CAMERA_STATE_HA}        # the camera in his way: the bump as well
    addi 4, 4, {CAMERA_STATE_LO}
    lfs 1, 0x140(4)
    lfs 2, 0x80(30)
    fsubs 1, 1, 2
    lfs 3, 0x144(4)
    lfs 4, 0x84(30)
    fsubs 3, 3, 4
    fmuls 5, 1, 1
    fmadds 5, 3, 3, 5
    lfs 6, {P_CAMERA_BUMP_SQ}(29)
    lwz 5, 0xc8(31)                 # tuning: another squared distance
    cmpwi 5, 0
    beq cl_camera
    lfs 6, 0xc8(31)
cl_camera:
    fcmpu 0, 5, 6
    bge cl_wall
    lfs 6, 0xe0(30)
    fmuls 6, 6, 1
    lfs 7, 0xe4(30)
    fmadds 6, 7, 3, 6
    lfs 7, {P_ZERO}(29)
    fcmpu 0, 6, 7
    bgt cl_bonk
cl_wall:
    lbz 4, 0x257(30)                # a wall, and it stopped him: the bump
    cmpwi 4, 0
    beq cl_no_wall
    lfs 1, 0x194(30)
    lfs 2, {P_HALF}(29)
    fmuls 1, 1, 2
    fmuls 1, 1, 1
    lfs 0, 0x80(1)
    fcmpu 0, 0, 1
    bge cl_no_wall
cl_bonk:
    li 3, 1
    stw 3, 0xd4(31)
    li 3, 0
    stw 3, 0x94(31)                 # he drops from rest
    lfs 1, {P_BUMP_SPEED}(29)
    stfs 1, 0x194(30)
    lwz 3, 0xb4(31)
    cmpwi 3, 0
    bne cl_bonk_anim
    bl clank_wings_off
cl_bonk_anim:
    li 3, {CLANK_BUMP_ANIM}
    li 4, {CLANK_BUMP_ANIM_FLAGS}
    lfs 1, {P_CLANK_BUMP_BLEND}(29)
    bl {HERO_SET_ANIM}
    b cl_out

cl_bumping:                         # thrown back from the wall
    addi 3, 3, 1
    stw 3, 0xd4(31)
    li 3, 0
    stw 3, 0xa9c(30)
    lfs 1, {P_ZERO}(29)             # level again
    lfs 2, {P_CLANK_PITCH_STEP}(29)
    addi 3, 30, 0x94
    bl {APPROACH}
    lfs 1, {P_ZERO}(29)
    stfs 1, 0x190(30)
    lfs 2, {P_BUMP_DECEL}(29)
    addi 3, 30, 0x194
    bl {APPROACH}
    lfs 1, {P_BIG}(29)              # the velocity along his heading, turned round
    bl {BUILD_VELOCITY}
    lfs 1, 0xe0(30)
    fneg 1, 1
    stfs 1, 0xe0(30)
    lfs 1, 0xe4(30)
    fneg 1, 1
    stfs 1, 0xe4(30)
    lfs 1, 0x94(31)
    lfs 2, {P_BUMP_GRAVITY}(29)
    fsubs 1, 1, 2
    stfs 1, 0x94(31)
    stfs 1, 0xe8(30)
    lwz 3, 0xd4(31)
    cmpwi 3, {CLANK_BUMP_MAX_FRAMES}
    bgt cl_bump_end
    cmpwi 3, {CLANK_BUMP_FRAMES}
    blt cl_out
    bl clank_grounded
    cmpwi 3, 0
    beq cl_out
    li 3, 0
    stw 3, 0x194(30)
    b cl_land
cl_bump_end:
    li 3, 0
    stw 3, 0xd4(31)
    stw 3, 0x90(31)
    stw 3, 0x194(30)
    b cl_state
cl_no_wall:
    lwz 3, 0x90(31)
    cmpwi 3, {CLANK_DASH_MAX_FRAMES}
    bgt cl_end
    cmpwi 3, {CLANK_DASH_MIN_FRAMES}
    ble cl_out
    lhz 4, 0x30e(30)                # back on the ground
    cmpwi 4, 0
    bne cl_out
cl_end:
    li 3, 0                         # over: back to his own speed and animation
    stw 3, 0x90(31)
    lfs 1, {P_CLANK_RUN}(29)
    lfs 2, 0x194(30)
    fcmpu 0, 2, 1
    ble cl_slow
    stfs 1, 0x194(30)
cl_slow:
    lwz 3, 0xb4(31)
    cmpwi 3, 0
    bne cl_state
    bl clank_wings_off
    b cl_state
cl_land:                            # on the ground: his idle state takes over from there
    lwz 3, 0x2d8(30)
    stw 3, 0x88(30)
    li 3, 0
    stw 3, 0xe8(30)
    stw 3, 0x94(31)
    stw 3, 0xd4(31)
    stw 3, 0xd8(31)
    stw 3, 0x90(31)
    lfs 1, {P_CLANK_RUN}(29)
    lfs 2, 0x194(30)
    fcmpu 0, 2, 1
    ble cl_land_wings
    stfs 1, 0x194(30)
cl_land_wings:
    lwz 3, 0xb4(31)
    cmpwi 3, 0
    bne cl_land_state
    bl clank_wings_off
cl_land_state:
    li 3, {STATE_CLANK_IDLE}
    b cl_set
cl_state:
    lhz 4, 0x30e(30)
    li 3, {STATE_CLANK_IDLE}
    cmpwi 4, 0
    beq cl_set
    li 3, {STATE_CLANK_FALL}
cl_set:
    li 4, 1
    bl {HERO_SET_STATE}
cl_out:
    ld 29, 0x98(1)
    ld 30, 0xa0(1)
    ld 31, 0xa8(1)
    ld 0, 0xc0(1)
    mtlr 0
    addi 1, 1, 0xb0
    blr

clank_grounded:                     # -> r3 = 1 when he is going down and within reach of the ground
    li 3, 0
    lfs 0, {P_ZERO}(29)
    lfs 1, 0x94(31)
    fcmpu 0, 1, 0
    bgelr
    lfs 1, 0x2dc(30)
    lfs 2, {P_CLANK_NO_GROUND}(29)
    fcmpu 0, 1, 2
    bgelr
    lfs 1, 0x88(30)
    lfs 2, 0x2d8(30)
    fsubs 1, 1, 2
    lfs 2, {P_CLANK_LAND}(29)
    fcmpu 0, 1, 2
    bgtlr
    li 3, 1
    blr
"""


def rc2_animation(index, vaddr):
    """One of RC2's Ratchet animations, relocated for vaddr. Extracted once from RC2's archive."""
    cache = os.path.join(ASSETS, f"rc2_anim{index}.bin")
    if not os.path.exists(cache):
        from psarc import Psarc
        level = Psarc("rc2").read("/rc2/ps3data/level1/engine.ps3")
        table = struct.unpack_from(">I", level, 0x18)[0]       # player animation table
        offsets = struct.unpack_from(">157I", level, table)
        start = offsets[index]
        end = min(o for o in offsets if o > start)
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        with open(cache, "wb") as f:
            f.write(level[start:end])
    anim = bytearray(open(cache, "rb").read())
    frames = anim[0x10]
    for i in range(frames):                                    # frame pointers become absolute
        off = 0x1C + 4 * i
        struct.pack_into(">I", anim, off, struct.unpack_from(">I", anim, off)[0] + vaddr)
    anim[0x13] = 0                                             # RC1 animations have 0 here, RC2's 0xff
    return bytes(anim)


def animations():
    """The embedded animations: the charge at ANIM_VADDR, then the backwards walk. -> data, address of the latter"""
    blob = rc2_animation(RC2_CHARGE_ANIM, ANIM_VADDR)
    blob += bytes(-len(blob) % 16)
    back = ANIM_VADDR + len(blob)
    return blob + rc2_animation(RC2_BACK_ANIM, back), back


def charge_sound_bank():
    """One RC2 level sound bank cut down to the two charge sounds' sample data.

    File: 8 u32 (3, 2, block offset, block size, sample offset, sample size), then the 'SBlk'
    block: header (+0x14 sound count, +0x18 grain count << 16 | sample count, +0x1c sounds,
    +0x20 grains, +0x28/+0x2c sample size, +0x34 grain data), 12-byte sounds (+4 grain count,
    +8 first grain), 8-byte grains (type << 24 | data offset; type 1 is a tone), and tone
    records with the sample offset at +0x10 and its size at +0x14.
    """
    cache = os.path.join(ASSETS, "rc2_charge_sounds.bin")     # the cut-down bank, kept with the source
    if os.path.exists(cache):
        return open(cache, "rb").read()
    src = open(os.path.join(os.path.dirname(RC1_ELF), "rc2", "ps3data", f"level{SOUND_BANK_LEVEL}", "sound.bnk"), "rb").read()
    block_off, block_size, sample_off = struct.unpack_from(">3I", src, 8)
    block = bytearray(src[block_off:block_off + block_size])
    sounds, grains, grain_data = struct.unpack_from(">I", block, 0x1C)[0], struct.unpack_from(">I", block, 0x20)[0], struct.unpack_from(">I", block, 0x34)[0]
    samples, moved = bytearray(), {}
    for definition in SOUND_DEFS:
        sound = sounds + 12 * struct.unpack_from(">H", definition, 0x1A)[0]
        count, first = block[sound + 4], struct.unpack_from(">I", block, sound + 8)[0]
        for g in range(count):
            op = struct.unpack_from(">I", block, grains + first + 8 * g)[0]
            if op >> 24 != 1:
                continue
            tone = grain_data + (op & 0xFFFFFF)
            off, size = struct.unpack_from(">II", block, tone + 0x10)
            if off not in moved:
                moved[off] = len(samples)
                samples += src[sample_off + off:sample_off + off + size]
                samples += bytes(-len(samples) % 16)
            struct.pack_into(">I", block, tone + 0x10, moved[off])
    struct.pack_into(">II", block, 0x28, len(samples), len(samples))
    new_sample_off = (0x20 + len(block) + 15) & ~15
    out = bytearray(struct.pack(">8I", 3, 2, 0x20, len(block), new_sample_off, len(samples), 0, 0))
    out += block
    out += bytes(new_sample_off - len(out))
    with open(cache, "wb") as f:
        f.write(out + samples)
    return bytes(out + samples)


def ha(v):
    return ((v + 0x8000) >> 16) & 0xFFFF


def lo(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def bl(src, dst):
    return 0x48000001 | ((dst - src) & 0x03FFFFFC)


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--radius", type=float, default=14.0, help="Box Breaker radius in game units (default 14)")
    ap.add_argument("--keep-explosive", action="store_true", help="leave explosive crates alone")
    ap.add_argument("--no-charge-boots", action="store_true", help="build without the Charge Boots and the bolt crank boost")
    ap.add_argument("--burst-speed", type=float, default=30.0, help="units/s for the first second (RC2: 30)")
    ap.add_argument("--cruise-speed", type=float, default=11.5, help="units/s after that (RC2: 11.5)")
    ap.add_argument("--crank-speed", type=float, default=CRANK_SPEED, help="units/s at a boosted bolt crank (the game's own: 3.7)")
    ap.add_argument("--rc1-acceleration", action="store_true", help="keep RC1's ground acceleration (7.5 and 8.5 units/s^2; RC2: 18 and 20) and its slowing in turns")
    ap.add_argument("--in", dest="src", default=RC1_ELF, help="the untouched RC1.ppu.elf")
    ap.add_argument("--out", default=DEFAULT_OUT, help="default: build/EBOOT.elf")
    ap.add_argument("--install", action="store_true", help=f"copy the result to {RPCS3_EBOOT}")
    ap.add_argument("--export", metavar="FILE", help="also write the changes as a patch file for patch.py")
    return ap.parse_args()


def hook_table(charge, rc2_acceleration):
    """site -> (label in the cave, replaced call target or instruction word)"""
    hooks = {STRIKE_HOOK: ("strike", COLLECT)}           # site -> (label, replaced call or word)
    hooks[STRIKE_FX_HOOK] = ("strike_fx", STRIKE_FX_HOOK_WORD)
    hooks[SHAKE_HOOK] = ("shake", SHAKE_CHANNEL)
    hooks.update({h: ("crate_break", CRATE_BREAK_FX) for h in CRATE_BREAK_HOOKS})
    hooks[BOLTS_HOOK] = ("bolts", SPAWN_BOLTS)
    hooks.update({h: ("strafe_frame", HERO_MAIN) for h in FRAME_HOOKS})   # replaced below when charging
    hooks.update({
        WALK_QUICK_HOOK: ("walk_quick", WALK_QUICK_HOOK_WORD), WALK_TURN_HOOK: ("walk_turn", WALK_TURN_HOOK_WORD),
        WALK_VEL_HOOK: ("walk_vel", WALK_VEL_HOOK_WORD), IDLE_ALIGN_HOOK: ("idle_align", IDLE_ALIGN_HOOK_WORD),
        WALK_ALIGN_HOOK: ("walk_align", WALK_ALIGN_HOOK_WORD), FLIP_TYPE_HOOK: ("flip_type", STICK_TARGET),
        FLIP_TIME_HOOK: ("flip_time", STICK_TARGET), JUMP_CHOICE_HOOK: ("jump_choice", JUMP_CHOICE_HOOK_WORD),
        LEAN_HOOK: ("lean", LEAN_HOOK_WORD), WALK_ANIM_HOOK: ("walk_anim", WALK_ANIM_HOOK_WORD),
        FLIP_HEADING_HOOK: ("flip_heading", FLIP_HEADING_HOOK_WORD), FLIP_SPEED_HOOK: ("flip_speed", FLIP_SPEED_HOOK_WORD),
        FLIP_AIR_HOOK: ("flip_air", FLIP_AIR_HOOK_WORD), AIR_TURN_HOOK: ("air_turn", AIR_TURN_HOOK_WORD),
        AIR_TURNED_HOOK: ("air_turned", AIR_TURNED_HOOK_WORD), JUMP_VEL_HOOK: ("jump_vel", JUMP_VEL_HOOK_WORD)})
    if rc2_acceleration:
        hooks[SPEED_THRESHOLD_HOOK] = ("speed_threshold", SPEED_THRESHOLD_HOOK_WORD)
        hooks[WALK_FACTOR_HOOK] = ("walk_factor", WALK_FACTOR_HOOK_WORD)
        hooks[WALK_CAP_HOOK] = ("walk_cap", WALK_CAP_HOOK_WORD)
        hooks[WALK_SLOW_HOOK] = ("walk_slow", WALK_SLOW_HOOK_WORD)
    if charge:
        hooks.update({h: ("frame", HERO_MAIN) for h in FRAME_HOOKS})
        hooks.update({h: ("surface", SURFACE) for h in SURFACE_HOOKS})
        hooks[UPDATE_HOOK] = ("update", HERO_UPDATE)
        hooks[CHOOSER_HOOK] = ("chooser", CHOOSER)
        hooks[TRANS_HOOK] = ("trans", TRANS_HOOK_WORD)
        hooks[SKID_HOOK] = ("skid", SKID_HOOK_WORD)
        hooks[CRANK_HOOK] = ("crank", CRANK_HOOK_WORD)
        hooks[CRANK_ANIM_HOOK] = ("crank_anim", CRANK_ANIM_HOOK_WORD)
        hooks[CRANK_PULL_HOOK] = ("crank_pull", CRANK_PULL_HOOK_WORD)
        hooks[CRANK_TURN_HOOK] = ("crank_turn", CRANK_TURN_HOOK_WORD)
        hooks.update({h: ("boots_spawn", SPAWN) for h in FOOT_SPAWN_HOOKS})
        hooks.update({
            GRID_ENTRY_HOOK: ("grid_entry", GRID_ENTRY_HOOK_WORD), GRID_SELECTED_HOOK: ("grid_selected", GRID_SELECTED_HOOK_WORD),
            GRID_PRESS_HOOK: ("grid_press", GRID_PRESS_HOOK_WORD), GRID_WORN_HOOK: ("grid_worn", GRID_WORN_HOOK_WORD),
            GRID_EQUIP_HOOK: ("grid_equip", GRID_EQUIP_HOOK_WORD), TEXT_HOOK: ("menu_text", TEXT_LOOKUP),
            PREVIEW_CLASS_HOOK: ("preview_class", PREVIEW_CLASS_HOOK_WORD), PREVIEW_SPAWN_HOOK: ("preview_spawn", SPAWN)})
    return hooks


def constant_pool(args):
    """The cave's constants, addressed off one base register.

    Returns the pool, the offset of each constant as P_<name>, and the two generated pieces of
    assembly that write and clear the camera tuning.
    """
    pool, offsets = bytearray(), {}

    def const(name, data):
        offsets["P_" + name] = len(pool)
        pool.extend(data)

    def floats(*values):
        return struct.pack(f">{len(values)}f", *values)

    const("ZERO", floats(0.0))
    const("ONE", floats(1.0))
    const("SEVEN", floats(7.0))
    const("BOX_RADIUS", floats(args.radius))
    const("STRIKE_FRAME", floats(STRIKE_FRAME))
    const("SHAKE", floats(SHAKE_STRENGTH))
    const("SIXTY", floats(60.0))
    const("SHAKE_PHASE", floats(SHAKE_PHASE))
    const("SHAKE_FREQ", floats(SHAKE_FREQ))
    const("SHAKE_RAMP", floats(SHAKE_RAMP))
    const("PI", floats(PI))
    for power, term in zip((3, 5, 7, 9), SIN_TERMS):
        const(f"SIN{power}", floats(term))
    const("REVERSE", floats(STRAFE_REVERSE))
    const("FOUR", floats(4.0))
    const("QUARTER", floats(0.25))
    const("TURN_A", floats(STRAFE_TURN[0]))
    const("TURN_C", floats(STRAFE_TURN[2]))
    const("ALIGN_IDLE", floats(STRAFE_ALIGN_IDLE))
    const("ALIGN_WALK", floats(STRAFE_ALIGN_WALK))
    const("STOP_SPEED", floats(STRAFE_STOP_SPEED / 60))
    const("CLANK_LAND", floats(CLANK_LAND_HEIGHT))
    const("CLANK_TOUCH", floats(CLANK_TOUCH_HEIGHT))
    const("CLANK_NO_GROUND", floats(CLANK_LAND_NO_GROUND))
    const("TWIST_STICK", floats(STRAFE_TWIST_STICK))
    for name, value in zip("ABC", STRAFE_TWIST):
        const("TWIST_" + name, floats(value))
    const("BACK_BLEND", floats(STRAFE_BACK_BLEND))
    const("SPEED_THRESHOLD", floats(GROUND_DECEL[1]))
    const("FACTOR_STICK", floats(WALK_FACTOR_STICK))
    const("FACTOR_TURN", floats(WALK_FACTOR_TURN))
    const("CAP_SPEED", floats(WALK_CAP_SPEED / 60))
    const("CAP_PER_TURN", floats(WALK_CAP_PER_TURN / 60))
    const("SLOW_STICK", floats(WALK_SLOW_STICK))
    const("SLOW_TURN", floats(WALK_SLOW_TURN))
    const("SLOW_RATE", floats(WALK_SLOW_RATE))
    const("GAIT_BLEND", floats(STRAFE_GAIT_BLEND))
    for name, value in zip(("RATE", "MIN", "MAX"), STRAFE_BACK_RATE):
        const("BACK_" + name, floats(value))
    const("FLIP_STICK", floats(STRAFE_FLIP_STICK))
    const("FLIP_AIM", floats(STRAFE_FLIP_AIM_STICK))
    for name, value in zip(("FLIP_SPEED", "FLIP_SPEED_MIN", "FLIP_ACCEL"), STRAFE_FLIP_SPEED):
        const(name, floats(value))
    const("BURST", floats(args.burst_speed / 60))        # speeds are per frame
    const("CRUISE", floats(args.cruise_speed / 60))
    const("ACCEL", floats(ACCEL / 3600))
    const("DECEL", floats(DECEL / 3600))
    const("TURN", floats(TURN_RATE / 60))
    const("BURST_TURN", floats(BURST_TURN_SCALE))
    const("STEER_SMOOTH", floats(STEER_SMOOTH))
    const("DEADZONE", floats(STEER_DEADZONE))
    const("BIG", floats(99999.0))
    const("AHEAD", floats(DASH_SWEEP_AHEAD))
    const("DASH_RADIUS", floats(DASH_SWEEP_RADIUS))
    const("ANIM_BLEND", floats(ANIM_BLEND))
    const("HOVER", floats(HOVER_HEIGHT))
    const("HOVER_K", floats(HOVER_STIFFNESS))
    const("HOVER_D", floats(HOVER_DAMPING))
    const("HOVER_MAX", floats(HOVER_MAX_SPEED))
    const("HOVER_SNAP", floats(HOVER_MAX_SPEED * HOVER_SNAP))
    const("SKID_BLEND", floats(SKID_ANIM_BLEND))
    const("BUMP_RATIO", floats(BUMP_RATIO))
    const("PROBE_HEIGHT", floats(PROBE_HEIGHT))
    const("PROBE_REACH", floats(PROBE_REACH))
    const("GROUNDED", floats(GROUNDED_HEIGHT))
    const("CRANK_MAX", floats(args.crank_speed / 60))
    const("CRANK_ACCEL", floats(CRANK_ACCEL / 3600))
    const("CRANK_BLEND", floats(CRANK_ANIM_BLEND))
    const("CAM_GAIN", floats(CAMERA_TURN_GAIN))
    const("CAM_LIMIT", floats(CAMERA_TURN_LIMIT))
    const("HALF", floats(0.5))
    const("CLANK_STICK", floats(CLANK_DASH_STICK))
    const("CLANK_SPEED", floats(THRUST_SPEED / 60))
    const("CLANK_ACCEL", floats(THRUST_ACCEL / 3600))
    const("CLANK_LIFT", floats((2 * THRUST_HEIGHT * THRUST_GRAVITY) ** 0.5 / 60))
    const("CLANK_GRAVITY", floats(THRUST_GRAVITY / 3600))
    const("SWEEP_AHEAD", floats(THRUST_SWEEP_AHEAD))
    const("CLANK_BUMP_BLEND", floats(CLANK_BUMP_ANIM_BLEND))
    const("BUMP_SPEED", floats(BUMP_SPEED / 60))
    const("BUMP_DECEL", floats(BUMP_DECEL / 3600))
    const("BUMP_GRAVITY", floats(CLANK_BUMP_GRAVITY / 3600))
    const("CAMERA_BUMP_SQ", floats(CLANK_CAMERA_BUMP ** 2))
    const("SWEEP_UP", floats(THRUST_SWEEP_UP))
    const("SWEEP_RADIUS", floats(THRUST_SWEEP_RADIUS))
    const("CLANK_RUN", floats(CLANK_RUN_SPEED / 60))
    const("CLANK_PITCH", floats(CLANK_PITCH))
    const("CLANK_WINGS_AT", floats(*CLANK_WINGS_OFFSET))
    const("JET_VALUES", floats(*JET_VALUES))
    const("CLANK_PITCH_STEP", floats(CLANK_PITCH / CLANK_PITCH_FRAMES))
    const("CLANK_ANIM_BLEND", floats(CLANK_DASH_ANIM_BLEND))
    for off, value in CAMERA_FIELDS:
        const(f"CAM_{off:X}", floats(value))
    all_camera = [off for off, _ in CAMERA_FIELDS] + list(CAMERA_TURN_FIELDS)
    camera_set = "\n".join(f"    lfs 0, {offsets[f'P_CAM_{off:X}']}(29)\n    stfs 0, {off}(4)" for off, _ in CAMERA_FIELDS)
    camera_reset = ("    lis 8, {CAMERA_HA}\n    addi 8, 8, {CAMERA_LO}\n    li 7, 0\n".format(CAMERA_HA=ha(CAMERA), CAMERA_LO=lo(CAMERA))
                    + "\n".join(f"    stw 7, {off}(8)" for off in all_camera))
    const("TRAIL_VEC", floats(*TRAIL_VEC))
    const("TRAIL_A", TRAIL_DESCRIPTORS[0])
    const("TRAIL_B", TRAIL_DESCRIPTORS[1])
    return bytes(pool), offsets, dict(CAMERA_SET=camera_set, CAMERA_RESET=camera_reset)


def boots_data():
    """The embedded Charge Boots: model, texture entry, padding, pixels, the Foot Items table and
    the menu strings; and the sizes and addresses the code needs."""
    model, entry, pixels = (open(os.path.join(ASSETS, "boots", name), "rb").read() for name in BOOTS_FILES)
    icons = [open(os.path.join(ASSETS, "boots", name), "rb").read() for name in ICON_FILES]
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
    pixels_at = BOOTS_VADDR + len(blob)
    blob += pixels + bytes(-len(pixels) % 16)
    foot_table = BOOTS_VADDR + len(blob)
    items = (ITEM_GRINDBOOTS, ITEM_MAGNEBOOTS, ITEM_GRINDBOOTS)      # the third entry is the Charge Boots
    blob += b"".join(struct.pack(">5H", icon, 0, 0, item, 0) for icon, item in zip(FOOT_ICONS, items))
    charge_entry = foot_table + 10 * (len(items) - 1)
    name = BOOTS_VADDR + len(blob)
    blob += CHARGE_NAME + b"\0"
    text = BOOTS_VADDR + len(blob)
    blob += CHARGE_HELP + b"\0"
    blob += bytes(-len(blob) % 4)
    icon_entries = BOOTS_VADDR + len(blob)                   # one texture entry per icon version
    blob += ICON_ENTRY * len(icons)
    icon_slots = BOOTS_VADDR + len(blob)                     # room for both entries at any of 0x24 offsets
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


def template_fields(args, offsets, camera, boots_fields, back_anim):
    """Everything the assembly templates name in braces, except the pool address."""
    return dict(
        COLLECT=COLLECT, IS_CRATE=IS_CRATE, DEAL_DAMAGE=DEAL_DAMAGE, VEC_SCALE=VEC_SCALE, VEC_ADD=VEC_ADD,
        HERO_MAIN=HERO_MAIN, HERO_UPDATE=HERO_UPDATE, HERO_SET_STATE=HERO_SET_STATE,
        FRAME_HA=ha(FRAME_COUNTER), FRAME_LO=lo(FRAME_COUNTER), FRAMES=FRAMES, SHAKE_FRAMES=SHAKE_FRAMES,
        SHAKE_CHANNEL=SHAKE_CHANNEL, CAMERA_STATE_HA=ha(CAMERA_STATE), CAMERA_STATE_LO=lo(CAMERA_STATE),
        TIME_SCALE_HA=ha(TIME_SCALE), TIME_SCALE_LO=lo(TIME_SCALE), COUNT_DOWN=COUNT_DOWN,
        INT_TO_FLOAT=INT_TO_FLOAT, WRAP_ANGLE=WRAP_ANGLE, QUAT_TO_MATRIX=QUAT_TO_MATRIX,
        MATRIX_MULTIPLY=MATRIX_MULTIPLY, CRATE_BREAK_FX=CRATE_BREAK_FX, SPAWN_BOLTS=SPAWN_BOLTS,
        BOLT_FLY=BOLT_FLY, BOX_WINDOW=BOX_WINDOW,
        STRAFE_LAST_STATE=STRAFE_LAST_STATE, JOINTS_HA=ha(JOINTS), JOINTS_LO=lo(JOINTS),
        STRAFE_REVERSE_FRAMES=STRAFE_REVERSE_FRAMES, BACK_SLOT=BACK_SLOT, BACK_TABLE_OFF=0x48 + 4 * BACK_SLOT,
        BACK_ANIM_HA=ha(back_anim), BACK_ANIM_LO=lo(back_anim), WALK_FACTOR_DONE=WALK_FACTOR_DONE,
        APPROACH_ANGLE=APPROACH_ANGLE, ANGLE_DIFF=ANGLE_DIFF, ANGLE_GAP=ANGLE_GAP,
        WALK_QUICK_SKIP=WALK_QUICK_SKIP, WALK_TURN_DONE=WALK_TURN_DONE, WALK_VEL_DONE=WALK_VEL_DONE,
        IDLE_ALIGN_BACK=IDLE_ALIGN_BACK, IDLE_TO_WALK=IDLE_TO_WALK, WALK_ALIGN_BACK=WALK_ALIGN_BACK, WALK_TO_IDLE=WALK_TO_IDLE,
        WALK_STAYS=WALK_STAYS, FLIP_TYPE_EXIT=FLIP_TYPE_EXIT, FLIP_TIME_TAIL=FLIP_TIME_TAIL,
        JUMP_CHOICE_FLIP=JUMP_CHOICE_FLIP, LEAN_EXIT=LEAN_EXIT, WALK_ANIM_RATE=WALK_ANIM_RATE,
        WALK_ANIM_EXIT=WALK_ANIM_EXIT, FLIP_AIR_DONE=FLIP_AIR_DONE,
        STICK_TARGET=STICK_TARGET, ROTATE_HERO=ROTATE_HERO, APPROACH=APPROACH, BUILD_VELOCITY=BUILD_VELOCITY,
        CAMERA_HA=ha(CAMERA), CAMERA_LO=lo(CAMERA), **camera,
        CAM_TURN_A=CAMERA_TURN_FIELDS[0], CAM_TURN_B=CAMERA_TURN_FIELDS[1], CAM_TURN_C=CAMERA_TURN_FIELDS[2],
        SOUND_HA=ha(SOUND_VADDR), SOUND_LO=lo(SOUND_VADDR), SOUND_BANK_OFF=SOUND_BANK_OFF, SOUND_LOOP_FLAGS=SOUND_LOOP_FLAGS,
        VOICES_HA=ha(VOICES), VOICES_LO=lo(VOICES),
        BANK_LOAD_FROM_MEM=BANK_LOAD_FROM_MEM, PLAY_SOUND_DEF=PLAY_SOUND_DEF, STOP_VOICE=STOP_VOICE,
        ITEM_GRINDBOOTS=ITEM_GRINDBOOTS, ITEM_NONE=ITEM_NONE, FOOT_REQUEST=FOOT_REQUEST, FOOT_SAVED=FOOT_SAVED,
        FOOT_CURRENT=FOOT_CURRENT, BOOT_CLASS=BOOT_CLASS, COPY=COPY, MODEL_FIXUP=MODEL_FIXUP,
        MAIN_HEAP_HA=ha(MAIN_HEAP), MAIN_HEAP_LO=lo(MAIN_HEAP), GFX_HEAP_HA=ha(GRAPHICS_HEAP), GFX_HEAP_LO=lo(GRAPHICS_HEAP),
        RESERVE_HI=BOOTS_RESERVE >> 16, GCM_HA=ha(GCM_PTR), GCM_LO=lo(GCM_PTR),
        CLASS_MAP_HA=ha(CLASS_SLOT_MAP), CLASS_MAP_LO=lo(CLASS_SLOT_MAP),
        MODEL_TABLE_HA=ha(MODEL_TABLE), MODEL_TABLE_LO=lo(MODEL_TABLE), LEVEL_HA=ha(LEVEL), LEVEL_LO=lo(LEVEL),
        BOOTS_HA=ha(BOOTS_VADDR), BOOTS_LO=lo(BOOTS_VADDR), **boots_fields,
        STATE_TYPE_GRIND=STATE_TYPE_GRIND, FOOT_REMEMBERED_HA=ha(FOOT_REMEMBERED), FOOT_REMEMBERED_LO=lo(FOOT_REMEMBERED),
        MODEL_SLOTS=MODEL_SLOTS, CHARGE_CLASS=CHARGE_CLASS, SPAWN=SPAWN, MENU_HA=ha(MENU), MENU_LO=lo(MENU),
        ITEM_TABLE_HA=ha(ITEM_TABLE), ITEM_TABLE_LO=lo(ITEM_TABLE), GRID_DRAW_ICON=GRID_DRAW_ICON,
        GRID_PRESS_DONE=GRID_PRESS_DONE, TEXT_LOOKUP=TEXT_LOOKUP, PLAY_MODEL_SOUND=PLAY_MODEL_SOUND,
        GRID_ENTRY_NEXT=GRID_ENTRY_NEXT, HUD_HA=ha(HUD), HUD_LO=lo(HUD), ICON_SPRITE=ICON_SPRITE, ICON_DRAW=ICON_DRAW,
        CHARGE_ICON=FOOT_ICONS[2], MENU_FRAME_CLASS=MENU_FRAME_CLASS, FOOT_BOX_ANIM_OFF=0x48 + 4 * FOOT_BOX_ANIM,
        FOOT_BOX_OLD_Y=FOOT_BOX_NARROW[0], FOOT_BOX_OLD_HALF=FOOT_BOX_NARROW[1],
        FOOT_BOX_NEW_Y=FOOT_BOX_WIDE[0], FOOT_BOX_NEW_HALF=FOOT_BOX_WIDE[1],
        HERO_SET_ANIM=HERO_SET_ANIM, ANIM_SLOT=ANIM_SLOT, ANIM_TABLE_OFF=0x48 + 4 * ANIM_SLOT,
        ANIM_HA=ha(ANIM_VADDR), ANIM_LO=lo(ANIM_VADDR),
        SPRING_STEP=SPRING_STEP,
        JOINT_POS=JOINT_POS, TRAIL=TRAIL, JOINT_A=TRAIL_JOINTS[0], JOINT_B=TRAIL_JOINTS[1],
        HERO_HA=ha(HERO), HERO_LO=lo(HERO), RESULTS_HA=ha(RESULTS), RESULTS_LO=lo(RESULTS),
        STATE_HA=ha(STATE), STATE_LO=lo(STATE), PAD_HA=ha(PAD), PAD_LO=lo(PAD),
        CHARGE_BUTTON=CHARGE_BUTTON, BUTTON_MASK=~CHARGE_BUTTON, TAP_WINDOW=TAP_WINDOW,
        MIN_FRAMES=MIN_FRAMES, BURST_FRAMES=BURST_FRAMES,
        VEC_LENGTH=VEC_LENGTH, WALL_PROBE=WALL_PROBE, CHOOSER=CHOOSER, SURFACE=SURFACE, TRANS_EXIT=TRANS_EXIT,
        STATE_BUMP=STATE_BUMP, STATE_CRANK=STATE_CRANK, CRANK_PUSH_ANIM=CRANK_PUSH_ANIM, CRANK_ANIM_DONE=CRANK_ANIM_DONE, SKID_LOCK=SKID_LOCK, SKID_ANIM=SKID_ANIM, NO_GROUND_HI=NO_GROUND >> 16,
        STATE_IDLE=STATE_IDLE, STATE_WALK=STATE_WALK, STATE_SKID=STATE_SKID, STATE_CROUCH=STATE_CROUCH,
        HERO_CLANK=HERO_CLANK, STATE_CLANK_IDLE=STATE_CLANK_IDLE, STATE_CLANK_WALK=STATE_CLANK_WALK,
        CLANK_BUTTON=CLANK_BUTTON, CLANK_JUMP_BUTTON=CLANK_JUMP_BUTTON,
        THRUSTER_CLASS=THRUSTER_CLASS, CLANK_WINGS_ANIM=CLANK_WINGS_ANIM, MOBY_SET_ANIM=MOBY_SET_ANIM,
        MOBY_DELETE=MOBY_DELETE, MOBY_MOVED=MOBY_MOVED, JET_SPAWN=JET_SPAWN, JET_EMIT=JET_EMIT,
        JET_DRAW_HA=ha(JET_DRAW), JET_DRAW_LO=lo(JET_DRAW), DRAW_REGISTER=DRAW_REGISTER, JET_OFF_STATE=JET_OFF_STATE,
        STATE_CLANK_FALL=STATE_CLANK_FALL, CLANK_DASH_ANIM=CLANK_DASH_ANIM,
        STATE_TYPE_JUMP=STATE_TYPE_JUMP, CAMERA_JUMP=CAMERA_JUMP, CLANK_BUMP_ANIM=CLANK_BUMP_ANIM, CLANK_BUMP_ANIM_FLAGS=CLANK_BUMP_ANIM_FLAGS,
        CLANK_BUMP_FRAMES=CLANK_BUMP_FRAMES, CLANK_BUMP_MAX_FRAMES=CLANK_BUMP_MAX_FRAMES,
        THRUST_DELAY=THRUST_DELAY, THRUST_SWEEP_FROM=THRUST_SWEEP_FROM, COS=COS, SIN=SIN,
        CLANK_PITCH_FRAMES=CLANK_PITCH_FRAMES, THRUSTER_SOUND=THRUSTER_SOUND, THRUSTER_SOUND_OFF=32 * THRUSTER_SOUND,
        CLANK_DASH_MIN_FRAMES=CLANK_DASH_MIN_FRAMES, CLANK_SPHERE_HI=CLANK_SPHERE_HEIGHT >> 16, CLANK_SPHERE_LO=CLANK_SPHERE_HEIGHT & 0xFFFF, CLANK_DASH_MAX_FRAMES=CLANK_DASH_MAX_FRAMES,
        SKIP_EXPLOSIVE=SKIP_EXPLOSIVE.format(EXPLOSIVE_CRATE=EXPLOSIVE_CRATE) if args.keep_explosive else "",
        **offsets)


def assemble(parts, fields):
    """Assemble the parts for the cave. Returns the source as assembled, the code and the pool address."""
    ks = keystone.Ks(keystone.KS_ARCH_PPC, keystone.KS_MODE_PPC64 | keystone.KS_MODE_BIG_ENDIAN)

    # Branches out of the cave are encoded here, not by keystone: it produced wrong targets for
    # absolute branches once the blob grew. They are assembled as marker words and patched.
    externals = {}

    def external(match):
        externals[len(externals)] = (match.group(1), int(match.group(2)))
        return f".long {0xDEAD0000 + len(externals) - 1:#x}"

    def run(pool_addr):
        externals.clear()
        text = "\n".join(line.split("#")[0] for part in parts
                         for line in part.format(POOL_HA=ha(pool_addr), POOL_LO=lo(pool_addr), **fields).splitlines())
        text = re.sub(r"^\s*(bl?)\s+(\d+)\s*$", external, text, flags=re.M)
        code = bytearray(ks.asm(text, CAVE_START)[0])
        for off in range(0, len(code), 4):
            word = struct.unpack_from(">I", code, off)[0]
            if word >> 16 == 0xDEAD:
                kind, target = externals[word & 0xFFFF]
                struct.pack_into(">I", code, off, 0x48000000 | (kind == "bl") | ((target - (CAVE_START + off)) & 0x03FFFFFC))
        return text, bytes(code)

    # The pool follows the code; the code size does not depend on the pool address.
    _, code = run(CAVE_START)
    pool_addr = CAVE_START + len(code)
    text, code = run(pool_addr)

    # Every branch must land inside the cave or on a game function named in this file.
    allowed = {v for k, v in globals().items() if k.isupper() and isinstance(v, int)}
    for insn in capstone.Cs(capstone.CS_ARCH_PPC, capstone.CS_MODE_64 | capstone.CS_MODE_BIG_ENDIAN).disasm(code, CAVE_START):
        if insn.mnemonic.startswith("b") and insn.op_str and insn.op_str.split()[-1].startswith("0x"):
            target = int(insn.op_str.split()[-1], 16)
            if not (CAVE_START <= target < pool_addr or target in allowed):
                sys.exit(f"bad branch at {insn.address:#x}: {insn.mnemonic} {insn.op_str}")
    return text, code, pool_addr


def label_address(text, label):
    """keystone has no symbol output; every statement is one 4-byte word."""
    head = text[:text.index("\n" + label + ":")]
    return CAVE_START + 4 * sum(1 for line in head.splitlines() if line.strip() and not line.strip().endswith(":"))


def patch(elf, payload, segments):
    """A copy of the ELF with the cave filled, the state block reserved and the extra segments
    (program header index, address, data) appended."""
    out = bytearray(elf.data)
    phoff = struct.unpack_from(">Q", out, 0x20)[0]
    p_off, p_va, _, p_fsz, p_msz = struct.unpack_from(">QQQQQ", out, phoff + 8)
    new_size = SEG_END - p_va
    if p_va + p_fsz > CAVE_START or any(out[p_off + p_fsz:p_off + new_size]):
        sys.exit("segment padding is not free")
    if CAVE_START + len(payload) > SEG_END:
        sys.exit("payload does not fit")
    struct.pack_into(">QQ", out, phoff + 32, new_size, new_size)   # grow the R+X segment over the caves
    cave_off = p_off + (CAVE_START - p_va)
    out[cave_off:cave_off + len(payload)] = payload

    rw = phoff + 56                                                # grow the RW segment's bss over STATE
    rw_va, rw_msz = struct.unpack_from(">Q", out, rw + 16)[0], struct.unpack_from(">Q", out, rw + 40)[0]
    if rw_va + rw_msz > STATE:
        sys.exit("state block overlaps existing bss")
    struct.pack_into(">Q", out, rw + 40, STATE_END - rw_va)

    for index, vaddr, blob in segments:                            # mapped through unused PT_LOAD entries
        ph = phoff + 56 * index
        p_type, _, _, _, _, s_fsz, s_msz, align = struct.unpack_from(">IIQQQQQQ", out, ph)
        if p_type != 1 or s_fsz or s_msz:
            sys.exit(f"program header {index} is not a free PT_LOAD")
        out.extend(bytes(-len(out) % align))
        if len(out) % align != vaddr % align or vaddr < STATE_END:
            sys.exit("extra segment placement is invalid")
        struct.pack_into(">QQQQQ", out, ph + 8, len(out), vaddr, vaddr, len(blob), len(blob))
        out.extend(blob)
    return out


def export_patch(original, patched, path):
    """The difference between the two executables in patch.py's format: the bytes that changed
    (runs closer than 16 bytes are joined) and everything behind the original's end.

    File: b"BBRC1\x01", then zlib data: md5 of the original and of the result (16 bytes each),
    their sizes (u64 each), the number of records (u32), and per record offset (u64), length
    (u32) and the new bytes. All big-endian.
    """
    import zlib
    records, shared, pos = [], min(len(original), len(patched)), 0
    while pos < shared:
        end = min(pos + 4096, shared)
        if original[pos:end] == patched[pos:end]:
            pos = end
            continue
        while pos < end and original[pos] == patched[pos]:
            pos += 1
        if pos == end:
            continue
        stop = same = pos
        while stop < shared and same - stop < 16:                # a run ends at 16 equal bytes
            if original[same] != patched[same]:
                stop = same + 1
            same += 1
            if same >= shared:
                break
        if records and pos - (records[-1][0] + len(records[-1][1])) < 16:
            start = records.pop()[0]
        else:
            start = pos
        records.append((start, bytes(patched[start:stop])))
        pos = stop
    if len(patched) > shared:
        records.append((shared, bytes(patched[shared:])))
    body = hashlib.md5(original).digest() + hashlib.md5(patched).digest()
    body += struct.pack(">QQI", len(original), len(patched), len(records))
    for offset, data in records:
        body += struct.pack(">QI", offset, len(data)) + data
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"BBRC1\x01" + zlib.compress(body, 9))
    print(f"exported {len(records)} changes ({sum(len(d) for _, d in records)} bytes) to {path}")


def install(path):
    """Put the build where RPCS3 boots it, keeping the file found there the first time."""
    if not os.path.isdir(os.path.dirname(RPCS3_EBOOT)):
        sys.exit(f"cannot install: {os.path.dirname(RPCS3_EBOOT)} does not exist (set RPCS3_EBOOT)")
    backup = RPCS3_EBOOT + ".bak"
    if os.path.exists(RPCS3_EBOOT) and not os.path.exists(backup):
        shutil.copyfile(RPCS3_EBOOT, backup)
        print(f"kept the previous file as {backup}")
    shutil.copyfile(path, RPCS3_EBOOT)
    print(f"installed to {RPCS3_EBOOT}; close and restart RPCS3 to run it")


def main():
    args = parse_args()
    elf = Elf(args.src)
    if hashlib.md5(elf.data).hexdigest() != ORIG_MD5:
        sys.exit(f"{args.src}: not the expected NPEA00385 RC1 ELF (md5 mismatch)")
    charge = not args.no_charge_boots
    hooks = hook_table(charge, not args.rc1_acceleration)
    for va, (_, old) in hooks.items():
        if elf.u32(va) not in (old, bl(va, old)):
            sys.exit(f"unexpected instruction at hook site {va:#x}")

    pool, offsets, camera = constant_pool(args)
    boots_blob, boots_fields = boots_data()
    parts = [SWEEP, STRIKE, BOX, STRAFE] + ([BOOTS, BOOTS_MENU, FRAME, GATES, UPDATE, CLANK] if charge else [])
    anim_blob, back_anim = animations()
    text, code, pool_addr = assemble(parts, template_fields(args, offsets, camera, boots_fields, back_anim))

    segments, words = [(ANIM_PHDR, ANIM_VADDR, anim_blob)], {}     # words: data address -> (old, new)
    if not args.rc1_acceleration:
        for offset, rc1, rc2 in (GROUND_ACCEL, GROUND_DECEL):
            words[HERO_TABLE + offset] = tuple(struct.unpack(">I", struct.pack(">f", v))[0] for v in (rc1, rc2))
    if charge:
        words[FOOT_GRID + 0x44] = (2, boots_fields["FOOT_COLUMNS"])
        words[FOOT_GRID + 0x48] = (FOOT_GRID_TABLE, boots_fields["FOOT_TABLE"])
        sound = SOUND_DEFS[0] + SOUND_DEFS[1] + charge_sound_bank()
        segments += [(SOUND_PHDR, SOUND_VADDR, sound), (BOOTS_PHDR, BOOTS_VADDR, boots_blob)]
    out = patch(elf, code + pool, segments)
    for va, (old, new) in words.items():
        if elf.u32(va) != old:
            sys.exit(f"unexpected data at {va:#x}")
        struct.pack_into(">I", out, elf.off(va), new)
    for va, (label, _) in sorted(hooks.items()):
        target = label_address(text, label)
        struct.pack_into(">I", out, elf.off(va), bl(va, target))
        print(f"hook {va:#x} -> {label} at {target:#x}")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "wb") as f:
        f.write(out)
    print(f"code {len(code)} bytes at {CAVE_START:#x}, constants at {pool_addr:#x}; box breaker radius {args.radius:g}"
          + (f"; charge {args.burst_speed:g} then {args.cruise_speed:g} units/s" if charge else ""))
    print(f"wrote {args.out}")
    if args.export:
        export_patch(elf.data, out, args.export)
    if args.install:
        install(args.out)
    return args.out, len(code)


if __name__ == "__main__":
    path, size = main()
    if os.environ.get("SHOW"):
        show(Elf(path), CAVE_START, CAVE_START + size)
