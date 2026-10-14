#!/usr/bin/env python3
"""Build the mods in mods/ into Ratchet & Clank 1 HD (NPEA00385).

Each mod is one module in mods/ (see mods/__init__.py for what a mod consists of, and each
module's top for what it does and where its numbers come from):
    boxbreaker     the hyper-strike breaks every crate around Ratchet
    chargeboots    RC2's charge dash, and the boost at the bolt cranks
    strafing       RC2's strafing and ground acceleration
    clank          Clank's thruster dash
    weaponlevels   weapons reach a second level by use
This file puts them into the executable:
  * A mod's assembly and its constants go into the code cave, one mod after the other, and
    behind the embedded data once the cave is full. Every mod is assembled every time and keeps
    its place whether it is built in or not.
  * The game instructions a mod hooks become calls of its routines. Where several mods hook the
    same instruction, their routines are chained (Hook in mods/game.py).
  * The data a mod embeds is appended to the file and loaded through unused program headers.
Each mod comes out as a patch of its own (patch.py's Patch), and the executable is the
untouched one with the chosen patches linked in by patch.py's own code, so what this file
builds and what the patcher makes of the exported patch files are the same bytes.

Usage
-----
    .venv/bin/python build.py              build build/EBOOT.elf from the untouched RC1.ppu.elf
    .venv/bin/python build.py --mods boxbreaker,strafing
                                           ... with these mods only
    .venv/bin/python build.py --install    ... and copy it over RPCS3's EBOOT.BIN (the file there
                                           is kept once as EBOOT.BIN.bak); restart RPCS3 afterwards
    .venv/bin/python build.py --export     ... and write every mod as a patch file to patches/;
                                           patch.py applies any choice of them to the same
                                           executable without any of this file's dependencies
    .venv/bin/python build.py --help       the mods' tuning options (radius, speeds) and paths
    SHOW=1 .venv/bin/python build.py       also print the disassembly of the cave
The input ELF is found through tools/ppu.py (environment variable RC1_ELF overrides the path),
the installation target through RPCS3_EBOOT.
"""
import argparse
import hashlib
import os
import re
import shutil
import struct
import sys

import capstone
import keystone

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from ppu import RC1_ELF, Elf, show  # noqa: E402

import patch as patcher  # noqa: E402
from mods import LIBRARIES, MODS  # noqa: E402
from mods.game import CAVE_START, FAR_CODE, GAME, ORIG_MD5, SEG_END, SEGMENTS, STATE, STATE_END, floats, ha, lo  # noqa: E402

DEFAULT_OUT = os.path.join(ROOT, "build", "EBOOT.elf")
PATCHES = os.path.join(ROOT, "patches")
# RPCS3 boots EBOOT.BIN of the installed game, and takes a plain ELF there.
RPCS3_EBOOT = os.environ.get("RPCS3_EBOOT") or os.path.expanduser(
    f"~/.config/rpcs3/dev_hdd0/game/{GAME}/USRDIR/EBOOT.BIN")

KS = keystone.Ks(keystone.KS_ARCH_PPC, keystone.KS_MODE_PPC64 | keystone.KS_MODE_BIG_ENDIAN)
CS = capstone.Cs(capstone.CS_ARCH_PPC, capstone.CS_MODE_64 | capstone.CS_MODE_BIG_ENDIAN)


class Fields(dict):
    """What a module's assembly templates name in braces: the values given, and by name the
    module's integer constants (which include those of mods/game.py), with NAME_HA and NAME_LO
    for the two halves of the address NAME."""

    def __init__(self, module, values):
        super().__init__(values)
        self.module = module

    def __missing__(self, key):
        value = getattr(self.module, key, None)
        if value is None and key[-3:] in ("_HA", "_LO"):
            value = getattr(self.module, key[:-3], None)
            if isinstance(value, int):
                value = ha(value) if key.endswith("_HA") else lo(value)
        if not isinstance(value, int):
            raise KeyError(f"{self.module.NAME}: nothing to put for {{{key}}}")
        return value


