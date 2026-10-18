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
    --rc2 FOLDER                       Ratchet & Clank 2's data, if it is not found by itself

The file has to be the game's decrypted executable: the EBOOT.elf that RPCS3 writes with
Utilities > Decrypt PS3 Binaries from the game's USRDIR/EBOOT.BIN, or RC1.ppu.elf decrypted
from the Trilogy disc. A file this patcher has patched before is taken too: its mods are
taken out first, so the choice can be changed. The result is a plain ELF; RPCS3 boots it when
it is named EBOOT.BIN in the game's USRDIR folder.

Some mods use data of Ratchet & Clank 2 (the Charge Boots' model, animation and sounds,
strafing's backwards walk). Nothing of it is in the patch files: it is taken from the player's
own RC2, the folder rc2/ps3data next to RC1 in the Trilogy's USRDIR (found by itself next to the
executable, or given with --rc2), and checked by its hash. Without it, those mods are left out.

Needs nothing but Python 3 (and rc2data.py next to this file). Each mod is one patch file in
patches/, which build.py writes (--export); see README.md.
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
sys.path.insert(0, ROOT)
import rc2data  # noqa: E402

MAGIC = b"BBRC1\x03"
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

    site: the instruction (file offset and address).
    handler: the mod's routine. slot: an instruction of the mod (file offset and address, 0 for
    none) that goes on to whatever the instruction did before; when several mods hook the same
    instruction, each one's slot leads to the next one's handler and the last one's to fallback.
    link: 1 for a call (bl), 0 for a jump (b) where the instruction is in a function that does
    not keep its return address.
    """
    FIELDS = ("site_off", "site", "handler", "slot_off", "slot", "fallback", "link")

    def __init__(self, *values):
        self.link = 1
        for name, value in zip(self.FIELDS, values):
            setattr(self, name, value)

    def values(self):
        return [getattr(self, name) for name in self.FIELDS]


class Patch:
    """One mod: the bytes it writes, the RC2 data it needs, and its hooks.

    records: (file offset, new bytes). fills: (file offset, extract name, its arguments, length,
    SHA-256): the RC2 data (rc2data.py) that goes there; the records hold zeros in its place.
    Nothing of the game is stored: the executable it goes into is known by its MD5 and size.
    File: MAGIC, then zlib data: the length of a JSON header (u32, big-endian), the header, and
    the records' bytes one after the other.
    """

    def __init__(self, name, title, about, order, source_md5, source_size, records, fills, hooks, size=0, path=None):
        self.name, self.title, self.about, self.order, self.path = name, title, about, order, path
        self.source_md5, self.source_size = source_md5, source_size
        self.records, self.fills, self.hooks = [(offset, bytes(new)) for offset, new in records], fills, hooks
        self.size = max([size, source_size] + [offset + len(new) for offset, new in self.records])

    def save(self, path):
        header = json.dumps(dict(
            game=GAME, name=self.name, title=self.title, about=self.about, order=self.order,
            source_md5=self.source_md5.hex(), source_size=self.source_size, size=self.size,
            records=[(offset, len(new)) for offset, new in self.records], fills=self.fills,
            hooks=[hook.values() for hook in self.hooks])).encode()
        body = struct.pack(">I", len(header)) + header + b"".join(new for _, new in self.records)
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
        for offset, size in header["records"]:
            records.append((offset, body[pos:pos + size]))
            pos += size
        return cls(header["name"], header["title"], header["about"], header["order"],
                   bytes.fromhex(header["source_md5"]), header["source_size"], records,
                   [tuple(fill) for fill in header["fills"]], [Hook(*values) for values in header["hooks"]],
                   header["size"], path)

    def needs_rc2(self):
        return bool(self.fills)

    def applied(self, data):
        """Is this mod in the executable? (Its slots are compared as they are: they are linked;
        so is the RC2 data, which comes from the player's copy.)"""
        skip = [(hook.slot_off, 4) for hook in self.hooks if hook.slot] + [(fill[0], fill[3]) for fill in self.fills]
        for offset, new in self.records:
            have, want = bytearray(data[offset:offset + len(new)]), bytearray(new)
            if len(have) != len(want):
                return False
            for start, size in skip:
                lo, hi = max(start, offset), min(start + size, offset + len(new))
                if lo < hi:
                    want[lo - offset:hi - offset] = have[lo - offset:hi - offset]
            if have != want:
                return False
        return True


def link(source, patches, rc2=None):
    """The unmodified executable with these mods in it. rc2: RC2's data (rc2data.Rc2), needed
    by the mods that use it."""
    patches = sorted(patches, key=lambda patch: patch.order)
    out = bytearray(source)
    out.extend(bytes(max([len(out)] + [patch.size for patch in patches]) - len(out)))
    done = []                                               # (offset, bytes, mod)
    for patch in patches:
        for offset, new in patch.records:
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
    for patch in patches:
        if patch.fills and rc2 is None:
            raise ValueError(f"{patch.title} needs data of Ratchet & Clank 2 (see --rc2)")
        for offset, name, args, size, sha256 in patch.fills:
            try:
                piece = rc2data.extract(rc2, name, args, sha256)
            except rc2data.Missing as error:
                raise ValueError(str(error))
            if len(piece) != size:
                raise ValueError(f"{name}: unexpected size")
            out[offset:offset + size] = piece
    return bytes(out)


def md5(data):
    return hashlib.md5(data).digest()


def original_near(path, patches):
    """The unmodified executable among the files next to a patched one (the copy this patcher
    kept as .bak, RPCS3's decrypted EBOOT.elf, ...), or None."""
    folder = os.path.dirname(path)
    for name in (os.path.basename(path) + ".bak",) + NAMES:
        other = os.path.join(folder, name)
        if os.path.isfile(other) and os.path.getsize(other) == patches[0].source_size:
            with open(other, "rb") as f:
                data = f.read()
            if md5(data) == patches[0].source_md5:
                return data
    return None


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
    """-> (what the file is, the unmodified executable it stands for or None)"""
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError as error:
        return f"cannot be read ({error.strerror})", None
    if len(data) == patches[0].source_size and md5(data) == patches[0].source_md5:
        return "unmodified game executable: can be patched", data
    inside = [patch.title for patch in patches if patch.applied(data)]
    if inside:
        original = original_near(path, patches)
        if original:
            return "patched already (" + ", ".join(inside) + "): the choice can be changed", original
        return ("patched already (" + ", ".join(inside) + "), but the unmodified executable is not next to it: "
                "decrypt the game's EBOOT.BIN again, or patch the copy kept as .bak"), None
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
        needs = " - needs Ratchet & Clank 2's data" if patch.needs_rc2() else ""
        print(f"  [{number}] {patch.title} ({patch.name}){needs}\n      {patch.about}")


def find_rc2(source, given, interactive):
    """RC2's data: the folder given, rc2/ps3data next to the executable, or one typed in.
    -> rc2data.Rc2, or None to go without it."""
    folder = given or rc2data.find(source)
    if not folder and interactive:
        print("\nSome mods use data of Ratchet & Clank 2 (from the Trilogy disc), and it was not found")
        print("next to the executable. It is the folder rc2/ps3data in the disc's PS3_GAME/USRDIR.")
        while True:
            answer = ask("Path of that folder (empty to go without those mods): ")
            if not answer:
                return None
            try:
                return rc2data.Rc2(clean(answer))
            except rc2data.Missing as error:
                print(f"  {error}")
    if not folder:
        return None
    try:
        return rc2data.Rc2(clean(folder))
    except rc2data.Missing as error:
        if given:
            sys.exit(str(error))
        return None


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
    ap.add_argument("--rc2", help="Ratchet & Clank 2's data folder (rc2/ps3data of the Trilogy), for the mods that use it")
    args = ap.parse_args()

    patches = load_patches(args.patches)
    if args.list:
        list_mods(patches)
        return
    chosen = named_mods(args.mods, patches) if args.mods else None
    interactive = not (args.replace or args.output)

    if args.file:
        source = clean(args.file)
        what, original = describe(source, patches)
        if not original:
            sys.exit(f"{source}: {what}")
    else:
        source, original = choose_source(patches)
        what = describe(source, patches)[0]
    print(f"\n{source}\n      {what.split(':')[0]}")

    rc2 = None
    if any(patch.needs_rc2() for patch in chosen or patches):
        rc2 = find_rc2(source, args.rc2, interactive)
        print(f"\nRatchet & Clank 2's data: {rc2.folder}" if rc2 else "\nRatchet & Clank 2's data: not used")
    available = [patch for patch in patches if rc2 or not patch.needs_rc2()]
    if chosen is not None:
        missing = [patch.title for patch in chosen if patch not in available]
        if missing:
            sys.exit(f"{', '.join(missing)} need Ratchet & Clank 2's data (--rc2 FOLDER)")
    else:
        if len(available) < len(patches):
            print("left out without it: " + ", ".join(patch.title for patch in patches if patch not in available))
        chosen = choose_mods(available) if interactive else available
    if args.replace:
        target = source
    elif args.output:
        target = clean(args.output)
    else:
        target = choose_target(source)

    try:
        result = link(original, chosen, rc2)
    except ValueError as error:
        sys.exit(str(error))
    if not all(patch.applied(result) for patch in chosen) or any(patch.applied(result) for patch in patches if patch not in chosen and patch.records):
        sys.exit("the patched file does not check out; nothing was written")
    print("\nmods: " + (", ".join(patch.title for patch in chosen) or "none (the unmodified executable)"))
    write(target, result)
    if os.path.basename(target) != "EBOOT.BIN":
        print("RPCS3 boots the file named EBOOT.BIN in the game's USRDIR folder; copy the result there under that name.")
    print("Close RPCS3 completely and start it again to play the patched game.")


if __name__ == "__main__":
    main()
