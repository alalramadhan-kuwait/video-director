"""Audio + word-timing helpers (from video-ad-editor motion/voice.py, so this skill runs on its own)."""
import os, re, subprocess, tempfile, wave, difflib
import numpy as np

SR = 48000
AR_DIAC = re.compile(r'[ً-ٰٟـ]')


def run(cmd):
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0:
        raise RuntimeError('command failed: ' + ' '.join(cmd) + '\n' + r.stderr.decode('utf-8', 'replace')[-800:])
    return r.stdout


def decode(path_or_bytes, suffix='.mp3'):
    """any audio → float32 mono @48k"""
    tmp = None
    if isinstance(path_or_bytes, (bytes, bytearray)):
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False); tmp.write(path_or_bytes); tmp.close(); src = tmp.name
    else:
        src = path_or_bytes
    raw = run(['ffmpeg', '-v', 'error', '-i', src, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'])
    if tmp: os.unlink(tmp.name)
    return np.frombuffer(raw, dtype=np.float32).copy()


def write_wav(path, x):
    x = np.clip(x, -1, 1)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype('<i2').tobytes())


def norm(w):
    w = AR_DIAC.sub('', w)
    w = re.sub(r'[إأآٱ]', 'ا', w); w = w.replace('ة', 'ه').replace('ى', 'ي').replace('ؤ', 'و').replace('ئ', 'ي')
    w = re.sub(r'[^\w]', '', w, flags=re.UNICODE)
    return w.lower()


def split_words(text):
    return [w for w in re.split(r'\s+', text.strip()) if norm(w)]


def align(script_words, heard):
    """map each script word to a heard word time (difflib on normalized tokens), interpolate gaps"""
    A = [norm(w) for w in script_words]; B = [norm(h['w']) for h in heard]
    times = [None] * len(A)
    sm = difflib.SequenceMatcher(a=A, b=B, autojunk=False)
    for blk in sm.get_opcodes():
        tag, a0, a1, b0, b1 = blk
        if tag == 'equal' or (tag == 'replace' and (a1 - a0) == (b1 - b0)):
            for k in range(a1 - a0): times[a0 + k] = (heard[b0 + k]['s'], heard[b0 + k]['e'])
        elif tag == 'replace' and b1 > b0:          # uneven replace → spread proportionally over the heard span
            s0, e0 = heard[b0]['s'], heard[b1 - 1]['e']; n = a1 - a0
            for k in range(n): times[a0 + k] = (s0 + (e0 - s0) * k / n, s0 + (e0 - s0) * (k + 1) / n)
    # interpolate missing
    known = [i for i, t in enumerate(times) if t]
    if not known: raise RuntimeError('whisper alignment found no matching words')
    for i in range(len(times)):
        if times[i]: continue
        prv = max([k for k in known if k < i], default=None); nxt = min([k for k in known if k > i], default=None)
        if prv is None: s = times[nxt][0] - 0.25 * (nxt - i); times[i] = (max(0, s), max(0, s) + 0.2)
        elif nxt is None: s = times[prv][1] + 0.05 * (i - prv); times[i] = (s, s + 0.25)
        else:
            s0, e0 = times[prv][1], times[nxt][0]; span = (e0 - s0) / (nxt - prv)
            times[i] = (s0 + span * (i - prv - 1) + 0.01, s0 + span * (i - prv))
    return times


