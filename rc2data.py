"""The Ratchet & Clank 2 data some mods use, taken from the player's own copy of the game.

Nothing of RC2 is in this repository or in the patch files. A patch file names what it needs
(an extract's name and its arguments, and the SHA-256 of the result); build.py and patch.py
extract it here from RC2's data folder, `rc2/ps3data` next to RC1 in the Trilogy's USRDIR, and
check it against the hash.

Python standard library only, like patch.py.
"""
import hashlib
import lzma
import os
import struct

# Ratchet's animations: level file engine.ps3 header +0x18 is the player animation table
# (file offsets, one per animation of model 0).
ANIMATIONS = 157
# The Charge Boots (class 0xe70) in level 1: the model's place in engine.ps3, its texture's
# entry in the texture table (header +0x54; 0x24 bytes each, +0 the pixels' offset in vram.ps3)
# and the size of its pixels (256x256, 9 mip levels).
BOOTS_MODEL = (0x12CFDC0, 0x15800)
BOOTS_TEXTURE = 774
BOOTS_PIXELS = 0x15580
# The charge's sounds: Ratchet's sound definitions 13 (the loop) and 9 (the end), 32 bytes each
# from model 0's table (+0x28) in level 5, where they play level-bank sounds 24 and 20. A
# definition's +0x1a is its sound in the bank; the level loader fills it in, so it is put here.
SOUND_LEVEL = 5
SOUND_DEFS = ((13, 24), (9, 20))


class Missing(Exception):
    """RC2's data is not there, or not the version the mods were made with."""


class Rc2:
    """RC2's data folder: the loose files, and PS3arc.psarc for the rest."""

    def __init__(self, folder):
        self.folder = folder
        archive = os.path.join(folder, "PS3arc.psarc")
        if not os.path.isfile(archive):
            raise Missing(f"{folder}: no PS3arc.psarc (this is not RC2's ps3data folder)")
        self.archive = archive
        self.files, self.cache = None, {}

    def read(self, name):
        """A file of the folder by its path below ps3data, e.g. 'level1/engine.ps3'."""
        if name not in self.cache:
            loose = os.path.join(self.folder, *name.split("/"))
            if os.path.isfile(loose):
                with open(loose, "rb") as f:
                    self.cache[name] = f.read()
            else:
                self.cache[name] = self._from_archive("/rc2/ps3data/" + name)
        return self.cache[name]

    def names(self):
        """The archive's file names (full paths, '/rc2/ps3data/level1/engine.ps3')."""
        self._table()
        return list(self.files)

    def _table(self):
        """PSARC with LZMA blocks: header, table of entries {.., u32 first block, u40 length,
        u40 offset}, then the block sizes (u16, 0 for a full block); entry 0 lists the names."""
        if self.files is not None:
            return
        with open(self.archive, "rb") as f:
            magic, _, kind, toc_len, entry_size, entries, self.block = struct.unpack(">4sI4sIIII", f.read(28))
            f.read(4)
            if magic != b"PSAR" or kind != b"lzma":
                raise Missing(f"{self.archive}: not an archive of the expected kind")
            toc = f.read(toc_len - 32)
            table = []
            for i in range(entries):
                e = toc[i * entry_size:(i + 1) * entry_size]
                table.append((struct.unpack(">I", e[16:20])[0], int.from_bytes(e[20:25], "big"), int.from_bytes(e[25:30], "big")))
            count = (toc_len - 32 - entries * entry_size) // 2
            self.blocks = struct.unpack(f">{count}H", toc[entries * entry_size:entries * entry_size + 2 * count])
            names = self._entry(f, table[0]).decode("latin1").split("\n")
            self.files = dict(zip(names, table[1:]))

    def _from_archive(self, name):
        self._table()
        if name not in self.files:
            raise Missing(f"{self.archive}: no {name}")
        with open(self.archive, "rb") as f:
            return self._entry(f, self.files[name])

    def _entry(self, f, entry):
        block, length, offset = entry
        out = bytearray()
        f.seek(offset)
        while len(out) < length:
            size = self.blocks[block] or self.block
            data = f.read(size)
            block += 1
            if size == self.block:
                out += data
                continue
            try:
                out += lzma.decompress(data)
            except lzma.LZMAError:
                out += data
        return bytes(out[:length])


def animation(rc2, index, vaddr):
    """Ratchet's animation index from level 1, for the address vaddr: its frame pointers made
    absolute, and +0x13 cleared (0 in RC1's animations, 0xff in RC2's)."""
    level = rc2.read("level1/engine.ps3")
    table = struct.unpack_from(">I", level, 0x18)[0]
    offsets = struct.unpack_from(f">{ANIMATIONS}I", level, table)
    start = offsets[index]
    anim = bytearray(level[start:min(o for o in offsets if o > start)])
    for i in range(anim[0x10]):
        at = 0x1C + 4 * i
        struct.pack_into(">I", anim, at, struct.unpack_from(">I", anim, at)[0] + vaddr)
    anim[0x13] = 0
    return bytes(anim)


