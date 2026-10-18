"""Clank's thruster dash (not in the games).

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
RC1 has no state for it, so it runs in place of hero_update with the state left as it is, and
that state's transitions are skipped meanwhile, so X does not jump.
The pack's two jets burn meanwhile: the game's own jet mobys, driven from here, and Ratchet's
Thruster-Pack sound plays when it starts.
"""
from . import sweep
from .game import *  # noqa: F401,F403

NAME = "clank"
TITLE = "Clank's thruster dash"
ABOUT = "As Clank, hold R1, push the stick and press X: he makes Ratchet's Thruster-Pack long jump, wings and jets out, breaking crates and bouncing off walls."
USES = (sweep,)

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

# Clank's dash. clank_tick runs in front of hero_main: it keeps the frame counter and starts a
# dash. clank_update runs in place of hero_update while the counter runs.
CLANK = """
clank_tick:                         # replaces bl HERO_MAIN; r31 = state block, r30 = hero in all of this part
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
clank_tick_next:
    {CHAIN}

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
    lis 4, {CLASS_SLOT_MAP_HA}           # Ratchet's model: class 0
    lbz 4, {CLASS_SLOT_MAP_LO}(4)
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

clank_update_next:
    {CHAIN}
clank_update:                       # replaces bl HERO_UPDATE
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x90(11)
    cmpwi 12, 0
    ble clank_update_next
    lis 10, {HERO_HA}
    addi 10, 10, {HERO_LO}
    lwz 12, 0x2084(10)
    cmpwi 12, {STATE_CLANK_IDLE}
    beq cl_run
    cmpwi 12, {STATE_CLANK_WALK}
    bne clank_update_next
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
    bl {CRATE_SWEEP}
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

# The hook sites the dash shares with other mods (see Hook in game.py).
# clank_chooser: replaces bl CHOOSER. No weapons or gadgets during a dash.
# clank_trans: replaces the load of the state in front of the transition switch. During a dash
#   none of his idle/walk transitions (jump, punch, fall) run.
# clank_surface: replaces bl SURFACE, the call behind hero_main: his wings follow him once
#   hero_main has moved him.
CLANK_GATES = """
clank_chooser:
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x90(11)
    cmpwi 12, 0
    ble clank_chooser_next
    li 3, 0
    blr
clank_chooser_next:
    {CHAIN}

clank_trans:
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x90(11)
    cmpwi 12, 0
    ble clank_trans_next
    lwz 3, 0x2084(19)
    cmpwi 3, {STATE_CLANK_IDLE}
    beq clank_trans_skip
    cmpwi 3, {STATE_CLANK_WALK}
    bne clank_trans_next
clank_trans_skip:
    b {TRANS_EXIT}
clank_trans_next:
    {CHAIN}

clank_surface:
    lis 11, {STATE_HA}
    addi 11, 11, {STATE_LO}
    lwz 12, 0x9c(11)
    cmpwi 12, 0
    beq clank_surface_next
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    bl clank_wings
    bl clank_jets
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
clank_surface_next:
    {CHAIN}
"""


def hooks(args):
    return [*(Hook(site, "clank_tick", HERO_MAIN, chain=True) for site in FRAME_HOOKS),
            *(Hook(site, "clank_surface", SURFACE, chain=True) for site in SURFACE_HOOKS),
            Hook(UPDATE_HOOK, "clank_update", HERO_UPDATE, chain=True),
            Hook(CHOOSER_HOOK, "clank_chooser", CHOOSER, chain=True),
            Hook(TRANS_HOOK, "clank_trans", TRANS_HOOK_WORD, chain=True)]


def pool(args):
    return dict(
        ZERO=0.0, ONE=1.0, HALF=0.5, BIG=99999.0, CLANK_LAND=CLANK_LAND_HEIGHT, CLANK_NO_GROUND=CLANK_LAND_NO_GROUND,
        CLANK_STICK=CLANK_DASH_STICK, CLANK_SPEED=THRUST_SPEED / 60, CLANK_ACCEL=THRUST_ACCEL / 3600,
        CLANK_LIFT=(2 * THRUST_HEIGHT * THRUST_GRAVITY) ** 0.5 / 60, CLANK_GRAVITY=THRUST_GRAVITY / 3600,
        SWEEP_AHEAD=THRUST_SWEEP_AHEAD, SWEEP_UP=THRUST_SWEEP_UP, SWEEP_RADIUS=THRUST_SWEEP_RADIUS,
        CLANK_BUMP_BLEND=CLANK_BUMP_ANIM_BLEND, BUMP_SPEED=BUMP_SPEED / 60, BUMP_DECEL=BUMP_DECEL / 3600,
        BUMP_GRAVITY=CLANK_BUMP_GRAVITY / 3600, CAMERA_BUMP_SQ=CLANK_CAMERA_BUMP ** 2, CLANK_RUN=CLANK_RUN_SPEED / 60,
        CLANK_PITCH=CLANK_PITCH, CLANK_PITCH_STEP=CLANK_PITCH / CLANK_PITCH_FRAMES, CLANK_ANIM_BLEND=CLANK_DASH_ANIM_BLEND,
        CLANK_WINGS_AT=CLANK_WINGS_OFFSET, JET_VALUES=JET_VALUES)


def parts(args):
    return [CLANK, CLANK_GATES]


def fields(args, addr):
    return dict(CLANK_SPHERE_HI=CLANK_SPHERE_HEIGHT >> 16, CLANK_SPHERE_LO=CLANK_SPHERE_HEIGHT & 0xFFFF,
                THRUSTER_SOUND_OFF=32 * THRUSTER_SOUND)
