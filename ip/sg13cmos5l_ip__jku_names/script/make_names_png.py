# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Render the author name block that `make logo` turns into Metal4 geometry.

The name is drawn on the diagonal because the block is square and a name is
wide: at 45 degrees it fits the 100 um block at roughly twice the cap height it
would get horizontally. Black on white, which is what img2lay.py --invert wants.

Run: python3 script/make_names_png.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1] / "logo/jku_names.png"
SIZE = 750           # px, matches what the block was drawn at before
NAMES = ["M. KOEFINGER"]
ANGLE = 45           # degrees, counter-clockwise
FONT = "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"
MARGIN = 40          # px of white kept around the rotated text


def render(size: int) -> Image.Image:
    """The name block at one font size, rotated and cropped to its ink."""
    font = ImageFont.truetype(FONT, size)
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    line_h = int(size * 1.35)
    w = int(max(probe.textlength(n, font=font) for n in NAMES)) + size
    strip = Image.new("L", (w, line_h * len(NAMES) + size // 2), 255)
    d = ImageDraw.Draw(strip)
    for i, line in enumerate(NAMES):
        tw = d.textlength(line, font=font)
        d.text(((w - tw) / 2, i * line_h), line, font=font, fill=0)
    rotated = strip.rotate(ANGLE, expand=True, fillcolor=255, resample=Image.BICUBIC)
    return rotated.crop(rotated.point(lambda v: 255 - v).getbbox())


def build() -> None:
    # Rotating makes the bounding box grow by roughly (width + height) / sqrt(2),
    # so fitting the text to the diagonal is not enough: it has to be measured
    # after the rotation or the ends run off the corners.
    room = SIZE - 2 * MARGIN
    size = 10
    best = render(size)
    while True:
        nxt = render(size + 2)
        if max(nxt.size) > room:
            break
        size, best = size + 2, nxt

    out = Image.new("L", (SIZE, SIZE), 255)
    out.paste(best, ((SIZE - best.width) // 2, (SIZE - best.height) // 2))
    out.convert("RGBA").save(OUT)
    print(f"wrote {OUT}: font {size}, ink {best.width}x{best.height} in {room} px")


if __name__ == "__main__":
    build()
