"""Find the RC1 counterpart of an RC2 function by comparing opcode 3-gram profiles."""
import collections
import struct
import sys

from ppu import RC1_ELF, Elf

RC2_ELF = RC1_ELF.replace("RC1.ppu.elf", "RC2.ppu.elf")


def ops(elf, start, end):
    out = []
    for va in range(start, end, 4):
        w = elf.u32(va)
        op = w >> 26
        if op in (31, 59, 63, 19, 4):
            op = (op << 11) | ((w >> 1) & 0x3FF)
        out.append(op)
    return out


def profile(elf, f):
    o = ops(elf, f, elf.func_end(f))
    return collections.Counter(zip(o, o[1:], o[2:])), len(o)


def similarity(a, b):
    inter = sum((a & b).values())
    union = sum((a | b).values())
    return inter / union if union else 0.0


class Matcher:
    def __init__(self):
        self.rc1, self.rc2 = Elf(RC1_ELF), Elf(RC2_ELF)
        self.by_size = collections.defaultdict(list)
        for f in self.rc1.funcs:
            self.by_size[(self.rc1.func_end(f) - f) // 4].append(f)
        self.cache = {}

    def match(self, f2, top=3):
        p2, n = profile(self.rc2, f2)
        cands = []
        for size in range(int(n * 0.7), int(n * 1.4) + 2):
            for f1 in self.by_size.get(size, ()):
                if f1 not in self.cache:
                    self.cache[f1] = profile(self.rc1, f1)[0]
                cands.append((similarity(p2, self.cache[f1]), f1))
        return n, sorted(cands, reverse=True)[:top]


if __name__ == "__main__":
    m = Matcher()
    for arg in sys.argv[1:]:
        f2 = int(arg, 16)
        n, best = m.match(f2)
        print(f"RC2 {f2:#x} ({n} insns): " + ", ".join(f"RC1 {f:#x} {s:.2f}" for s, f in best))
