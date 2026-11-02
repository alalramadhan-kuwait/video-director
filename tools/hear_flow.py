"""Listen to a film's narration as one performance, before the pictures (the owner's last rule for the voice:
«Listen to the entire narration without watching the video. If it sounds like separate recordings stitched together,
fix it before publishing»).

    python3 tools/hear_flow.py films/<film>.yaml <voice_dir>

Prints the delivery plan (each line's tone, director/narration.py) and its faults, then the joins where the recorded
voice jumps in loudness, pitch or pace as if a new recording had started, and writes <voice_dir>/narration.mp4: the
lines end to end, nothing else, to listen to on the phone. Exit 1 when a join jumps or a line is missing."""
from __future__ import annotations

import json, subprocess, sys, tempfile, wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from director import brand as B, narration, quickfilm  # noqa: E402


def read(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path)) as w:
        sr, n = w.getframerate(), w.getnframes()
        return np.frombuffer(w.readframes(n), '<i2').astype(float) / 32768, sr


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    if len(argv) != 2: print(__doc__); return 2
    film = quickfilm.load(argv[0]); vdir = Path(argv[1]); brand = film.get('brand', 'timekeeper')
    for p in narration.plan(film['lines']): print(f"  {p['id']:>5}  {p['tone']:<9} {'▮' * p['energy']}")
    faults = [f'delivery: {m}' for m in narration.check(film['lines'])]
    takes, missing = [], []
    for ln in film['lines']:
        f = vdir / f"{ln['id']}.wav"
        if not f.is_file(): missing.append(ln['id']); continue
        a, sr = read(f)
        takes.append((ln['id'], a, sr, len(B.spoken(ln.get('say') or ln['text'], brand))))
    joins = narration.review(takes)
    for m in faults + [f'join: {j}' for j in joins] + [f'missing: {i}' for i in missing]: print(m)
    if takes:
        sr = takes[0][2]
        whole = np.concatenate([a if s == sr else np.interp(np.arange(0, len(a), s / sr), np.arange(len(a)), a) for _, a, s, _ in takes])
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as t:
            with wave.open(t.name, 'wb') as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((whole.clip(-1, 1) * 32767).astype('<i2').tobytes())
        mp4 = vdir / 'narration.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=c=black:s=720x1280:r=30', '-i', t.name,
                        '-shortest', '-c:v', 'libx264', '-tune', 'stillimage', '-c:a', 'aac', '-b:a', '160k', str(mp4)], check=True)
        Path(t.name).unlink()
        print(f'narration: {len(whole) / sr:.1f} s → {mp4}')
    print('one performance ✓' if not (joins or missing) else f'{len(joins)} joins to fix')
    return 1 if joins or missing else 0


if __name__ == '__main__':
    raise SystemExit(main())
