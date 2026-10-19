"""Ratchet & Clank 2's data in what a mod embeds.

A mod's data() may give a list of pieces instead of bytes: bytes of its own, and Extract for
data of RC2 (rc2data.py). build.py takes the extracts from the RC2 next to the RC1 executable
(rc2/ps3data of the Trilogy, or the folder in the environment variable RC2_DATA); the patch
files only name them, and patch.py takes them from the player's own copy. The extracts of
rc2data.RC1_EXTRACTS come from RC1's own data in the same way (rc1/ps3data next to the
executable, or RC1_DATA).
"""
import hashlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import rc2data  # noqa: E402

_sources = {}


def source(game="rc2"):
    """A game's data folder of this machine (RC2's, or RC1's own)."""
    if game not in _sources:
        from ppu import RC1_ELF                             # tools/ppu.py
        folder = os.environ.get(f"{game.upper()}_DATA") or rc2data.find(RC1_ELF, game)
        if not folder:
            sys.exit(f"{game.upper()}'s data ({game}/ps3data) is not next to {RC1_ELF}; set {game.upper()}_DATA to the folder")
        try:
            _sources[game] = rc2data.Rc2(folder, game)
        except rc2data.Missing as error:
            sys.exit(str(error))
    return _sources[game]


class Extract:
    """One piece of a game's data: rc2data.EXTRACTS[name](its data folder, *args)."""

    def __init__(self, name, *args):
        self.name, self.args = name, list(args)
        try:
            self.data = rc2data.extract(source(rc2data.game(name)), name, args)
        except rc2data.Missing as error:
            sys.exit(str(error))
        self.sha256 = hashlib.sha256(self.data).hexdigest()

    def __len__(self):
        return len(self.data)


def flatten(pieces):
    """bytes, or a list of bytes and Extract -> (the bytes with the extracts in them, [(offset, Extract)])."""
    if isinstance(pieces, (bytes, bytearray)):
        return bytes(pieces), []
    out, extracts = bytearray(), []
    for piece in pieces:
        if isinstance(piece, Extract):
            extracts.append((len(out), piece))
            out += piece.data
        else:
            out += piece
    return bytes(out), extracts
