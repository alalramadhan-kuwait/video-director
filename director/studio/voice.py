"""Draft narration for a studio project: FREE draft voice only, clearly labelled, never the final voice.

  1. narration(): the approved script → narration-ready text per line. The pronunciation library (this project's
     rules + the brand's approved entries) is applied for the DRAFT provider (gtts). The script itself is never edited.
  2. generate(): each line → Google's free text-to-speech (gTTS, the Time Keeper profile's draft provider; no key,
     no account, no credits) → silence trimmed → a take (content-addressed, read-only).
  3. Each take is transcribed on this machine (faster-whisper, cached model) with word timestamps and aligned to the
     script words, so every word on screen knows where it is in the audio. A word whisper did not hear is placed
     between its neighbours and marked 'estimated'. The transcript only places words; whether a word is said
     right is decided by a person listening.
  4. A waveform (peak per bin) is stored with the take for the page to draw.

What the draft voice can and cannot tell you: wording, order, length, rhythm and whether a respelling changes how a
machine voice reads a word. It cannot tell you how ElevenLabs will say a name: that is checked after the final
recording, which needs the owner's authorization and is never run here.
"""
from __future__ import annotations
import difflib, hashlib, io, json, os, re, subprocess, tempfile
from pathlib import Path

import numpy as np

from ..library import Library, Entry
from . import checks

SR = 24000
PROVIDER = 'gtts'
_WHISPER = {}


def approved_script(st):
    ap = [s for s in st['scripts'] if s['status'] == 'approved']
    return ap[-1] if ap else None


def library_for(studio, pid, st) -> Library:
    entries = [Entry(**{k: v for k, v in r.items()}) for r in st['voice']['rules']]
    return Library(entries, name=f'project:{pid}')


def narration(studio, pid, st=None) -> dict:
    st = st or studio.state(pid)
    sv = approved_script(st)
    if sv is None:
        from .store import Refused
        raise Refused('approve a script version first: the voice reads the approved script only')
    lib = library_for(studio, pid, st)
    lines = []
    for ln in studio.read_json(pid, sv['file'])['lines']:
        spoken, finds = lib.prepare(ln['text'], PROVIDER, line=ln['id'])
        lines.append({'id': ln['id'], 'text': ln['text'], 'spoken': spoken, 'rules': [f.__dict__ for f in finds],
                      'changed': spoken != ln['text']})
    return {'script_v': sv['v'], 'library_version': lib.version, 'provider': PROVIDER, 'lines': lines}


def _ff(*a, inp=None):
    return subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', *map(str, a)], input=inp, capture_output=True, check=True).stdout


def synth(text: str) -> bytes:
    """One gTTS request (network to translate.google.com). Returns mp3 bytes."""
    if os.environ.get('VD_DRAFT_VOICE') == 'offline-mock':          # tests: a tone per word, never sent anywhere
        return _mock_mp3(text)
    from gtts import gTTS
    buf = io.BytesIO()
    gTTS(text, lang='ar').write_to_fp(buf)
    return buf.getvalue()


def _mock_mp3(text):
    """Tests only: one tone per word, never sent anywhere. Each word has its own pitch and length (from its letters), so
    a line's sound is not periodic and the film's sync check can find it (a repeating tone matches itself every word)."""
    parts = []
    for w in checks.words(text) or ['_']:
        w = checks.bare(w)                                    # vowel marks alone do not change the mock sound
        k = int(hashlib.sha256(w.encode()).hexdigest()[:6], 16)
        d = 0.26 + 0.035 * min(len(w), 8)
        t = np.arange(int(SR * d)) / SR
        f0 = 130 + k % 170
        parts.append(0.3 * np.sin(2 * np.pi * (f0 + 60 * t / d) * t) * np.sin(np.pi * t / d) ** 2)
        parts.append(np.zeros(int(SR * (0.04 + (k % 5) * 0.012))))
    a = np.concatenate(parts).astype(np.float32)
    return _ff('-f', 'f32le', '-ar', SR, '-ac', 1, '-i', '-', '-c:a', 'libmp3lame', '-b:a', '64k', '-f', 'mp3', '-', inp=a.tobytes())


def decode(data: bytes) -> np.ndarray:
    raw = _ff('-i', '-', '-ac', 1, '-ar', SR, '-f', 'f32le', '-', inp=data)
    return np.frombuffer(raw, np.float32).astype(np.float64)


def trim(a, thr=.01):
    idx = np.where(np.abs(a) > thr)[0]
    return a[max(0, idx[0] - int(.05 * SR)): idx[-1] + int(.12 * SR)] if len(idx) else a


