"""The film's sound mix, set in the storyboard before the engine renders it (vendor/paper-story/scripts/render.mjs).

Étienne measured the Halter mix: the music sat 40 dB under the voice, beds played in 3 of 13 scenes (one ~30 dB
under), and 44 one-shots ran at 23 a minute, 73 % of them paper sounds. The targets since then:
  music      about 18-20 dB under the voice while it speaks, about 10 dB under in the pauses of the finished film: its
             gain is measured against the voice (`music_gain`, MUSIC_UNDER), never above the brand's music.gain_db;
             render.mjs ducks it (ratio 3, threshold 0.03, release 400 ms; the brand's music.duck). At a fixed -6 dB
             it sat 2.5 dB over the quieter OmniVoice takes in v10's pauses.
  beds       felt, not heard (the owner on v10: «الاصوات اللي بالخلفية مزعجة جدا»). Every scene with a world (`set:`)
             or a feeling (`mood:`) plays one main bed: BED_AIM dB under the voice while it sets the place (from LEAD s
             before the cut, a J-cut, to BED_HEAD s after it), then it settles to BED_SETTLE dB under. A repetitive
             bed (a tick, a tock, a running movement) is never over TICK_UNDER dB under. A second bed sits at least
             BED_SECOND dB below the main one; any more are dropped. A film's gain from its film file is kept but
             never above those levels, and `beds: {gain: dB}` in the film file turns every bed down further
  one-shots  SHOT_UNDER dB under the voice, at most PER_MINUTE a minute (the least important are dropped first), and
             paper sounds only when paper really comes in: a banner or a card, a slide of the page; never two within
             PAPER_GAP s, never more than PAPER_MAX in one scene
Levels are measured on the files (the voice's spoken parts, each sound's own loudness), so a quiet bed and a loud
bed both land where they should. A sound file that is missing keeps the gain the template gave it.
"""
from __future__ import annotations
import math, subprocess, wave
from functools import lru_cache
from pathlib import Path

import numpy as np

from . import engine

SFX = engine.ENGINE / 'assets/sfx'
BED_UNDER = (32, 36)                  # dB under the voice, the scene's main bed while it sets the place
BED_AIM = 34
BED_SETTLE = 40                       # dB under the voice, after the first BED_HEAD s of the scene
BED_HEAD = 1.5                        # s after the cut: a bed sets the place, then sits low
BED_RAMP = 1.0                        # s to settle
BED_SECOND = 6                        # dB: a second bed at least this far under the main one; a third is dropped
TICK_UNDER = 36                       # dB under the voice at most: a repetitive bed never competes with the narration
REPETITIVE = {'tick', 'tock', 'tick_pair', 'tick_slow', 'watch_run'}
MUSIC_UNDER = 14                      # dB under the voice's measured level, the music in the pauses: the master's limiter
                                      # brings the voice ~3-4 dB nearer, so pauses land 7-10 dB under it in the film
SHOT_UNDER = (3, 6)                   # dB under the voice, a one-shot effect
LONG_SHOT, LONG_UNDER = 2.0, 16       # an effect that runs over 2 s (a train passing, a horn, footsteps) is levelled
                                      # like a bed: its running level 16 dB under the voice, not its peak 3-6 under
LEAD = 0.5                            # s: a bed starts this long before its cut
PER_MINUTE = 15
PAPER = {'paper_place', 'paper_slide', 'fold', 'tape', 'paper_tear'}
PAPER_GAP, PAPER_MAX = 0.8, 2
# how much a sound matters to the story when the film has too many: the least important go first
RANK = {'gavel': 8, 'tower_strike': 8, 'train_horn': 8, 'train': 7, 'tick_slow': 7, 'footsteps': 7, 'thud': 7,
        'stamp': 6, 'shutter': 6, 'bell_far': 6, 'chime': 5, 'heartbeat': 5, 'boom': 5, 'sonar': 5, 'door_chime': 5,
        'crown_wind': 5, 'clasp': 5, 'geiger': 4, 'bubbles': 4, 'pin': 3, 'click': 3, 'tick_pair': 3, 'tick': 3, 'tock': 3,
        'notif': 3, 'mic_tap': 3, 'whoosh': 2, 'plane': 2}
