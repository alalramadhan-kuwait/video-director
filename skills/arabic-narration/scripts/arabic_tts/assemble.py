"""Assemble a full-episode narration for review, the same way production does (clean → 0.12 s lead / 0.1 s tail →
line gaps), with word timings for the review page. Reads production files only; writes under runs/review/.

  python -m arabic_tts.assemble RUN.json SCRIPT.json OUTDIR [--tts-texts ITEMS.json]
  python -m arabic_tts.assemble --current PROD_VO_DIR OUTDIR          # the approved narration, untouched, for comparison
"""
import sys, os, json, subprocess, argparse
import numpy as np
from . import engine

CLEAN = os.path.join(engine.PKG, 'voice_clean.sh')


def concat(lines, wav_of, out_dir, sr):
    from .audio_util import decode, write_wav
    parts, t, meta = [], 0.0, []
    for l in lines:
        x = decode(wav_of(l))
        meta.append(dict(id=l['id'], start=round(t, 3), dur=round(len(x) / sr, 3),
                         words=[dict(w=w['w'], s=round(t + w['s'], 3), e=round(t + w['e'], 3)) for w in l['words']]))
        parts += [x, np.zeros(int(sr * l['gap_after']))]
        t += len(x) / sr + l['gap_after']
    full = np.concatenate(parts)
    os.makedirs(out_dir, exist_ok=True)
    write_wav(os.path.join(out_dir, 'full.wav'), full)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', os.path.join(out_dir, 'full.wav'), '-ac', '1', '-b:a', '64k',
                    os.path.join(out_dir, 'full.mp3')], check=True)
    return meta, round(t, 2)


def main(argv=None):
    from .audio_util import decode, write_wav, split_words, align, SR
    ap = argparse.ArgumentParser()
    ap.add_argument('a'); ap.add_argument('b'); ap.add_argument('c', nargs='?')
    ap.add_argument('--current', action='store_true'); ap.add_argument('--tts-texts')
    a = ap.parse_args(argv)
    if a.current:
        vo, out_dir = a.a, a.b
        d = json.load(open(os.path.join(vo, 'words.json')))
        meta, total = concat(d['lines'], lambda l: os.path.join(vo, os.path.basename(l['file'])), out_dir, SR)
        json.dump(dict(lines=meta, total=total), open(os.path.join(out_dir, 'timing.json'), 'w'), ensure_ascii=False, indent=1)
        print('current', total, 's'); return
    run, script, out_dir = json.load(open(a.a)), json.load(open(a.b)), a.c
    tts = {x['id']: x['tts'] for x in json.load(open(a.tts_texts))} if a.tts_texts else {}
    from faster_whisper import WhisperModel
    wm = WhisperModel('medium', device='cpu', compute_type='int8')
    vo = os.path.join(out_dir, 'vo'); os.makedirs(vo, exist_ok=True)
    lines = []
    for l in script:
        r = run[l['id']]
        cln = os.path.join(vo, l['id'] + '_clean.wav')
        subprocess.run(['bash', CLEAN, r['file'], cln], check=True, capture_output=True)
        x = decode(cln); x = np.concatenate([np.zeros(int(SR * 0.12)), x, np.zeros(int(SR * 0.1))])
        fn = os.path.join(vo, l['id'] + '.wav'); write_wav(fn, x); dur = len(x) / SR
        segs, _ = wm.transcribe(fn, language='ar', word_timestamps=True, beam_size=5)
        heard = [{'w': w.word.strip(), 's': float(w.start), 'e': float(w.end)} for s in segs for w in (s.words or []) if w.word.strip()]
        sw = split_words(l['text']); T = align(sw, heard)
        words = [{'w': sw[i], 's': round(max(0, min(dur, T[i][0])), 3), 'e': round(max(0, min(dur, T[i][1])), 3)} for i in range(len(sw))]
        lines.append(dict(id=l['id'], text=l['text'], words=words, gap_after=l['gap_after'], file=fn, take=r['chosen'],
                          heard=' '.join(h['w'] for h in heard), tts=tts.get(l['id'], r.get('text'))))
        print(l['id'], round(dur, 2), flush=True)
    meta, total = concat(lines, lambda l: l['file'], out_dir, SR)
    for m, l in zip(meta, lines):
        m.update(text=l['text'], tts=l['tts'], heard=l['heard'], take=l['take'])
    json.dump(dict(lines=meta, total=total), open(os.path.join(out_dir, 'timing.json'), 'w'), ensure_ascii=False, indent=1)
    print('new', total, 's')


if __name__ == '__main__':
    main()
