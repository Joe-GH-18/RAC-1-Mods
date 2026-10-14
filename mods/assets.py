"""The data taken from Ratchet & Clank 2 that the mods embed, kept in assets/."""
import os
import struct

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")


def asset(*name):
    with open(os.path.join(ASSETS, *name), "rb") as f:
        return f.read()


def rc2_animation(index, vaddr):
    """One of RC2's Ratchet animations, relocated for vaddr. Extracted once from RC2's archive."""
    cache = os.path.join(ASSETS, f"rc2_anim{index}.bin")
    if not os.path.exists(cache):
        from psarc import Psarc
        level = Psarc("rc2").read("/rc2/ps3data/level1/engine.ps3")
        table = struct.unpack_from(">I", level, 0x18)[0]       # player animation table
        offsets = struct.unpack_from(">157I", level, table)
        start = offsets[index]
        end = min(o for o in offsets if o > start)
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        with open(cache, "wb") as f:
            f.write(level[start:end])
    anim = bytearray(asset(f"rc2_anim{index}.bin"))
    frames = anim[0x10]
    for i in range(frames):                                    # frame pointers become absolute
        off = 0x1C + 4 * i
        struct.pack_into(">I", anim, off, struct.unpack_from(">I", anim, off)[0] + vaddr)
    anim[0x13] = 0                                             # RC1 animations have 0 here, RC2's 0xff
    return bytes(anim)


def rc2_sound_bank(level, definitions, name):
    """One RC2 level sound bank cut down to the sample data of the sounds that the model sound
    definitions (32 bytes each, the bank's sound index at +0x1a) play; kept in assets/ as name.

    File: 8 u32 (3, 2, block offset, block size, sample offset, sample size), then the 'SBlk'
    block: header (+0x14 sound count, +0x18 grain count << 16 | sample count, +0x1c sounds,
    +0x20 grains, +0x28/+0x2c sample size, +0x34 grain data), 12-byte sounds (+4 grain count,
    +8 first grain), 8-byte grains (type << 24 | data offset; type 1 is a tone), and tone
    records with the sample offset at +0x10 and its size at +0x14.
    """
    cache = os.path.join(ASSETS, name)                          # the cut-down bank, kept with the source
    if os.path.exists(cache):
        return open(cache, "rb").read()
    from ppu import RC1_ELF                                    # tools/ppu.py: the bank is cut from the game folders next to the ELF
    src = open(os.path.join(os.path.dirname(RC1_ELF), "rc2", "ps3data", f"level{level}", "sound.bnk"), "rb").read()
    block_off, block_size, sample_off = struct.unpack_from(">3I", src, 8)
    block = bytearray(src[block_off:block_off + block_size])
    sounds, grains, grain_data = struct.unpack_from(">I", block, 0x1C)[0], struct.unpack_from(">I", block, 0x20)[0], struct.unpack_from(">I", block, 0x34)[0]
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
    with open(cache, "wb") as f:
        f.write(out + samples)
    return bytes(out + samples)
