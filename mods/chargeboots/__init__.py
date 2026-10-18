"""Charge Boots: RC2's charge dash, and a boost at the bolt cranks.

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
The charge animation is RC2's own (Ratchet animation 139), and so are RC2's charge loop and end
sounds (a cut-down copy of one RC2 level sound bank); both are taken from the player's RC2
(rc2data.py) and embedded in the ELF.
The Charge Boots are an entry of their own under Foot Items on the pause menu's Gadgets page,
owned from the start and put on by default. The confirm button there takes them off and puts
them on again, as it does with the Magneboots and Grindboots. While they are on, Ratchet wears
RC2's Charge Boots model (class 0xe70 with its texture, also from the player's RC2) through RC1's foot slot
whenever the game does not want other boots there; taken off, there is no charge and no boost
at the bolt crank. The Grindboots keep their own model.
RC2's camera tuning for the charge is written to RC1's camera config struct.

Bolt crank boost (not in RC2)
-----------------------------
Double-tapping and holding R1 while Ratchet turns a bolt crank (hero state 0x3b, driven by the
crank's own update 0x32adf8) raises the crank's speed cap from 3.7 to 30 units/s (the charge's
burst speed), with the charge animation, sound and foot trails. Position and facing follow the
circle at once there.

The files: charge.py (the charge), crank.py (the bolt crank boost), boots.py (the boots model on
his feet), menu.py (the menu item), art/ (its icon, drawn by tools/icon.py). This file has the
mod's interface for build.py; the routines are assembled in the order of parts().
"""
import struct

from .. import sweep
from ..game import *  # noqa: F401,F403
from ..rc2 import Extract
from .charge import *  # noqa: F401,F403
from .crank import *  # noqa: F401,F403
from .menu import *  # noqa: F401,F403
from .boots import *  # noqa: F401,F403

NAME = "chargeboots"
TITLE = "Charge Boots"
ABOUT = ("Tap R1 twice and hold it: RC2's charge dash, with its animation, sounds and boots model, as an item under "
         "Foot Items on the pause menu. At a bolt crank the same turns the crank at the speed of a charge.")
USES = (sweep,)


def options(ap):
    ap.add_argument("--burst-speed", type=float, default=30.0, help="units/s for the first second of a charge (RC2: 30)")
    ap.add_argument("--cruise-speed", type=float, default=11.5, help="units/s after that (RC2: 11.5)")
    ap.add_argument("--crank-speed", type=float, default=CRANK_SPEED, help="units/s at a boosted bolt crank (the game's own: 3.7)")


def hooks(args):
    return [
        *(Hook(site, "frame", HERO_MAIN, chain=True) for site in FRAME_HOOKS),
        *(Hook(site, "surface", SURFACE, chain=True) for site in SURFACE_HOOKS),
        Hook(UPDATE_HOOK, "update", HERO_UPDATE, chain=True), Hook(CHOOSER_HOOK, "chooser", CHOOSER, chain=True),
        Hook(TRANS_HOOK, "trans", TRANS_HOOK_WORD, chain=True), Hook(SKID_HOOK, "skid", SKID_HOOK_WORD),
        Hook(CRANK_HOOK, "crank", CRANK_HOOK_WORD), Hook(CRANK_ANIM_HOOK, "crank_anim", CRANK_ANIM_HOOK_WORD),
        Hook(CRANK_PULL_HOOK, "crank_pull", CRANK_PULL_HOOK_WORD), Hook(CRANK_TURN_HOOK, "crank_turn", CRANK_TURN_HOOK_WORD),
        *(Hook(site, "boots_spawn", SPAWN) for site in FOOT_SPAWN_HOOKS),
        Hook(GRID_ENTRY_HOOK, "grid_entry", GRID_ENTRY_HOOK_WORD), Hook(GRID_SELECTED_HOOK, "grid_selected", GRID_SELECTED_HOOK_WORD),
        Hook(GRID_PRESS_HOOK, "grid_press", GRID_PRESS_HOOK_WORD), Hook(GRID_WORN_HOOK, "grid_worn", GRID_WORN_HOOK_WORD),
        Hook(GRID_EQUIP_HOOK, "grid_equip", GRID_EQUIP_HOOK_WORD), Hook(TEXT_HOOK, "menu_text", TEXT_LOOKUP),
        Hook(PREVIEW_CLASS_HOOK, "preview_class", PREVIEW_CLASS_HOOK_WORD), Hook(PREVIEW_SPAWN_HOOK, "preview_spawn", SPAWN)]


