"""Ratchet & Clank 2's data in what a mod embeds.

A mod's data() may give a list of pieces instead of bytes: bytes of its own, and Extract for
data of RC2 (rc2data.py). build.py takes the extracts from the RC2 next to the RC1 executable
(rc2/ps3data of the Trilogy, or the folder in the environment variable RC2_DATA); the patch
files only name them, and patch.py takes them from the player's own copy.
"""
import hashlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import rc2data  # noqa: E402

_source = None


def source():
    """RC2's data folder of this machine."""
    global _source
    if _source is None:
        from ppu import RC1_ELF                             # tools/ppu.py
        folder = os.environ.get("RC2_DATA") or rc2data.find(RC1_ELF)
        if not folder:
            sys.exit(f"RC2's data (rc2/ps3data) is not next to {RC1_ELF}; set RC2_DATA to the folder")
        try:
            _source = rc2data.Rc2(folder)
        except rc2data.Missing as error:
            sys.exit(str(error))
    return _source


class Extract:
    """One piece of RC2's data: rc2data.EXTRACTS[name](rc2, *args)."""

    def __init__(self, name, *args):
        self.name, self.args = name, list(args)
        try:
            self.data = rc2data.extract(source(), name, args)
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
