#!/usr/bin/env python3
"""Patch Ratchet & Clank HD (NPEA00385) with the mods of this repository.

    python patch.py                    look for the game's executable, ask which one to patch,
                                       which mods to put in and where the result goes
    python patch.py FILE               patch that file (the mods and the target are asked for)
    python patch.py FILE -o OUT        write the result to OUT without asking anything
    python patch.py FILE --replace     put the result in FILE's place; the original is kept
                                       next to it once as FILE.bak
    python patch.py --list             list the mods
    --mods boxbreaker,clank            only these mods (default without questions: all of them)

The file has to be the game's decrypted executable: the EBOOT.elf that RPCS3 writes with
Utilities > Decrypt PS3 Binaries from the game's USRDIR/EBOOT.BIN, or RC1.ppu.elf decrypted
from the Trilogy disc. A file this patcher has patched before is taken too: its mods are
taken out first, so the choice can be changed. The result is a plain ELF; RPCS3 boots it when
it is named EBOOT.BIN in the game's USRDIR folder.

Needs nothing but Python 3. Each mod is one patch file in patches/, which build.py writes
(--export); see README.md.
"""
import argparse
import glob
import hashlib
import json
import os
import shutil
import struct
import sys
import zlib

ROOT = os.path.dirname(os.path.abspath(__file__))
MAGIC = b"BBRC1\x02"
GAME = "NPEA00385"
NAMES = ("EBOOT.elf", "EBOOT.BIN", "EBOOT.elf.bak", "EBOOT.BIN.bak", "RC1.ppu.elf")
# Where RPCS3 keeps installed games, per platform; a portable RPCS3 has dev_hdd0 next to itself.
GAME_FOLDERS = (
    "~/.config/rpcs3/dev_hdd0/game",
    "~/.var/app/net.rpcs3.RPCS3/config/rpcs3/dev_hdd0/game",
    "~/Library/Application Support/rpcs3/dev_hdd0/game",
    "dev_hdd0/game",
)


def branch(src, dst, link=False):
    """The PowerPC instruction b (or bl) from address src to dst."""
    return 0x48000000 | link | ((dst - src) & 0x03FFFFFC)


class Hook:
    """A game instruction a mod replaces with a call of its own code.

    site: the instruction (file offset and address) and the word the game has there.
    handler: the mod's routine. slot: an instruction of the mod (file offset and address, 0 for
    none) that goes on to whatever the instruction did before; when several mods hook the same
    instruction, each one's slot leads to the next one's handler and the last one's to fallback.
    link: 1 for a call (bl), 0 for a jump (b) where the instruction is in a function that does
    not keep its return address.
    """
    FIELDS = ("site_off", "site", "old", "handler", "slot_off", "slot", "fallback", "link")

    def __init__(self, *values):
        self.link = 1
        for name, value in zip(self.FIELDS, values):
            setattr(self, name, value)

    def values(self):
        return [getattr(self, name) for name in self.FIELDS]


class Patch:
    """One mod: the bytes it writes (offset, new, the original's bytes there) and its hooks.

    File: MAGIC, then zlib data: the length of a JSON header (u32, big-endian), the header, and
    the new and the original bytes of every record one after the other.
    """

    def __init__(self, name, title, about, order, source, records, hooks, size=0, path=None):
        """source: the unmodified executable, or (its md5, its size) when read from a file."""
        self.name, self.title, self.about, self.order, self.path = name, title, about, order, path
        self.hooks = hooks
        if isinstance(source, tuple):
            self.source_md5, self.source_size = source
            self.records = records
        else:
            self.source_md5, self.source_size = hashlib.md5(source).digest(), len(source)
            self.records = [(offset, bytes(new), bytes(source[offset:offset + len(new)])) for offset, new in records]
        self.size = max([size, self.source_size] + [offset + len(new) for offset, new, _ in self.records])

    def save(self, path):
        header = json.dumps(dict(
            game=GAME, name=self.name, title=self.title, about=self.about, order=self.order,
            source_md5=self.source_md5.hex(), source_size=self.source_size, size=self.size,
            records=[(offset, len(new), len(old)) for offset, new, old in self.records],
            hooks=[hook.values() for hook in self.hooks])).encode()
        body = struct.pack(">I", len(header)) + header + b"".join(new + old for _, new, old in self.records)
        with open(path, "wb") as f:
            f.write(MAGIC + zlib.compress(body, 9))
        self.path = path

    @classmethod
    def load(cls, path):
        data = open(path, "rb").read()
        if not data.startswith(MAGIC):
            raise ValueError(f"{path} is not a patch file of this version")
        body = zlib.decompress(data[len(MAGIC):])
        length = struct.unpack_from(">I", body)[0]
        header, pos, records = json.loads(body[4:4 + length]), 4 + length, []
        for offset, new, old in header["records"]:
            records.append((offset, body[pos:pos + new], body[pos + new:pos + new + old]))
            pos += new + old
        return cls(header["name"], header["title"], header["about"], header["order"],
                   (bytes.fromhex(header["source_md5"]), header["source_size"]), records,
                   [Hook(*values) for values in header["hooks"]], header["size"], path)

    def applied(self, data):
        """Is this mod in the executable? (Its slots are compared as they are: they are linked.)"""
        slots = [hook.slot_off for hook in self.hooks if hook.slot]
        for offset, new, _ in self.records:
            have, want = bytearray(data[offset:offset + len(new)]), bytearray(new)
            if len(have) != len(want):
                return False
            for slot in slots:
                if offset <= slot < offset + len(new):
                    want[slot - offset:slot - offset + 4] = have[slot - offset:slot - offset + 4]
            if have != want:
                return False
        return True


