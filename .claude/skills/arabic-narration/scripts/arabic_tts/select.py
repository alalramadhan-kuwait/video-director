"""Phase 3: candidate selection.

Each take is checked by three independent signals and the result says which ones fired:
  phonemes  wav2vec2 phoneme recognizer vs the expected pronunciation of the fully diacritized text (vowel-level)
  whisper   content completeness only: missing / extra words (Whisper cannot hear diacritics)
  audio     truncation, repetition, extra speech after the line, implausible pacing
plus lexicon `avoid` patterns (known mispronunciations such as «الإنسورين»).

Takes are generated with the unchanged engine settings; if every take of the first N has a hard problem, up to
`max_takes` are tried (the temperature cycle simply continues). The chosen take is the one with no hard problem and
the lowest phoneme distance. A line is marked UNCERTAIN (needs human approval) when no take is clean, when the two
recognizers disagree about a word, or when the line was not cleared by Phases 1-2.

None of these scores is proof of correct pronunciation; they decide which takes a human should hear first.
"""
import os, re, json, difflib, wave
import numpy as np
from . import engine
from .phon import expected, norm_rec, local
from .run import transcribe, norm, duration

LEXICON = engine.LEXICON
_pm = None


def phoneme_model():
    global _pm
    if _pm is None:
        import torch
        from transformers import Wav2Vec2ForCTC, Wav2Vec2FeatureExtractor
        from huggingface_hub import snapshot_download
        pp = snapshot_download('facebook/wav2vec2-xlsr-53-espeak-cv-ft')
        inv = {v: k for k, v in json.load(open(f"{pp}/vocab.json")).items()}
        _pm = (Wav2Vec2ForCTC.from_pretrained(pp).eval(), Wav2Vec2FeatureExtractor.from_pretrained(pp), inv)
    return _pm


def load16(fn):
    import subprocess
    raw = subprocess.run(['ffmpeg', '-v', 'quiet', '-i', fn, '-ac', '1', '-ar', '16000', '-f', 's16le', '-'], capture_output=True).stdout
    return np.frombuffer(raw, '<i2').astype(np.float32) / 32768


def phones(x):
    import torch
    m, fe, inv = phoneme_model()
    with torch.no_grad():
        lg = m(fe(x, sampling_rate=16000, return_tensors='pt').input_values).logits[0]
    ids = lg.argmax(-1).tolist(); out = []; prev = None
    for i in ids:
        if i != prev and i not in (0, 1, 2, 3):
            out.append(inv[i])
        prev = i
    return ' '.join(out)


NUM_WORDS = re.compile(r'^(و?(ألف|الف|مئة|مائة|مئتين|ألفين|عشر|عشرة|عشرين|ثلاث|ثلاثة|ثلاثين|أربع|اربع|خمس|خمسة|ست|ستة|سبع|ثمان|تسع|واحد|اثن)\w*)$')


def content_check(text, heard):
    """Whisper completeness: missing and extra words, ignoring numbers and Latin (Whisper writes those inconsistently)."""
    ref = [w for w in norm(text) if not w.isdigit() and not NUM_WORDS.match(w)]
    hw = [w for w in norm(heard) if not w.isdigit() and not NUM_WORDS.match(w)]
    sm = difflib.SequenceMatcher(a=ref, b=hw, autojunk=False)
    missing, extra = [], []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == 'replace' and ''.join(ref[i1:i2]) == ''.join(hw[j1:j2]):
            continue                                    # same letters, different spacing («واما» / «و اما»)
        if op in ('delete', 'replace'):
            missing += ref[i1:i2]
        if op in ('insert', 'replace'):
            extra += hw[j1:j2]
    return dict(ratio=round(sm.ratio(), 3), missing=missing, extra=extra)


def audio_checks(fn, words_ts, exp_len, heard, text):
    """Truncation / extra speech / repetition / pacing from the waveform and Whisper word timings."""
    flags = []
    with wave.open(fn) as w:
        sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32) / 32768
    dur = len(x) / sr
    peak = float(np.max(np.abs(x))) + 1e-9
    tail = x[-int(0.04 * sr):]
    if np.sqrt(np.mean(tail ** 2)) > 0.12 * peak:
        flags.append('cut-off ending (audio still loud in the last 40 ms)')
    # speech activity
    fr = int(0.02 * sr); e = np.array([np.sqrt(np.mean(x[i:i + fr] ** 2)) for i in range(0, len(x) - fr, fr)])
    act = e > max(0.02 * peak, 0.004)
    speech = act.sum() * 0.02
    rate = exp_len / max(speech, 0.1)
    if rate > 19:
        flags.append(f'too fast / swallowed ({rate:.1f} phonemes per second of speech)')
    if rate < 6 and exp_len > 8:
        flags.append(f'too slow / stretched ({rate:.1f} phonemes per second of speech)')
    # repetition: a word repeated back-to-back that the text does not repeat
    hw = norm(heard); tw = norm(text)
    for a, b in zip(hw, hw[1:]):
        if a == b and len(a) > 2 and not any(p == q == a for p, q in zip(tw, tw[1:])):
            flags.append(f'repeated word «{a}»'); break
    # extra speech after the last expected word (a pause, then more voice)
    if words_ts:
        last_end = words_ts[-1]['e']
        after = act[int(last_end / 0.02) + 10:] if last_end / 0.02 + 10 < len(act) else np.array([])
        if after.size and after.sum() * 0.02 > 0.25:
            flags.append(f'{after.sum() * 0.02:.2f} s of voice after the last recognized word')
    return flags, dict(dur=round(dur, 2), speech=round(speech, 2), rate=round(rate, 1))


