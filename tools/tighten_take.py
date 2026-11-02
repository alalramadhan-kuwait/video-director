"""Shorten the long silences of a recorded take, never the voice: python3 tools/tighten_take.py <voice_dir> [--cap 0.5]

The owner, on Faisal's v3 take: «نخليها اسرع شوي». ElevenLabs' speed setting barely moves a v3 voice's own pace and
the held beats («…», the emotion tags) leave pauses of 0.7 s and more, so the take feels slow. This keeps every sound
as it was and cuts each silence longer than `cap` down to `cap` (half kept on each side, so no breath is clipped),
then rewrites raw/whole.mp3 (the original kept as raw/whole.untightened.mp3) and every line's piece (lN.wav) and its
from/to in lN.json from the same time map, so the scenes still follow the voice. The reference reel never pauses
more than about 0.4 s (references/ai-film.md); never speed the voice up (cut silence or the script instead)."""
import argparse, json, subprocess, wave
from pathlib import Path
import numpy as np

SR = 24000


def load(f: Path) -> np.ndarray:
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(f), '-ac', '1', '-ar', str(SR), '-f', 's16le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).copy()


def silences(a: np.ndarray, floor: float = .02, hop: float = .01) -> list[tuple[float, float]]:
    """[start, end) seconds of every quiet run: 10 ms frames under `floor` of the take's loud level."""
    h = int(hop * SR); x = a.astype(float)
    env = np.array([np.sqrt((x[i:i + h] ** 2).mean()) for i in range(0, len(x) - h + 1, h)])
    q = env < np.percentile(env, 95) * floor * 2
    out, i = [], 0
    while i < len(q):
        if q[i]:
            j = i
            while j < len(q) and q[j]: j += 1
            out.append((i * hop, j * hop)); i = j
        else: i += 1
    return out


def plan(quiet: list[tuple[float, float]], total: float, cap: float) -> list[tuple[float, float]]:
    """The spans of the old take to keep, in order: everything but the middle of each silence longer than cap."""
    keep, at = [], 0.0
    for s, e in quiet:
        if e - s <= cap or s <= 0 or e >= total: continue
        keep.append((at, s + cap / 2)); at = e - cap / 2
    keep.append((at, total))
    return keep


def remap(t: float, keep: list[tuple[float, float]]) -> float:
    """Where old time t lands in the tightened take (a time inside a cut lands at the cut)."""
    new = 0.0
    for a, b in keep:
        if t <= a: return new
        if t <= b: return new + (t - a)
        new += b - a
    return new


def write(path: Path, a: np.ndarray) -> None:
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(a.astype(np.int16).tobytes())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0]); ap.add_argument('voice_dir'); ap.add_argument('--cap', type=float, default=.5)
    a = ap.parse_args(argv); d = Path(a.voice_dir)
    src = d / 'raw' / 'whole.untightened.mp3'
    if not src.exists(): (d / 'raw' / 'whole.mp3').rename(src)
    x = load(src); total = len(x) / SR
    keep = plan(silences(x), total, a.cap)
    y = np.concatenate([x[int(s * SR):int(e * SR)] for s, e in keep])
    tmp = d / 'raw' / 'whole.wav'; write(tmp, y)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(tmp), '-b:a', '128k', str(d / 'raw' / 'whole.mp3')], check=True); tmp.unlink()
    for j in sorted(d.glob('l*.json')):
        m = json.loads(j.read_text(encoding='utf-8'))
        if 'from' not in m: continue
        m['from'], m['to'] = round(remap(m['from'], keep), 3), round(remap(m['to'], keep), 3); m['tightened'] = a.cap
        write(j.with_suffix('.wav'), y[int(m['from'] * SR):int(m['to'] * SR)])
        j.write_text(json.dumps(m, ensure_ascii=False), encoding='utf-8')
    print(f'{total:.1f} s -> {len(y) / SR:.1f} s (silences over {a.cap} s cut to {a.cap} s)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
