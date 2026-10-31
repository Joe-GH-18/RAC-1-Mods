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
import math
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


def level_animation(rc1, level, index, vaddr):
    """Ratchet's animation index from an RC1 level (one that has it: some are only in the levels
    that use them, as the pose riding Giant Clank's back, 129, in levels 0, 15 and 18), for the
    address vaddr, its frame pointers made absolute, as animation."""
    data = rc1.read(f"level{level}/engine.ps3")
    table = struct.unpack_from(">I", data, 0x18)[0]
    offsets = struct.unpack_from(f">{ANIMATIONS}I", data, table)
    start = offsets[index]
    anim = bytearray(data[start:min([o for o in offsets if o > start] + [len(data)])])
    for i in range(anim[0x10]):
        at = 0x1C + 4 * i
        struct.pack_into(">I", anim, at, struct.unpack_from(">I", anim, at)[0] + vaddr)
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


def level_sound_bank(rc1, level, indices):
    """An RC1 level's sound bank cut down to the samples of these of its sounds (the co-op Clank's
    picks that other levels lack: mods/coop/layout.OWN_BANKS)."""
    defs = [struct.pack(">26xH4x", index) for index in indices]
    return sound_bank(rc1, level, defs)


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


def _model(rc1, level, cls):
    """A class's model in an RC1 level's engine.ps3 -> (the level file, offset, size): the size
    reaches to the next model of the model table (+0: its offset; count, then {id, offset})."""
    data = rc1.read(f"level{level}/engine.ps3")
    table = struct.unpack_from(">I", data, 0)[0]
    count = struct.unpack_from(">I", data, table)[0]
    models = dict(struct.unpack_from(">II", data, table + 4 + 8 * i) for i in range(count))
    start = models[cls]
    end = min([offset for offset in models.values() if offset > start] + [len(data)])
    return data, start, end - start


def _giant(rc1, cls=GIANT_CLASS):
    """Giant Clank's model (or another class's of his level, as his missile's) in level 18."""
    return _model(rc1, GIANT_LEVEL, cls)


def _model_textures(rc1, level, cls):
    """The distinct texture ids of the model's mesh groups, in order, and each group's index in that list."""
    data, start, size = _model(rc1, level, cls)
    model = data[start:start + size]
    mesh = struct.unpack_from(">I", model, 0)[0]
    count, groups = struct.unpack_from(">I", model, mesh)[0], struct.unpack_from(">I", model, mesh + 8)[0]
    ids = [struct.unpack_from(">I", model, groups + 0x10 * i)[0] for i in range(count)]
    distinct = list(dict.fromkeys(ids))
    return distinct, [distinct.index(i) for i in ids]


def _giant_textures(rc1, cls=GIANT_CLASS):
    return _model_textures(rc1, GIANT_LEVEL, cls)


def level_model(rc1, level, cls):
    """A class's model of an RC1 level, for a mod to install in every level: its groups' texture
    ids cleared (the mod puts its own entries there) and without its sounds (header +0xd the
    count, +0x28 the definitions): their places in the sound bank are filled in by the loader
    of its own levels only, and Giant Clank's animations playing them elsewhere crashed the
    sound update (0x15be68)."""
    data, start, size = _model(rc1, level, cls)
    model = bytearray(data[start:start + size])
    model[0xD] = 0
    struct.pack_into(">I", model, 0x28, 0)
    mesh = struct.unpack_from(">I", model, 0)[0]
    count, groups = struct.unpack_from(">I", model, mesh)[0], struct.unpack_from(">I", model, mesh + 8)[0]
    for i in range(count):
        struct.pack_into(">I", model, groups + 0x10 * i, 0)
    return bytes(model)


def giant_model(rc1, cls=GIANT_CLASS):
    """Giant Clank's model (or cls's of his level 18), as level_model."""
    return level_model(rc1, GIANT_LEVEL, cls)


