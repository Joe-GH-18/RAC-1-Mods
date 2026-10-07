"""DXT5 (the PS3's COMPRESSED_DXT45, format byte 0x88) to and from RGBA pixels, for the HUD icons."""
import struct


def _565(c):
    return ((c >> 11) * 255 + 15) // 31, (((c >> 5) & 63) * 255 + 31) // 63, ((c & 31) * 255 + 15) // 31


def decode(data, width, height):
    """-> list of rows of (r, g, b, a)"""
    rows = [[None] * width for _ in range(height)]
    pos = 0
    for by in range(0, height, 4):
        for bx in range(0, width, 4):
            a0, a1 = data[pos], data[pos + 1]
            abits = int.from_bytes(data[pos + 2:pos + 8], "little")
            c0, c1, cbits = struct.unpack_from("<HHI", data, pos + 8)
            pos += 16
            if a0 > a1:
                alphas = [a0, a1] + [((7 - i) * a0 + i * a1) // 7 for i in range(1, 7)]
            else:
                alphas = [a0, a1] + [((5 - i) * a0 + i * a1) // 5 for i in range(1, 5)] + [0, 255]
            p0, p1 = _565(c0), _565(c1)
            colors = [p0, p1, tuple((2 * a + b) // 3 for a, b in zip(p0, p1)), tuple((a + 2 * b) // 3 for a, b in zip(p0, p1))]
            for i in range(16):
                rows[by + i // 4][bx + i % 4] = colors[(cbits >> (2 * i)) & 3] + (alphas[(abits >> (3 * i)) & 7],)
    return rows


def encode(rows):
    """rows of (r, g, b, a), width and height multiples of 4 -> DXT5 data"""
    out = bytearray()
    for by in range(0, len(rows), 4):
        for bx in range(0, len(rows[0]), 4):
            px = [rows[by + i // 4][bx + i % 4] for i in range(16)]
            a0, a1 = max(p[3] for p in px), min(p[3] for p in px)
            if a0 == a1:
                alphas, abits = [a0] * 8, 0
            else:
                alphas = [a0, a1] + [((7 - i) * a0 + i * a1) // 7 for i in range(1, 7)]
                abits = sum(min(range(8), key=lambda k: abs(alphas[k] - p[3])) << (3 * i) for i, p in enumerate(px))
            out += bytes((a0, a1)) + abits.to_bytes(6, "little")
            hi = tuple(max(p[c] for p in px) for c in range(3))
            lo = tuple(min(p[c] for p in px) for c in range(3))
            c0 = (hi[0] * 31 // 255 << 11) | (hi[1] * 63 // 255 << 5) | hi[2] * 31 // 255
            c1 = (lo[0] * 31 // 255 << 11) | (lo[1] * 63 // 255 << 5) | lo[2] * 31 // 255
            if c0 < c1:
                c0, c1 = c1, c0
            if c0 == c1:
                cbits = 0
            else:
                p0, p1 = _565(c0), _565(c1)
                colors = [p0, p1, tuple((2 * a + b) // 3 for a, b in zip(p0, p1)), tuple((a + 2 * b) // 3 for a, b in zip(p0, p1))]
                cbits = sum(min(range(4), key=lambda k: sum((colors[k][c] - p[c]) ** 2 for c in range(3))) << (2 * i)
                            for i, p in enumerate(px))
            out += struct.pack("<HHI", c0, c1, cbits)
    return bytes(out)