class Unit:
    """A mod or a shared part of mods/, assembled for its place in the cave."""

    def __init__(self, module, args, elf):
        self.module, self.name, self.args = module, module.NAME, args
        self.uses = getattr(module, "USES", ())
        self.hooks = module.hooks(args) if hasattr(module, "hooks") else []
        for hook in self.hooks:                              # a replaced call, or the expected word
            word = elf.u32(hook.site)
            hook.call = not hook.jump and word == patcher.branch(hook.site, hook.original, link=True)
            if not hook.call and word != hook.original or hook.jump and hook.chain:
                sys.exit(f"{self.name}: unexpected instruction at hook site {hook.site:#x}")
        self.pool, self.offsets = bytearray(), {}            # the constants and P_<name> -> offset
        for name, value in module.pool(args).items():
            self.offsets["P_" + name] = len(self.pool)
            self.pool += value if isinstance(value, bytes) else floats(*value) if isinstance(value, tuple) else floats(value)
        self.addr, self.data = {}, []                        # embedded data: name -> address; (segment, offset, bytes)
        self.far = False                                     # its code is in the segment FAR_CODE, not in the cave

    def embed(self, segments):
        """Put the mod's data behind what the segments hold already."""
        for key, name, make in (self.module.data(self.args) if hasattr(self.module, "data") else ()):
            blob = segments[key]
            blob.extend(bytes(-len(blob) % 16))
            self.addr[name] = SEGMENTS[key][1] + len(blob)
            self.data.append((key, len(blob), make(self.addr[name])))
            blob.extend(self.data[-1][2])

    def assemble(self, base, exports):
        """Assemble the parts at base, the constants behind them. exports: the labels of shared
        parts as template fields."""
        fields = Fields(self.module, {**self.offsets, **exports, "CHAIN": "trap"})
        if hasattr(self.module, "fields"):
            fields.update(self.module.fields(self.args, self.addr))
        parts = list(self.module.parts(self.args))
        for label, word in {hook.label: hook.original for hook in self.hooks if hook.chain and not hook.call}.items():
            parts.append(f"\n{label}_orig:\n    .long {word}\n    blr\n")   # the displaced instruction, for the last mod of a chain

        # Branches out of the cave are encoded here, not by keystone: it produced wrong targets for
        # absolute branches once the blob grew. They are assembled as marker words and patched.
        externals = {}

        def external(match):
            externals[len(externals)] = (match.group(1), int(match.group(2)))
            return f".long {0xDEAD0000 + len(externals) - 1:#x}"

        def run(pool_addr):
            externals.clear()
            fields.update(POOL_HA=ha(pool_addr), POOL_LO=lo(pool_addr))
            text = "\n".join(line.split("#")[0] for part in parts for line in part.format_map(fields).splitlines())
            text = re.sub(r"^\s*(bl?)\s+(\d+)\s*$", external, text, flags=re.M)
            code = bytearray(KS.asm(text, base)[0])
            for off in range(0, len(code), 4):
                word = struct.unpack_from(">I", code, off)[0]
                if word >> 16 == 0xDEAD:
                    kind, target = externals[word & 0xFFFF]
                    struct.pack_into(">I", code, off, patcher.branch(base + off, target, link=kind == "bl"))
            return text, bytes(code)

        # The pool follows the code; the code size does not depend on the pool address.
        self.base, self.pool_addr = base, base + len(run(base)[1])
        self.text, self.code = run(self.pool_addr)
        self.end = self.pool_addr + len(self.pool)
        for kind, target in externals.values():
            if abs(target - base) >= 0x2000000 - 0x10000:
                sys.exit(f"{self.name}: {target:#x} is out of reach of a branch")

        # Every branch must land inside the unit's code, on a shared part's label or on a game
        # function named in the module.
        allowed = {v for k, v in vars(self.module).items() if k.isupper() and isinstance(v, int)} | set(exports.values())
        for off in range(0, len(self.code), 4):
            for insn in CS.disasm(self.code[off:off + 4], base + off):
                if insn.mnemonic.startswith("b") and insn.op_str and insn.op_str.split()[-1].startswith("0x"):
                    target = int(insn.op_str.split()[-1], 16)
                    if not (base <= target < self.pool_addr or target in allowed):
                        sys.exit(f"{self.name}: bad branch at {insn.address:#x}: {insn.mnemonic} {insn.op_str}")

    def label(self, label):
        """keystone has no symbol output; every statement is one 4-byte word."""
        if "\n" + label + ":" not in self.text:
            sys.exit(f"{self.name}: no label {label}")
        head = self.text[:self.text.index("\n" + label + ":")]
        return self.base + 4 * sum(1 for line in head.splitlines() if line.strip() and not line.strip().endswith(":"))


