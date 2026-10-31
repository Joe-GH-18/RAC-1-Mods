#!/usr/bin/env python3
"""icon.py [charge|zapper]: draw the mods' own pause menu icons and write each as the two 64x64
DXT5 textures its mod embeds (both without an argument).

The game's item icons come in two versions: a black shape for an item that is not in use and a
white one for the item worn. The background is taken from an icon of the same grid, a plane
fitted to its coloured pixels per colour channel:
  charge  the Charge Boots (Foot Items, mods/chargeboots/art/charge_icon{0,1}.bin), on the
          Grindboots icon's red (build/assets/icons/grindboots{0,1}.png, decoded from
          level1/vram.ps3 at 0xcc080 and 0xcd080)
  zapper  the Clank Zapper (Back Packs, mods/coop/art/zapper_icon{0,1}.bin), on the Heli-Pack
          icon's yellow (icon 0xea62, decoded from the player's level1 files by rc2data.py)
Needs Pillow (system python3 has it). Writes a preview of each, build/assets/icons/<name>.png.
"""
import os
import struct
import sys

from PIL import Image, ImageDraw

from dxt import decode, encode

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ASSETS = os.path.join(ROOT, "build", "assets")   # extracted game files (not in the repository)
SIZE, SCALE = 64, 8

# Shapes in icon pixels: polygons, and circles (centre x, y, radius) to fill or cut out.
# Charge Boots: a boot seen from the side, toe to the right, hovering over a ground line, with the
# jet's streaks behind the heel.
BOOT = [(27, 5), (41, 5), (41, 25), (45, 30), (54, 33), (58, 38), (58, 44), (21, 44), (21, 36), (27, 29)]
STREAKS = [[(7, 24), (20, 24), (20, 27), (10, 27)], [(1, 31), (17, 31), (17, 35), (4, 35)], [(6, 39), (17, 39), (17, 43), (9, 43)]]
GROUND = [(14, 51), (62, 49), (62, 54), (14, 56)]
# Clank Zapper: Clank's head from the front (wide, the round eyes cut out, the antenna with its
# ball) over his body, and a lightning bolt beside him.
HEAD = (6, 18, 42, 42, 11)                        # rounded box: x0, y0, x1, y1, corner radius
EYES = [(16, 30, 6), (32, 30, 6)]
ANTENNA = [(23, 7), (25, 7), (25, 19), (23, 19)]
BALL = (24, 6, 4)
BODY = [(14, 44), (34, 44), (32, 60), (16, 60)]
BOLT = [(55, 2), (42, 30), (50, 30), (39, 62), (62, 24), (54, 24), (61, 2)]


def red(p):
    """The Grindboots icon's red (as it was chosen for the Charge Boots)."""
    return p[0] > 180 and p[1] < 175 and p[0] - p[1] > 60


def coloured(p):
    """Neither the white or black shape nor its grey edge: a strong colour."""
    return max(p[:3]) - min(p[:3]) > 70


def background(reference, keep):
    """The reference icon's gradient without its shape: least squares plane through its pixels that keep() takes."""
    px = reference.load()
    rows = [(x, y, px[x, y]) for y in range(SIZE) for x in range(SIZE) if keep(px[x, y])]
    n = len(rows)
    sx, sy = sum(r[0] for r in rows), sum(r[1] for r in rows)
    sxx, syy, sxy = sum(r[0] ** 2 for r in rows), sum(r[1] ** 2 for r in rows), sum(r[0] * r[1] for r in rows)
    det = n * (sxx * syy - sxy ** 2) - sx * (sx * syy - sxy * sy) + sy * (sx * sxy - sxx * sy)
    planes = []
    for c in range(3):
        sv, sxv, syv = sum(r[2][c] for r in rows), sum(r[0] * r[2][c] for r in rows), sum(r[1] * r[2][c] for r in rows)
        a = (sv * (sxx * syy - sxy ** 2) - sx * (sxv * syy - sxy * syv) + sy * (sxv * sxy - sxx * syv)) / det
        b = (n * (sxv * syy - syv * sxy) - sv * (sx * syy - sxy * sy) + sy * (sx * syv - sxv * sy)) / det
        k = (n * (sxx * syv - sxy * sxv) - sx * (sx * syv - sxv * sy) + sv * (sx * sxy - sxx * sy)) / det
        planes.append((a, b, k))
    out = Image.new("RGBA", (SIZE, SIZE))
    out.putdata([tuple(max(0, min(255, round(a + b * x + k * y))) for a, b, k in planes) + (255,) for y in range(SIZE) for x in range(SIZE)])
    return out