def words(args, addr):
    """The Foot Items grid: three columns, from the embedded table."""
    boots = boots_data(addr["boots"])[1]
    return {FOOT_GRID + 0x44: (struct.pack(">I", 2), struct.pack(">I", boots["FOOT_COLUMNS"])),
            FOOT_GRID + 0x48: (struct.pack(">I", FOOT_GRID_TABLE), struct.pack(">I", boots["FOOT_TABLE"]))}


def data(args):
    return [("ro", "anim", lambda vaddr: [Extract("animation", RC2_CHARGE_ANIM, vaddr)]),
            ("rw", "sound", lambda vaddr: [Extract("charge_sounds")]),
            ("rw2", "boots", lambda vaddr: boots_data(vaddr)[0])]


def pool(args):
    return dict(
        ZERO=0.0, ONE=1.0, HALF=0.5, BIG=99999.0,
        BURST=args.burst_speed / 60, CRUISE=args.cruise_speed / 60,       # speeds are per frame
        ACCEL=ACCEL / 3600, DECEL=DECEL / 3600, TURN=TURN_RATE / 60, BURST_TURN=BURST_TURN_SCALE,
        STEER_SMOOTH=STEER_SMOOTH, DEADZONE=STEER_DEADZONE, AHEAD=DASH_SWEEP_AHEAD, DASH_RADIUS=DASH_SWEEP_RADIUS,
        ANIM_BLEND=ANIM_BLEND, HOVER=HOVER_HEIGHT, HOVER_K=HOVER_STIFFNESS, HOVER_D=HOVER_DAMPING,
        HOVER_MAX=HOVER_MAX_SPEED, HOVER_SNAP=HOVER_MAX_SPEED * HOVER_SNAP, SKID_BLEND=SKID_ANIM_BLEND,
        BUMP_RATIO=BUMP_RATIO, PROBE_HEIGHT=PROBE_HEIGHT, PROBE_REACH=PROBE_REACH, GROUNDED=GROUNDED_HEIGHT,
        CRANK_MAX=args.crank_speed / 60, CRANK_ACCEL=CRANK_ACCEL / 3600, CRANK_BLEND=CRANK_ANIM_BLEND,
        CAM_GAIN=CAMERA_TURN_GAIN, CAM_LIMIT=CAMERA_TURN_LIMIT, **{f"CAM_{off:X}": value for off, value in CAMERA_FIELDS},
        TRAIL_VEC=TRAIL_VEC, TRAIL_A=TRAIL_DESCRIPTORS[0], TRAIL_B=TRAIL_DESCRIPTORS[1])


def parts(args):
    # (the order is that of the code in the game; the pieces of a file are not kept together)
    return [BOOTS_A, FOOT_BOX, BOOTS_B, BOOTS_MENU, FRAME, GATES_A, CRANK, GATES_B, UPDATE]


def fields(args, addr):
    return dict(
        **pair("ANIM", addr["anim"]), **pair("SOUND", addr["sound"]), **pair("BOOTS", addr["boots"]),
        **boots_data(addr["boots"])[1],
        ANIM_TABLE_OFF=0x48 + 4 * ANIM_SLOT, BUTTON_MASK=~CHARGE_BUTTON, NO_GROUND_HI=NO_GROUND >> 16,
        CAM_TURN_A=CAMERA_TURN_FIELDS[0], CAM_TURN_B=CAMERA_TURN_FIELDS[1], CAM_TURN_C=CAMERA_TURN_FIELDS[2],
        JOINT_A=TRAIL_JOINTS[0], JOINT_B=TRAIL_JOINTS[1], RESERVE_HI=BOOTS_RESERVE >> 16, CHARGE_ICON=FOOT_ICONS[2],
        FOOT_BOX_ANIM_OFF=0x48 + 4 * FOOT_BOX_ANIM, FOOT_BOX_OLD_Y=FOOT_BOX_NARROW[0], FOOT_BOX_OLD_HALF=FOOT_BOX_NARROW[1],
        FOOT_BOX_NEW_Y=FOOT_BOX_WIDE[0], FOOT_BOX_NEW_HALF=FOOT_BOX_WIDE[1])
