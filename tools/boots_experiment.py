#!/usr/bin/env python3
"""Install RC2's Charge Boots model into a running RC1 from outside, to test the port's design.

Does by hand what the game's model fix-up (0xdbc38) does, with the model at the top of the main
heap and its texture at the top of the graphics heap, then points class 0xc3 at it and asks the
foot slot for the Grindboots.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from live import read, u32, write  # noqa: E402

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "build", "assets", "boots")
MAIN, VRAM = 0x4ACE0000, 0xCF8E0000
HERO, LEVEL, GCM_PTR = 0x969CE0, 0xA15F4C, 0x8FA564
SCALE = struct.unpack(">f", read(0xDBC34, 4))[0]

model = bytearray(open(os.path.join(ASSETS, "rc2_e70_model.bin"), "rb").read())
pixels = open(os.path.join(ASSETS, "rc2_e70_texture.bin"), "rb").read()
entry = bytearray(open(os.path.join(ASSETS, "rc2_e70_texentry.bin"), "rb").read())

io_base = u32(u32(GCM_PTR) + 0x4A8)
local_base = u32(u32(GCM_PTR) + 0x4AC)
tex_table = u32(LEVEL + 0x1C)
entry_addr = MAIN + len(model)
struct.pack_into(">I", entry, 0, VRAM - local_base)


def g(off):
    return struct.unpack_from(">I", model, off)[0]


def p(off, value):
    struct.pack_into(">I", model, off, value & 0xFFFFFFFF)


def reloc(off):
    if g(off):
        p(off, g(off) + MAIN)


mesh = g(0)
reloc(0)
tex_count, other_count, tex_ptr, other_ptr, vtx, idx = struct.unpack_from(">6I", model, mesh)
reloc(mesh + 8)
reloc(mesh + 0xC)
p(mesh + 0x10, MAIN + vtx - io_base)
p(mesh + 0x14, MAIN + idx - io_base)
for base_off, count in ((tex_ptr, tex_count), (other_ptr, other_count)):
    for k in range(count):
        cfg = base_off + 16 * k
        tid = struct.unpack_from(">i", model, cfg)[0]
        p(cfg, entry_addr if tid >= 0 else tex_table + (0x24 if tid == -3 else 0))
bones = model[8]
reloc(0x10)
mats = g(0x14)
reloc(0x14)
for b in range(bones):
    o = mats + 0x40 * b
    x, y, z = struct.unpack_from(">3f", model, o + 0x30)
    struct.pack_into(">3f", model, o + 0x30, x * SCALE, y * SCALE, z * SCALE)
    p(o + 0xC, 0), p(o + 0x1C, 0), p(o + 0x2C, 0), p(o + 0x3C, 0x3F800000)
data = g(0x18)
reloc(0x18)
for b in range(bones):
    o = data + 0x10 * b
    x, y, z = struct.unpack_from(">3f", model, o)
    struct.pack_into(">3f", model, o, x * SCALE, y * SCALE, z * SCALE)
tab = g(0x1C)
reloc(0x1C)
if tab:
    for k in range(struct.unpack_from(">i", model, tab)[0]):
        reloc(tab + 4 + 4 * k)
reloc(0x28)
for k in range(model[0xC]):
    anim = g(0x48 + 4 * k)
    if not anim:
        continue
    reloc(0x48 + 4 * k)
    reloc(anim + 0x14)
    for f in range(model[anim + 0x10]):
        reloc(anim + 0x1C + 4 * f)

if "--dry" in sys.argv:
    print(f"io base {io_base:#x} local base {local_base:#x} texture table {tex_table:#x}")
    print("header", model[:0x60].hex())
    print("mesh  ", model[mesh:mesh + 0x20].hex())
    sys.exit()

slot = read(0xA354C0 + 0xC3, 1)[0]
original = u32(0xA34C00 + 4 * slot)
model[0x2C:0x30] = read(original + 0x2C, 4)   # set at runtime on the original (looks like an update function descriptor)
model[0xB] = 0xFF                             # RC1 models have 0xff here, RC2's 0

write(VRAM, pixels)
write(MAIN, bytes(model) + bytes(entry))
print(f"class 0xc3 slot {slot}: model {original:#x} -> {MAIN:#x}")
write(0xA34C00 + 4 * slot, struct.pack(">I", MAIN))
write(HERO + 0x20F4, struct.pack(">I", 0x26))
write(HERO + 0x20BC, struct.pack(">I", 0x1D))
print("requested the boots; restore the table with:")
print(f"  tools/peek.py w {0xA34C00 + 4 * slot:x} {original:08x}")