def charge_shape(draw, s):
    for polygon in [BOOT, GROUND] + STREAKS:
        draw.polygon([(x * s, y * s) for x, y in polygon], fill=255)


def zapper_shape(draw, s):
    x0, y0, x1, y1, r = HEAD
    draw.rounded_rectangle((x0 * s, y0 * s, x1 * s, y1 * s), radius=r * s, fill=255)
    for polygon in (ANTENNA, BODY, BOLT):
        draw.polygon([(x * s, y * s) for x, y in polygon], fill=255)
    cx, cy, cr = BALL
    draw.ellipse(((cx - cr) * s, (cy - cr) * s, (cx + cr) * s, (cy + cr) * s), fill=255)
    for cx, cy, cr in EYES:
        draw.ellipse(((cx - cr) * s, (cy - cr) * s, (cx + cr) * s, (cy + cr) * s), fill=0)


def mask(draw_shape):
    big = Image.new("L", (SIZE * SCALE, SIZE * SCALE), 0)
    draw_shape(ImageDraw.Draw(big), SCALE)
    return big.resize((SIZE, SIZE), Image.LANCZOS)


def grindboots(version):
    return Image.open(os.path.join(ASSETS, "icons", f"grindboots{version}.png")).convert("RGBA")


def game_icon(icon_id):
    """-> function(version) -> the game's icon icon_id as an image, from the player's level 1."""
    sys.path.insert(0, ROOT)
    from rc2data import Rc2
    rc1 = Rc2(os.path.join(os.path.dirname(open(os.path.join(ROOT, "rc1_elf.path")).read().strip()), "rc1", "ps3data"), "rc1")
    engine, vram = rc1.read("level1/engine.ps3"), rc1.read("level1/vram.ps3")
    table = struct.unpack_from(">I", engine, 0x54)[0]          # the texture table: 0x24 bytes an entry, +0 the pixels in vram.ps3
    at = 0xA0                                                 # the HUD's icons {id, versions, first sprite, -} (NOTES.md)
    while struct.unpack_from(">H", engine, at)[0] != icon_id:
        at += 8
    first = struct.unpack_from(">H", engine, at + 4)[0]

    def image(version):
        texture = struct.unpack_from(">i", engine, 0x270 + 4 * (first + version))[0]
        pixels = struct.unpack_from(">I", engine, table + 0x24 * texture)[0]
        out = Image.new("RGBA", (SIZE, SIZE))
        out.putdata([p for row in decode(vram[pixels:pixels + SIZE * SIZE], SIZE, SIZE) for p in row])
        return out
    return image


ICONS = {   # name: (shape, reference icon by version, its background pixels, folder, file name)
    "charge": (charge_shape, lambda: grindboots, red, os.path.join(ROOT, "mods", "chargeboots", "art"), "charge_icon", "charge_boots"),
    "zapper": (zapper_shape, lambda: game_icon(0xEA62), coloured, os.path.join(ROOT, "mods", "coop", "art"), "zapper_icon", "clank_zapper"),
}


def make(name):
    draw_shape, reference, keep, folder, stem, preview_name = ICONS[name]
    shape, preview, reference = mask(draw_shape), Image.new("RGBA", (SIZE * 8, SIZE * 4)), reference()
    os.makedirs(folder, exist_ok=True)
    for version, colour in enumerate(((16, 16, 16, 255), (244, 244, 244, 255))):
        icon = background(reference(version), keep)
        icon.paste(Image.new("RGBA", (SIZE, SIZE), colour), (0, 0), shape)
        data = encode([[icon.getpixel((x, y)) for x in range(SIZE)] for y in range(SIZE)])
        with open(os.path.join(folder, f"{stem}{version}.bin"), "wb") as f:
            f.write(data)
        shown = Image.new("RGBA", (SIZE, SIZE))
        shown.putdata([p for row in decode(data, SIZE, SIZE) for p in row])      # as the game will show it
        preview.paste(shown.resize((SIZE * 4, SIZE * 4), Image.NEAREST), (version * SIZE * 4, 0))
    os.makedirs(os.path.join(ASSETS, "icons"), exist_ok=True)
    preview.save(os.path.join(ASSETS, "icons", f"{preview_name}.png"))


def main():
    for name in sys.argv[1:] or ICONS:
        make(name)


if __name__ == "__main__":
    main()
