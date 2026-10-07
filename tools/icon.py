#!/usr/bin/env python3
"""Draw the Charge Boots menu icon and write it as the two 64x64 DXT5 textures build.py embeds.

The game's item icons come in two versions: a black shape for an item that is not in use and a
white one for the item worn. The background is taken from the Grindboots icon
(build/assets/icons/grindboots{0,1}.png, decoded from level1/vram.ps3 at 0xcc080 and 0xcd080):
a plane is fitted to its red pixels per colour channel. Needs Pillow (system python3 has it).
Writes build/assets/boots/charge_icon{0,1}.bin and a preview, build/assets/icons/charge_boots.png.
"""
import os

from PIL import Image, ImageDraw

from dxt import decode, encode

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "build", "assets")
SIZE, SCALE = 64, 8

# Shapes in icon pixels: a boot seen from the side, toe to the right, hovering over a ground
# line, with the jet's streaks behind the heel.
BOOT = [(27, 5), (41, 5), (41, 25), (45, 30), (54, 33), (58, 38), (58, 44), (21, 44), (21, 36), (27, 29)]
STREAKS = [[(7, 24), (20, 24), (20, 27), (10, 27)], [(1, 31), (17, 31), (17, 35), (4, 35)], [(6, 39), (17, 39), (17, 43), (9, 43)]]
GROUND = [(14, 51), (62, 49), (62, 54), (14, 56)]


def background(reference):
    """The reference icon's gradient without its shape: least squares plane through its red pixels."""
    px = reference.load()
    rows = [(x, y, px[x, y]) for y in range(SIZE) for x in range(SIZE) if px[x, y][0] > 180 and px[x, y][1] < 175 and px[x, y][0] - px[x, y][1] > 60]
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


def shape():
    mask = Image.new("L", (SIZE * SCALE, SIZE * SCALE), 0)
    draw = ImageDraw.Draw(mask)
    for polygon in [BOOT, GROUND] + STREAKS:
        draw.polygon([(x * SCALE, y * SCALE) for x, y in polygon], fill=255)
    return mask.resize((SIZE, SIZE), Image.LANCZOS)


def main():
    mask, preview = shape(), Image.new("RGBA", (SIZE * 8, SIZE * 4))
    for version, colour in enumerate(((16, 16, 16, 255), (244, 244, 244, 255))):
        reference = Image.open(os.path.join(ASSETS, "icons", f"grindboots{version}.png")).convert("RGBA")
        icon = background(reference)
        icon.paste(Image.new("RGBA", (SIZE, SIZE), colour), (0, 0), mask)
        data = encode([[icon.getpixel((x, y)) for x in range(SIZE)] for y in range(SIZE)])
        with open(os.path.join(ASSETS, "boots", f"charge_icon{version}.bin"), "wb") as f:
            f.write(data)
        shown = Image.new("RGBA", (SIZE, SIZE))
        shown.putdata([p for row in decode(data, SIZE, SIZE) for p in row])      # as the game will show it
        preview.paste(shown.resize((SIZE * 4, SIZE * 4), Image.NEAREST), (version * SIZE * 4, 0))
    preview.save(os.path.join(ASSETS, "icons", "charge_boots.png"))


if __name__ == "__main__":
    main()
