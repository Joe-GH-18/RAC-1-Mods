"""Build/query an index of absolute data references formed by lis + (addi|load|store) pairs and TOC loads."""
import os
import pickle
import struct
import sys

from ppu import Elf, RC1_ELF

LOADS = {32: "lwz", 34: "lbz", 40: "lhz", 42: "lha", 48: "lfs", 50: "lfd", 58: "ld"}
STORES = {36: "stw", 38: "stb", 44: "sth", 52: "stfs", 54: "stfd", 62: "std"}


def s16(x):
    return x - 0x10000 if x & 0x8000 else x


def build(elf):
    refs = []  # (ea, site, kind)
    funcs = set(elf.funcs)
    for va, off, sz in elf.code:
        hi = {}
        for i in range(0, sz - 3, 4):
            a = va + i
            if a in funcs:
                hi = {}
            w = struct.unpack_from(">I", elf.data, off + i)[0]
            op, rt, ra, imm = w >> 26, (w >> 21) & 31, (w >> 16) & 31, w & 0xFFFF
            if op == 15 and ra == 0:  # lis
                hi[rt] = (imm << 16) & 0xFFFFFFFF
                continue
            if op in (12, 14):  # addi / addic (SNC emits addic)
                if ra in hi:
                    v = (hi[ra] + s16(imm)) & 0xFFFFFFFF
                    refs.append((v, a, "addr"))
                    hi[rt] = v  # keep: later loads use it as a base
                    hi_base = True
                else:
                    hi.pop(rt, None)
                continue
            if op == 24:  # ori rA,rS,imm (rS is the 'rt' field); imm 0 is SNC's mr
                if rt not in hi:
                    hi.pop(ra, None)
                    continue
                if imm == 0:
                    hi[ra] = hi[rt]
                    continue
                v = hi[rt] | imm
                refs.append((v, a, "addr"))
                hi[ra] = v
                continue
            if op in LOADS or op in STORES:
                d = s16(imm) if op not in (58, 62) else s16(imm & 0xFFFC)
                if ra in hi:
                    refs.append(((hi[ra] + d) & 0xFFFFFFFF, a, LOADS.get(op) or STORES[op]))
                elif ra == 2 and op in (32, 58):
                    slot = elf.toc + d
                    v = elf.u32(slot)
                    if v is not None:
                        refs.append((v, a, "toc"))
                if op in LOADS and op not in (48, 50):
                    hi.pop(rt, None)
                continue
            if op == 18 and (w & 1):  # bl clobbers volatiles
                for r in (0, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12):
                    hi.pop(r, None)
                continue
            # anything else writing a GPR in the rt slot: drop tracking (coarse)
            if op in (7, 8, 13, 31, 20, 21, 23, 28, 29, 30, 46):
                hi.pop(ra if op in (20, 21, 23, 28, 29, 30) or (op == 31 and False) else rt, None)
    refs.sort()
    return refs


def load(path=RC1_ELF):
    cache = os.path.join(os.path.dirname(__file__), "..", "build", os.path.basename(path) + ".xref.pkl")
    elf = Elf(path)
    if os.path.exists(cache):
        return elf, pickle.load(open(cache, "rb"))
    refs = build(elf)
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    pickle.dump(refs, open(cache, "wb"))
    return elf, refs


def query(refs, lo, hi=None):
    import bisect
    hi = hi if hi is not None else lo + 1
    i = bisect.bisect_left(refs, (lo, 0, ""))
    out = []
    while i < len(refs) and refs[i][0] < hi:
        out.append(refs[i])
        i += 1
    return out


if __name__ == "__main__":
    elf, refs = load()
    lo = int(sys.argv[1], 16)
    hi = int(sys.argv[2], 16) if len(sys.argv) > 2 else lo + 1
    for ea, site, kind in query(refs, lo, hi):
        print(f"{ea:08x} <- {site:08x} {kind:5s} in fn {elf.func_of(site):08x}")