def giant_sounds(rc1, classes):
    """The sound definitions of these classes' models in level 18 (Giant Clank's 9, his missile's
    1), one after the other, each with its sound in level 18's bank at +0x1a (the level loader
    puts it there from engine.ps3 header +0x48: {u16 offset, u16 count} a model in the model
    table's order from +8, to u32 bank sounds), then from the next 16 bytes that bank cut down to
    their samples (sound_bank)."""
    level = rc1.read(f"level{GIANT_LEVEL}/engine.ps3")
    table = struct.unpack_from(">I", level, 0)[0]
    count = struct.unpack_from(">I", level, table)[0]
    models = [struct.unpack_from(">II", level, table + 4 + 8 * i) for i in range(count)]
    remap = struct.unpack_from(">I", level, 0x48)[0]
    defs = []
    for cls in classes:
        index, model = next((i, at) for i, (c, at) in enumerate(models) if c == cls)
        n = level[model + 0xD]
        at = model + struct.unpack_from(">I", level, model + 0x28)[0]
        offset, listed = struct.unpack_from(">HH", level, remap + 8 + 4 * index)
        if listed != n:
            raise ValueError(f"class {cls:#x}: {n} sounds, {listed} in the level's list")
        for k in range(n):
            d = bytearray(level[at + 32 * k:at + 32 * k + 32])
            struct.pack_into(">H", d, 0x1A, struct.unpack_from(">I", level, remap + offset + 4 * k)[0])
            defs.append(bytes(d))
    head = b"".join(defs)
    return head + bytes(-len(head) % 16) + sound_bank(rc1, GIANT_LEVEL, defs)


def level_textures(rc1, level, cls):
    """A level model's textures: the group count, each group's texture (u8 each, padded to 8),
    then the texture entries with +0 the pixels' offset in level_pixels."""
    distinct, uses = _model_textures(rc1, level, cls)
    data = rc1.read(f"level{level}/engine.ps3")
    table = struct.unpack_from(">I", data, 0x54)[0]
    out = bytearray(bytes([len(uses)] + uses).ljust(8, b"\0"))
    at = 0
    for texture in distinct:
        entry = bytearray(data[table + 0x24 * texture:table + 0x24 * texture + 0x24])
        struct.pack_into(">I", entry, 0, at)
        at += _pixels_size(data, table, texture)
        out += entry
    return bytes(out)


def giant_textures(rc1, cls=GIANT_CLASS):
    """Giant Clank's textures (or cls's), as level_textures."""
    return level_textures(rc1, GIANT_LEVEL, cls)


def _pixels_size(level, table, texture):
    """A texture's pixels run to where the next texture's begin (the table is in vram.ps3 order)."""
    return struct.unpack_from(">I", level, table + 0x24 * (texture + 1))[0] - struct.unpack_from(">I", level, table + 0x24 * texture)[0]


def level_pixels(rc1, level, cls):
    """The pixels of a level model's textures, one after the other (each 0x80-aligned in vram.ps3, so kept so)."""
    distinct, uses = _model_textures(rc1, level, cls)
    data, vram = rc1.read(f"level{level}/engine.ps3"), rc1.read(f"level{level}/vram.ps3")
    table = struct.unpack_from(">I", data, 0x54)[0]
    out = bytearray()
    for texture in distinct:
        at = struct.unpack_from(">I", data, table + 0x24 * texture)[0]
        pixels = vram[at:at + _pixels_size(data, table, texture)]
        if level == GIANT_LEVEL and cls == GIANT_CLASS:
            group = uses.index(distinct.index(texture))
            pixels = _lift(rc1, group, data[table + 0x24 * texture:table + 0x24 * texture + 0x24], pixels)
        out += pixels
    return bytes(out)


def giant_pixels(rc1, cls=GIANT_CLASS):
    """The pixels of Giant Clank's textures (or cls's). His own have the dark metal of his
    shoulders and of the ball made light (_lift)."""
    return level_pixels(rc1, GIANT_LEVEL, cls)


