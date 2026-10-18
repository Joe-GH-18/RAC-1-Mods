"""The charge itself: RC2's trigger, transitions, speeds, hover, steering, camera, animation,
sounds and foot trails, run in place of RC1's idle and walk states while it lasts."""
from ..game import *  # noqa: F401,F403

# Skid state transitions (RC1 0xc13dc, RC2 0x84e270): with the stick past 0.2 the skid goes on
# to idle or walk. RC2 first tests the lock timer +0x1e0 there (0x84e3d8) and stays in the skid
# while it runs; RC1's block has no such test. SKID_HOOK is the first instruction after RC1's
# stick test.
SKID_HOOK = 0xC14F0                # li r3, 0
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
# writable segment, with the two definitions, already carrying the mapped indices, in front
# (rc2data.charge_sounds, taken from the player's RC2).
# RC2 0x82e9f4 starts the loop again whenever its voice has ended or been taken over.
SOUND_LOOP_FLAGS = 4
SOUND_BANK_OFF = 0x40          # bank offset inside the segment; must be 16-byte aligned
BANK_LOAD_FROM_MEM = 0x60AE8C  # (r3 bank image) -> handle, 0 on failure
STOP_VOICE = 0x15CDB0          # (r3 voice slot)

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
GATES_A = """
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
"""

GATES_B = """
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
