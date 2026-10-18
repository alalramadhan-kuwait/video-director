"""Phase 4: text preprocessing for the spoken track (captions are never changed).

  1. Latin terms and abbreviations → their spoken Arabic form from the lexicon (DNA → دِي إِنْ إِيه).
  2. Years written in digits after عام / سنة / العام → words, fully diacritized, in the genitive the construct requires
     (في عامِ 1936 → في عامِ أَلْفٍ وَتِسْعِمِئَةٍ وَسِتَّةٍ وَثَلَاثِينَ). Any other digits are left alone and flagged:
     Arabic number agreement depends on the counted noun, so a person writes those.
  3. Punctuation that makes the engine babble is removed from the spoken text: quotation marks and a trailing ellipsis
     («يَتْبَعُ…» → يَتْبَعُ.). Ellipses inside a line are kept (they give the pauses the narration relies on).
  4. Very short lines (≤ 2 words) are flagged `short`; synth_short() says them inside their real neighbouring
     sentence and cuts them out at a verified pause, so no extra words are added.

  python -m arabic_tts.preprocess IN.json OUT.json [--text-key tts]
"""
import re, json, argparse, os, wave
import numpy as np
from .arabic import strip, tokens, is_arabic_word

UNITS = {1: 'وَاحِدٍ', 2: 'اثْنَيْنِ', 3: 'ثَلَاثَةٍ', 4: 'أَرْبَعَةٍ', 5: 'خَمْسَةٍ', 6: 'سِتَّةٍ', 7: 'سَبْعَةٍ', 8: 'ثَمَانِيَةٍ', 9: 'تِسْعَةٍ'}
TEENS = {10: 'عَشَرَةٍ', 11: 'أَحَدَ عَشَرَ', 12: 'اثْنَيْ عَشَرَ', 13: 'ثَلَاثَةَ عَشَرَ', 14: 'أَرْبَعَةَ عَشَرَ', 15: 'خَمْسَةَ عَشَرَ',
         16: 'سِتَّةَ عَشَرَ', 17: 'سَبْعَةَ عَشَرَ', 18: 'ثَمَانِيَةَ عَشَرَ', 19: 'تِسْعَةَ عَشَرَ'}
TENS = {2: 'عِشْرِينَ', 3: 'ثَلَاثِينَ', 4: 'أَرْبَعِينَ', 5: 'خَمْسِينَ', 6: 'سِتِّينَ', 7: 'سَبْعِينَ', 8: 'ثَمَانِينَ', 9: 'تِسْعِينَ'}
HUNDREDS = {1: 'مِئَةٍ', 2: 'مِئَتَيْنِ', 3: 'ثَلَاثِمِئَةٍ', 4: 'أَرْبَعِمِئَةٍ', 5: 'خَمْسِمِئَةٍ', 6: 'سِتِّمِئَةٍ', 7: 'سَبْعِمِئَةٍ',
            8: 'ثَمَانِمِئَةٍ', 9: 'تِسْعِمِئَةٍ'}


def below_100(n):
    if n == 0:
        return []
    if n < 10:
        return [UNITS[n]]
    if n < 20:
        return [TEENS[n]]
    u, t = n % 10, n // 10
    return ([UNITS[u]] if u else []) + [TENS[t]]


def year_genitive(n):
    """Year as words in the genitive (it follows عام/سنة as the second term of a construct)."""
    parts = []
    th, rest = divmod(n, 1000)
    if th == 1:
        parts.append('أَلْفٍ')
    elif th == 2:
        parts.append('أَلْفَيْنِ')
    h, r = divmod(rest, 100)
    if h:
        parts.append(HUNDREDS[h])
    parts += below_100(r)
    return ' وَ'.join(parts)


def numbers(text):
    """Years after عام/سنة (with any diacritics or proclitics) → genitive words. Other digits are flagged."""
    flags = []
    toks = re.findall(r'\d+|[^\d]+', text)
    for i, t in enumerate(toks):
        if not t.isdigit() or not (3 <= len(t) <= 4):
            continue
        before = strip(''.join(toks[:i])).split()
        cue = re.sub('^[وفب]?(ال)?', '', before[-1]) if before else ''
        if cue in ('عام', 'سنة', 'عاما'):
            toks[i] = year_genitive(int(t))
    out = ''.join(toks)
    for d in re.findall(r'\d+', out):
        flags.append(f'number «{d}» needs a written-out spoken form (agreement depends on the noun)')
    return out, flags


def punctuation(text):
    t = re.sub('[«»"“”]', '', text).strip()
    t = re.sub(r'\s*…\s*$', '.', t)
    t = re.sub(r'\.\.\.$', '.', t)
    if t and t[-1] not in '.؟!،:':
        t += '.'
    return t


def is_short(text):
    return len([t for t in tokens(text) if is_arabic_word(t)]) <= 2


