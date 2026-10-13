"""Playable previews and style-board samples for the dashboard, made locally and for free (tracked tasks).

Every input is read-only; outputs go to the dashboard media folder only.
  * ep7 preview: the published render re-encoded small, as H.264/AAC MP4 (Safari, iPhone) and VP9/Opus WebM (Chromium).
  * scene clips: a WebM copy next to every MP4 clip, so both browser families can play them.
  * Royal Oak animatic: the storyboard's own captions on its own theme colours, with the APPROVED narration placed
    where the storyboard places it. Clearly not the film: the photographs and renders are not in this workspace.
  * Time Keeper end card: drawn by the unchanged production renderer (paper-story render.mjs) from the end-card scene
    in the published Royal Oak storyboard, on a temporary copy.
"""
from __future__ import annotations
import json, os, shutil, subprocess, tempfile
from pathlib import Path

from ..events import EventLog

ROOT = Path(__file__).resolve().parents[2]
CAIRO = Path('/home/user/majedphotos/video-ad-editor/video-ad-editor/motion/fonts/Cairo-VF.ttf')


def _ff(*a, timeout=900):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *map(str, a)], check=True, timeout=timeout)


def _dur(p) -> float:
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(p)],
                                capture_output=True, text=True, check=True).stdout)


def two_formats(src, dst_stem: Path, scale='540:960', audio=True):
    """dst_stem.mp4 (H.264/AAC, faststart) and dst_stem.webm (VP9/Opus)."""
    a_mp4 = ['-c:a', 'aac', '-b:a', '64k'] if audio else ['-an']
    a_webm = ['-c:a', 'libopus', '-b:a', '48k'] if audio else ['-an']
    _ff('-i', src, '-vf', f'scale={scale}', '-c:v', 'libx264', '-crf', '30', '-preset', 'veryfast', '-pix_fmt', 'yuv420p',
        *a_mp4, '-movflags', '+faststart', dst_stem.with_suffix('.mp4'))
    _ff('-i', src, '-vf', f'scale={scale}', '-c:v', 'libvpx-vp9', '-crf', '40', '-b:v', '0', '-deadline', 'realtime',
        '-cpu-used', '8', '-row-mt', '1', *a_webm, dst_stem.with_suffix('.webm'))


def ep7_preview(log: EventLog, S: Path, media: Path):
    out = media / 'ep7/preview'; out.mkdir(parents=True, exist_ok=True)
    clips = sorted((media / 'ep7/clips').glob('*.mp4'))
    with log.task('diabetes-history', 'playable previews (full episode + 20 scene clips, MP4 and WebM)', 1 + len(clips),
                  video='ep7', stage='dashboard') as t:
        two_formats(S / 'ep7/out/ep7_tiktok_full_29mb.mp4', out / 'ep7_full')
        t.unit(what='full episode')
        for c in clips:
            _ff('-i', c, '-c:v', 'libvpx-vp9', '-crf', '40', '-b:v', '0', '-deadline', 'realtime', '-cpu-used', '8', '-an',
                c.with_suffix('.webm'))
            t.unit(scene=c.stem)


