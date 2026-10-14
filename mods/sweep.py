"""The crate sweep: damage every crate in a sphere, as the game's own crate-only sweeps do.

Not a mod of its own: a shared routine for the mods that break crates (USES = (sweep,) there;
their assembly calls it with bl {CRATE_SWEEP}).
"""
from .game import *  # noqa: F401,F403

NAME = "sweep"
TITLE = "Crate sweep (shared by the mods that break crates)"
EXPORTS = {"CRATE_SWEEP": "crate_sweep"}      # template field for the mods -> label

EXPLOSIVE_CRATE = 0x1F5

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


def options(ap):
    ap.add_argument("--keep-explosive", action="store_true", help="leave explosive crates alone")


def pool(args):
    return dict(ONE=1.0, SEVEN=7.0)


def parts(args):
    return [SWEEP]


def fields(args, addr):
    return dict(SKIP_EXPLOSIVE=SKIP_EXPLOSIVE.format(EXPLOSIVE_CRATE=EXPLOSIVE_CRATE) if args.keep_explosive else "")
