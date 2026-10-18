"""Run a set of lines through the fixed engine and a candidate selector.

  python -m arabic_tts.run ITEMS.json OUT.json [--text-key tts] [--select baseline|phase3] [--takes 3]

ITEMS: [{id, <text-key>, ...}]. `baseline` reproduces production selection exactly (fasih_lines.py: Whisper ratio minus a
slowness penalty, stop at the first take above 0.97, else the best of N). `phase3` is defined in ttsdev/select.py.
"""
import sys, json, re, difflib, argparse, os, wave
from . import engine

DIAC = re.compile('[ً-ْٰـ]')
_wm = None


def whisper():
    global _wm
    if _wm is None:
        from faster_whisper import WhisperModel
        _wm = WhisperModel('medium', device='cpu', compute_type='int8')
    return _wm


def norm(s):  # identical to production
    s = DIAC.sub('', s); s = re.sub('[إأآا]', 'ا', s); s = s.replace('ة', 'ه').replace('ى', 'ي'); return re.sub(r'[^ء-ي0-9 ]', ' ', s).split()


def transcribe(fn):
    segs, _ = whisper().transcribe(fn, language='ar', beam_size=5, word_timestamps=True)
    segs = list(segs)
    words = [dict(w=w.word.strip(), s=w.start, e=w.end, p=w.probability) for s in segs for w in (s.words or [])]
    return ' '.join(s.text for s in segs).strip(), words


def duration(fn):
    with wave.open(fn) as w:
        return w.getnframes() / w.getframerate()


def baseline_score(text, fn, heard):
    ref_w, hw = norm(text), norm(heard)
    sc = difflib.SequenceMatcher(a=ref_w, b=hw, autojunk=False).ratio()
    return sc - 0.15 * max(0, duration(fn) / max(1, len(ref_w)) - 0.75)


def select_baseline(text, n):
    takes, best = [], None
    for k in range(n):
        fn = engine.synth(text, k); heard, words = transcribe(fn)
        sc = baseline_score(text, fn, heard)
        takes.append(dict(k=k, file=fn, heard=heard, words=words, score=round(sc, 3), dur=round(duration(fn), 2)))
        if best is None or sc > best['score']:
            best = takes[-1]
        if sc > 0.97:
            break
    return dict(chosen=best['k'], file=best['file'], takes=takes, flags=[])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('items'); ap.add_argument('out')
    ap.add_argument('--text-key', default='tts'); ap.add_argument('--select', default='baseline')
    ap.add_argument('--takes', type=int, default=3)
    a = ap.parse_args(argv)
    items = json.load(open(a.items))
    res = json.load(open(a.out)) if os.path.exists(a.out) else {}
    if a.select == 'phase3':
        from .select import select_phase3
    for it in items:
        if it['id'] in res:
            continue
        text = it[a.text_key]
        r = select_baseline(text, a.takes) if a.select == 'baseline' else select_phase3(text, it, a.takes)
        res[it['id']] = dict(id=it['id'], text=text, **r)
        print(it['id'], 'take', r['chosen'], next((t['heard'] for t in r['takes'] if t['k'] == r['chosen']), ''), r.get('flags'), flush=True)
        json.dump(res, open(a.out, 'w'), ensure_ascii=False, indent=1)
    print('RUN DONE', flush=True)


if __name__ == '__main__':
    main()