# ------------------------------------------------------------------------------------------------ Time Keeper end card
def tk_endcard(log: EventLog, S: Path, media: Path):
    A = S / 'audit/claude_success-story-video'
    tool = A / '.claude/skills/paper-story/scripts/render.mjs'
    part3 = json.loads((A / 'video/royal-oak/part3.json').read_text(encoding='utf-8'))
    out = media / 'timekeeper/endcard'; out.mkdir(parents=True, exist_ok=True)
    with log.task('timekeeper', 'end card drawn by the production renderer (read-only)', 2, stage='dashboard') as t, \
            tempfile.TemporaryDirectory() as td:
        scenes = [s for s in part3['scenes'] if s.get('endcard') == 'timekeeper']
        for s in scenes:
            for e in s['elements']:
                if e.get('src'):
                    e['src'] = str((A / 'video/royal-oak' / e['src']).resolve())   # read the published logo in place
        sb = {k: part3[k] for k in ('width', 'height', 'fps', 'style', 'themes')} | {'dir': part3.get('dir', 'rtl'), 'scenes': scenes}
        sbp = Path(td) / 'endcard.json'; sbp.write_text(json.dumps(sb, ensure_ascii=False), encoding='utf-8')
        env = {**os.environ, 'NODE_PATH': os.path.join(subprocess.run(['npm', 'root', '-g'], capture_output=True, text=True).stdout.strip(), 'playwright', 'node_modules'),
               'PLAYWRIGHT_BROWSERS_PATH': '/opt/pw-browsers'}
        env.pop('ELEVENLABS_API_KEY', None); env.pop('FAL_KEY', None)
        subprocess.run(['node', str(tool), str(sbp), '--still', '0.8,1.6,2.6', '-o', td + '/stills'], check=True, env=env,
                       cwd=td, timeout=600, capture_output=True)
        for i, f in enumerate(sorted(Path(td, 'stills').glob('*.png'))):
            _ff('-i', f, '-vf', 'scale=360:-2', '-q:v', '3', out / f'still_{i}.jpg')
        t.unit(what='stills')
        subprocess.run(['node', str(tool), str(sbp), '-o', td + '/endcard.mp4'], check=True, env=env, cwd=td, timeout=900,
                       capture_output=True)
        two_formats(Path(td) / 'endcard.mp4', out / 'endcard', scale='360:640')
        t.unit(what='clip')


# ------------------------------------------------------------------------------------------------ Royal Oak animatic
FRAME = """<!doctype html><meta charset=utf-8><style>
@font-face{{font-family:Cairo;src:url('file://{font}')}}
html,body{{margin:0;width:540px;height:960px;overflow:hidden;background:{bg};font-family:Cairo}}
.c{{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;align-items:center;gap:14px;padding:0 44px;direction:rtl;text-align:center}}
.c p{{margin:0;font-size:{fs}px;font-weight:700;line-height:1.5;color:{ink}}}
.tag{{position:absolute;top:24px;left:0;right:0;text-align:center;font:600 15px Cairo;color:{ink};opacity:.75;direction:ltr}}
.wm{{position:absolute;bottom:26px;left:0;right:0;text-align:center;font:600 14px Cairo;color:{ink};opacity:.7;direction:ltr}}
</style><div class=tag>{sid} · {theme}</div><div class=c>{lines}</div>
<div class=wm>ANIMATIC · storyboard text + approved narration · not the film</div>"""