def link(source, patches):
    """The unmodified executable with these mods in it."""
    patches = sorted(patches, key=lambda patch: patch.order)
    out = bytearray(source)
    out.extend(bytes(max([len(out)] + [patch.size for patch in patches]) - len(out)))
    done = []                                               # (offset, bytes, mod)
    for patch in patches:
        for offset, new, _ in patch.records:
            for other, data, name in done:                  # mods share bytes only where they agree
                start, end = max(offset, other), min(offset + len(new), other + len(data))
                if start < end and data[start - other:end - other] != new[start - offset:end - offset]:
                    raise ValueError(f"{patch.name} and {name} do not go together")
            out[offset:offset + len(new)] = new
            done.append((offset, new, patch.name))

    chains, words = {}, {}

    def put(offset, word, patch):
        if words.setdefault(offset, word) != word:
            raise ValueError(f"{patch.name} cannot be linked with the other mods")

    for patch in patches:
        for hook in patch.hooks:
            chains.setdefault(hook.site_off, []).append((hook, patch))
    for site_off, chain in chains.items():
        if len(chain) > 1 and not all(hook.slot for hook, _ in chain):
            raise ValueError(" and ".join(patch.name for _, patch in chain) + " change the same instruction")
        put(site_off, branch(chain[0][0].site, chain[0][0].handler, link=bool(chain[0][0].link)), chain[0][1])
        for (hook, patch), following in zip(chain, chain[1:] + [None]):
            if hook.slot:
                put(hook.slot_off, branch(hook.slot, following[0].handler if following else hook.fallback), patch)
    for offset, word in words.items():
        struct.pack_into(">I", out, offset, word)
    return bytes(out)


def restore(data, patches):
    """The unmodified executable back from one that has any of these mods in it, or None when
    the file is something else."""
    if not patches:
        return None
    out = bytearray(data)
    for patch in patches:
        for offset, _, old in patch.records:
            if offset < len(out):
                out[offset:offset + len(old)] = old
        for hook in patch.hooks:
            if hook.site_off < len(out):
                struct.pack_into(">I", out, hook.site_off, hook.old)
    del out[patches[0].source_size:]
    return bytes(out) if hashlib.md5(out).digest() == patches[0].source_md5 else None


def load_patches(folder):
    paths = sorted(glob.glob(os.path.join(folder, "*.bbpatch")))
    if not paths:
        sys.exit(f"no patch file in {folder}; build them with build.py --export (see README.md)")
    try:
        patches = sorted((Patch.load(path) for path in paths), key=lambda patch: patch.order)
    except ValueError as error:
        sys.exit(str(error))
    if len({patch.source_md5 for patch in patches}) != 1:
        sys.exit(f"the patch files in {folder} are not for the same executable")
    return patches


def describe(path, patches):
    """-> (what the file is, the unmodified executable it holds or None)"""
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError as error:
        return f"cannot be read ({error.strerror})", None
    original = restore(data, patches)
    if original == data:
        return "unmodified game executable: can be patched", original
    if original:
        inside = [patch.title for patch in patches if patch.applied(data)]
        return "patched already (" + (", ".join(inside) or "mods of another version") + "): the choice can be changed", original
    if data[:4] == b"SCE\0":
        return "still encrypted: decrypt it in RPCS3 first (Utilities > Decrypt PS3 Binaries)", None
    if data[:4] == b"\x7fELF":
        return "an executable, but not the supported one (another game, region, or modified by something else)", None
    return "not a PS3 executable", None


def candidates():
    """Files that could be the executable: next to this script, in the current folder and in
    RPCS3's game folder."""
    found = []
    folders = [os.getcwd(), ROOT]
    for base in GAME_FOLDERS:
        folders.append(os.path.join(os.path.expanduser(base), GAME, "USRDIR"))
    for folder in folders:
        for name in NAMES:
            path = os.path.join(folder, name)
            if os.path.isfile(path) and os.path.abspath(path) not in found:
                found.append(os.path.abspath(path))
    return found


def ask(prompt):
    try:
        return input(prompt).strip()
    except EOFError:
        sys.exit("\nno answer; nothing was changed")


