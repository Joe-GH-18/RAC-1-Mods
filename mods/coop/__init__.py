"""Co-op Clank: Player 2 is Clank (docs/coop-clank-spec.md).

Plug in a second controller and Clank leaves Ratchet's back as Player 2. pad.py reads Player 2's
controller, flight.py runs the modes and his flight every frame before the hero, body.py makes
and shows his body, hud.py places what is placed late. Nothing is shared with Golden Clank but
the words STATE + COOP_* (mods/game.py), which it reads.

The mod's block (COOP, writable data behind the tag layout.TAG, for tools/peek.py; tools/coop.py
finds it and names its fields) is laid out in layout.py: runtime words, then the values to tune.
"""
import struct

from ..game import *  # noqa: F401,F403
from ..rc2 import Extract
from .. import sweep
from . import body, combat, flight, fx, hud, layout, pad

# The parts' game addresses and numbers, as the module's own (build.py lets branches go to those).
globals().update({name: value for part in (pad, body, flight, combat, fx) for name, value in vars(part).items()
                  if name.isupper() and isinstance(value, int)})

NAME = "coop"
TITLE = "Co-op Clank"
USES = (sweep,)
ABOUT = ("Plug in a second controller: Clank jumps off Ratchet's back and is Player 2. He flies, "
         "zaps, dive-punches and docks back on.")


def model_data():
    args = (body.CLANK_LEVEL, body.CLANK_CLASS)
    return Extract("level_model", *args), Extract("level_textures", *args), Extract("level_pixels", *args)


def reserve(size):
    """Heap memory for size bytes, in the 64 KB steps addis takes."""
    return (size + 0xFFFF) >> 16


def hooks(args):
    return [Hook(pad.PAD_READ_HOOK, "coop_pad", pad.PAD_READ_HOOK_WORD),
            *(Hook(site, "coop_frame", HERO_MAIN, chain=True) for site in FRAME_HOOKS),
            Hook(HUD_HOOK, "coop_hud", HUD_HOOK_WORD, chain=True)]


def data(args):
    model, textures, pixels = model_data()
    return [("rw", "coop", lambda vaddr: [layout.TAG + layout.block()]),
            ("rw2", "clank_model", lambda vaddr: [model]), ("rw2", "clank_textures", lambda vaddr: [textures]),
            ("rw2", "clank_pixels", lambda vaddr: [pixels])]


def pool(args):
    return dict(JET_VALUES=body.JET_VALUES)


def parts(args):
    return [pad.CODE, flight.CODE, body.CODE, combat.CODE, fx.CODE, hud.CODE]


def fields(args, addr):
    model, textures, pixels = model_data()
    entries = (len(textures) - 8) // 0x24
    assert len(model) % 0x10 == 0
    skip = 31 - (body.SKIP_UPDATE.bit_length() - 1)
    constants = {name: value for module in (pad, body, flight, combat, fx) for name, value in vars(module).items()
                 if name.isupper() and isinstance(value, int)}
    return dict(**constants, **layout.fields(), **pair("COOP", addr["coop"] + len(layout.TAG)),
                **pair("CLANK_MODEL", addr["clank_model"]), **pair("CLANK_TEXTURES", addr["clank_textures"]),
                **pair("CLANK_PIXELS", addr["clank_pixels"]),
                **{f"{name}_HA": ha(value) for name, value in constants.items()},
                **{f"{name}_LO": lo(value) for name, value in constants.items()},
                MODEL_SIZE_HI=len(model) >> 16, MODEL_SIZE_LO=len(model) & 0xFFFF,
                PIXELS_SIZE_HI=len(pixels) >> 16, PIXELS_SIZE_LO=len(pixels) & 0xFFFF,
                ENTRY_COUNT=entries, ENTRIES_SIZE=entries * 0x24,
                MODEL_RESERVE_HI=reserve(len(model) + entries * 0x24), PIXELS_RESERVE_HI=reserve(len(pixels)),
                NOT_SKIP_MB=(skip + 1) % 32, NOT_SKIP_ME=(skip - 1) % 32)