def ro_animatic(log: EventLog, S: Path, media: Path, audio_dir: Path):
    A = S / 'audit/claude_success-story-video/video/royal-oak'
    ro = json.loads((A / 'ro-style.json').read_text(encoding='utf-8'))
    out = media / 'royal-oak/animatic'; (out / 'frames').mkdir(parents=True, exist_ok=True)
    scenes = []
    for part in (1, 2, 3):
        p = json.loads((A / f'part{part}.json').read_text(encoding='utf-8'))
        scenes += [(f'P{part}-{i:02d}', s) for i, s in enumerate(p['scenes'], 1)]
    endstill = media / 'timekeeper/endcard/still_1.jpg'
    # frames and audio segments are like units; the final encode is different work, so it is its own task
    # (mixing them made the first ETA wrong: 38.5 s predicted, 82 s actual)
    with tempfile.TemporaryDirectory() as td, log.task('timekeeper', 'Royal Oak animatic frames and audio', len(scenes),
                                                         video='royal-oak', stage='dashboard') as t:
        concat_v, concat_a = [], []
        for sid, s in scenes:
            frame = out / 'frames' / f'{sid}.jpg'
            th = ro['themes'].get(s.get('theme'), {})
            if s.get('endcard') and endstill.exists():
                _ff('-i', endstill, '-vf', 'scale=540:960:force_original_aspect_ratio=decrease,pad=540:960:(ow-iw)/2:(oh-ih)/2:black', frame)
            else:
                caps = [c.strip() for c in (s.get('captions') or '').split('|') if c.strip()]
                fs = 34 if len(caps) <= 6 else 28 if len(caps) <= 10 else 23
                html = FRAME.format(font=CAIRO, bg=th.get('bg', '#16181D'), ink=th.get('capBg', '#EFE8D6'), fs=fs, sid=sid,
                                    theme=s.get('theme', ''), lines=''.join(f'<p>{c}</p>' for c in caps) or '<p>·</p>')
                h = Path(td) / 'f.html'; h.write_text(html, encoding='utf-8'); png = Path(td) / 'f.png'
                subprocess.run(['node', str(ROOT / 'tools/html_shot.mjs'), str(h), str(png), '540', '960'], check=True)
                _ff('-i', png, '-q:v', '3', frame)
            d = float(s.get('dur', 4))
            concat_v.append(f"file '{frame}'\nduration {d:.3f}\n")
            seg = Path(td) / f'{sid}.wav'
            line = Path(s.get('voice') or '').stem
            src = audio_dir / f'{line}.mp3'
            if line and src.exists():
                at = float(s.get('voiceAt', 0.12))
                _ff('-i', src, '-af', f'adelay={int(at * 1000)}:all=1,apad,atrim=0:{d:.3f}', '-ar', '44100', '-ac', '1', seg)
            else:
                _ff('-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=mono', '-t', f'{d:.3f}', seg)
            concat_a.append(f"file '{seg}'\n")
            t.unit(scene=sid)
        concat_v.append(f"file '{out / 'frames' / scenes[-1][0]}.jpg'\n")       # concat demuxer needs the last file twice
        (Path(td) / 'v.txt').write_text(''.join(concat_v)); (Path(td) / 'a.txt').write_text(''.join(concat_a))
        with log.task('timekeeper', 'Royal Oak animatic encode (MP4 + WebM)', 1, video='royal-oak', stage='dashboard') as e:
            _ff('-f', 'concat', '-safe', '0', '-i', Path(td) / 'a.txt', Path(td) / 'audio.wav')
            _ff('-f', 'concat', '-safe', '0', '-i', Path(td) / 'v.txt', '-i', Path(td) / 'audio.wav', '-r', '15',
                '-c:v', 'libx264', '-crf', '28', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-shortest',
                '-c:a', 'pcm_s16le', Path(td) / 'animatic.mkv')
            two_formats(Path(td) / 'animatic.mkv', out / 'royal_oak_animatic', scale='540:960')
            e.unit(what='encode')


def dh_characters(log: EventLog, media: Path):
    """Character and image-treatment crops for the style board, from the published ep7 frames."""
    out = media / 'diabetes/board'; out.mkdir(parents=True, exist_ok=True)
    crops = [('elizabeth', 'a1', 'crop=iw*0.46:ih*0.5:iw*0.27:ih*0.28'), ('scientists', 'b4', 'crop=iw*0.42:ih*0.45:iw*0.54:ih*0.3'),
             ('microscope', 'b3', 'crop=iw*0.8:ih*0.4:iw*0.1:ih*0.22'), ('chips', 'd5', 'crop=iw:ih*0.42:0:ih*0.08')]
    with log.task('diabetes-history', 'style board crops from published frames', len(crops), stage='dashboard') as t:
        for name, scene, crop in crops:
            _ff('-i', ROOT / 'var/review/ep7-final/stills' / f'{scene}_mid.jpg', '-vf', crop, '-q:v', '3', out / f'{name}.jpg')
            t.unit(scene=scene)


def tk_board(S: Path, media: Path):
    """The published logo and the M4 style boards, copied for the identity page (no processing)."""
    out = media / 'timekeeper/board'; out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(S / 'audit/claude_success-story-video/public/icon-512.png', media / 'timekeeper/logo.png')
    for f in ('tk-paper.jpg', 'tk-blueprint.jpg', 'tk-editorial.jpg'):
        shutil.copyfile(ROOT / 'var/pages/directions/img' / f, out / f)
