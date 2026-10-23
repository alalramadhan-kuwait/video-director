#!/usr/bin/env python3
"""Local OmniVoice narration for review; no provider API or time stretching.

--output take.wav     the whole script in one request (one voice, one file)
--lines-dir DIR       one file per script line (DIR/<id>.wav + .json), the model loaded once and the same seed and
                      speaker description for every line; a film is made from them with make_film.py --voice-dir DIR.
                      Lines already in DIR are kept (never replaced): move a take aside to read that line again.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

MODEL = 'k2-fsa/OmniVoice'


def read_script(path):
    path = Path(path)
    raw = path.read_text(encoding='utf-8')
    if path.suffix.lower() == '.json':
        data = json.loads(raw)
        lines = data.get('lines') if isinstance(data, dict) else data
        if not isinstance(lines, list) or not lines:
            raise ValueError('JSON must be a nonempty list, or an object containing lines')
        texts = [line.get('text') if isinstance(line, dict) else line for line in lines]
        if any(not isinstance(t, str) or not t.strip() for t in texts):
            raise ValueError('Every script line must contain nonempty text')
        text = '\n'.join(texts)
    else:
        text = raw.strip()
    if not text.strip():
        raise ValueError('The script is empty')
    return text


def read_records(path):
    """The script as [{id, text}] (a film's voice script: tools/voice_script.py), for one file per line."""
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    lines = data.get('lines') if isinstance(data, dict) else data
    if not isinstance(lines, list) or not lines or not all(isinstance(r, dict) and r.get('id') and str(r.get('text') or '').strip() for r in lines):
        raise ValueError('--lines-dir needs a JSON list of {id, text} records (tools/voice_script.py writes one)')
    if len({r['id'] for r in lines}) != len(lines):
        raise ValueError('Line ids must be unique')
    return [{'id': str(r['id']), 'text': r['text'].strip()} for r in lines]


def brand_settings(path):
    """Narration settings and the pronunciation list from the brand config (brand/<id>.json); {} without one."""
    if not path:
        return {}, {}
    path = Path(path)
    cfg = json.loads(path.read_text(encoding='utf-8')).get('narration') or {}
    lex = {}
    if cfg.get('pronunciation'):
        lp = path.parent.parent / cfg['pronunciation']        # paths in the config are relative to the repository root
        if lp.is_file():
            lex = {k: v for k, v in json.loads(lp.read_text(encoding='utf-8')).items() if not k.startswith('_')}
    return cfg, lex


def spoken(text, lex):
    """What the voice is given: watch names as they are said (longest first, whole words). Captions keep the script."""
    for k in sorted(lex, key=len, reverse=True):
        text = re.sub(r'(?<![\w\u0600-\u06FF])' + re.escape(k) + r'(?![\w\u0600-\u06FF])', lex[k], text)
    return text


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--script', required=True, type=Path, help='Approved UTF-8 text or JSON lines')
    out = p.add_mutually_exclusive_group(required=True)
    out.add_argument('--output', type=Path, help='New WAV file; existing takes are never replaced')
    out.add_argument('--lines-dir', type=Path, help='One WAV per line in this folder (DIR/<id>.wav); existing lines are kept')
    p.add_argument('--only', default=None, help='With --lines-dir: only these line ids, comma separated')
    p.add_argument('--model', default=MODEL)
    p.add_argument('--device', choices=['auto', 'mps', 'cuda', 'cpu'], default='auto')
    p.add_argument('--brand', type=Path, help='Brand config (brand/timekeeper.json): voice settings and pronunciation')
    p.add_argument('--language', default=None, help='OmniVoice language ID; arb = Standard Arabic (default)')
    p.add_argument('--instruct', default=None, help='Speaker description (default: the brand config, else male, middle-aged, low pitch)')
    p.add_argument('--seed', type=int, default=1234)
    p.add_argument('--steps', type=int, default=32)
    p.add_argument('--plan', action='store_true', help='Inspect the request without importing or downloading models')
    return p


def request(args):
    if args.output is not None and args.output.suffix.lower() != '.wav':
        raise ValueError('Output must be a .wav file')
    if args.steps < 1 or args.steps > 100:
        raise ValueError('Steps must be between 1 and 100')
    cfg, lex = brand_settings(args.brand)
    script = read_script(args.script) if args.lines_dir is None else '\n'.join(r['text'] for r in read_records(args.script))
    text = spoken(script, lex)
    language = args.language or cfg.get('language') or 'arb'
    instruct = args.instruct or cfg.get('instruct') or 'male, middle-aged, low pitch'
    return dict(provider='omnivoice', model=args.model, text=text,
                text_sha256=hashlib.sha256(text.encode()).hexdigest(),
                script_sha256=hashlib.sha256(script.encode()).hexdigest(),
                pronunciation_applied=sorted(k for k in lex if k in script),
                language=language, instruct=instruct, seed=args.seed,
                num_step=args.steps, speed=1.0, status='candidate',
                license_note='Upstream pretrained model: CC-BY-NC; non-commercial review only',
                source='https://huggingface.co/k2-fsa/OmniVoice')


def _load(args):
    # Optional heavy dependencies are imported only for actual synthesis.
    import numpy as np
    import torch
    from omnivoice import OmniVoice
    device = args.device
    if device == 'auto':
        device = 'cuda' if torch.cuda.is_available() else 'mps' if torch.backends.mps.is_available() else 'cpu'
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    dtype = torch.float32 if device == 'cpu' else torch.float16
    print(f'Loading {args.model} on {device}', flush=True)
    model = OmniVoice.from_pretrained(args.model, device_map=device, dtype=dtype)
    return model, device


def _synth(model, args, req, output):
    """One request to the model, saved exclusively as `output` with its provenance next to it."""
    import numpy as np
    import soundfile as sf
    import torch
    torch.manual_seed(args.seed)                              # the same seed for every request: one voice
    np.random.seed(args.seed)
    audio = model.generate(text=req['text'], language=req['language'],
                           instruct=req['instruct'], num_step=args.steps, speed=1.0)[0]
    audio = np.asarray(audio)
    if audio.ndim != 1 or not audio.size or not np.isfinite(audio).all():
        raise ValueError('Model returned empty or invalid audio; no take saved')
    rate = int(model.sampling_rate)
    if rate <= 0:
        raise ValueError('Invalid sample rate')
    output.parent.mkdir(parents=True, exist_ok=True)
    # Link the complete temporary file exclusively: another process cannot be overwritten.
    fd, tmp = tempfile.mkstemp(suffix='.wav', dir=output.parent)
    os.close(fd)
    try:
        sf.write(tmp, audio, rate, subtype='PCM_16')
        os.link(tmp, output)
    finally:
        Path(tmp).unlink(missing_ok=True)
    req.update(sample_rate=rate, seconds=round(len(audio) / rate, 3),
               audio_sha256=hashlib.sha256(output.read_bytes()).hexdigest())
    with output.with_suffix('.json').open('x', encoding='utf-8') as f:
        json.dump(req, f, ensure_ascii=False, indent=2)
    return req


def generate_lines(args):
    """One take per line in args.lines_dir; lines that already have a take (or its record) are kept."""
    cfg, lex = brand_settings(args.brand)
    recs = read_records(args.script)
    if args.only:
        want = {x.strip() for x in args.only.split(',') if x.strip()}
        unknown = want - {r['id'] for r in recs}
        if unknown:
            raise ValueError('Unknown line ids: ' + ', '.join(sorted(unknown)))
        recs = [r for r in recs if r['id'] in want]
    base = request(args)
    plan = []
    for r in recs:
        text = spoken(r['text'], lex)
        out = args.lines_dir / f"{r['id']}.wav"
        kept = out.exists() or out.with_suffix('.json').exists()
        plan.append({**base, 'line': r['id'], 'text': text, 'text_sha256': hashlib.sha256(text.encode()).hexdigest(),
                     'script_sha256': hashlib.sha256(r['text'].encode()).hexdigest(),
                     'pronunciation_applied': sorted(k for k in lex if k in r['text']), 'kept': kept})
    if args.plan:
        return {'lines_dir': str(args.lines_dir), 'lines': plan}
    todo = [q for q in plan if not q['kept']]
    if not todo:
        return {'lines_dir': str(args.lines_dir), 'made': [], 'kept': [q['line'] for q in plan]}
    model, device = _load(args)
    made = []
    for i, q in enumerate(todo, 1):
        print(f"[{i}/{len(todo)}] {q['line']}", flush=True)
        q = {k: v for k, v in q.items() if k != 'kept'}
        q['device'] = device
        made.append(_synth(model, args, q, args.lines_dir / f"{q['line']}.wav"))
    return {'lines_dir': str(args.lines_dir), 'made': [m['line'] for m in made], 'kept': [q['line'] for q in plan if q['kept']],
            'seconds': round(sum(m['seconds'] for m in made), 1)}


def generate(args):
    if args.lines_dir is not None:
        return generate_lines(args)
    req = request(args)
    if args.plan:
        return req
    meta = args.output.with_suffix('.json')
    if args.output.exists() or meta.exists():
        raise FileExistsError('Choose a new output name; existing takes are preserved')
    model, device = _load(args)
    print('Generating the complete narration at natural speed', flush=True)
    req['device'] = device
    return _synth(model, args, req, args.output)


def main():
    args = parser().parse_args()
    try:
        result = generate(args)
    except (ValueError, FileExistsError, FileNotFoundError, ImportError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
