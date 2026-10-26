"""Co-op Clank: Player 2 is Clank (docs/coop-clank-spec.md).

Step 0 (the spike): Player 2's pad is read (pad.py) and nothing else is done with it yet.

The mod's block (COOP, writable data, for tools/peek.py; tools/coop.py block prints where it is):
  +0x00 C_READ   the frame Player 2's pad was read last
  +0x04 C_READS  how many reads so far
  +0x08 C_PORT   the port Player 2 was found on last
  +0x0c C_HELD   Player 2's buttons held (PAD's bits), +0x10 C_PRESSED pressed this frame
The shared words STATE + COOP_* are described in mods/game.py.
"""
from ..game import *  # noqa: F401,F403
from . import pad

NAME = "coop"
TITLE = "Co-op Clank"
ABOUT = "Plug in a second controller: Clank jumps off Ratchet's back and is Player 2."

C_READ, C_READS, C_PORT, C_HELD, C_PRESSED = 0x0, 0x4, 0x8, 0xC, 0x10
BLOCK_SIZE = 0x100
# The block begins with this tag, so the tools can find it in a running game.
TAG = b"COOP-CLANK-BLOCK"


def hooks(args):
    return [Hook(pad.PAD_READ_HOOK, "coop_pad", pad.PAD_READ_HOOK_WORD)]


def data(args):
    return [("rw", "coop", lambda vaddr: [TAG + bytes(BLOCK_SIZE)])]


def pool(args):
    return {}


def parts(args):
    return [pad.CODE]


def fields(args, addr):
    return dict(**pair("COOP", addr["coop"] + len(TAG)), **pair("PAD_DRIVER", pad.PAD_DRIVER),
                PORT_COUNT=pad.PORT_COUNT, PORT_SIZE=pad.PORT_SIZE, PORT_ACTIVE=pad.PORT_ACTIVE, PAD_HELD=pad.PAD_HELD,
                C_READ=C_READ, C_READS=C_READS, C_PORT=C_PORT, C_HELD=C_HELD, C_PRESSED=C_PRESSED)