# The mod tints his parts gold, which turns his light grey metal gold but his dark metal brown:
# the hubs his arms swing from (the shoulder ring, bone 33, and the disc on the upper arm, bone
# 35, mirrored 53 and 55) were dark brown discs with orange patches beside the gold. Their
# texels (of mesh group 0) are made a light grey (LIFT: grey = base + scale * luminance) at
# every mipmap level; the disc's screw head (u beyond 0.5), which the thighs use too, is left.
# So is the ball the mod joins them to Clank with (the outer half of bone 4's hip joint, beyond
# y = 1.8, as the mod's BALL; group 3): its texels are shared only with the rest of that joint.
HUB_GROUP, HUB_BONES, HUB_DISC_BONES, LIFT = 0, (33, 53), (35, 55), (140, 0.45)
BALL_GROUP, BALL_BONE, BALL_CUT = 3, 4, 1.8


def _lifted(group, corners, side):
    """Whether a triangle of group (corners: u, v in texels, bone, model y) is one whose texels are lightened."""
    bones = [c[2] for c in corners]
    bone = max(set(bones), key=bones.count)
    if group == HUB_GROUP:
        return bone in HUB_BONES or (bone in HUB_DISC_BONES and all(c[0] < side / 2 for c in corners))
    return group == BALL_GROUP and all(c[2] == BALL_BONE and c[3] > BALL_CUT for c in corners)


