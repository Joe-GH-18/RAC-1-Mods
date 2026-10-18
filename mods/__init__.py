"""The mods, one module (or package) each. build.py assembles them; patch.py puts any choice of
them into the game.

A mod is a module, or a package whose __init__.py gives the same, with
    NAME, TITLE, ABOUT        its name on the command line and for its patch file, and what the
                              patcher says about it
    parts(args)               its assembly: templates whose fields in braces are the module's own
                              constants and those of game.py by name (NAME_HA and NAME_LO for the
                              halves of an address), the constants of pool() as P_<name> (offsets
                              from {POOL_HA}/{POOL_LO}), and what fields() adds
    hooks(args)               the game instructions it replaces (game.Hook)
    pool(args)                its constants: name -> float, tuple of floats or bytes
and optionally
    USES                      shared routines it calls (modules like sweep.py)
    options(parser)           its build options
    data(args)                what it embeds: (segment of game.SEGMENTS, name, function of the
                              address -> bytes, or a list of bytes and rc2.Extract for data of
                              Ratchet & Clank 2); the addresses come back as addr[name]
    words(args, addr)         data of the game it changes: address -> (bytes there, new bytes)
    fields(args, addr)        template fields that are worked out
Each mod gets its own stretch of the code area, whether it is built in or not, so every mod's patch
file is the same whatever it is combined with.
"""
from . import boxbreaker, chargeboots, clank, strafing, sweep, weaponlevels

LIBRARIES = (sweep,)
# The order in which mods that hook the same instruction run there.
MODS = (boxbreaker, strafing, clank, chargeboots, weaponlevels)
