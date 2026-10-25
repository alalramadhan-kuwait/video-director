#!/usr/bin/env python3
"""Cut the subject of a photo out of its background, for the paper cut-out look (rule 12h): a whole watch, a whole
person, an instrument, on the paper of the scene. Free and local: rembg (MIT) with the IS-Net model (Apache-2.0),
downloaded once (about 180 MB). Nothing is sent anywhere.

  python3 tools/cutout_photo.py PHOTO OUT.png [--person]

Writes OUT.png (transparent, cropped to the subject with a small margin) and prints one JSON line:
  {"out": ..., "aspect": w/h, "whole": true|false, "cut_sides": [...], "coverage": share of the frame}
`whole` is false when the subject runs off an edge of the original photo (the photo itself cuts it): then the cut-out
cannot show it whole, and the film draws it instead (rule 12h)."""
import argparse, json, sys
from PIL import Image

ap = argparse.ArgumentParser(); ap.add_argument('src'); ap.add_argument('out')
ap.add_argument('--person', action='store_true', help='a person: the human segmentation model')
a = ap.parse_args()
from rembg import new_session, remove
im = Image.open(a.src).convert('RGB')
cut = remove(im, session=new_session('u2net_human_seg' if a.person else 'isnet-general-use'), post_process_mask=True)
alpha = cut.split()[3].point(lambda v: 255 if v > 40 else 0)
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
area = sum(1 for v in alpha.getdata() if v) / (W * H)
print(json.dumps({'out': a.out, 'aspect': round(out.width / out.height, 3), 'whole': not cut_sides, 'cut_sides': cut_sides,
                  'coverage': round(area, 3), 'size': [out.width, out.height]}))