def elf_frame(elf, segments, far):
    """The changes to the program headers that make room: the R+X segment grown over the cave,
    the RW segment's bss over the state block, and the data segments mapped behind the end of the
    file through unused PT_LOAD entries. All of it is the same for every choice of mods.
    -> the records every mod needs, file offset of a code address, per segment (file offset,
    its program header's records)."""
    data = elf.data
    phoff = struct.unpack_from(">Q", data, 0x20)[0]
    code_flags = data[phoff + 4:phoff + 8]
    p_off, p_va, _, p_fsz, _ = struct.unpack_from(">QQQQQ", data, phoff + 8)
    new_size = SEG_END - p_va
    if p_va + p_fsz > CAVE_START or any(data[p_off + p_fsz:p_off + new_size]):
        sys.exit("segment padding is not free")
    common = [(phoff + 32, struct.pack(">QQ", new_size, new_size))]

    rw = phoff + 56
    rw_va, rw_msz = struct.unpack_from(">Q", data, rw + 16)[0], struct.unpack_from(">Q", data, rw + 40)[0]
    if rw_va + rw_msz > STATE:
        sys.exit("state block overlaps existing bss")
    common.append((rw + 40, struct.pack(">Q", STATE_END - rw_va)))

    placed, pos, floor = {}, len(data), STATE_END
    for key, (index, vaddr) in SEGMENTS.items():
        size = len(segments[key])
        if not size:
            continue
        ph = phoff + 56 * index
        p_type, _, _, _, _, s_fsz, s_msz, align = struct.unpack_from(">IIQQQQQQ", data, ph)
        if p_type != 1 or s_fsz or s_msz:
            sys.exit(f"program header {index} is not a free PT_LOAD")
        pos += -pos % align
        if pos % align != vaddr % align or vaddr < floor:
            sys.exit(f"segment {key} cannot be placed")
        placed[key] = (pos, [(ph + 8, struct.pack(">QQQQQ", pos, vaddr, vaddr, size, size))])
        if key == FAR_CODE and far:
            placed[key][1].append((ph + 4, code_flags))      # executable, as the game's own code segment
        pos, floor = pos + size, vaddr + size

    def code_off(va):
        if CAVE_START <= va < SEG_END:
            return p_off + (va - p_va)
        return placed[FAR_CODE][0] + (va - SEGMENTS[FAR_CODE][1])
    return common, code_off, placed


def make_patch(unit, order, elf, units, common, cave_off, placed, segments):
    """Everything one mod changes, as patch.py takes it."""
    records, size = dict(common), 0
    for part in [unit] + [units[module.NAME] for module in unit.uses]:
        if not part.far:
            records[cave_off(part.base)] = part.code + bytes(part.pool)
        for key, offset, blob in part.data:
            seg_off, headers = placed[key]
            records.update(headers)
            records[seg_off + offset] = blob
            size = max(size, seg_off + len(segments[key]))
    words = unit.module.words(unit.args, unit.addr) if hasattr(unit.module, "words") else {}
    for va, (old, new) in words.items():
        if elf.data[elf.off(va):elf.off(va) + len(old)] != old:
            sys.exit(f"{unit.name}: unexpected data at {va:#x}")
        records[elf.off(va)] = new
    hooks = []
    for hook in unit.hooks:
        slot = unit.label(hook.label + "_next") if hook.chain else 0
        fallback = 0 if not hook.chain else hook.original if hook.call else unit.label(hook.label + "_orig")
        hooks.append(patcher.Hook(elf.off(hook.site), hook.site, elf.u32(hook.site), unit.label(hook.label),
                                  cave_off(slot) if slot else 0, slot, fallback, int(not hook.jump)))
    return patcher.Patch(unit.name, unit.module.TITLE, unit.module.ABOUT, order, elf.data, sorted(records.items()), hooks, size)


def parse_args():
    names = [module.NAME for module in MODS]
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--mods", default="all", help=f"the mods to build in, separated by commas: {', '.join(names)} (default: all)")
    ap.add_argument("--in", dest="src", default=RC1_ELF, help="the untouched RC1.ppu.elf")
    ap.add_argument("--out", default=DEFAULT_OUT, help="default: build/EBOOT.elf")
    ap.add_argument("--install", action="store_true", help=f"copy the result to {RPCS3_EBOOT}")
    ap.add_argument("--export", nargs="?", const=PATCHES, metavar="FOLDER",
                    help="also write every mod as a patch file for patch.py (default folder: patches/)")
    for module in LIBRARIES + MODS:
        if hasattr(module, "options"):
            module.options(ap.add_argument_group(getattr(module, "TITLE", module.NAME)))
    args = ap.parse_args()
    wanted = [name.strip() for name in args.mods.split(",") if name.strip()]
    unknown = [name for name in wanted if name not in names + ["all"]]
    if unknown:
        ap.error(f"no such mod: {', '.join(unknown)} (there are: {', '.join(names)})")
    args.mods = names if "all" in wanted else [name for name in names if name in wanted]
    return args


