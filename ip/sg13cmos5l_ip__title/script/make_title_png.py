# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Render the title block that `make logo` turns into Metal4 geometry.

One centered line per entry, at the largest font that fits the block. Black is metal (img2lay.py --invert). Pixels that touch only at a corner are filled, since they break Metal4 width and space.

Run: python3 script/make_title_png.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1] / "logo/title.png"
SIZE = 400           # px, BLOCK_SIZE / PIXEL_SIZE, so img2lay.py does not resample
LINES = ["IHP__MPC9724", "2026", "DSA1_DIG", "BATMON"]
FONT = next(f for f in ("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf") if Path(f).exists())   # host, image
MARGIN = 24          # px of white kept around the text
LEADING = 1.25       # line pitch over font size


def render(size: int) -> Image.Image:
    """The text lines at one font size, cropped to their ink."""
    font = ImageFont.truetype(FONT, size)
    pitch = int(size * LEADING)
    w = int(max(ImageDraw.Draw(Image.new("L", (1, 1))).textlength(t, font=font) for t in LINES)) + size
    img = Image.new("L", (w, pitch * len(LINES) + size), 255)
    d = ImageDraw.Draw(img)
    for i, line in enumerate(LINES):
        d.text((w / 2, size / 2 + i * pitch), line, font=font, fill=0, anchor="mt")
    return img.crop(img.point(lambda v: 255 - v).getbbox())


def fill_diagonals(metal: np.ndarray) -> np.ndarray:
    """Fill each 2 x 2 checkerboard."""
    metal = metal.copy()
    while True:
        tl, tr, bl, br = metal[:-1, :-1], metal[:-1, 1:], metal[1:, :-1], metal[1:, 1:]
        diag = (tl & br & ~tr & ~bl) | (tr & bl & ~tl & ~br)
        if not diag.any():
            return metal
        ys, xs = np.nonzero(diag)
        metal[ys, xs] = metal[ys, xs + 1] = metal[ys + 1, xs] = metal[ys + 1, xs + 1] = True


def build() -> None:
    room = SIZE - 2 * MARGIN
    size = 10
    best = render(size)
    while max((nxt := render(size + 1)).size) <= room:
        size, best = size + 1, nxt

    out = Image.new("L", (SIZE, SIZE), 255)
    out.paste(best, ((SIZE - best.width) // 2, (SIZE - best.height) // 2))
    metal = fill_diagonals(np.asarray(out) < 128)
    Image.fromarray(np.where(metal, 0, 255).astype(np.uint8)).save(OUT)
    print(f"{OUT}: font {size} px, ink {best.width} x {best.height} px, metal {metal.mean() * 100:.1f} %")


if __name__ == "__main__":
    build()
