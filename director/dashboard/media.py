"""Media the dashboard shows, made from approved outputs without touching them (read-only inputs, new small files).
Every step runs as a tracked task, so its progress and time are real."""
from __future__ import annotations
import json, shutil, subprocess
from pathlib import Path
from ..events import EventLog


def _ff(*args):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *map(str, args)], check=True)


def ep7_media(log: EventLog, S: Path, pack_dir: Path, out: Path):
    video = S / 'ep7/out/ep7_tiktok_full_29mb.mp4'
    pack = json.loads((pack_dir / 'pack.json').read_text(encoding='utf-8'))
    (out / 'ep7/clips').mkdir(parents=True, exist_ok=True); (out / 'ep7/stills').mkdir(parents=True, exist_ok=True)
    with log.task('diabetes-history', 'motion previews (3 s per scene)', len(pack['scenes']), video='ep7', stage='dashboard') as t:
        for s in pack['scenes']:
            mid = (s['start'] + s['end']) / 2; st = max(s['start'], mid - 1.5); dur = min(3.0, s['end'] - st)
            _ff('-ss', f'{st:.2f}', '-i', video, '-t', f'{dur:.2f}', '-an', '-vf', 'scale=270:480', '-c:v', 'libx264',
                '-crf', '30', '-preset', 'veryfast', '-movflags', '+faststart', out / f"ep7/clips/{s['id']}.mp4")
            shutil.copyfile(pack_dir / s['stills']['mid'], out / f"ep7/stills/{s['id']}.jpg")
            t.unit(scene=s['id'])
    # b1 was revised three times on 2026-10-12; each check image shows the doctor moment and the skin moment
    revs = [('A', 'p2b.png', (0, 720), 'b1_v1'), ('B', 'p2c.png', (0, 360), 'b1_v2'), ('C', 'p2d.png', (0, 360), 'b1_v3')]
    (out / 'ep7/revisions').mkdir(parents=True, exist_ok=True)
    with log.task('diabetes-history', 'revision frames for the gallery', len(revs), video='ep7', stage='dashboard') as t:
        for label, src, (x1, x2), name in revs:
            _ff('-i', S / 'ep7/chk' / src, '-filter_complex',
                f'[0]crop=360:640:{x1}:0[a];[0]crop=360:640:{x2}:0[b];[a][b]hstack,setsar=1',
                '-pix_fmt', 'yuvj420p', '-q:v', '3', out / f'ep7/revisions/{name}.jpg')
            t.unit(scene='b1', version=label)


def royal_oak_media(log: EventLog, audio_dir: Path, out: Path):
    files = sorted(audio_dir.glob('*.mp3'))
    (out / 'royal-oak/audio').mkdir(parents=True, exist_ok=True)
    with log.task('timekeeper', 'approved narration copied for listening (read-only source)', len(files),
                  video='royal-oak', stage='dashboard') as t:
        for f in files:
            shutil.copyfile(f, out / 'royal-oak/audio' / f.name)
            t.unit(scene=f.stem)
