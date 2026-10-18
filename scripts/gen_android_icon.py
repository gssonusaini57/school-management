#!/usr/bin/env python3
"""Generate Android adaptive-icon foreground PNGs from the KIS school crest.

The launcher icon shows ONLY the round emblem (yellow ring + Khanda), not the
red "AFFILIATED TO P.S.E.B." ribbon that sits under it in crest-full.png. The
ribbon is wider than the icon viewport, so on a masked adaptive icon it used to
appear as a cropped red band along the bottom edge.

Steps
  1. open packages/design-system/brand/crest-full.png (the exact school logo);
  2. find the emblem's circle - the ribbon is the only thing outside it and it
     sits entirely below it, so every opaque row in the upper part of the
     image is a chord of the circle;
  3. make everything outside that circle transparent and crop to it;
  4. draw the emblem centred on a TRANSPARENT 108 dp canvas at 66 dp, the
     adaptive-icon safe zone, so no launcher mask (circle, squircle, teardrop)
     clips its black outline - at every launcher density. The launcher
     composites this over @color/ic_launcher_background (white) and masks it.

Output : android/app/src/main/res/drawable-<density>/ic_launcher_foreground.png
Re-run after swapping the crest image:  /usr/bin/python3 scripts/gen_android_icon.py
Requires Pillow (the macOS system python3 has it).
"""
import math
import os

from PIL import Image, ImageChops, ImageDraw

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "packages/design-system/brand/crest-full.png")
RES = os.path.join(REPO, "android/app/src/main/res")

# Adaptive foreground is a 108 dp square. Pixel size per density bucket:
DENSITIES = {"mdpi": 108, "hdpi": 162, "xhdpi": 216, "xxhdpi": 324, "xxxhdpi": 432}
CANVAS_DP = 108
EMBLEM_DP = 66          # adaptive-icon safe-zone diameter
EDGE_PAD_PX = 1.0       # keep the outline's own anti-aliased edge inside the mask
SUPERSAMPLE = 4         # anti-aliasing for the circular mask
ALPHA_ON = 128          # alpha threshold for "opaque" when measuring the circle


def find_emblem_circle(im):
    """Return (cx, cy, r) of the round emblem, in source pixels.

    The widest chord in the top 60 % of the image is the diameter (its midpoint
    is cx). Every narrower chord then gives one estimate of cy through
    (y - cy)^2 = r^2 - hw^2, and those estimates are averaged.
    """
    w, h = im.size
    alpha = im.getchannel("A").load()
    chords = []  # (y, half-width, midpoint)
    for y in range(h * 6 // 10):
        xs = [x for x in range(w) if alpha[x, y] > ALPHA_ON]
        if xs:
            chords.append((y, (xs[-1] - xs[0] + 1) / 2, (xs[0] + xs[-1]) / 2))
    if len(chords) < 50:
        raise SystemExit("could not find the emblem: too few opaque rows")
    r = max(hw for _, hw, _ in chords)
    if not (0.2 * w < r < 0.5 * w):
        raise SystemExit(f"implausible emblem radius {r:.1f}px for a {w}px-wide crest")
    equator = [y for y, hw, _ in chords if hw >= r - 0.5]
    y_mid = sum(equator) / len(equator)
    cx = sorted(m for _, _, m in chords)[len(chords) // 2]
    estimates = []
    for y, hw, _ in chords:
        if hw < r - 2:  # chords away from the equator pin cy down best
            off = math.sqrt(r * r - hw * hw)
            estimates.append(y + off if y < y_mid else y - off)
    cy = sum(estimates) / len(estimates) if estimates else y_mid
    return cx, cy, r


def cut_emblem(im, cx, cy, r):
    """Square RGBA tile holding just the emblem; everything outside its circle is transparent."""
    rad = r + EDGE_PAD_PX
    side = int(math.ceil(2 * rad)) + 2
    x0 = int(round(cx - side / 2))
    y0 = int(round(cy - side / 2))
    tile = im.crop((x0, y0, x0 + side, y0 + side))  # out-of-bounds areas come back transparent
    big = Image.new("L", (side * SUPERSAMPLE, side * SUPERSAMPLE), 0)
    ccx, ccy, rr = (cx - x0) * SUPERSAMPLE, (cy - y0) * SUPERSAMPLE, rad * SUPERSAMPLE
    ImageDraw.Draw(big).ellipse((ccx - rr, ccy - rr, ccx + rr, ccy + rr), fill=255)
    mask = big.resize((side, side), Image.Resampling.LANCZOS)
    tile.putalpha(ImageChops.multiply(tile.getchannel("A"), mask))
    return tile


def main():
    crest = Image.open(SRC).convert("RGBA")
    cx, cy, r = find_emblem_circle(crest)
    print(f"emblem circle in {os.path.relpath(SRC, REPO)}: centre ({cx:.1f}, {cy:.1f}) radius {r:.1f}px")
    emblem = cut_emblem(crest, cx, cy, r)
    for name, px in DENSITIES.items():
        canvas = Image.new("RGBA", (px, px), (0, 0, 0, 0))
        d = int(round(px * EMBLEM_DP / CANVAS_DP))
        off = (px - d) // 2
        canvas.alpha_composite(emblem.resize((d, d), Image.Resampling.LANCZOS), (off, off))
        out_dir = os.path.join(RES, f"drawable-{name}")
        os.makedirs(out_dir, exist_ok=True)
        out = os.path.join(out_dir, "ic_launcher_foreground.png")
        canvas.save(out, optimize=True)
        print(f"wrote {os.path.relpath(out, REPO)}  ({px}x{px}, emblem {d}px = {EMBLEM_DP}dp)")


if __name__ == "__main__":
    main()