def encode(a: np.ndarray, fmt: str) -> bytes:
    args = ['-c:a', 'libmp3lame', '-b:a', '96k', '-f', 'mp3'] if fmt == 'mp3' else ['-c:a', 'pcm_s16le', '-f', 'wav']
    return _ff('-f', 'f64le', '-ar', SR, '-ac', 1, '-i', '-', '-ar', 48000 if fmt == 'wav' else SR, *args, '-',
               inp=a.clip(-.99, .99).tobytes())


def peaks(a: np.ndarray, bins=160) -> list[float]:
    if not len(a): return []
    chunks = np.array_split(np.abs(a), bins)
    p = np.array([c.max() if len(c) else 0 for c in chunks])
    return [round(float(x), 3) for x in (p / (p.max() or 1))]


def whisper():
    if 'm' not in _WHISPER:
        os.environ.setdefault('HF_HUB_OFFLINE', '1')
        from faster_whisper import WhisperModel
        _WHISPER['m'] = WhisperModel(os.environ.get('VD_WHISPER', 'small'), device='cpu', compute_type='int8')
    return _WHISPER['m']


def hear(wav_bytes: bytes) -> list[dict]:
    if os.environ.get('VD_DRAFT_VOICE') == 'offline-mock':
        return []
    with tempfile.NamedTemporaryFile(suffix='.wav') as f:
        f.write(wav_bytes); f.flush()
        segs, _ = whisper().transcribe(f.name, language='ar', word_timestamps=True, beam_size=5, condition_on_previous_text=False)
        return [{'w': w.word.strip(), 's': round(w.start, 3), 'e': round(w.end, 3), 'p': round(w.probability, 3)}
                for s in segs for w in (s.words or [])]


def _n(w):
    w = checks.bare(w).strip('،,.:;!?؟…«»"\'()-–— ')
    return w.replace('ى', 'ي').replace('ة', 'ه')


def align(script_words: list[str], heard: list[dict], seconds: float) -> list[dict]:
    """Give every script word a start and end in the take. Matched words take whisper's times; the others are
    spread between their matched neighbours by length and marked estimated."""
    a, b = [_n(w) for w in script_words], [_n(h['w']) for h in heard]
    out = [{'w': w, 's': None, 'e': None, 'est': True} for w in script_words]
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal' or (tag == 'replace' and i2 - i1 == j2 - j1):
            for k in range(i2 - i1):
                h = heard[j1 + k]
                out[i1 + k].update(s=h['s'], e=h['e'], est=(tag != 'equal'), heard=h['w'], p=h['p'])
    # fill gaps by character weight between known anchors
    i = 0
    while i < len(out):
        if out[i]['s'] is not None: i += 1; continue
        j = i
        while j < len(out) and out[j]['s'] is None: j += 1
        t0 = out[i - 1]['e'] if i > 0 else 0.05
        t1 = out[j]['s'] if j < len(out) else max(t0 + 0.2, seconds - 0.1)
        wts = [len(out[k]['w']) + 1 for k in range(i, j)]; tot = sum(wts); acc = t0
        for k, wt in zip(range(i, j), wts):
            d = (t1 - t0) * wt / tot
            out[k].update(s=round(acc, 3), e=round(acc + d, 3)); acc += d
        i = j
    return out


def take_id(line_id, spoken):
    return 'tk-' + line_id + '-' + hashlib.sha256(f'{PROVIDER}|{spoken}'.encode()).hexdigest()[:8]