def install(path):
    """Put the build where RPCS3 boots it, keeping the file found there the first time."""
    if not os.path.isdir(os.path.dirname(RPCS3_EBOOT)):
        sys.exit(f"cannot install: {os.path.dirname(RPCS3_EBOOT)} does not exist (set RPCS3_EBOOT)")
    backup = RPCS3_EBOOT + ".bak"
    if os.path.exists(RPCS3_EBOOT) and not os.path.exists(backup):
        shutil.copyfile(RPCS3_EBOOT, backup)
        print(f"kept the previous file as {backup}")
    shutil.copyfile(path, RPCS3_EBOOT)
    print(f"installed to {RPCS3_EBOOT}; close and restart RPCS3 to run it")


def build(args, elf):
    """Assemble every mod. -> the units by name and one patch per mod, in the order of MODS."""
    units = {module.NAME: Unit(module, args, elf) for module in LIBRARIES + MODS}
    segments = {key: bytearray() for key in SEGMENTS}
    for unit in units.values():
        unit.embed(segments)
    base, exports, far = CAVE_START, {}, segments[FAR_CODE]
    for unit in units.values():
        unit.assemble(base, exports)
        if unit.end > SEG_END:                               # the cave is full: behind the embedded data
            far.extend(bytes(-len(far) % 16))
            unit.far = True
            unit.assemble(SEGMENTS[FAR_CODE][1] + len(far), exports)
            unit.data.append((FAR_CODE, len(far), unit.code + bytes(unit.pool)))
            far.extend(unit.data[-1][2])
        else:
            base = unit.end
        exports.update({field: unit.label(label) for field, label in getattr(unit.module, "EXPORTS", {}).items()})
    common, cave_off, placed = elf_frame(elf, segments, any(unit.far for unit in units.values()))
    patches = [make_patch(units[module.NAME], order, elf, units, common, cave_off, placed, segments)
               for order, module in enumerate(MODS)]
    return units, patches


def main():
    args = parse_args()
    elf = Elf(args.src)
    if hashlib.md5(elf.data).hexdigest() != ORIG_MD5:
        sys.exit(f"{args.src}: not the expected {GAME} RC1 ELF (md5 mismatch)")
    units, patches = build(args, elf)
    chosen = [patch for patch in patches if patch.name in args.mods]
    try:
        out = patcher.link(elf.data, chosen)
        patcher.link(elf.data, patches)                      # the patch files must go together as well
    except ValueError as error:
        sys.exit(str(error))
    if patcher.restore(out, patches) != elf.data:
        sys.exit("the build cannot be taken back to the original: a mod writes outside its records")

    end = max(unit.end for unit in units.values() if not unit.far)
    for unit in units.values():
        built = unit.name in args.mods or any(unit.module in units[name].uses for name in args.mods)
        print(f"{unit.name}: code {len(unit.code)} bytes at {unit.base:#x}, constants at {unit.pool_addr:#x}"
              + (" (behind the data)" if unit.far else "") + ("" if built else " (left out)"))
        if unit.name in args.mods:
            for hook in sorted(unit.hooks, key=lambda hook: hook.site):
                print(f"  hook {hook.site:#x} -> {hook.label} at {unit.label(hook.label):#x}")
    print(f"cave: {end - CAVE_START} of {SEG_END - CAVE_START} bytes used")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "wb") as f:
        f.write(out)
    print(f"wrote {args.out} with " + (", ".join(patch.title for patch in chosen) or "no mods"))
    if args.export:
        os.makedirs(args.export, exist_ok=True)
        for patch in patches:
            patch.save(os.path.join(args.export, f"{patch.name}-{GAME.lower()}.bbpatch"))
            print(f"exported {patch.title} to {patch.path} ({os.path.getsize(patch.path)} bytes)")
    if args.install:
        install(args.out)
    return args.out, end


if __name__ == "__main__":
    path, end = main()
    if os.environ.get("SHOW"):
        show(Elf(path), CAVE_START, end)
