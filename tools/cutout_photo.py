#!/usr/bin/env python3
"""Cut the subject of a photo out of its background, for the paper cut-out look (rule 12h): a whole watch, a whole
person, an instrument, on the paper of the scene. Free and local: rembg (MIT) with the IS-Net model (Apache-2.0),
downloaded once (about 180 MB). Nothing is sent anywhere.

  python3 tools/cutout_photo.py PHOTO OUT.png [--person]

Writes OUT.png (transparent, cropped to the subject with a small margin) and prints one JSON line:
  {"out": ..., "aspect": w/h, "whole": true|false, "cut_sides": [...], "coverage": share of the frame}
`whole` is false when the subject runs off an edge of the original photo (the photo itself cuts it): then the cut-out
cannot show it whole, and the film draws it instead (rule 12h).

A drawing on a flat ground (our AI illustrations: a sticker-edged figure on plain grey) is not given to the remover at
all: the ground is taken away by its colour, from the edges in, and everything it encloses stays. The owner, of Halter
in a white coat on a light grey ground with half his coat and his legs gone: «Why did you part of him is missing. It is
repeated issue». The remover cannot tell a white coat or grey trousers from a grey ground; the colour can.
A remover's cut of a person is checked too: holes inside the figure, or the figure in pieces, make it not whole
(`why` says so), so a broken cut-out never reaches a film."""
import argparse, json, sys
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

FLAT = 6.0          # the edges' colour spread (std, 0–255) under which the ground is flat: a drawing, not a photo
NEAR = 14           # how close (max channel difference) a pixel is to the ground to be ground
HOLES = .02         # a person's cut-out with more than this share of holes inside it is broken
PIECE = .03         # …or with a second piece bigger than this share of the first


def flat_ground(rgb: np.ndarray):
    """The subject's mask when the picture is a drawing on a flat ground (None for a photo): the ground is the colour
    of the edges, joined to the edges; everything else, and everything it encloses, is the subject."""
    edges = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    if edges.std(0).max() > FLAT: return None
    near = np.abs(rgb - np.median(edges, 0)).max(2) < NEAR
    lab, _ = ndimage.label(near)
    touching = np.setdiff1d(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])), [0])
    subject = ndimage.binary_fill_holes(~np.isin(lab, touching))
    lab, n = ndimage.label(subject)                          # specks of noise in the ground are not the subject
    if n > 1:
        sizes = ndimage.sum(subject, lab, range(1, n + 1))
        subject = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s >= .01 * sizes.max()])
    return subject


def broken(mask: np.ndarray) -> str | None:
    """Why a person's cut-out is not whole: holes inside the figure, or the figure in pieces."""
    area = mask.sum()
    if not area: return 'no subject'
    holes = (ndimage.binary_fill_holes(mask) & ~mask).sum() / area
    lab, n = ndimage.label(mask)
    sizes = sorted(ndimage.sum(mask, lab, range(1, n + 1)), reverse=True) if n else [0]
    if holes > HOLES: return f'holes inside the figure ({holes:.0%})'
    if len(sizes) > 1 and sizes[1] > PIECE * sizes[0]: return f'the figure is in {sum(1 for s in sizes if s > PIECE * sizes[0])} pieces'
    return None

ap = argparse.ArgumentParser(); ap.add_argument('src'); ap.add_argument('out')
ap.add_argument('--person', action='store_true', help='a person: the human segmentation model')
a = ap.parse_args()
im = Image.open(a.src).convert('RGB')
subject = flat_ground(np.asarray(im).astype(np.int16))
if subject is not None:                                      # a drawing: its ground by colour, nothing lost inside
    method, why = 'flat ground', None
    soft = Image.fromarray((subject * 255).astype('uint8')).filter(ImageFilter.GaussianBlur(1.2))
    cut = im.convert('RGBA'); cut.putalpha(soft)
    alpha = Image.fromarray((subject * 255).astype('uint8'))
else:
    from rembg import new_session, remove
    method = 'rembg'
    cut = remove(im, session=new_session('u2net_human_seg' if a.person else 'isnet-general-use'), post_process_mask=True)
    alpha = cut.split()[3].point(lambda v: 255 if v > 40 else 0)
    why = broken(np.asarray(alpha) > 0) if a.person else None
box = alpha.getbbox()
if not box:
    print(json.dumps({'out': None, 'whole': False, 'why': 'no subject found'})); sys.exit(2)
W, H = im.size
# the subject is cut by the photo when it touches an edge along more than 6 % of that edge
edge = lambda xs: sum(1 for v in xs if v) / max(1, len(xs))
px = alpha.load()
sides = {'top': edge([px[x, 0] for x in range(W)]), 'bottom': edge([px[x, H - 1] for x in range(W)]),
         'left': edge([px[0, y] for y in range(H)]), 'right': edge([px[W - 1, y] for y in range(H)])}
cut_sides = [k for k, v in sides.items() if v > 0.06]
m = int(0.02 * max(W, H))
x0, y0, x1, y1 = max(0, box[0] - m), max(0, box[1] - m), min(W, box[2] + m), min(H, box[3] + m)
out = cut.crop((x0, y0, x1, y1))
out.save(a.out)
area = float((np.asarray(alpha) > 0).mean())
rec = {'out': a.out, 'aspect': round(out.width / out.height, 3), 'whole': not cut_sides and not why, 'cut_sides': cut_sides,
       'coverage': round(area, 3), 'size': [out.width, out.height], 'method': method}
if why: rec['why'] = why
print(json.dumps(rec))
