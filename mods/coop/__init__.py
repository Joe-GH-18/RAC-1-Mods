"""Co-op Clank: Player 2 is Clank (docs/coop-clank-spec.md).

Plug in a second controller and Clank leaves Ratchet's back as Player 2. pad.py reads Player 2's
controller, flight.py runs the modes and his flight every frame before the hero, body.py makes
and shows his body, hud.py places what is placed late, camera.py keeps both players in the picture,
menu.py is the Clank Zapper on the pause menu (AI Clank), preview.py his zapping preview there. Nothing is shared with Golden Clank but
the words STATE + COOP_* (mods/game.py), which it reads.

The mod's block (COOP, writable data behind the tag layout.TAG, for tools/peek.py; tools/coop.py
finds it and names its fields) is laid out in layout.py: runtime words, then the values to tune.
"""
import struct

from ..game import *  # noqa: F401,F403
from ..rc2 import Extract
from .. import sweep
from . import ai, body, camera, combat, flight, fx, hud, layout, menu, mini, pad, preview

# The parts' game addresses and numbers, as the module's own (build.py lets branches go to those).
globals().update({name: value for part in (pad, body, flight, combat, fx, hud, mini, ai, menu, camera, preview) for name, value in vars(part).items()
                  if name.isupper() and isinstance(value, int)})

NAME = "coop"
TITLE = "Co-op Clank"
USES = (sweep,)
ABOUT = ("Plug in a second controller: Clank jumps off Ratchet's back and is Player 2. He flies, "
         "zaps, rams, ground-pounds and docks back on. Alone, the Clank Zapper on the pause menu "
         "makes him fight by himself.")


def model_data():
    args = (body.CLANK_LEVEL, body.CLANK_CLASS)
    return Extract("level_model", *args), Extract("level_textures", *args), Extract("level_pixels", *args)


def pixel_pieces():
    """Clank's pixels, then (0x80-aligned) the Clank Zapper's two menu icons (menu.py): they go into
    the graphics heap together (coop_install); -> the pieces, the icons' offset from the first pixel."""
    pixels = model_data()[2]
    pad = bytes(-len(pixels) % 0x80)
    return [pixels, pad, *menu.icon_pixels()], len(pixels) + len(pad)


def reserve(size):
    """Heap memory for size bytes, in the 64 KB steps addis takes."""
    return (size + 0xFFFF) >> 16


def hooks(args):
    return [Hook(pad.PAD_READ_HOOK, "coop_pad", pad.PAD_READ_HOOK_WORD),
            *(Hook(site, "coop_frame", HERO_MAIN, chain=True) for site in FRAME_HOOKS),
            Hook(HUD_HOOK, "coop_hud", HUD_HOOK_WORD, chain=True),
            Hook(flight.PACK_HOOK, "coop_pack", flight.PACK_HOOK_WORD),
            Hook(body.GRID_SEARCH_HOOK, "coop_grid_search", body.GRID_SEARCH_HOOK_WORD, jump=True),
            Hook(hud.HUD_DRAW_HOOK, "coop_hud_draw", hud.HUD_DRAW_HOOK_WORD),
            Hook(menu.GRID_ENTRY_HOOK, "coop_grid_entry", menu.GRID_ENTRY_HOOK_WORD, chain=True),
            Hook(menu.GRID_PRESS_HOOK, "coop_grid_press", menu.GRID_PRESS_HOOK_WORD, chain=True),
            Hook(menu.TEXT_HOOK, "coop_menu_text", TEXT_LOOKUP, chain=True),
            Hook(menu.TEXT_OWNED_HOOK, "coop_text_owned", menu.TEXT_OWNED_HOOK_WORD),
            Hook(preview.MENU_PANELS_HOOK, "coop_preview_panels_drawn", preview.MENU_STUB_A),
            Hook(preview.MENU_DRAWN_HOOK, "coop_preview_menu_drawn", preview.MENU_STUB_B)]


def words(args, addr):
    """The Back Packs grid: four columns, from the embedded table with the Clank Zapper."""
    return {menu.PACK_GRID + 0x44: (struct.pack(">I", 3), struct.pack(">I", 4)),
            menu.PACK_GRID + 0x48: (struct.pack(">I", menu.PACK_GRID_TABLE), struct.pack(">I", addr["zapper"]))}


