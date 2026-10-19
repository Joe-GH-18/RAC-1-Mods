"""The Ratchet & Clank 2 data some mods use, taken from the player's own copy of the game, and
the data of RC1's own levels that a mod moves to others (Giant Clank).

Nothing of either game is in this repository or in the patch files. A patch file names what it
needs (an extract's name and its arguments, and the SHA-256 of the result); build.py and patch.py
extract it here from the game's data folder, `rc2/ps3data` next to RC1 in the Trilogy's USRDIR
for RC2 and `rc1/ps3data` next to the RC1 executable (Trilogy or PSN version) for RC1, and check
it against the hash. RC1_EXTRACTS names the extracts of RC1's data.

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
# Giant Clank (class 0x1a3, only in RC1's levels 15 and 18), from level 18: the model, and the
# textures of its mesh groups (mesh = model +0; +0 group count, +8 the groups, 0x10 bytes each
# with the texture id at +0).
GIANT_LEVEL, GIANT_CLASS = 18, 0x1A3


class Missing(Exception):
    """The game's data is not there, or not the version the mods were made with."""


class Rc2:
    """A game's data folder (RC2's, or RC1's with game "rc1"): the loose files, and PS3arc.psarc
    for the rest."""

    def __init__(self, folder, game="rc2"):
        self.folder, self.game = folder, game
        archive = os.path.join(folder, "PS3arc.psarc")
        if not os.path.isfile(archive):
            raise Missing(f"{folder}: no PS3arc.psarc (this is not {game.upper()}'s ps3data folder)")
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
                self.cache[name] = self._from_archive(f"/{self.game}/ps3data/" + name)
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


def _giant(rc1):
    """Giant Clank's model in level 18's engine.ps3 -> (the level file, offset, size): the size
    reaches to the next model of the model table (+0: its offset; count, then {id, offset})."""
    level = rc1.read(f"level{GIANT_LEVEL}/engine.ps3")
    table = struct.unpack_from(">I", level, 0)[0]
    count = struct.unpack_from(">I", level, table)[0]
    models = dict(struct.unpack_from(">II", level, table + 4 + 8 * i) for i in range(count))
    start = models[GIANT_CLASS]
    end = min([offset for offset in models.values() if offset > start] + [len(level)])
    return level, start, end - start


def _giant_textures(rc1):
    """The distinct texture ids of Giant Clank's mesh groups, in order, and each group's index in that list."""
    level, start, size = _giant(rc1)
    model = level[start:start + size]
    mesh = struct.unpack_from(">I", model, 0)[0]
    count, groups = struct.unpack_from(">I", model, mesh)[0], struct.unpack_from(">I", model, mesh + 8)[0]
    ids = [struct.unpack_from(">I", model, groups + 0x10 * i)[0] for i in range(count)]
    distinct = list(dict.fromkeys(ids))
    return distinct, [distinct.index(i) for i in ids]


def giant_model(rc1):
    """Giant Clank's model, its groups' texture ids cleared (the mod puts its own entries there)
    and without its 9 sounds (header +0xd the count, +0x28 the definitions): their places in the
    sound bank are filled in by the loader of his own levels only, and his animations playing
    them elsewhere crashed the sound update (0x15be68)."""
    level, start, size = _giant(rc1)
    model = bytearray(level[start:start + size])
    model[0xD] = 0
    struct.pack_into(">I", model, 0x28, 0)
    mesh = struct.unpack_from(">I", model, 0)[0]
    count, groups = struct.unpack_from(">I", model, mesh)[0], struct.unpack_from(">I", model, mesh + 8)[0]
    for i in range(count):
        struct.pack_into(">I", model, groups + 0x10 * i, 0)
    return bytes(model)


def giant_textures(rc1):
    """Giant Clank's textures: the group count, each group's texture (u8 each, padded to 8),
    then the texture entries with +0 the pixels' offset in giant_pixels."""
    distinct, uses = _giant_textures(rc1)
    level = rc1.read(f"level{GIANT_LEVEL}/engine.ps3")
    table = struct.unpack_from(">I", level, 0x54)[0]
    out = bytearray(bytes([len(uses)] + uses).ljust(8, b"\0"))
    at = 0
    for texture in distinct:
        entry = bytearray(level[table + 0x24 * texture:table + 0x24 * texture + 0x24])
        struct.pack_into(">I", entry, 0, at)
        at += _pixels_size(level, table, texture)
        out += entry
    return bytes(out)