def clean(path):
    """A path as typed or dragged into the console: quotes and a trailing space go."""
    return os.path.abspath(os.path.expanduser(path.strip().strip('"').strip("'")))


def choose_source(patches):
    print("Looking for the game's executable ...")
    usable = []
    for path in candidates():
        what, original = describe(path, patches)
        if original:
            usable.append((path, original))
            print(f"  [{len(usable)}] {path}\n      {what}")
        else:
            print(f"   -  {path}\n      {what}")
    if not usable:
        print("  none found that can be patched.")
    while True:
        answer = ask("\nNumber of the file to patch, or the path of another one (empty to quit): ")
        if not answer:
            sys.exit("nothing was changed")
        if answer.isdigit() and 1 <= int(answer) <= len(usable):
            return usable[int(answer) - 1]
        path = clean(answer)
        what, original = describe(path, patches)
        if original:
            return path, original
        print(f"  {path}\n      {what}")


def named_mods(names, patches):
    """The patches a comma-separated list of names stands for."""
    by_name = {patch.name: patch for patch in patches}
    wanted = [name.strip().lower() for name in names.split(",") if name.strip()]
    unknown = [name for name in wanted if name not in by_name and name != "all"]
    if unknown:
        sys.exit(f"no such mod: {', '.join(unknown)} (there are: {', '.join(by_name)})")
    return patches if "all" in wanted else [patch for patch in patches if patch.name in wanted]


def list_mods(patches):
    for number, patch in enumerate(patches, 1):
        print(f"  [{number}] {patch.title} ({patch.name})\n      {patch.about}")


def choose_mods(patches):
    print("\nWhich mods should go in?")
    list_mods(patches)
    while True:
        answer = ask("Numbers, e.g. 1 3 (empty for all of them): ").replace(",", " ").split()
        if all(number.isdigit() and 1 <= int(number) <= len(patches) for number in answer):
            return [patches[int(number) - 1] for number in sorted(set(answer))] if answer else patches
        print("  that is not a list of the numbers above")


def choose_target(source):
    folder = os.path.dirname(source)
    boot = os.path.join(folder, "EBOOT.BIN")
    print("\nWhere should the patched executable go?")
    print(f"  [1] {boot}\n      the file RPCS3 boots when this is the game's USRDIR folder"
          + ("; the one there now is kept as EBOOT.BIN.bak" if os.path.exists(boot) else ""))
    print("  [2] another file")
    while True:
        answer = ask("Number (empty to quit): ")
        if not answer:
            sys.exit("nothing was changed")
        if answer == "1":
            return boot
        if answer == "2":
            path = ask("Path of the file to write: ")
            if path:
                return clean(path)


def write(target, data):
    """Write the result; a file already there is kept once as <name>.bak."""
    if os.path.exists(target):
        backup = target + ".bak"
        if os.path.exists(backup):
            print(f"{backup} exists already and is left as it is")
        else:
            shutil.copyfile(target, backup)
            print(f"kept the previous file as {backup}")
    folder = os.path.dirname(target)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(target, "wb") as f:
        f.write(data)
    print(f"wrote {target}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("file", nargs="?", help="the decrypted executable (asked for when left out)")
    ap.add_argument("-o", "--output", help="write the result here")
    ap.add_argument("--replace", action="store_true", help="put the result in the file's place, keeping it as <file>.bak")
    ap.add_argument("--mods", help="the mods to put in, separated by commas (see --list), or 'all'")
    ap.add_argument("--list", action="store_true", help="list the mods and quit")
    ap.add_argument("--patches", default=os.path.join(ROOT, "patches"), help="the folder with the patch files (default: patches/)")
    args = ap.parse_args()

    patches = load_patches(args.patches)
    if args.list:
        list_mods(patches)
        return
    chosen = named_mods(args.mods, patches) if args.mods else None

    if args.file:
        source = clean(args.file)
        what, original = describe(source, patches)
        if not original:
            sys.exit(f"{source}: {what}")
    else:
        source, original = choose_source(patches)
        what = describe(source, patches)[0]
    print(f"\n{source}\n      {what.split(':')[0]}")

    if chosen is None:
        chosen = patches if args.replace or args.output else choose_mods(patches)
    if args.replace:
        target = source
    elif args.output:
        target = clean(args.output)
    else:
        target = choose_target(source)

    try:
        result = link(original, chosen)
    except ValueError as error:
        sys.exit(str(error))
    if restore(result, patches) != original:
        sys.exit("the patched file does not check out; nothing was written")
    print("\nmods: " + (", ".join(patch.title for patch in chosen) or "none (the unmodified executable)"))
    write(target, result)
    if os.path.basename(target) != "EBOOT.BIN":
        print("RPCS3 boots the file named EBOOT.BIN in the game's USRDIR folder; copy the result there under that name.")
    print("Close RPCS3 completely and start it again to play the patched game.")


if __name__ == "__main__":
    main()
