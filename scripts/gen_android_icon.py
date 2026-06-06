#!/usr/bin/env python3
"""Generate Android adaptive-icon foreground PNGs from the KIS school crest.

Renders the crest centered on a TRANSPARENT square canvas (so the white adaptive
background layer shows around/behind it) at every launcher density. The launcher
composites foreground over @color/ic_launcher_background and applies the device
mask. Re-run this after swapping the crest image.

Source : packages/design-system/brand/crest-full.png  (the exact school logo)
Output : android/app/src/main/res/drawable-<density>/ic_launcher_foreground.png

Requires Pillow (already installed in this environment).
"""
import os
from PIL import Image

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "packages/design-system/brand/crest-full.png")
RES = os.path.join(REPO, "android/app/src/main/res")

# Adaptive foreground is a 108dp square. Pixel size per density bucket:
DENSITIES = {"mdpi": 108, "hdpi": 162, "xhdpi": 216, "xxhdpi": 324, "xxxhdpi": 432}
# Crest width as a fraction of the canvas. The crest is ~circular within a 5:4
# frame, so ~0.94 fills the icon nicely while the circular emblem stays within
# the always-visible zone of circular masks.
SCALE = 0.94


def main():
    crest = Image.open(SRC).convert("RGBA")
    cw, ch = crest.size
    for name, px in DENSITIES.items():
        canvas = Image.new("RGBA", (px, px), (0, 0, 0, 0))
        target_w = int(round(px * SCALE))
        target_h = int(round(target_w * ch / cw))
        resized = crest.resize((target_w, target_h), Image.Resampling.LANCZOS)
        ox = (px - target_w) // 2
        oy = (px - target_h) // 2
        canvas.alpha_composite(resized, (ox, oy))
        out_dir = os.path.join(RES, f"drawable-{name}")
        os.makedirs(out_dir, exist_ok=True)
        out = os.path.join(out_dir, "ic_launcher_foreground.png")
        canvas.save(out)
        print(f"wrote {out}  ({px}x{px}, crest {target_w}x{target_h})")


if __name__ == "__main__":
    main()