def data(args):
    model, textures, pixels = model_data()
    return [("rw", "coop", lambda vaddr: [layout.TAG + layout.block()]),
            ("rw2", "clank_model", lambda vaddr: [model]), ("rw2", "clank_textures", lambda vaddr: [textures]),
            ("rw2", "clank_pixels", lambda vaddr: pixel_pieces()[0]),
            ("rw", "zapper", lambda vaddr: [menu.menu_data()[0]]),
            ("rw2", "rider_anim", lambda vaddr: [Extract("level_animation", mini.RIDER_ANIM_LEVEL, mini.RIDER_ANIM_SLOT, vaddr)]),
            *(("rw2", f"own_bank{k}", lambda vaddr, level=level, indices=indices: [Extract("level_sound_bank", level, indices)])
              for k, (level, indices) in enumerate(layout.OWN_BANKS))]


def own_banks_load(addr):
    """body.coop_banks' loads: each of layout.OWN_BANKS (writable, 16-aligned) to its handle word."""
    lines = []
    for k in range(len(layout.OWN_BANKS)):
        at = addr[f"own_bank{k}"]
        lines += [f"    lis 3, {ha(at)}", f"    addi 3, 3, {lo(at)}", f"    bl {body.BANK_LOAD_FROM_MEM}",
                  "    cmpwi 3, 0", f"    bne cbk_{k}", "    li 3, -1", f"cbk_{k}:",
                  f"    stw 3, {layout.C_OWN_BANKS + 4 * k}(29)"]
    return "\n".join(lines)


def pool(args):
    return dict(JET_VALUES=body.JET_VALUES)


def parts(args):
    return [pad.CODE, flight.CODE, body.CODE, combat.CODE, fx.CODE, mini.CODE, ai.CODE, hud.CODE, menu.CODE, camera.CODE, preview.CODE]


def fields(args, addr):
    model, textures, _ = model_data()
    pieces, icons_at = pixel_pieces()
    pixels = sum(len(piece) for piece in pieces)
    entries = (len(textures) - 8) // 0x24
    assert len(model) % 0x10 == 0
    skip = 31 - (body.SKIP_UPDATE.bit_length() - 1)
    constants = {name: value for module in (pad, body, flight, combat, fx, hud, mini, ai, menu, camera, preview) for name, value in vars(module).items()
                 if name.isupper() and isinstance(value, int)}
    return dict(**constants, **layout.fields(), **pair("COOP", addr["coop"] + len(layout.TAG)),
                **pair("CLANK_MODEL", addr["clank_model"]), **pair("CLANK_TEXTURES", addr["clank_textures"]),
                **pair("CLANK_PIXELS", addr["clank_pixels"]), **pair("RIDER_ANIM", addr["rider_anim"]),
                **{k: v for name, at in menu.menu_data()[1].items() for k, v in pair(name, addr["zapper"] + at).items()},
                ZAPPER_ENTRY_HI=(addr["zapper"] + 30) >> 16, ZAPPER_ENTRY_LO=(addr["zapper"] + 30) & 0xFFFF,
                **{f"{name}_HA": ha(value) for name, value in constants.items()},
                **{f"{name}_LO": lo(value) for name, value in constants.items()},
                MODEL_SIZE_HI=len(model) >> 16, MODEL_SIZE_LO=len(model) & 0xFFFF,
                PIXELS_SIZE_HI=pixels >> 16, PIXELS_SIZE_LO=pixels & 0xFFFF,
                ZAPPER_PIXELS_HI=icons_at >> 16, ZAPPER_PIXELS_LO=icons_at & 0xFFFF,
                ENTRY_COUNT=entries, ENTRIES_SIZE=entries * 0x24,
                MODEL_RESERVE_HI=reserve(len(model) + entries * 0x24), PIXELS_RESERVE_HI=reserve(pixels),
                NOT_SKIP_MB=(skip + 1) % 32, NOT_SKIP_ME=(skip - 1) % 32, OWN_BANKS_LOAD=own_banks_load(addr))
