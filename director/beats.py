"""The music's beats and the film's cuts: the scenes change on a beat. Learned from video-ad-editor (beat.py, beat-fx.js):
an effect lands on the beat or on the cut, never at a rough time.

The film's timing belongs to the voice, so nothing in the film moves: only the music shifts. A positive offset starts
it later in its own track (when the track is longer than the film); a negative one lets it enter a moment after the
film starts (at most `max_delay` s, under the opening's own sounds), so a track as long as the film still fits. The
offset is the one that puts the most cuts on a strong beat; the smallest shift wins a tie. Optionally a
scene that starts on a beat gets a small camera push (`punch`), the only beat effect calm enough for a documentary.
Free and local: the beats are found by spectral flux on the decoded track (numpy + ffmpeg), nothing is sent anywhere.
"""
from __future__ import annotations
import subprocess
from pathlib import Path

import numpy as np

SR, HOP, WIN = 22050, 512, 2048
NEAR = 0.07                                     # a cut this close to a beat (s) is on it: about two frames at 30 fps


def decode(path: Path, seconds: float | None = None) -> np.ndarray:
    cmd = ['ffmpeg', '-v', 'error', '-i', str(path)] + (['-t', str(seconds)] if seconds else []) + ['-ac', '1', '-ar', str(SR), '-f', 'f32le', '-']
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, dtype=np.float32)


def onsets(a: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(times in s, strengths 0..1) of the track's onsets: peaks of the positive spectral change above the local level."""
    if len(a) < WIN * 4:
        return np.zeros(0), np.zeros(0)
    n = 1 + (len(a) - WIN) // HOP
    frames = np.lib.stride_tricks.as_strided(a, shape=(n, WIN), strides=(a.strides[0] * HOP, a.strides[0]))
    mag = np.log1p(np.abs(np.fft.rfft(frames * np.hanning(WIN), axis=1)))
    flux = np.maximum(0, np.diff(mag, axis=0)).sum(axis=1)
    flux = np.concatenate([[0], flux])
    k = 43                                                        # about one second of frames: the local level
    box = np.ones(2 * k + 1) / (2 * k + 1)
    mean = lambda x: np.convolve(np.pad(x, k, mode='edge'), box, mode='valid')
    local = mean(flux)
    spread = np.sqrt(np.maximum(0, mean(flux ** 2) - local ** 2))
    peak = (flux > local + 0.8 * spread) & (flux >= np.roll(flux, 1)) & (flux >= np.roll(flux, -1))
    for d in (2, 3):                                              # one onset per 70 ms
        peak &= (flux >= np.roll(flux, d)) & (flux >= np.roll(flux, -d))
    idx = np.nonzero(peak)[0]
    if not len(idx):
        return np.zeros(0), np.zeros(0)
    s = flux[idx] / flux[idx].max()
    return (idx * HOP + WIN / 2) / SR, s                         # the frame's centre


def best_offset(times: np.ndarray, strength: np.ndarray, cuts: list[float], later: float, earlier: float = 0.0,
                step: float = 0.01) -> tuple[float, int]:
    """(offset, cuts on a beat): the music shift (-earlier..later s) that puts the most cuts, weighted by beat strength,
    on a beat. A cut at c meets the music's time c + offset. Near-ties go to the smallest shift."""
    if not len(times) or not cuts:
        return 0.0, 0
    c = np.asarray(cuts)
    cand = sorted(np.round(np.arange(-max(0.0, earlier), max(0.0, later) + 1e-9, step), 2), key=abs)
    best, best_o = -1.0, 0.0
    for o in cand:
        d = np.abs(times[None, :] - (c[:, None] + o))
        # each cut on a beat counts 1, plus up to 1 more for a strong beat hit squarely: more cuts first, then better ones
        sc = float(np.where(d < NEAR, 1 + strength[None, :] * (1 - d / NEAR), 0).max(axis=1).sum())
        if sc > best * 1.03 + 1e-6:                              # a smaller shift keeps its place unless clearly worse
            best, best_o = sc, float(o)
    d = np.abs(times[None, :] - (c[:, None] + best_o))
    return round(best_o, 2), int((d.min(axis=1) < NEAR).sum())


def on_beat(times: np.ndarray, cuts: list[float], offset: float) -> list[bool]:
    return [bool(len(times) and np.abs(times - (c + offset)).min() < NEAR) for c in cuts]


def align(music: Path, cuts: list[float], film_seconds: float, out: Path, max_later: float = 20.0, max_delay: float = 2.0) -> dict:
    """The music shifted so the cuts land on its beats, written to `out` (FLAC) when it moves.
    Returns {file, offset, on_beat (per cut), hits, cuts}; a negative offset is a delayed entry."""
    a = decode(music, seconds=film_seconds + max_later + 2)
    t, s = onsets(a)
    room = min(max_later, max(0.0, len(a) / SR - film_seconds - 1))  # never so late that the track ends inside the film
    o, hits = best_offset(t, s, cuts, room, max_delay)
    f = music
    if o > 0:
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(o), '-i', str(music), '-c:a', 'flac', str(out)], check=True)
        f = out
    elif o < 0:                                       # enters a moment late; ends with a fade rather than a cut
        ms = int(round(-o * 1000))
        end = len(a) / SR - o
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(music), '-af',
                        f'adelay={ms}:all=1,afade=t=in:st={-o:.2f}:d=0.6,afade=t=out:st={max(0, end - 2.5):.2f}:d=2.5',
                        '-c:a', 'flac', str(out)], check=True)
        f = out
    return {'file': f, 'offset': o, 'on_beat': on_beat(t, cuts, o), 'hits': hits, 'cuts': len(cuts)}


def punch(scene: dict, amount: float = 0.025, dur: float = 0.35) -> bool:
    """A small camera push on a scene that starts on a beat: the zoom starts `amount` closer and settles in `dur` s.
    Only scenes with a zoom that starts at 0 are touched (the rest keep their camera as it is)."""
    cam = scene.get('camera') or {}
    z = cam.get('zoom')
    if not (isinstance(z, list) and z and isinstance(z[0], list) and z[0][0] == 0):
        return False
    z0 = z[0][1]
    nxt = [k for k in z[1:] if k[0] > dur]
    cam['zoom'] = [[0, round(z0 * (1 + amount), 4)], [dur, z0, 'outCubic']] + nxt
    return True
