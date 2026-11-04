"""The Time Keeper watermark (the owner, 4 Nov 2026: «I want to add a little watermark to show that this video is made by
Timekeeper. I'm afraid that someone will see the video without mentioning us»; of four mockups the owner chose «1»):
the tk monogram alone, white, about 80 % opaque with a thin dark edge, top left just under the app's top bar (Instagram's
buttons hold the right side and the bottom, the captions the middle). It stays on the whole film except the end card,
which draws the logo itself. Sizes are fractions of the frame, so 720x1280 and 1080x1920 films look the same."""
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageFilter

DEFAULT = {'size': 0.139, 'x': 0.042, 'y': 0.117, 'opacity': 0.8}   # 100 px wide at 30, 150 on a 720x1280 frame


def config(brand_cfg: dict) -> dict | None:
    """The brand's watermark settings over the defaults, or None when the brand has no watermark."""
    w = brand_cfg.get('watermark')
    if not w or w.get('off'):
        return None
    return {**DEFAULT, **{k: v for k, v in w.items() if not k.startswith('_')}}


def mark(logo: Path, width: int, height: int, cfg: dict | None = None) -> Image.Image:
    """A transparent frame-sized layer with the monogram on it: the logo's dark strokes become white, its pale disc and
    faint dial ring drop out, the strokes a touch heavier, with a thin dark edge (about 43 %) so the mark still reads on
    a cream print or a bright sky, where a white mark alone disappears."""
    c = {**DEFAULT, **(cfg or {})}
    g = Image.open(logo).convert('L')
    a = g.point(lambda v: 255 if v < 90 else (0 if v > 170 else int((170 - v) * 255 / 80))).filter(ImageFilter.MaxFilter(3))
    s = max(8, round(c['size'] * width))
    k = max(1, round(width / 720))                                       # the edge: 1 px on 720 wide, 2 px on 1080
    pad = 4 * k
    A = Image.new('L', (s + 2 * pad, s + 2 * pad), 0); A.paste(a.resize((s, s), Image.LANCZOS), (pad, pad))
    edge = A.filter(ImageFilter.MaxFilter(2 * k + 1)).filter(ImageFilter.GaussianBlur(0.8 * k))
    m = Image.new('RGBA', A.size, (10, 10, 10, 0)); m.putalpha(edge.point(lambda v: v * 110 // 255))
    white = Image.new('RGBA', A.size, (255, 255, 255, 0)); white.putalpha(A.point(lambda v: int(v * c['opacity'])))
    m.alpha_composite(white)
    layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    layer.alpha_composite(m, (round(c['x'] * width) - pad, round(c['y'] * height) - pad))
    return layer


def _probe(src: Path) -> tuple[int, int, float]:
    r = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
                                   '-show_entries', 'format=duration', '-of', 'json', str(src)], capture_output=True, text=True, check=True).stdout)
    return int(r['streams'][0]['width']), int(r['streams'][0]['height']), float(r['format']['duration'])


def apply(src: Path, dst: Path, logo: Path, ending: float = 3.0, cfg: dict | None = None, crf: int = 18) -> Path:
    """Burn the mark into `src` from the first frame until `ending` seconds before the end (the end card); the audio is
    copied untouched."""
    src, dst = Path(src), Path(dst)
    w, h, dur = _probe(src)
    png = dst.with_suffix('.mark.png'); mark(Path(logo), w, h, cfg).save(png)
    until = max(0.0, round(dur - ending, 3))
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(src), '-i', str(png), '-filter_complex',
                    f"[0:v][1:v]overlay=0:0:enable='lt(t,{until})',format=yuv420p[v]", '-map', '[v]', '-map', '0:a?',
                    '-c:v', 'libx264', '-crf', str(crf), '-preset', 'slow', '-c:a', 'copy', '-movflags', '+faststart', str(dst)], check=True)
    png.unlink()
    return dst