def preprocess(text, lexicon=None):
    flags, changes = [], []
    t = text
    if lexicon is not None:
        t, ch = lexicon.spoken(t)
        changes += [f'«{c["term"]}» → «{c["spoken"]}»' for c in ch]
    if re.search('[A-Za-z]', t):
        flags.append('Latin text left without a spoken form: ' + ' '.join(re.findall('[A-Za-z][A-Za-z0-9 ]*', t)))
    t2, nf = numbers(t)
    if t2 != t:
        changes.append('year digits → words (genitive)')
    t, flags = t2, flags + nf
    t3 = punctuation(t)
    if t3 != t:
        changes.append('quotes / trailing ellipsis removed for speech')
    return dict(tts=t3, short=is_short(t3), flags=flags, changes=changes)


# ---------------------------------------------------------------------------------------------------------------
# Very short lines: synthesize inside the real neighbouring sentence, cut at a verified pause.

def synth_short(target, context, k, out_dir):
    """Say `context` + `target` in one take; return (path, info) of the target cut at a silent gap, or (None, info).

    The cut is accepted only if: Whisper hears the context words before the cut and only the target words after it,
    and the gap between them has at least 120 ms of near-silence. Otherwise the caller falls back to standalone takes.
    """
    from . import engine
    from .run import transcribe, norm
    combined = context.rstrip() + ' ' + target
    fn = engine.synth(combined, k)
    with wave.open(fn) as w:
        sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32) / 32768
    heard, words = transcribe(fn)
    tw = norm(target)
    hw = [norm(w['w']) for w in words]
    flat = [(i, t) for i, ws in enumerate(hw) for t in ws]
    # locate the first target word among the last words heard
    idx = None
    for j in range(len(flat) - len(tw), -1, -1):
        if [t for _, t in flat[j:j + len(tw)]] == tw:
            idx = flat[j][0]; break
    info = dict(combined=combined, heard=heard)
    if idx is None or idx == 0:
        info['reason'] = 'target words not found after the context'
        return None, info
    prev_end, start = words[idx - 1]['e'], words[idx]['s']
    fr = int(0.01 * sr)
    a, b = int(prev_end * sr), int(start * sr)
    if b - a < int(0.12 * sr):
        # Whisper word boundaries are loose: search the 400 ms around them for the quietest stretch
        a, b = max(0, a - int(0.2 * sr)), min(len(x), b + int(0.2 * sr))
    seg = x[a:b]
    if len(seg) < fr * 12:
        info['reason'] = 'no pause between context and target'
        return None, info
    e = np.array([np.sqrt(np.mean(seg[i:i + fr] ** 2)) for i in range(0, len(seg) - fr, fr)])
    thr = max(0.01, 0.06 * float(np.max(np.abs(x))))
    quiet = e < thr
    best_len, best_end, cur = 0, 0, 0
    for i, q in enumerate(quiet):
        cur = cur + 1 if q else 0
        if cur > best_len:
            best_len, best_end = cur, i
    if best_len < 12:
        info['reason'] = f'pause too short ({best_len * 10} ms)'
        return None, info
    cut = a + (best_end - best_len // 2) * fr                      # middle of the quiet stretch
    y = x[cut:]
    pad = np.zeros(int(0.12 * sr), dtype=np.float32)               # same lead-in silence the timeline adds
    y = np.concatenate([pad, y])
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f'short_{abs(hash((target, context, k))) % 10**10}.wav')
    with wave.open(out, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((np.clip(y, -1, 1) * 32767).astype('<i2').tobytes())
    heard2, _ = transcribe(out)
    info.update(cut_at=round(cut / sr, 2), pause_ms=best_len * 10, heard_after_cut=heard2)
    if norm(heard2) != tw:
        info['reason'] = f'after the cut Whisper hears «{heard2}», not only the target'
        return None, info
    return out, info


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('inp'); ap.add_argument('out'); ap.add_argument('--text-key', default='tts')
    ap.add_argument('--overrides', help='JSON {line_id: [{from, to}]} spoken-only replacements a reviewer asked for')
    a = ap.parse_args(argv)
    ov = json.load(open(a.overrides)) if a.overrides else {}
    from .lexicon import Lexicon
    from . import engine
    lx = Lexicon(engine.LEXICON)
    items = json.load(open(a.inp))
    for it in items:
        for o in ov.get(it['id'], []):
            if o['from'] not in it[a.text_key]:
                print(it['id'], 'override not applied (text not found):', o['from'])
            it[a.text_key] = it[a.text_key].replace(o['from'], o['to'])
        r = preprocess(it[a.text_key], lx)
        it['pre_text'] = it[a.text_key]; it[a.text_key] = r['tts']; it['short'] = r['short']
        it['pre_flags'] = r['flags']; it['pre_changes'] = r['changes']
        if r['changes'] or r['flags'] or r['short']:
            print(it['id'], '|', it['pre_text'], '→', r['tts'], '|', r['changes'], r['flags'], 'SHORT' if r['short'] else '')
    json.dump(items, open(a.out, 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
