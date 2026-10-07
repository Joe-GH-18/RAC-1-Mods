"""Offline helpers for poking at a decrypted PS3 PPU ELF (big-endian PPC64, 32-bit pointers)."""
import bisect
import os
import struct
import sys

import capstone

# The decrypted executable. Where it is on this machine comes from the environment variable
# RC1_ELF or from the first line of the file rc1_elf.path next to build.py (not part of the
# repository); without either it is RC1.ppu.elf in the current folder. The tools that read game
# data (psarc.py, match.py) expect RC2.ppu.elf and the game's folders next to it, as on the
# Trilogy disc.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _local(name, default):
    """A path of this machine: the first line of <name> next to build.py, if that file exists."""
    try:
        with open(os.path.join(_ROOT, name)) as f:
            return f.readline().strip() or default
    except OSError:
        return default


RC1_ELF = os.environ.get("RC1_ELF") or _local("rc1_elf.path", "RC1.ppu.elf")

_md = capstone.Cs(capstone.CS_ARCH_PPC, capstone.CS_MODE_64 | capstone.CS_MODE_BIG_ENDIAN)


class Elf:
    def __init__(self, path=RC1_ELF):
        self.path = path
        self.data = open(path, "rb").read()
        d = self.data
        self.entry_opd = struct.unpack_from(">Q", d, 0x18)[0]
        phoff = struct.unpack_from(">Q", d, 0x20)[0]
        shoff = struct.unpack_from(">Q", d, 0x28)[0]
        phentsize, phnum, shentsize, shnum = struct.unpack_from(">HHHH", d, 0x36)
        self.segments = []  # (vaddr, offset, filesz, memsz, flags)
        for i in range(phnum):
            p_type, p_flags, p_off, p_va, _, p_fsz, p_msz, _ = struct.unpack_from(
                ">IIQQQQQQ", d, phoff + i * phentsize)
            if p_type == 1 and p_msz:
                self.segments.append((p_va, p_off, p_fsz, p_msz, p_flags))
        self.sections = []  # (vaddr, offset, size, flags, type)
        for i in range(shnum):
            _, s_type, s_flags, s_va, s_off, s_sz = struct.unpack_from(
                ">IIQQQQ", d, shoff + i * shentsize)
            if s_va:
                self.sections.append((s_va, s_off, s_sz, s_flags, s_type))
        self.code = [(va, off, sz) for va, off, sz, fl, _ in self.sections if fl & 4]
        self.text_start = min(va for va, _, _ in self.code)
        self.text_end = max(va + sz for va, _, sz in self.code)
        self._find_opd()

    def off(self, va):
        for s_va, s_off, fsz, _, _ in self.segments:
            if s_va <= va < s_va + fsz:
                return s_off + (va - s_va)
        return None

    def read(self, va, n):
        o = self.off(va)
        return None if o is None else self.data[o:o + n]

    def u32(self, va):
        b = self.read(va, 4)
        return None if b is None or len(b) < 4 else struct.unpack(">I", b)[0]

    def f32(self, va):
        b = self.read(va, 4)
        return None if b is None or len(b) < 4 else struct.unpack(">f", b)[0]

    def cstr(self, va, maxlen=200):
        b = self.read(va, maxlen) or b""
        return b.split(b"\0")[0].decode("latin1")

    def _find_opd(self):
        """The OPD is the section holding the entry descriptor: {func u32, toc u32} pairs."""
        self.toc = self.u32(self.entry_opd + 4)
        for va, _, sz, _, _ in self.sections:
            if va <= self.entry_opd < va + sz:
                self.opd_start, self.opd_size = va, sz
        funcs = set()
        self.opd = {}  # func addr -> descriptor addr
        for a in range(self.opd_start, self.opd_start + self.opd_size, 8):
            f, t = self.u32(a), self.u32(a + 4)
            if t == self.toc and self.text_start <= f < self.text_end:
                funcs.add(f)
                self.opd.setdefault(f, a)
        self.funcs = sorted(funcs)

    def func_of(self, va):
        i = bisect.bisect_right(self.funcs, va) - 1
        return self.funcs[i] if i >= 0 else None

    def func_end(self, start):
        i = bisect.bisect_right(self.funcs, start)
        return self.funcs[i] if i < len(self.funcs) else self.text_end

    def disasm(self, start, end=None):
        end = end or self.func_end(start)
        out = []
        while start < end:  # capstone stops at words it cannot decode (some AltiVec); skip them
            chunk = list(_md.disasm(self.read(start, end - start), start))
            out += chunk
            start = (chunk[-1].address if chunk else start) + (8 if chunk else 4)
        return out

    def words(self):
        """Yield (va, word) for every instruction word in executable sections."""
        for va, off, sz in self.code:
            for i in range(0, sz - 3, 4):
                yield va + i, struct.unpack_from(">I", self.data, off + i)[0]

    def callers(self, target):
        """All `bl target` / `b target` sites."""
        out = []
        for va, w in self.words():
            if w >> 26 == 18 and not (w & 2):
                d = w & 0x03FFFFFC
                if d & 0x02000000:
                    d -= 0x04000000
                if va + d == target:
                    out.append((va, "bl" if w & 1 else "b"))
        return out

    def toc_slots(self, value):
        """TOC-relative offsets (from r2) of slots holding `value`."""
        out = []
        for va, _, sz, _, st in self.sections:
            if st != 1 or not (self.toc - 0x8000 <= va + sz and va < self.toc + 0x8000):
                continue
            for a in range(max(va, self.toc - 0x8000) & ~3, min(va + sz, self.toc + 0x8000), 4):
                if self.u32(a) == value:
                    out.append(a - self.toc)
        return out


def show(elf, start, end=None, out=sys.stdout):
    for i in elf.disasm(start, end):
        print(f"{i.address:08x}  {i.mnemonic:8s} {i.op_str}", file=out)


if __name__ == "__main__":
    e = Elf(sys.argv[1] if len(sys.argv) > 1 else RC1_ELF)
    print(f"entry opd {e.entry_opd:#x}  toc {e.toc:#x}  opd {e.opd_start:#x}+{e.opd_size:#x}")
    print(f"text {e.text_start:#x}-{e.text_end:#x}  functions {len(e.funcs)}")
    for s in e.segments:
        print("seg va=%#x off=%#x fsz=%#x msz=%#x fl=%d" % s)