def _lift(rc1, group, entry, pixels):
    """A DXT5 texture of his (entry: +4 levels, +0x18 width, height), group's, with the texels _lifted lightened."""
    if group not in (HUB_GROUP, BALL_GROUP):
        return pixels
    level, start, size = _giant(rc1)
    model = level[start:start + size]
    mesh = struct.unpack_from(">I", model, 0)[0]
    vertices, indices = struct.unpack_from(">II", model, mesh + 0x10)
    first, count = struct.unpack_from(">II", model, struct.unpack_from(">I", model, mesh + 8)[0] + 0x10 * group + 4)
    index = struct.unpack_from(f">{count}H", model, indices + 2 * first)
    side = struct.unpack_from(">H", entry, 0x18)[0]
    levels = entry[5]

    def corner(v):
        at = vertices + 0x28 * v
        weights, bones = model[at + 0x20:at + 0x24], model[at + 0x24:at + 0x28]
        u, w = struct.unpack_from(">2f", model, at + 0x18)
        return u % 1.0 * side, w * side, bones[max(range(4), key=lambda i: weights[i])], struct.unpack_from(">f", model, at + 4)[0]

    mask = set()
    for t in range(0, count - count % 3, 3):
        corners = [corner(v) for v in index[t:t + 3]]
        if not _lifted(group, corners, side):
            continue
        (x0, y0, _, _), (x1, y1, _, _), (x2, y2, _, _) = corners
        area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
        if not area:
            continue
        for y in range(max(int(min(y0, y1, y2)), 0), min(int(max(y0, y1, y2)) + 1, side)):
            for x in range(max(int(min(x0, x1, x2)), 0), min(int(max(x0, x1, x2)) + 1, side)):
                px, py = x + 0.5, y + 0.5
                a = ((x1 - px) * (y2 - py) - (x2 - px) * (y1 - py)) / area
                b = ((x2 - px) * (y0 - py) - (x0 - px) * (y2 - py)) / area
                if min(a, b, 1 - a - b) >= 0:
                    mask.add((x, y))
    mask = {(x + dx, y + dy) for x, y in mask for dx in range(-2, 3) for dy in range(-2, 3)}    # (two texels beyond the edges)
    base, scale = LIFT
    out, at = bytearray(pixels), 0
    for step in range(levels):
        size = max(side >> step, 1)
        blocks = max(size // 4, 1)
        if size >= 4:
            hit = {(x * size // side // 4, y * size // side // 4) for x, y in mask}
            for by, bx in ((by, bx) for by in range(blocks) for bx in range(blocks) if (bx, by) in hit):
                block = at + 16 * (by * blocks + bx)
                rows = _dxt5_colours(out[block:block + 16], 4)
                for j in range(4):
                    for i in range(4):
                        x, y = (bx * 4 + i) * side // size, (by * 4 + j) * side // size
                        if any((x + dx, y + dy) in mask for dx in range(side // size) for dy in range(side // size)):
                            r, g, b = rows[j][i]
                            grey = min(255, int(base + scale * (0.299 * r + 0.587 * g + 0.114 * b)))
                            rows[j][i] = (grey, grey, grey)
                out[block + 8:block + 16] = _dxt5(rows)[8:]       # (the block's alpha kept)
        at += 16 * blocks * blocks
    return bytes(out)


CLANK_LEVEL, CLANK_CLASS = 1, 0x259     # backpack Clank, in every level


def _clank_texture(rc1):
    """The texture of backpack Clank's mesh group 1, his eyes (one texture for all of him) ->
    (level 1's engine.ps3, its entry offset, its pixels' offset in vram.ps3, their size)."""
    level = rc1.read(f"level{CLANK_LEVEL}/engine.ps3")
    table = struct.unpack_from(">I", level, 0)[0]
    count = struct.unpack_from(">I", level, table)[0]
    models = dict(struct.unpack_from(">II", level, table + 4 + 8 * i) for i in range(count))
    model = models[CLANK_CLASS]
    mesh = model + struct.unpack_from(">I", level, model)[0]
    texture = struct.unpack_from(">I", level, model + struct.unpack_from(">I", level, mesh + 8)[0] + 0x10)[0]
    entries = struct.unpack_from(">I", level, 0x54)[0]
    at = struct.unpack_from(">I", level, entries + 0x24 * texture)[0]
    return level, entries + 0x24 * texture, at, _pixels_size(level, entries, texture)


def _dxt5_colours(data, size):
    """The RGB of a DXT5 texture's top level, size x size (alpha left out) -> rows of (r, g, b)."""
    def rgb(c):
        return ((c >> 11) * 255 + 15) // 31, (((c >> 5) & 63) * 255 + 31) // 63, ((c & 31) * 255 + 15) // 31
    rows = [[None] * size for _ in range(size)]
    at = 0
    for by in range(0, size, 4):
        for bx in range(0, size, 4):
            c0, c1, bits = struct.unpack_from("<HHI", data, at + 8)
            at += 16
            p0, p1 = rgb(c0), rgb(c1)
            colours = [p0, p1, tuple((2 * a + b) // 3 for a, b in zip(p0, p1)), tuple((a + 2 * b) // 3 for a, b in zip(p0, p1))]
            for i in range(16):
                rows[by + i // 4][bx + i % 4] = colours[(bits >> (2 * i)) & 3]
    return rows


def _dxt5(rows):
    """Rows of (r, g, b), opaque, sides multiples of 4 (or less: padded) -> DXT5 blocks."""
    size = len(rows)
    out = bytearray()
    for by in range(0, max(size, 4), 4):
        for bx in range(0, max(size, 4), 4):
            px = [rows[min(by + i // 4, size - 1)][min(bx + i % 4, size - 1)] for i in range(16)]
            out += bytes((255, 255)) + bytes(6)
            hi = tuple(max(p[c] for p in px) for c in range(3))
            lo = tuple(min(p[c] for p in px) for c in range(3))
            c0 = (hi[0] * 31 // 255 << 11) | (hi[1] * 63 // 255 << 5) | hi[2] * 31 // 255
            c1 = (lo[0] * 31 // 255 << 11) | (lo[1] * 63 // 255 << 5) | lo[2] * 31 // 255
            if c0 < c1:
                c0, c1 = c1, c0
            bits = 0
            if c0 != c1:
                ends = [hi, lo, tuple((2 * a + b) // 3 for a, b in zip(hi, lo)), tuple((a + 2 * b) // 3 for a, b in zip(hi, lo))]
                bits = sum(min(range(4), key=lambda k: sum((ends[k][c] - p[c]) ** 2 for c in range(3))) << (2 * i)
                           for i, p in enumerate(px))
            out += struct.pack("<HHI", c0, c1, bits)
    return bytes(out)


EYES_SIZE = 128


def clank_gold_eyes(rc1):
    """Backpack Clank's texture in gold, at EYES_SIZE (a texture of the same size and format as
    his own showed his own green eyes in the game, though its memory held the gold) with its
    mipmaps: only his eyes' group is pointed at it, which samples only their corner. -> its texture
    entry (+0 the pixels' offset, 0; levels and size its own) and from +0x80 the pixels."""
    level, entry, at, size = _clank_texture(rc1)
    head = bytearray(level[entry:entry + 0x24])
    side = struct.unpack_from(">H", head, 0x18)[0]
    rows = _dxt5_colours(rc1.read(f"level{CLANK_LEVEL}/vram.ps3")[at:at + side * side], side)
    step = side // EYES_SIZE
    small = [[tuple(sum(rows[y * step + j][x * step + i][c] for j in range(step) for i in range(step)) // (step * step)
                    for c in range(3)) for x in range(EYES_SIZE)] for y in range(EYES_SIZE)]

    def gold(p):                    # gold of its brightness, brightened: his eyes glow
        light = 0.3 * p[0] + 0.59 * p[1] + 0.11 * p[2]
        return tuple(min(255, int(light * k)) for k in (1.7, 1.3, 0.35))

    level_rows = [[gold(p) for p in row] for row in small]
    pixels, levels = bytearray(), 0
    while True:
        pixels += _dxt5(level_rows)
        levels += 1
        if len(level_rows) == 1:
            break
        half = len(level_rows) // 2
        level_rows = [[tuple(sum(level_rows[2 * y + j][2 * x + i][c] for j in (0, 1) for i in (0, 1)) // 4 for c in range(3))
                       for x in range(half)] for y in range(half)]
    struct.pack_into(">I", head, 0, 0)
    head[5] = levels
    struct.pack_into(">HH", head, 0x18, EYES_SIZE, EYES_SIZE)
    return bytes(head) + bytes(-len(head) % 0x80) + bytes(pixels)


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


def _giant_ball(rc1, bone, cut):
    """A whole ball from a hemisphere of Giant Clank's: the triangles of bone whose corners all lie
    beyond the plane y = cut (the outer half of a joint, its inner half inside the next piece),
    taken about the centre of their base (the lowest y) and mirrored through it. -> (his vertex buffer with the
    ball's vertices first, an index buffer of his length with only the ball's triangles, at the
    start of the group the hemisphere is in)."""
    level, start, size = _giant(rc1)
    model = level[start:start + size]
    mesh = struct.unpack_from(">I", model, 0)[0]
    vertices, indices = struct.unpack_from(">II", model, mesh + 0x10)
    count, groups = struct.unpack_from(">I", model, mesh)[0], struct.unpack_from(">I", model, mesh + 8)[0]
    spans = [struct.unpack_from(">II", model, groups + 0x10 * g + 4) for g in range(count)]
    total = max(first + length for first, length in spans)
    index = struct.unpack_from(f">{total}H", model, indices)

    def vertex(v):
        at = vertices + 0x28 * v
        weights, bones = model[at + 0x20:at + 0x24], model[at + 0x24:at + 0x28]
        return struct.unpack_from(">3f", model, at), bones[max(range(4), key=lambda i: weights[i])]

    cap, group = [], None
    for t in range(0, total - total % 3, 3):
        corners = [vertex(v) for v in index[t:t + 3]]
        if all(b == bone and p[1] > cut for p, b in corners):
            cap.append(index[t:t + 3])
            group = next(g for g, (first, length) in enumerate(spans) if first <= t < first + length)
    used = sorted({v for triangle in cap for v in triangle})
    points = [vertex(v)[0] for v in used]
    centre = (sum(p[0] for p in points) / len(points), min(p[1] for p in points), sum(p[2] for p in points) / len(points))
    out = bytearray(model[vertices:indices])
    new = {}
    for side in (1, -1):                            # the hemisphere, then its mirror image
        for v in used:
            at = vertices + 0x28 * v
            x, y, z, nx, ny, nz = struct.unpack_from(">6f", model, at)
            new[side, v] = len(new)
            struct.pack_into(">6f", out, 0x28 * new[side, v], x - centre[0], side * (y - centre[1]), z - centre[2], nx, side * ny, nz)
            out[0x28 * new[side, v] + 0x18:0x28 * new[side, v] + 0x28] = model[at + 0x18:at + 0x28]
    ball = [new[1, v] for triangle in cap for v in triangle] + [new[-1, v] for a, b, c in cap for v in (a, c, b)]
    first = spans[group][0]
    assert len(ball) <= spans[group][1]
    index = [0] * total
    index[first:first + len(ball)] = ball
    return bytes(out), struct.pack(f">{total}H", *index)


def giant_ball_vertices(rc1, bone, cut):
    """The vertex buffer of _giant_ball."""
    return _giant_ball(rc1, bone, cut)[0]


def _profile_at(profile, t):
    """A tube's radius at t (0..1 along it): a Catmull-Rom curve through profile's (t, radius) points."""
    i = next(i for i in range(len(profile) - 1) if t <= profile[i + 1][0])
    t0, t1 = profile[i][0], profile[i + 1][0]
    u = (t - t0) / (t1 - t0)
    p0, p1 = profile[max(i - 1, 0)][1], profile[i][1]
    p2, p3 = profile[i + 1][1], profile[min(i + 2, len(profile) - 1)][1]
    return 0.5 * (2 * p1 + (p2 - p0) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (3 * p1 - p0 - 3 * p2 + p3) * u ** 3)


TUBE_UV = ((-0.14, -0.10), (0.52, 0.70))   # a plain light patch of his shoulder ring's texture (group 0, lifted)
TUBE_GROUP = 0


def _giant_tubes(rc1, tubes):
    """Smooth tubes in place of his forearm pistons (rods along y from the elbow's end to the
    hand's): one mesh each, rings of `sides` vertices at `steps` + 1 places along the piston,
    their radius following a profile ((t, radius as a share of the piston's length), t = 0 at the
    elbow's end) as a smooth curve, normals from the curve, the texture a plain patch of his
    shoulder ring's (TUBE_UV), bound wholly to the piston's bone (bone 67 and the rest of the right
    side mirrored in y). tubes: [(bone, profile, sides, steps)]. The corners overwrite his vertex
    buffer from the start (only the tubes' index buffers use this one; the mesh's count stays).
    -> (that vertex buffer, [[triangles of vertex numbers] for each tube])."""
    level, start, size = _giant(rc1)
    model = level[start:start + size]
    mesh = struct.unpack_from(">I", model, 0)[0]
    vertices, indices = struct.unpack_from(">II", model, mesh + 0x10)
    count, groups = struct.unpack_from(">I", model, mesh)[0], struct.unpack_from(">I", model, mesh + 8)[0]
    spans = [struct.unpack_from(">II", model, groups + 0x10 * g + 4) for g in range(count)]
    total = max(first + length for first, length in spans)
    index = struct.unpack_from(f">{total}H", model, indices)

    def owner(v):
        at = vertices + 0x28 * v
        weights, owners = model[at + 0x20:at + 0x24], model[at + 0x24:at + 0x28]
        return owners[max(range(4), key=lambda i: weights[i])]

    out, made, at = bytearray(model[vertices:indices]), [], 0
    (u0, u1), (v0, v1) = TUBE_UV
    for bone, profile, sides, steps in tubes:
        rod = {v for t in range(0, total - total % 3, 3) for v in index[t:t + 3] if owner(v) == bone}
        points = [struct.unpack_from(">3f", model, vertices + 0x28 * v) for v in rod]
        mid_x = (min(p[0] for p in points) + max(p[0] for p in points)) / 2
        mid_z = (min(p[2] for p in points) + max(p[2] for p in points)) / 2
        inner, outer = min(abs(p[1]) for p in points), max(abs(p[1]) for p in points)
        length, sign = outer - inner, -1 if min(p[1] for p in points) < 0 else 1
        first = at
        for k in range(steps + 1):
            t = k / steps
            radius = _profile_at(profile, t) * length
            slope = (_profile_at(profile, min(t + 0.01, 1)) - _profile_at(profile, max(t - 0.01, 0))) / \
                (min(t + 0.01, 1) - max(t - 0.01, 0))           # dr/dt in shares of the length: = dr/dy
            for j in range(sides + 1):                          # (the seam twice, for the texture)
                angle = 2 * math.pi * j / sides
                c, s = math.cos(angle), math.sin(angle)
                n = math.sqrt(1 + slope * slope)
                struct.pack_into(">3f3f2f", out, 0x28 * at,
                                 mid_x + radius * c, sign * (inner + t * length), mid_z + radius * s,
                                 c / n, sign * -slope / n, s / n,
                                 u0 + (u1 - u0) * j / sides, v0 + (v1 - v0) * t)
                out[0x28 * at + 0x20:0x28 * at + 0x28] = bytes((255, 0, 0, 0, bone, 0, 0, 0))
                at += 1
        triangles = []
        for k in range(steps):
            for j in range(sides):
                a, b = first + k * (sides + 1) + j, first + k * (sides + 1) + j + 1
                c, d = a + sides + 1, b + sides + 1
                for tri in ((a, c, b), (b, c, d)):              # outward for y up the rod
                    triangles.append(tri if sign > 0 else (tri[0], tri[2], tri[1]))
        made.append(triangles)
    assert at <= len(out) // 0x28
    return bytes(out), made


def giant_tube_vertices(rc1, tubes):
    """The vertex buffer of _giant_tubes."""
    return _giant_tubes(rc1, tubes)[0]


def giant_tube_indices(rc1, tubes, which):
    """An index buffer of his length with only tube `which` of _giant_tubes in it (in TUBE_GROUP)."""
    level, start, size = _giant(rc1)
    model = level[start:start + size]
    mesh = struct.unpack_from(">I", model, 0)[0]
    count, groups = struct.unpack_from(">I", model, mesh)[0], struct.unpack_from(">I", model, mesh + 8)[0]
    spans = [struct.unpack_from(">II", model, groups + 0x10 * g + 4) for g in range(count)]
    total = max(first + length for first, length in spans)
    first, length = spans[TUBE_GROUP]
    triangles = _giant_tubes(rc1, tubes)[1][which]
    assert 3 * len(triangles) <= length
    index = [0] * total
    for k, tri in enumerate(triangles):
        index[first + 3 * k:first + 3 * k + 3] = tri
    return struct.pack(f">{total}H", *index)


def giant_ball_indices(rc1, bone, cut):
    """The index buffer of _giant_ball."""
    return _giant_ball(rc1, bone, cut)[1]


EXTRACTS = dict(animation=animation, charge_sounds=charge_sounds, boots_model=boots_model,
                boots_texture_entry=boots_texture_entry, boots_pixels=boots_pixels,
                giant_model=giant_model, giant_textures=giant_textures, giant_pixels=giant_pixels,
                giant_part=giant_part, giant_ball_vertices=giant_ball_vertices, giant_ball_indices=giant_ball_indices,
                giant_tube_vertices=giant_tube_vertices, giant_tube_indices=giant_tube_indices, clank_gold_eyes=clank_gold_eyes,
                giant_sounds=giant_sounds, level_model=level_model, level_textures=level_textures,
                level_pixels=level_pixels, level_animation=level_animation, level_sound_bank=level_sound_bank)
RC1_EXTRACTS = {"level_model", "level_textures", "level_pixels", "giant_model", "giant_textures", "giant_pixels", "giant_part", "giant_ball_vertices", "giant_ball_indices",
                "giant_tube_vertices", "giant_tube_indices", "clank_gold_eyes",
                "giant_sounds", "level_animation", "level_sound_bank"}


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
