#!/usr/bin/env python3
"""Patch Ratchet & Clank HD (NPEA00385) with the mods of this repository.

    python patch.py                    look for the game's executable, ask which one to patch
    python patch.py FILE               patch that file (it is asked where the result goes)
    python patch.py FILE -o OUT        write the result to OUT without asking anything
    python patch.py FILE --replace     put the result in FILE's place; the original is kept
                                       next to it once as FILE.bak

The file has to be the game's decrypted executable: the EBOOT.elf that RPCS3 writes with
Utilities > Decrypt PS3 Binaries from the game's USRDIR/EBOOT.BIN, or RC1.ppu.elf decrypted
from the Trilogy disc. The result is a plain ELF; RPCS3 boots it when it is named EBOOT.BIN
in the game's USRDIR folder.

Needs nothing but Python 3. The changes come from the patch file in patches/, which build.py
writes (--export); see README.md.
"""
import argparse
import glob
import hashlib
import os
import shutil
import struct
import sys
import zlib

ROOT = os.path.dirname(os.path.abspath(__file__))
MAGIC = b"BBRC1\x01"
GAME = "NPEA00385"
NAMES = ("EBOOT.elf", "EBOOT.BIN", "EBOOT.elf.bak", "EBOOT.BIN.bak", "RC1.ppu.elf")
# Where RPCS3 keeps installed games, per platform; a portable RPCS3 has dev_hdd0 next to itself.
GAME_FOLDERS = (
    "~/.config/rpcs3/dev_hdd0/game",
    "~/.var/app/net.rpcs3.RPCS3/config/rpcs3/dev_hdd0/game",
    "~/Library/Application Support/rpcs3/dev_hdd0/game",
    "dev_hdd0/game",
)


class Patch:
    def __init__(self, path):
        self.path = path
        data = open(path, "rb").read()
        if not data.startswith(MAGIC):
            raise ValueError(f"{path} is not a patch file")
        body = zlib.decompress(data[len(MAGIC):])
        self.source_md5, self.result_md5 = body[:16], body[16:32]
        self.source_size, self.result_size, count = struct.unpack_from(">QQI", body, 32)
        self.records, pos = [], 52
        for _ in range(count):
            offset, length = struct.unpack_from(">QI", body, pos)
            self.records.append((offset, body[pos + 12:pos + 12 + length]))
            pos += 12 + length

    def apply(self, source):
        out = bytearray(source)
        out.extend(bytes(self.result_size - len(out)))
        for offset, data in self.records:
            out[offset:offset + len(data)] = data
        if hashlib.md5(out).digest() != self.result_md5:
            raise ValueError("the patched file does not have the expected checksum")
        return bytes(out)


def describe(path, patches):
    """-> (what the file is, the patch that fits or None)"""
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError as error:
        return f"cannot be read ({error.strerror})", None
    md5 = hashlib.md5(data).digest()
    for patch in patches:
        if md5 == patch.source_md5:
            return "unmodified game executable: can be patched", patch
    for patch in patches:
        if md5 == patch.result_md5:
            return "already patched with " + os.path.basename(patch.path), None
    if data[:4] == b"SCE\0":
        return "still encrypted: decrypt it in RPCS3 first (Utilities > Decrypt PS3 Binaries)", None
    if data[:4] == b"\x7fELF":
        return "an executable, but not the supported one (another game, region, or already modified)", None
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
        what, patch = describe(path, patches)
        if patch:
            usable.append((path, patch))
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
        what, patch = describe(path, patches)
        if patch:
            return path, patch
        print(f"  {path}\n      {what}")


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
    ap.add_argument("--patch", help="the patch file (default: the ones in patches/)")
    args = ap.parse_args()

    paths = [args.patch] if args.patch else sorted(glob.glob(os.path.join(ROOT, "patches", "*.bbpatch")))
    if not paths:
        sys.exit("no patch file in patches/; build one with build.py --export (see README.md)")
    patches = [Patch(path) for path in paths]

    if args.file:
        source = clean(args.file)
        what, patch = describe(source, patches)
        if not patch:
            sys.exit(f"{source}: {what}")
    else:
        source, patch = choose_source(patches)
    print(f"\n{source}\n      unmodified game executable; applying {os.path.basename(patch.path)}")

    if args.replace:
        target = source
    elif args.output:
        target = clean(args.output)
    else:
        target = choose_target(source)

    with open(source, "rb") as f:
        result = patch.apply(f.read())
    write(target, result)
    if os.path.basename(target) != "EBOOT.BIN":
        print("RPCS3 boots the file named EBOOT.BIN in the game's USRDIR folder; copy the result there under that name.")
    print("Close RPCS3 completely and start it again to play the patched game.")


if __name__ == "__main__":
    main()
