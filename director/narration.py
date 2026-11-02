"""One narrator telling one story: the delivery plan of a script, and the check that the recorded narration sounds
like one performance.

The owner, 2 Nov 2026, on Halter 2: «Each scene sounds like a separate recording. Sometimes the narrator is excited,
then suddenly calm, then overly excited again… The narrator is telling one continuous story, not performing each
scene independently. His emotions should develop naturally with the story, not restart with every scene.» And the
order of work: «النص الكامل ← توليد صوت واحد ← استخراج توقيت الجمل والكلمات ← إنشاء المشاهد حسب المعنى ← مزامنة
المشاهد مع الصوت… الصوت يكون هو الأساس، والمشاهد تتبعه، مو العكس.»

A line may carry `tone:` (calm, serious, curious, warm, surprised, excited). `plan()` reads the whole script first and
gives every line its energy (a line without a tone keeps the one before it, so the voice never resets at a cut);
`check()` names what breaks one performance: a jump of more than one step between neighbours, surprise or excitement
spent on more than a few lines, an opening louder than the story has earned. `review()` measures the recorded lines
(loudness, pitch, pace) and names the joins where the voice changes as if a new recording had started."""
from __future__ import annotations

import numpy as np

ENERGY = {'calm': 1, 'serious': 2, 'warm': 2, 'curious': 3, 'surprised': 4, 'excited': 4}
PEAKS = 2                     # lines of surprise or excitement in a film, at most: they mean something when they are rare
START_MAX = 3                 # the opening hooks with curiosity, not with a shout
JUMP = 1                      # energy steps between neighbouring lines, at most
# a join that sounds like a new recording (measured on the speech of the two lines either side of it)
LOUD_DB, PITCH_PCT, PACE_PCT = 3.0, 12.0, 25.0


def plan(lines: list[dict]) -> list[dict]:
    """Every line's tone and energy, read across the whole script: a line without a `tone` carries the one before it
    (the first line without one is curious)."""
    out, tone = [], 'curious'
    for ln in lines:
        tone = ln.get('tone') or tone
        out.append({'id': ln['id'], 'tone': tone, 'energy': ENERGY.get(tone, 2), 'act': bool(ln.get('act'))})
    return out


def check(lines: list[dict]) -> list[str]:
    """What breaks one continuous performance in the delivery plan. Empty when the arc holds."""
    arc, out = plan(lines), []
    bad = [ln['id'] for ln in lines if ln.get('tone') and ln['tone'] not in ENERGY]
    if bad: out.append(f"tone: {', '.join(bad)} use a tone outside {', '.join(ENERGY)}")
    if arc and arc[0]['energy'] > START_MAX:
        out.append(f"{arc[0]['id']}: the opening is {arc[0]['tone']}; open curious and let the story earn the surprise")
    for a, b in zip(arc, arc[1:]):
        if abs(b['energy'] - a['energy']) > JUMP:
            why = ' at the start of an act' if b['act'] else ''
            out.append(f"{a['id']} → {b['id']}: {a['tone']} to {b['tone']}{why}; build to it over a line or two")
    peaks = [a['id'] for a in arc if a['energy'] >= 4]
    if len(peaks) > PEAKS:
        out.append(f"surprise or excitement on {len(peaks)} lines ({', '.join(peaks)}); keep it for the {PEAKS} that deserve it")
    return out


def _speech(a: np.ndarray, sr: int) -> np.ndarray:
    n = int(.04 * sr)
    fr = [a[i:i + n] for i in range(0, len(a) - n, n)]
    loud = [f for f in fr if np.sqrt((f ** 2).mean()) > .02]
    return np.concatenate(loud) if loud else a[:0]


def pitch(a: np.ndarray, sr: int) -> float | None:
    """Median pitch (Hz) of the voiced frames, by autocorrelation, 70–300 Hz."""
    n, ps = int(.04 * sr), []
    for i in range(0, len(a) - n, n):
        f = a[i:i + n]
        if np.sqrt((f ** 2).mean()) < .03: continue
        f = f - f.mean(); c = np.correlate(f, f, 'full')[n - 1:]
        lo, hi = int(sr / 300), int(sr / 70)
        if hi >= len(c) or c[0] <= 0: continue
        k = lo + int(np.argmax(c[lo:hi]))
        if c[k] / c[0] > .45: ps.append(sr / k)
    return float(np.median(ps)) if len(ps) >= 5 else None


def measure(a: np.ndarray, sr: int, chars: int) -> dict:
    s = _speech(a, sr)
    return {'loud': round(float(20 * np.log10(np.sqrt((s ** 2).mean()) + 1e-9)), 1) if len(s) else None,
            'pitch': (lambda p: round(p, 1) if p else None)(pitch(a, sr)),
            'pace': round(chars / max(len(s) / sr, .1), 1) if len(s) else None}


def review(takes: list[tuple[str, np.ndarray, int, int]]) -> list[str]:
    """`takes`: (line id, audio, sample rate, characters spoken), in film order. The joins where the voice changes as if
    a new recording had started: loudness, pitch or pace jumping between neighbouring lines."""
    m = [(i, measure(a, sr, n)) for i, a, sr, n in takes]
    out = []
    for (ia, a), (ib, b) in zip(m, m[1:]):
        if a['loud'] is not None and b['loud'] is not None and abs(a['loud'] - b['loud']) > LOUD_DB:
            out.append(f'{ia} → {ib}: loudness jumps {b["loud"] - a["loud"]:+.1f} dB')
        if a['pitch'] and b['pitch'] and abs(b['pitch'] / a['pitch'] - 1) * 100 > PITCH_PCT:
            out.append(f'{ia} → {ib}: pitch jumps {(b["pitch"] / a["pitch"] - 1) * 100:+.0f}%')
        if a['pace'] and b['pace'] and abs(b['pace'] / a['pace'] - 1) * 100 > PACE_PCT:
            out.append(f'{ia} → {ib}: pace jumps {(b["pace"] / a["pace"] - 1) * 100:+.0f}%')
    return out
