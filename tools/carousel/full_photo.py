"""A photo that becomes the slide (the owner, 8 Nov 2026: «make sure the boundary seems seamless… increase the size of
the picture, that it will seem as one integrated»): the photo fills the slide's width from the top edge, and its lower
part fades into one flat colour taken from the photo itself; the text sits on that colour (`"layout": "full"` with
`"paper"` set to the colour this prints). No box, no edge. The watch is never cut out and stays whole in the frame.

  python3 tools/carousel/full_photo.py PHOTO OUT.jpg [--height 980] [--focus 0.4] [--fade 300]

`--focus` is where the crop centres, 0 = keep the top, 1 = keep the bottom. Prints the paper colour (#rrggbb)."""
import argparse
from PIL import Image, ImageDraw

W = 1080


def compose(src, out, height=980, focus=0.4, fade=300):
    im = Image.open(src).convert('RGB')
    h = round(im.height * W / im.width)
    im = im.resize((W, h), Image.LANCZOS)
    if h > height:                                                  # crop to the frame, around the focus
        top = round((h - height) * min(1, max(0, focus)))
        im = im.crop((0, top, W, top + height))
    H = im.height
    strip = im.crop((0, H - 40, W, H)).resize((1, 1), Image.LANCZOS)  # the colour the photo ends in
    paper = strip.getpixel((0, 0))
    canvas = Image.new('RGB', (W, 1350), paper)
    canvas.paste(im, (0, 0))
    over = Image.new('RGBA', (W, 1350), paper + (0,))
    d = ImageDraw.Draw(over)
    f = min(fade, H)
    for y in range(H - f, H):                                       # fade the photo into the paper
        a = (y - (H - f)) / f
        d.line([(0, y), (W, y)], fill=paper + (round(255 * a * a * (3 - 2 * a)),))
    lum = 0.299 * paper[0] + 0.587 * paper[1] + 0.114 * paper[2]
    band = (0, 0, 0) if lum < 140 else (255, 255, 255)              # keep the logo readable over the photo's top
    for y in range(0, 240):
        a = 0.42 * (1 - y / 240)
        d.line([(0, y), (W, y)], fill=band + (round(255 * a),))
    canvas = Image.alpha_composite(canvas.convert('RGBA'), over).convert('RGB')
    canvas.save(out, quality=93)
    return '#%02x%02x%02x' % paper, H


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('photo'); ap.add_argument('out')
    ap.add_argument('--height', type=int, default=980); ap.add_argument('--focus', type=float, default=0.4)
    ap.add_argument('--fade', type=int, default=300)
    a = ap.parse_args()
    print(compose(a.photo, a.out, a.height, a.focus, a.fade)[0])
