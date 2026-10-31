#!/usr/bin/env python3
"""bank2wav.py <sound.bnk> <folder>: write every sound of a sound bank as <folder>/sNNN.wav, to listen through.

NNN is the sound's index in the bank (what a model sound definition carries at +0x1a once the
level is loaded). The bank's layout is described in rc2data.py (sound_bank); it is a
bank of Sony's SCREAM library. A sound is a list of grains, 8 bytes each: type << 24 | offset of
its data, then the ticks (1/240 s) to wait behind it. A tone grain (type 1) starts a sample:
+1 volume, +2/+3 centre note and fine, +0x10/+0x14 the sample; it is played at note 60, which
for the negative centre notes these banks use is 48000 Hz * 2^((60 - (-note + fine / 128)) / 12).
Each sound is written as the game would start it: its tones mixed at their times and pitches,
mono at 48000 Hz. Of the grains that pick one of the next few at random (type 0x30, first data
byte the number) the first choice is taken; pitch bends and the like are left out.
"""
import os
import struct
import sys
import wave

FILTERS = ((0, 0), (60, 0), (115, -52), (98, -55), (122, -60))


def decode(data):
    out, a, b = [], 0, 0
    for at in range(0, len(data) - 15, 16):
        shift, which, flags = data[at] & 15, data[at] >> 4, data[at + 1]
        if flags == 7:
            break
        f0, f1 = FILTERS[which] if which < 5 else (0, 0)
        for byte in data[at + 2:at + 16]:
            for nibble in (byte & 15, byte >> 4):
                value = (nibble - 16 if nibble & 8 else nibble) << 12 >> shift if shift <= 12 else 0
                value += (a * f0 + b * f1) >> 6
                value = max(-32768, min(32767, value))
                out.append(value)
                a, b = value, a
        if flags & 1:
            break
    return struct.pack(f"<{len(out)}h", *out)


RATE = 48000
SECONDS = 8


def resampled(pcm, rate, volume):
    """16-bit samples at rate -> floats at RATE."""
    count = len(pcm) // 2
    data = struct.unpack(f"<{count}h", pcm)
    step = rate / RATE
    out = []
    for i in range(int(count / step)):
        at = i * step
        k = int(at)
        nxt = data[k + 1] if k + 1 < count else 0
        out.append((data[k] + (nxt - data[k]) * (at - k)) * volume)
    return out


class Bank:
    """A sound bank's sounds (src: the whole .bnk file)."""

    def __init__(self, src):
        self.src = src
        block_off, block_size, self.sample_off = struct.unpack_from(">3I", src, 8)
        self.block = block = src[block_off:block_off + block_size]
        self.count = struct.unpack_from(">I", block, 0x14)[0]
        self.sounds, self.grains, self.grain_data = (struct.unpack_from(">I", block, at)[0] for at in (0x1C, 0x20, 0x34))
        self.decoded = {}

    def grain_list(self, index):
        """The sound's grains: (kind, data offset in the block, ticks to wait behind it)."""
        sound = self.sounds + 12 * index
        first = struct.unpack_from(">I", self.block, sound + 8)[0]
        out = []
        for g in range(self.block[sound + 4]):
            op, wait = struct.unpack_from(">II", self.block, self.grains + first + 8 * g)
            out.append((op >> 24, self.grain_data + (op & 0xFFFFFF), wait))
        return out

    def tone(self, data):
        """A tone grain's sample bytes and its volume, note, fine."""
        volume, note, fine = self.block[data + 1], struct.unpack_from("b", self.block, data + 2)[0], self.block[data + 3]
        off, size = struct.unpack_from(">II", self.block, data + 0x10)
        return self.src[self.sample_off + off:self.sample_off + off + size], volume, note, fine

    def fingerprint(self, index):
        """What makes the sound the same in another bank: its grains' kinds, waits and settings and
        its samples' bytes, not where they lie in the bank."""
        parts = []
        for kind, data, wait in self.grain_list(index):
            parts.append(struct.pack(">BI", kind, wait))
            if kind == 1:
                sample, volume, note, fine = self.tone(data)
                parts += [self.block[data:data + 0x10], sample]
            elif kind == 0x30:
                parts.append(self.block[data:data + 1])
        return b"".join(parts)

    def render(self, index):
        """The sound as the game would start it: 16-bit mono samples at RATE (empty when silent)."""
        mix, ticks, skip, grains = [], 0, 0, self.grain_list(index)
        g = 0
        while g < len(grains):
            kind, data, wait = grains[g]
            g += 1
            if kind == 0x30:                       # one of the next few: the first
                skip = self.block[data] - 1
                continue
            if kind == 1:
                sample, volume, note, fine = self.tone(data)
                rate = 48000 * 2 ** ((60 - (-note + fine / 128)) / 12) if note < 0 else 44100 * 2 ** ((60 - (note + fine / 128)) / 12)
                key = struct.unpack_from(">II", self.block, data + 0x10)
                if key not in self.decoded:
                    self.decoded[key] = decode(sample)
                tone = resampled(self.decoded[key], rate, volume / 127)
                start = ticks * RATE // 240
                if start < SECONDS * RATE:
                    tone = tone[:SECONDS * RATE - start]
                    mix += [0.0] * (start + len(tone) - len(mix))
                    for i, value in enumerate(tone):
                        mix[start + i] += value
                if skip:                           # the other choices
                    g, skip = g + skip, 0
            ticks += wait
        if not mix:
            return b""
        peak = max(1.0, max(abs(v) for v in mix) / 32767)
        return struct.pack(f"<{len(mix)}h", *(int(v / peak) for v in mix))


def write_wav(path, pcm):
    with wave.open(path, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes(pcm)


def main(path, folder):
    bank = Bank(open(path, "rb").read())
    os.makedirs(folder, exist_ok=True)
    written = 0
    for index in range(bank.count):
        pcm = bank.render(index)
        if pcm:
            write_wav(os.path.join(folder, f"s{index:03d}.wav"), pcm)
            written += 1
    print(f"{written} sounds of {bank.count} in {folder}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