def analyze(fn, text, lexicon=None):
    """All checks for one audio file against its (fully diacritized) text."""
    heard, words_ts = transcribe(fn)
    R = norm_rec(phones(load16(fn)))
    ex = expected(text)
    E = [x for _, ph in ex for x in ph]
    per = local(E, R)[0] / max(1, len(E)) if E else 0.0
    per_word = []
    for w, ph in ex:
        if len(ph) >= 3:
            d = local(ph, R)[0] / len(ph)
            per_word.append((w, ''.join(ph), round(d, 2)))
    content = content_check(text, heard)
    hard, soft = [], []
    if content['missing']:
        hard.append('missing words: ' + ' '.join(content['missing']))
    if len(content['extra']) >= 2:
        hard.append('extra words: ' + ' '.join(content['extra']))
    aflags, stats = audio_checks(fn, words_ts, len(E), heard, text)
    hard += [f for f in aflags if f.startswith(('cut-off', 'repeated', 'too fast'))]
    soft += [f for f in aflags if not f.startswith(('cut-off', 'repeated', 'too fast'))]
    if lexicon is not None:
        hn = ' '.join(norm(heard)) + ' '
        Rs = ''.join(R)
        for rk in lexicon.risks(text):
            for p in rk.get('whisper', []):
                if p in hn:
                    hard.append(f'known mispronunciation of {rk["term"]}: heard «{p.strip()}»')
            for p in rk.get('phon', []):
                if p in Rs:
                    hard.append(f'known mispronunciation of {rk["term"]}: phonemes «{p}»')
    worst = max(per_word, key=lambda t: t[2]) if per_word else ('', '', 0.0)
    if worst[2] >= 0.5:
        soft.append(f'word may be mispronounced: «{worst[0]}» (phoneme distance {worst[2]})')
    # disagreement between recognizers
    heard_set = set(norm(heard))
    for w, ph, d in per_word:
        nw = norm(w)
        if not nw:
            continue
        if nw[0] in heard_set and d >= 0.5:
            soft.append(f'recognizers disagree on «{w}» (Whisper heard it, phonemes distance {d})')
        elif nw[0] in content['missing'] and d <= 0.15:
            soft.append(f'recognizers disagree on «{w}» (Whisper missed it, phonemes match)')
    score = 10 * len(hard) + per + 0.5 * worst[2] + 0.2 * len(soft)
    return dict(heard=heard, phon=''.join(R), per=round(per, 3), worst=worst, content=content, stats=stats,
                hard=hard, soft=soft, score=round(score, 3))


def select_phase3(text, item=None, n=3, max_takes=5, lexicon=None):
    if lexicon is None:
        from .lexicon import Lexicon
        lexicon = Lexicon(LEXICON)
    takes = []
    reject = set((item or {}).get('reject_takes', []))     # takes the listener already rejected for this exact text
    k = 0
    while len(takes) < max_takes:
        if k in reject:
            k += 1
            continue
        fn = engine.synth(text, k)
        a = analyze(fn, text, lexicon)
        takes.append(dict(k=k, file=fn, **a))
        clean = not a['hard'] and not a['soft'] and a['per'] <= 0.2
        k += 1
        if clean:
            break                                   # a clean take: stop early like production does
        if len(takes) >= n and any(not t['hard'] for t in takes):
            break                                   # at least one usable take within the normal budget
    best = min(takes, key=lambda t: t['score'])
    flags = []
    if best['hard']:
        flags += ['no take without a hard problem'] + best['hard']
    flags += best['soft']
    if best['per'] > 0.25:
        flags.append(f'high phoneme distance {best["per"]}')
    if item and item.get('status') == 'REVIEW':
        flags.append('text not cleared by Phase 1/2 review')
    return dict(chosen=best['k'], file=best['file'], takes=takes, flags=flags, uncertain=bool(flags))