def _pixels_size(level, table, texture):
    """A texture's pixels run to where the next texture's begin (the table is in vram.ps3 order)."""
    return struct.unpack_from(">I", level, table + 0x24 * (texture + 1))[0] - struct.unpack_from(">I", level, table + 0x24 * texture)[0]


def giant_pixels(rc1):
    """The pixels of Giant Clank's textures, one after the other (each 0x80-aligned in vram.ps3, so kept so)."""
    distinct, _ = _giant_textures(rc1)
    level, vram = rc1.read(f"level{GIANT_LEVEL}/engine.ps3"), rc1.read(f"level{GIANT_LEVEL}/vram.ps3")
    table = struct.unpack_from(">I", level, 0x54)[0]
    out = bytearray()
    for texture in distinct:
        at = struct.unpack_from(">I", level, table + 0x24 * texture)[0]
        out += vram[at:at + _pixels_size(level, table, texture)]
    return bytes(out)


def giant_part(rc1, ranges):
    """Giant Clank's index buffer with only the triangles of the bones in ranges ([first, last]
    pairs) left: the others are made empty (all three corners the same vertex). A vertex counts
    for the bone with its largest weight (vertices of 0x28 bytes: +0x20 four weights, +0x24 four
    bones), a triangle for the bone most of its corners count for. Model +0: mesh, mesh +0x10 and
    +0x14 the vertex and index buffers (u16 indices, model offsets), mesh +0 the group count and
    +8 the groups {texture, first index, index count, flags}."""
    level, start, size = _giant(rc1)
    model = level[start:start + size]
    mesh = struct.unpack_from(">I", model, 0)[0]
    vertices, indices = struct.unpack_from(">II", model, mesh + 0x10)
    count, groups = struct.unpack_from(">I", model, mesh)[0], struct.unpack_from(">I", model, mesh + 8)[0]
    total = max(sum(struct.unpack_from(">II", model, groups + 0x10 * g + 4)) for g in range(count))
    index = list(struct.unpack_from(f">{total}H", model, indices))

    def inside(v):
        at = vertices + 0x28 * v
        weights, bones = model[at + 0x20:at + 0x24], model[at + 0x24:at + 0x28]
        bone = bones[max(range(4), key=lambda i: weights[i])]
        return any(first <= bone <= last for first, last in ranges)

    for t in range(0, total - total % 3, 3):
        if sum(inside(v) for v in index[t:t + 3]) < 2:
            index[t + 1] = index[t + 2] = index[t]
    return struct.pack(f">{total}H", *index)


EXTRACTS = dict(animation=animation, charge_sounds=charge_sounds, boots_model=boots_model,
                boots_texture_entry=boots_texture_entry, boots_pixels=boots_pixels,
                giant_model=giant_model, giant_textures=giant_textures, giant_pixels=giant_pixels,
                giant_part=giant_part)
RC1_EXTRACTS = {"giant_model", "giant_textures", "giant_pixels", "giant_part"}


def game(name):
    """The game an extract is taken from: "rc1" or "rc2"."""
    return "rc1" if name in RC1_EXTRACTS else "rc2"


def extract(rc2, name, args, sha256=None):
    """One extract, checked against its hash when one is given."""
    try:
        data = EXTRACTS[name](rc2, *args)
    except (struct.error, ValueError, IndexError, KeyError) as error:
        raise Missing(f"{rc2.folder}: cannot extract {name} ({error})")
    if sha256 and hashlib.sha256(data).hexdigest() != sha256:
        raise Missing(f"{rc2.folder}: {name} is not what the mods expect (another version of {rc2.game.upper()}?)")
    return data


def find(near, game="rc2"):
    """A game's data folder for an RC1 executable at near: rc2/ps3data (or rc1/ps3data) in its
    folder (the Trilogy's USRDIR, or the PSN version's for RC1), or None."""
    folder = os.path.join(os.path.dirname(os.path.abspath(near)), game, "ps3data")
    return folder if os.path.isfile(os.path.join(folder, "PS3arc.psarc")) else None
