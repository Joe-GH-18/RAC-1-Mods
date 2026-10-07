"""Minimal reader for the trilogy's PSARC archives (LZMA blocks)."""
import lzma
import os
import struct
import sys

from ppu import RC1_ELF

USRDIR = os.path.dirname(RC1_ELF)


class Psarc:
    def __init__(self, game):
        self.f = open(os.path.join(USRDIR, game, "ps3data", "PS3arc.psarc"), "rb")
        magic, _, comp, toclen, entsz, nent, self.bsz, _ = struct.unpack(">4sI4sIIIII", self.f.read(32))
        assert magic == b"PSAR" and comp == b"lzma"
        toc = self.f.read(toclen - 32)
        ents = []
        for i in range(nent):
            e = toc[i * entsz:(i + 1) * entsz]
            ents.append((struct.unpack(">I", e[16:20])[0], int.from_bytes(e[20:25], "big"), int.from_bytes(e[25:30], "big")))
        nblocks = (toclen - 32 - nent * entsz) // 2
        self.blocks = struct.unpack(f">{nblocks}H", toc[nent * entsz:nent * entsz + nblocks * 2])
        names = self._read(ents[0]).decode("latin1").split("\n")
        self.files = dict(zip(names, ents[1:]))

    def _read(self, ent):
        zidx, length, off = ent
        out = bytearray()
        self.f.seek(off)
        while len(out) < length:
            size = self.blocks[zidx] or self.bsz
            data = self.f.read(size)
            zidx += 1
            if size == self.bsz:
                out += data
                continue
            try:
                out += lzma.decompress(data)
            except lzma.LZMAError:
                out += data
        return bytes(out[:length])

    def read(self, name):
        return self._read(self.files[name])

    def extract(self, name, dest_dir):
        path = os.path.join(dest_dir, name.lstrip("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(self.read(name))
        return path


if __name__ == "__main__":
    arc = Psarc(sys.argv[1])
    for pattern in sys.argv[2:]:
        for name in arc.files:
            if pattern in name:
                print(arc.extract(name, os.path.join(os.path.dirname(__file__), "..", "build", "assets")))
