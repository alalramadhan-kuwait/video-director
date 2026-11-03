"""The Time Keeper end card as a ready clip, for a film assembled outside make_film (the AI route):
    python3 tools/tk_endcard_clip.py vendor/paper-story <out_dir>
draws the 72 frames of vendor/paper-story/tk_endcard.py (dark plate, the gold hand sweeps once and draws the logo,
the logo rests, a fade to black over the last 0.35 s; 3 s at 24 fps, 720x1280) into <out_dir>/fr/. Mux them with the
card's two ticks (tick.wav at 0.2 s, -12 dB; tick_pair.wav at 1.8 s, -8 dB):
    ffmpeg -framerate 24 -i <out_dir>/fr/%03d.png -i card.wav ... card.mp4
The film's music ends before it, so the ticks are heard alone."""
import math, sys
from PIL import Image, ImageDraw
P, E = sys.argv[1], sys.argv[2]
W, H, FPS, DUR, DRAWN, FADE, SS = 720, 1280, 24, 3.0, 1.8, 0.35, 2
GOLD = (0xC9, 0xA3, 0x5F)
ease = lambda x: -(math.cos(math.pi * x) - 1) / 2
def key(t, a, b, va, vb, f=lambda x: x):
    if t <= a: return va
    if t >= b: return vb
    return va + (vb - va) * f((t - a) / (b - a))
logo = Image.open(f'{P}/tk-logo-512.png').convert('RGBA').resize((380 * SS, 380 * SS), Image.LANCZOS)
hand = Image.new('RGBA', (40 * SS, 600 * SS), (0, 0, 0, 0)); d = ImageDraw.Draw(hand)   # pivot at the centre of this tall canvas
d.rounded_rectangle((16 * SS, 0, 24 * SS, 300 * SS), 4 * SS, fill=GOLD + (255,)); d.ellipse(((20 - 14) * SS, (290 - 14) * SS, (20 + 14) * SS, (290 + 14) * SS), fill=GOLD + (255,))
for n in range(int(DUR * FPS)):
    t = n / FPS
    k = key(t, .2, DRAWN, 0, 1, ease)
    c = Image.new('RGBA', (W * SS, H * SS), (17, 17, 17, 255))
    if k > 0:
        m = Image.new('L', logo.size, 0); md = ImageDraw.Draw(m); r = logo.size[0]
        md.pieslice((-r, -r, 2 * r, 2 * r), -90, -90 + k * 360, fill=255) if k < 1 else md.rectangle((0, 0, r, r), fill=255)
        lm = Image.new('RGBA', logo.size, (0, 0, 0, 0)); lm.paste(logo, (0, 0), Image.composite(logo.getchannel('A'), Image.new('L', logo.size, 0), m))
        c.alpha_composite(lm, (360 * SS - logo.size[0] // 2, 560 * SS - logo.size[1] // 2))
    ho = key(t, .2, .3, 0, 1) if t < DRAWN else key(t, DRAWN, DRAWN + .3, 1, 0)
    if ho > 0:
        h = hand.rotate(-k * 360, resample=Image.BICUBIC, center=(20 * SS, 300 * SS))
        a = h.getchannel('A').point(lambda v: int(v * ho)); h.putalpha(a)
        c.alpha_composite(h, (360 * SS - 20 * SS, 560 * SS - 300 * SS))
    z = 1 + .05 * t / DUR; cw, ch = W * SS / z, H * SS / z; cx, cy = 360 * SS, 600 * SS
    img = c.crop((int(cx - cw / 2), int(cy - ch / 2), int(cx + cw / 2), int(cy + ch / 2))).resize((W, H), Image.LANCZOS).convert('RGB')
    f = key(t, DUR - FADE, DUR, 0, 1)
    if f > 0: img = Image.blend(img, Image.new('RGB', (W, H), 'black'), f)
    img.save(f'{E}/fr/{n:03d}.png')
