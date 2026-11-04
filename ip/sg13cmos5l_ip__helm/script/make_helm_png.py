# SPDX-FileCopyrightText: 2026 Michael Koefinger
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
"""Turn the helmet photo into the 1-bit image that `make logo` draws on Metal4.

Black is metal (img2lay.py --invert). The silhouette is the bright part with its enclosed holes filled, because shadows on the helmet are as dark as the background. Inside it the slits and the plate edges, pixels darker than their surroundings, are cut open so the plates read in metal. Islands and holes under MIN_PX pixels are removed, so no shape falls under the Metal4 minimum area.

Run: python3 script/make_helm_png.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = Path(__file__).resolve().parents[1]
SRC = HERE / "logo/helm_source.jpg"
OUT = HERE / "logo/helm.png"
SIZE = 400          # px, BLOCK_SIZE / PIXEL_SIZE, so img2lay.py does not resample
CROP = (0.06, 0.02, 0.97, 0.93)   # helmet bounds in the source, fractions of its edge
BG = 55             # gray above which a pixel is helmet, before the holes are filled
SLIT = 22           # gray below which a pixel is a slit
BLUR = 3            # px, surroundings for the plate edges
EDGE = 12           # a pixel this much darker than its surroundings is a plate edge
RIM = 3             # px of the outline kept solid, so edges do not eat the silhouette
MIN_PX = 12         # smallest island or hole kept, 0.75 um^2 at 0.25 um pixels (Metal4 needs 0.144)


def drop_small(mask: np.ndarray, min_px: int) -> np.ndarray:
    labels, n = ndimage.label(mask)
    sizes = ndimage.sum(mask, labels, range(1, n + 1))
    keep = np.zeros(n + 1, bool)
    keep[1:] = sizes >= min_px
    return keep[labels]


def fill_diagonals(metal: np.ndarray) -> np.ndarray:
    """Fill each 2 x 2 checkerboard, two pixels that touch only at a corner break Metal4 width and space."""
    metal = metal.copy()
    while True:
        tl, tr, bl, br = metal[:-1, :-1], metal[:-1, 1:], metal[1:, :-1], metal[1:, 1:]
        diag = (tl & br & ~tr & ~bl) | (tr & bl & ~tl & ~br)
        if not diag.any():
            return metal
        ys, xs = np.nonzero(diag)
        metal[ys, xs] = metal[ys, xs + 1] = metal[ys + 1, xs] = metal[ys + 1, xs + 1] = True


def main() -> None:
    img = Image.open(SRC).convert("L")
    w, h = img.size
    img = img.crop((int(CROP[0] * w), int(CROP[1] * h), int(CROP[2] * w), int(CROP[3] * h)))
    gray = np.asarray(img.resize((SIZE, SIZE), Image.LANCZOS), float)

    sil = ndimage.binary_fill_holes(ndimage.binary_closing(gray > BG, iterations=5))
    sil = drop_small(ndimage.binary_opening(sil, iterations=2), 2000)
    edges = (gray < ndimage.gaussian_filter(gray, BLUR) - EDGE) & ndimage.binary_erosion(sil, iterations=RIM)
    metal = sil & ~edges & ~(gray < SLIT)
    metal = drop_small(metal, MIN_PX)
    metal = ~drop_small(~metal, MIN_PX)           # fill holes that are too small
    metal = fill_diagonals(metal)
    metal = ~drop_small(~metal, MIN_PX)
    assert not (fill_diagonals(metal) ^ metal).any()

    Image.fromarray(np.where(metal, 0, 255).astype(np.uint8)).save(OUT)
    print(f"{OUT}: {SIZE} x {SIZE} px, metal {metal.mean() * 100:.1f} %")


if __name__ == "__main__":
    main()
