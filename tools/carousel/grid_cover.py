"""A grid cover: several watch photos in a grid on their own white ground, under the TK headline.

The owner, 8 Nov 2026 (GPHG winners): «another cover page where it will have all the photos of the… watches… like a grid.
That does not necessary to be all the photos… whatever fit in the image and looks nice».

  python3 tools/carousel/grid_cover.py OUT.jpg PHOTO… [--cols 4] [--rows 3]

Photos are used whole (never background-removed), first one top-right (Arabic reads right to left). The grid leaves
the logo band free and ends where the headline begins; set the cover's `"gap": 60` so the headline sits low."""
import argparse
from PIL import Image

W, H, TOP, BOTTOM, SIDE, PAD = 1080, 1350, 205, 1010, 24, 8


def grid(photos, cols=4, rows=3, ground=(255, 255, 255)):
    cv = Image.new('RGB', (W, H), ground)
    cw, ch = (W - 2 * SIDE) // cols, (BOTTOM - TOP) // rows
    for i, p in enumerate(photos[:cols * rows]):
        im = Image.open(p).convert('RGB'); im.thumbnail((cw - 2 * PAD, ch - 2 * PAD), Image.LANCZOS)
        c, r = cols - 1 - i % cols, i // cols                         # right to left
        cv.paste(im, (SIDE + c * cw + (cw - im.width) // 2, TOP + r * ch + (ch - im.height) // 2))
    return cv


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('out'); ap.add_argument('photos', nargs='+')
    ap.add_argument('--cols', type=int, default=4); ap.add_argument('--rows', type=int, default=3)
    a = ap.parse_args()
    grid(a.photos, a.cols, a.rows).save(a.out, quality=93)
    print(a.out)