def generate(studio, pid, task, lines=None, reason='draft read'):
    """Job: make draft takes for the given line ids (default: every line without a current take)."""
    st = studio.state(pid)
    nar = narration(studio, pid, st)
    vl = st['voice'].get('lines') or {}
    todo = [l for l in nar['lines'] if (lines is None and vl.get(l['id'], {}).get('status') in ('missing', 'stale', None))
            or (lines and l['id'] in lines)]
    made, reused = [], []
    for ln in todo:
        tid = take_id(ln['id'], ln['spoken'])
        if tid in st['voice']['takes']:
            reused.append(tid); task.unit(scene=ln['id'], reused=True); continue
        mp3 = synth(ln['spoken'])
        a = trim(decode(mp3))
        wav = encode(a, 'wav'); mp3c = encode(a, 'mp3')
        sig = hashlib.sha256(np.round(a, 3).tobytes()).hexdigest()[:20]           # what was actually said, not the label
        seconds = round(len(a) / SR, 3)
        heard = hear(wav)
        sw = checks.words(ln['text'])
        words = align(sw, heard, seconds)
        heard_txt = ' '.join(h['w'] for h in heard)
        missing = [w['w'] for w in words if w['est'] and not w.get('heard')] if heard else []
        prev = [st['voice']['takes'][i] for i in st['voice']['by_line'].get(ln['id'], [])]
        rec = {'id': tid, 'line': ln['id'], 'text': ln['text'], 'spoken': ln['spoken'], 'provider': PROVIDER,
               'label': 'DRAFT VOICE (gTTS, free) — not the final voice', 'script_v': nar['script_v'],
               'library_version': nar['library_version'], 'audio': studio.put(pid, mp3c, 'mp3'), 'wav': studio.put(pid, wav, 'wav'),
               'seconds': seconds, 'words': words, 'heard': heard_txt, 'not_heard': missing, 'peaks': peaks(a),
               'supersedes': prev[-1]['id'] if prev else None, 'reason': reason, 'audio_sig': sig,
               'same_audio_as': next((p['id'] for p in reversed(prev) if p.get('audio_sig') == sig), None),
               'rules_applied': [r['id'] for r in st['voice']['rules'] if ln['id'] in (r.get('lines') or [ln['id']]) and ln['changed']]}
        studio.act(pid, 'voice_take', rec, actor='system')
        made.append(tid)
        task.unit(scene=ln['id'], seconds=seconds)
    return {'made': made, 'reused': reused, 'lines': [l['id'] for l in todo]}


def fix_line(studio, pid, task, line, vflag):
    """Job: after a pronunciation rule was recorded, make a new take of THAT line only and prove the others did not
    change (their current take ids and audio files are compared before and after)."""
    st0 = studio.state(pid)
    before = {ln: ids[-1] for ln, ids in st0['voice']['by_line'].items() if ln != line}
    sums = {ln: hashlib.sha256(studio.path(pid, st0['voice']['takes'][t]['audio']).read_bytes()).hexdigest() for ln, t in before.items()}
    out = generate(studio, pid, task, lines=[line], reason=f'correction {vflag}')
    st1 = studio.state(pid)
    after = {ln: ids[-1] for ln, ids in st1['voice']['by_line'].items() if ln != line}
    sums1 = {ln: hashlib.sha256(studio.path(pid, st1['voice']['takes'][t]['audio']).read_bytes()).hexdigest() for ln, t in after.items()}
    out['others_unchanged'] = before == after and sums == sums1
    out['others_checked'] = len(before)
    new = st1['voice']['takes'][st1['voice']['by_line'][line][-1]]
    f = next((x for x in st1['voice']['flags'] if x['vflag'] == vflag), None)
    old = st1['voice']['takes'].get(f['take']) if f else None
    out['word_change'] = None
    if old and new['id'] != old['id'] and f['wi'] < len(old['words']) and f['wi'] < len(new['words']):
        out['word_change'] = round(word_change(decode(studio.path(pid, old['wav']).read_bytes()), decode(studio.path(pid, new['wav']).read_bytes()),
                                               old['words'][f['wi']], new['words'][f['wi']]), 3)
    # the draft voice ignored the respelling (whole take, or just the flagged word): say so, do not call it corrected
    out['no_effect'] = bool(new.get('same_audio_as')) or (out['word_change'] is not None and out['word_change'] < WORD_SAME)
    return out


WORD_SAME = 0.3


def word_change(a: np.ndarray, b: np.ndarray, wa: dict, wb: dict) -> float:
    """How different the flagged word sounds in two takes: relative RMS difference of the word's own audio window
    (plus 50 ms each side), at the best alignment within ±40 ms. 0 = the same sound; a changed sound is well above 0.3.
    A machine check of 'did anything change', not of 'is it right' (that is the owner's ear)."""
    seg = lambda x, w: x[int(max(0, w['s'] - .05) * SR): int((w['e'] + .05) * SR)]
    sa, sb = seg(a, wa), seg(b, wb)
    if not len(sa) or not len(sb) or abs(len(sa) - len(sb)) > 0.15 * max(len(sa), len(sb)):
        return 1.0                                              # the word's length changed: something changed
    n, L = min(len(sa), len(sb)), int(.04 * SR)
    if n <= 2 * L + 1:
        return 1.0
    x = sa[L:n - L]; ref = max(float(np.sqrt(np.mean(x ** 2))), 1e-9)
    best = min(float(np.sqrt(np.mean((x - sb[L + d:n - L + d]) ** 2))) for d in range(-L, L + 1, max(1, int(.002 * SR))))
    return best / ref