def sound_bank(rc2, level, definitions):
    """The sound bank of an RC2 level cut down to the samples of these definitions' sounds.

    File: 8 u32 (3, 2, block offset, block size, sample offset, sample size), then the 'SBlk'
    block: header (+0x1c sounds, +0x20 grains, +0x28/+0x2c sample size, +0x34 grain data),
    12-byte sounds (+4 grain count, +8 first grain), 8-byte grains (type << 24 | data offset;
    type 1 is a tone), and tone records with the sample offset at +0x10 and its size at +0x14.
    """
    src = rc2.read(f"level{level}/sound.bnk")
    block_off, block_size, sample_off = struct.unpack_from(">3I", src, 8)
    block = bytearray(src[block_off:block_off + block_size])
    sounds, grains = struct.unpack_from(">II", block, 0x1C)
    grain_data = struct.unpack_from(">I", block, 0x34)[0]
    samples, moved = bytearray(), {}
    for definition in definitions:
        sound = sounds + 12 * struct.unpack_from(">H", definition, 0x1A)[0]
        count, first = block[sound + 4], struct.unpack_from(">I", block, sound + 8)[0]
        for g in range(count):
            op = struct.unpack_from(">I", block, grains + first + 8 * g)[0]
            if op >> 24 != 1:
                continue
            tone = grain_data + (op & 0xFFFFFF)
            off, size = struct.unpack_from(">II", block, tone + 0x10)
            if off not in moved:
                moved[off] = len(samples)
                samples += src[sample_off + off:sample_off + off + size]
                samples += bytes(-len(samples) % 16)
            struct.pack_into(">I", block, tone + 0x10, moved[off])
    struct.pack_into(">II", block, 0x28, len(samples), len(samples))
    new_sample_off = (0x20 + len(block) + 15) & ~15
    out = bytearray(struct.pack(">8I", 3, 2, 0x20, len(block), new_sample_off, len(samples), 0, 0))
    out += block
    out += bytes(new_sample_off - len(out))
    return bytes(out + samples)


def charge_sounds(rc2):
    """The charge's two sound definitions, followed by the bank with their samples."""
    level = rc2.read(f"level{SOUND_LEVEL}/engine.ps3")
    models = struct.unpack_from(">I", level, 0)[0]
    ratchet = struct.unpack_from(">I", level, models + 8)[0]            # model 0, the first {id, offset}
    table = ratchet + struct.unpack_from(">I", level, ratchet + 0x28)[0]
    defs = []
    for index, sound in SOUND_DEFS:
        d = bytearray(level[table + 32 * index:table + 32 * index + 32])
        struct.pack_into(">H", d, 0x1A, sound)
        defs.append(bytes(d))
    return b"".join(defs) + sound_bank(rc2, SOUND_LEVEL, defs)


def boots_model(rc2):
    """The Charge Boots model, its two texture ids cleared (the mod puts its own entry there)."""
    start, size = BOOTS_MODEL
    model = bytearray(rc2.read("level1/engine.ps3")[start:start + size])
    mesh = struct.unpack_from(">I", model, 0)[0]
    groups = struct.unpack_from(">I", model, mesh + 8)[0]
    struct.pack_into(">I", model, groups, 0)
    struct.pack_into(">I", model, groups + 0x10, 0)
    return bytes(model)


def boots_texture_entry(rc2):
    level = rc2.read("level1/engine.ps3")
    table = struct.unpack_from(">I", level, 0x54)[0] + 0x24 * BOOTS_TEXTURE
    return level[table:table + 0x24]


def boots_pixels(rc2):
    at = struct.unpack_from(">I", boots_texture_entry(rc2), 0)[0]
    return rc2.read("level1/vram.ps3")[at:at + BOOTS_PIXELS]


EXTRACTS = dict(animation=animation, charge_sounds=charge_sounds, boots_model=boots_model,
                boots_texture_entry=boots_texture_entry, boots_pixels=boots_pixels)


def extract(rc2, name, args, sha256=None):
    """One extract, checked against its hash when one is given."""
    try:
        data = EXTRACTS[name](rc2, *args)
    except (struct.error, ValueError, IndexError, KeyError) as error:
        raise Missing(f"{rc2.folder}: cannot extract {name} ({error})")
    if sha256 and hashlib.sha256(data).hexdigest() != sha256:
        raise Missing(f"{rc2.folder}: {name} is not what the mods expect (another version of RC2?)")
    return data


def find(near):
    """RC2's data folder for an RC1 executable at near: rc2/ps3data in its folder (the Trilogy's
    USRDIR), or None."""
    folder = os.path.join(os.path.dirname(os.path.abspath(near)), "rc2", "ps3data")
    return folder if os.path.isfile(os.path.join(folder, "PS3arc.psarc")) else None