OWNER, ENDCARD = 20, 30               # a cue the film file asks for; the brand's end card ticks: never dropped


def _read(path: Path) -> np.ndarray | None:
    try:
        with wave.open(str(path)) as w:
            if w.getsampwidth() != 2: return None
            x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float64) / 32768
            return x.reshape(-1, w.getnchannels()).mean(axis=1) if w.getnchannels() > 1 else x
    except (OSError, wave.Error, EOFError):
        return None


def _db(p: float) -> float:
    return 10 * math.log10(max(p, 1e-12))


@lru_cache(maxsize=256)
def level(path: str, kind: str = 'active') -> float | None:
    """dB of a file: 'active' = mean power of its 50 ms frames within 30 dB of the loudest (the voice while it speaks, a
    bed as it runs); 'peak' = its loudest 50 ms (how loud a one-shot hits)."""
    x = _read(Path(path))
    if x is None or not len(x): return None
    n = 2205
    fr = x[:len(x) // n * n].reshape(-1, n) if len(x) >= n else x.reshape(1, -1)
    pw = (fr ** 2).mean(axis=1)
    if kind == 'peak': return round(_db(pw.max()), 2)
    top = pw.max()
    return round(_db(pw[pw >= top * 1e-3].mean()), 2) if top > 0 else None


@lru_cache(maxsize=256)
def seconds(path: str) -> float:
    """How long a wav runs (0 when it cannot be read)."""
    try:
        with wave.open(path) as w: return w.getnframes() / float(w.getframerate())
    except (OSError, wave.Error, EOFError):
        return 0.0


def music_gain(voice_db: dict[int, float], music: Path, most: float) -> float:
    """The music's gain so that, undocked in the pauses, it sits MUSIC_UNDER dB under the voice's measured level; never
    above `most` (the brand's gain). Unmeasurable (no voice, no ffmpeg, an unreadable file): `most`."""
    known = [v for v in voice_db.values() if v is not None]
    try:
        r = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(music), '-vn', '-ac', '1', '-ar', '22050', '-f', 's16le', '-'],
                           capture_output=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return most
    x = np.frombuffer(r.stdout, '<i2').astype(np.float64) / 32768
    if not known or len(x) < 1102: return most
    pw = (x[:len(x) // 1102 * 1102].reshape(-1, 1102) ** 2).mean(axis=1)      # 50 ms frames, as level() measures
    top = pw.max()
    if top <= 0: return most
    lv = _db(pw[pw >= top * 1e-3].mean())
    return round(min(most, float(np.median(known)) - MUSIC_UNDER - lv), 1)


def sound_file(name: str, bed: bool = False, extra: Path | None = None) -> Path | None:
    for d in ([extra] if extra else []) + [SFX]:
        for n in ([name + '_bed'] if bed else []) + [name]:
            f = d / (n if n.endswith('.wav') else n + '.wav')
            if f.is_file(): return f
    return None


def _importance(c: dict) -> float:
    if c.get('endcard'): return ENDCARD
    if c.get('owner'): return OWNER
    return RANK.get(c['name'], 0.5 if c['name'] in PAPER else 2) + (c.get('gain', -12) + 30) / 100     # a louder cue was meant to be heard


def paper_cues(scenes: list[dict]) -> None:
    """The engine's automatic paper sounds, made explicit so they are counted (and switched off in the engine): a
    paper slide when the page slides in, a paper place when a banner really comes in. Then the rule: never two paper
    sounds within PAPER_GAP s, at most PAPER_MAX in a scene."""
    for i, sc in enumerate(scenes):
        if sc.get('silent') or sc.get('endcard'): continue
        cues = sc.setdefault('sfx', [])
        if i > 0 and sc.get('transition', 'slide') in ('slide', 'push', 'rise', 'drop'):
            cues.append({'at': 0.0, 'name': 'paper_slide', 'gain': -9})
        if sc.get('banner') and not any(c['name'] == 'paper_place' and c['at'] < .8 for c in cues):
            cues.append({'at': 0.3, 'name': 'paper_place', 'gain': -14})
        keep, last, n = [], -9.0, 0
        for c in sorted(cues, key=lambda c: c['at']):
            if c['name'] in PAPER and not c.get('owner'):
                if c['at'] - last < PAPER_GAP or n >= PAPER_MAX: continue
                last, n = c['at'], n + 1
            keep.append(c)
        sc['sfx'] = keep


def cap(scenes: list[dict], per_minute: int = PER_MINUTE) -> list[dict]:
    """At most `per_minute` one-shots a minute: over the whole film and in any 60 s window. The least important cue goes
    first (paper, then whooshes and clicks; a sound the film file asks for stays). The end card is not counted.
    Returns the dropped cues."""
    starts, t = [], 0.0
    for sc in scenes:
        starts.append(t); t += float(sc.get('dur') or 0)
    story = [i for i, sc in enumerate(scenes) if not sc.get('endcard')]          # the brand's end card and its ticks are not counted
    total = sum(float(scenes[i].get('dur') or 0) for i in story)
    allc = [(starts[i] + c['at'], i, c) for i in story for c in scenes[i].get('sfx', [])]
    dropped = []

    def over():
        if len(allc) > max(1, math.floor(per_minute * max(total, 1) / 60 + 1e-9)): return [x for x in allc]
        ts = sorted(x[0] for x in allc)
        for j in range(len(ts)):
            w = [x for x in allc if ts[j] <= x[0] < ts[j] + 60]
            if len(w) > per_minute: return w
        return None
    while (grp := over()):
        cand = [x for x in grp if _importance(x[2]) < OWNER]
        if not cand: break
        x = min(cand, key=lambda x: (_importance(x[2]), -x[0]))
        allc.remove(x); dropped.append({**x[2], 'scene': scenes[x[1]].get('id'), 't': round(x[0], 2)})
    keep = {id(c) for _, _, c in allc}
    for i in story:
        sc = scenes[i]
        if sc.get('sfx') is not None:
            sc['sfx'] = [c for c in sc['sfx'] if id(c) in keep]
    return dropped


def _aim(name: str) -> float:
    return max(BED_AIM, TICK_UNDER) if name in REPETITIVE else BED_AIM


def levels(scenes: list[dict], voice_db: dict[int, float], sfx_dir: Path | None = None, bed_gain: float = 0.0) -> None:
    """Gains measured against the voice: the main bed BED_AIM dB under it (a tick or a tock TICK_UNDER), a second bed
    at least BED_SECOND dB under the main one, no third; one-shots SHOT_UNDER dB under it (a cue the template meant
    louder sits at 3, a quiet one at 6). A cue with `fixed: true` (the film file gave its gain) keeps it; a fixed bed
    keeps it too, but never above its level here. `bed_gain` (the film's `beds: {gain}`) turns every bed down."""
    known = [v for v in voice_db.values() if v is not None]
    ref = float(np.median(known)) if known else None
    for i, sc in enumerate(scenes):
        v = voice_db.get(i, ref)
        if sc.get('beds'):
            beds = sorted(sc['beds'], key=lambda b: (not b.get('fixed'), -b.get('gain', -22)))[:2]   # the film's own first, then the loudest
            sc['beds'] = [b for b in sc['beds'] if any(b is x for x in beds)]                        # one bed, a second far under it
            main, gap = beds[0], (beds[0].get('gain', -22) - beds[-1].get('gain', -22)) if len(beds) > 1 else 0
            for b in beds:
                f = sound_file(b['name'], True, sfx_dir)
                lv = f and level(str(f), 'active')
                below = _aim(b['name']) if b is main else max(_aim(b['name']), _aim(main['name']) + max(BED_SECOND, gap))
                if v is not None and lv is not None:
                    top = round(v - below - lv, 1)
                    b['gain'] = min(b['gain'], top) if b.get('fixed') else top
                elif v is not None:                                       # no file to measure: a safe level under the voice
                    b['gain'] = max(-46, min(b.get('gain', -30), -BED_UNDER[0] - (0 if b is main else BED_SECOND)))
                b['gain'] = round(b.get('gain', -30) + bed_gain, 1)
                if v is not None: b['settle'] = round(b['gain'] - max(0, BED_SETTLE - _aim(b['name'])), 1)
        if v is None: continue
        for c in sc.get('sfx', []):
            if c.get('fixed') or c.get('endcard'): continue
            f = sound_file(c['name'], False, sfx_dir)
            if f and seconds(str(f)) > LONG_SHOT:                # the owner: «صوت القطار لا زال عالي»
                lv = level(str(f), 'active')
                if lv is not None: c['gain'] = round(v - LONG_UNDER - lv, 1)
                continue
            lv = f and level(str(f), 'peak')
            if lv is None: continue
            g = c.get('gain', -12)
            under = SHOT_UNDER[1] - (SHOT_UNDER[1] - SHOT_UNDER[0]) * min(1, max(0, (g + 20) / 12))     # -20 dB -> 6 under, -8 -> 3
            if c['name'] in PAPER: under = SHOT_UNDER[1]
            c['gain'] = round(v + 3 - under - lv, 1)        # the voice's loudest moments run ~3 dB over its spoken mean


def settle(scenes: list[dict]) -> None:
    """Each bed sets the place at its gain until BED_HEAD s after the cut, then settles over BED_RAMP s to its
    `settle` gain (render.mjs: `settle: {at, gain, ramp}`, `at` in the bed's own seconds). A bed that carries on from
    the scene before (the same place) does not swell again: it stays settled."""
    for i, sc in enumerate(scenes):
        prev = {b['name']: b for b in scenes[i - 1].get('beds', [])} if i else {}
        for b in sc.get('beds', []):
            low = b.pop('settle', None)
            if low is None or low >= b['gain']: continue
            if b['name'] in prev and not b.get('from'):
                b['gain'] = low; continue
            b['settle'] = {'at': round(b.get('lead', 0) + BED_HEAD, 2), 'gain': low, 'ramp': BED_RAMP}


def jcut(scenes: list[dict], lead: float = LEAD) -> None:
    """Each scene's beds start `lead` s before its cut, unless the scene before already plays that bed (it carries on)."""
    for i, sc in enumerate(scenes):
        if i == 0: continue
        prev = {b['name'] for b in scenes[i - 1].get('beds', [])}
        for b in sc.get('beds', []):
            if not b.get('from') and b['name'] not in prev and 'lead' not in b:
                b['lead'] = lead


def apply(scenes: list[dict], voice_db: dict[int, float] | None = None, per_minute: int = PER_MINUTE,
          sfx_dir: Path | None = None, bed_gain: float = 0.0) -> dict:
    """The whole mix on the film's scenes (the end card included, last). Returns a report: one-shots kept and dropped,
    per minute, and the scenes with a bed."""
    for sc in scenes:
        if sc.get('endcard'):
            for c in sc.get('sfx', []): c['endcard'] = True
    paper_cues(scenes)
    dropped = cap(scenes, per_minute)
    jcut(scenes)
    levels(scenes, voice_db or {}, sfx_dir, bed_gain)
    settle(scenes)
    total = sum(float(s.get('dur') or 0) for s in scenes)
    n = sum(len(s.get('sfx', [])) for s in scenes)
    for sc in scenes:                                   # bookkeeping keys stay out of the engine's storyboard
        for c in sc.get('sfx', []):
            c.pop('endcard', None); c.pop('owner', None); c.pop('fixed', None)
        for b in sc.get('beds', []):
            b.pop('fixed', None)
    return {'one_shots': n, 'per_minute': round(n / max(total, 1) * 60, 1), 'dropped': dropped,
            'beds': [s.get('id') for s in scenes if s.get('beds')]}
