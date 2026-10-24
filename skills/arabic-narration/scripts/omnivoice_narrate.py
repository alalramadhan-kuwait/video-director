#!/usr/bin/env python3
"""Local narration (OmniVoice, or VoxCPM2 with --engine voxcpm2); no provider API or time stretching.

Engines (both free and local; each take's record keeps the model's own licence note as provenance):
  omnivoice   k2-fsa/OmniVoice   the owner's narration voice
  voxcpm2     openbmb/VoxCPM2    Apache-2.0 weights: commercial use permitted; Arabic among its 30 languages;
              read plain by default: an English «(description)» prefix made its Arabic worse (names broken,
              the year garbled; --voice-design turns it on). With --lines-dir, one line's take (--reference, the
              first line by default) is the voice reference for all the others, so the film keeps one voice

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
# the speaker words OmniVoice accepts (it refuses any other item in its comma-separated description)
OMNI_ITEMS = {'american accent', 'australian accent', 'british accent', 'canadian accent', 'child', 'chinese accent', 'elderly',
              'female', 'high pitch', 'indian accent', 'japanese accent', 'korean accent', 'low pitch', 'male', 'middle-aged',
              'moderate pitch', 'portuguese accent', 'russian accent', 'teenager', 'very high pitch', 'very low pitch', 'whisper',
              'young adult'}
ENGINES = {
    'omnivoice': {'model': MODEL, 'steps': 32, 'source': 'https://huggingface.co/k2-fsa/OmniVoice',
                  'license_note': 'Upstream pretrained model: CC-BY-NC; non-commercial review only'},
    'voxcpm2': {'model': 'openbmb/VoxCPM2', 'steps': 10, 'source': 'https://huggingface.co/openbmb/VoxCPM2',
                'license_note': 'Apache-2.0 weights (openbmb/VoxCPM2): commercial use permitted'},
}


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
    if cfg.get('keep_latin'):                                 # foreign names stay in Latin letters and are read as they are
        lex = {k: v for k, v in lex.items() if not re.search(r'[A-Za-z]', k)}
    return cfg, lex


def engine_lexicon(cfg, engine):
    """Respellings one engine needs on top of the brand's pronunciation (narration.engine_pronunciation.<engine>);
    applied after it, so a name the brand list produces can be respelled again for that engine."""
    return {k: v for k, v in ((cfg.get('engine_pronunciation') or {}).get(engine) or {}).items() if not k.startswith('_')}


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
    p.add_argument('--engine', choices=sorted(ENGINES), default='omnivoice')
    p.add_argument('--model', default=None, help="The engine's model (default: the engine's own)")
    p.add_argument('--device', choices=['auto', 'mps', 'cuda', 'cpu'], default='auto')
    p.add_argument('--brand', type=Path, help='Brand config (brand/timekeeper.json): voice settings and pronunciation')
    p.add_argument('--language', default=None, help='OmniVoice language ID; arb = Standard Arabic (default)')
    p.add_argument('--instruct', default=None, help='Speaker description (default: the brand config, else male, middle-aged, low pitch)')
    p.add_argument('--seed', type=int, default=1234)
    p.add_argument('--steps', type=int, default=None, help='Generation steps (default: 32 OmniVoice, 10 VoxCPM2)')
    p.add_argument('--cfg', type=float, default=2.0, help='VoxCPM2 guidance (its default 2.0)')
    p.add_argument('--voice-design', action='store_true', help='VoxCPM2: prefix the speaker description «(…)» (worse for Arabic)')
    p.add_argument('--reference', default='first', help="VoxCPM2 with --lines-dir: the line whose take is the voice for the others ('first', an id, or 'none')")
    p.add_argument('--plan', action='store_true', help='Inspect the request without importing or downloading models')
    return p


def request(args):
    eng = ENGINES[args.engine]
    args.model = args.model or eng['model']
    args.steps = args.steps or eng['steps']
    if args.output is not None and args.output.suffix.lower() != '.wav':
        raise ValueError('Output must be a .wav file')
    if args.steps < 1 or args.steps > 100:
        raise ValueError('Steps must be between 1 and 100')
    cfg, lex = brand_settings(args.brand)
    lex = {**lex, **engine_lexicon(cfg, args.engine)}
    script = read_script(args.script) if args.lines_dir is None else '\n'.join(r['text'] for r in read_records(args.script))
    text = spoken(script, lex)
    language = args.language or cfg.get('language') or 'arb'
    instruct = args.instruct or cfg.get('instruct') or 'male, middle-aged, low pitch'
    dropped = []
    if args.engine == 'omnivoice':                            # a free-form description (VoxCPM2's) keeps only OmniVoice's words
        items = [x.strip() for x in instruct.split(',') if x.strip()]
        dropped = [x for x in items if x.lower() not in OMNI_ITEMS]
        instruct = ', '.join(x for x in items if x.lower() in OMNI_ITEMS) or 'male, middle-aged, low pitch'
    return dict(provider=args.engine, model=args.model, text=text,
                text_sha256=hashlib.sha256(text.encode()).hexdigest(),
                script_sha256=hashlib.sha256(script.encode()).hexdigest(),
                pronunciation_applied=sorted(k for k in lex if k in script),
                language=language, instruct=instruct, seed=args.seed,
                num_step=args.steps, speed=1.0, status='candidate',
                **({'cfg': args.cfg, 'voice_design': bool(args.voice_design)} if args.engine == 'voxcpm2' else {}),
                license_note=eng['license_note'], source=eng['source'], **({'instruct_dropped': dropped} if dropped else {}))


def _load(args):
    # Optional heavy dependencies are imported only for actual synthesis.
    import numpy as np
    import torch
    device = args.device
    if device == 'auto':
        device = 'cuda' if torch.cuda.is_available() else 'mps' if torch.backends.mps.is_available() else 'cpu'
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    print(f'Loading {args.model} on {device}', flush=True)
    if args.engine == 'voxcpm2':
        from voxcpm import VoxCPM
        # no denoiser (it is for cleaning a reference recording; voice design needs none); compiling is for CUDA only
        model = VoxCPM.from_pretrained(args.model, load_denoiser=False, optimize=device == 'cuda', device=device)
        return model, device
    from omnivoice import OmniVoice
    dtype = torch.float32 if device == 'cpu' else torch.float16
    model = OmniVoice.from_pretrained(args.model, device_map=device, dtype=dtype)
    return model, device


def _audio(model, args, req):
    """One request: (waveform, sample rate). VoxCPM2 reads the text plain, or after its voice-design prefix, and
    speaks like the reference take when the request names one."""
    if args.engine == 'voxcpm2':
        import inspect
        text = f"({req['instruct']}){req['text']}" if args.voice_design else req['text']
        kw = dict(text=text, cfg_value=args.cfg, inference_timesteps=args.steps)
        if req.get('reference_wav'):
            kw.update(prompt_wav_path=req['reference_wav'], prompt_text=req['reference_text'])
        if 'seed' in inspect.signature(getattr(model, '_generate', model.generate)).parameters:
            kw['seed'] = args.seed                            # newer releases take it; 2.0.3 uses the torch seed set above
        audio = model.generate(**kw)
        return audio, int(model.tts_model.sample_rate)
    audio = model.generate(text=req['text'], language=req['language'],
                           instruct=req['instruct'], num_step=args.steps, speed=1.0)[0]
    return audio, int(model.sampling_rate)


def _synth(model, args, req, output):
    """One request to the model, saved exclusively as `output` with its provenance next to it."""
    import numpy as np
    import soundfile as sf
    import torch
    torch.manual_seed(args.seed)                              # the same seed for every request: one voice
    np.random.seed(args.seed)
    audio, rate = _audio(model, args, req)
    audio = np.asarray(audio)
    if audio.ndim != 1 or not audio.size or not np.isfinite(audio).all():
        raise ValueError('Model returned empty or invalid audio; no take saved')
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
    lex = {**lex, **engine_lexicon(cfg, args.engine)}
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
    ref = None                                                 # VoxCPM2: one line's take is the voice of all the others
    if args.engine == 'voxcpm2' and args.reference != 'none':
        allrecs = read_records(args.script)
        rid = allrecs[0]['id'] if args.reference == 'first' else args.reference
        rr = next((r for r in allrecs if r['id'] == rid), None)
        if rr is None:
            raise ValueError(f'Unknown reference line: {rid}')
        ref = {'id': rid, 'wav': args.lines_dir / f'{rid}.wav', 'text': spoken(rr['text'], lex)}
        if not ref['wav'].exists() and not any(q['line'] == rid for q in todo):
            raise ValueError(f'The reference line {rid} has no take yet: read it first (--only {rid})')
        todo.sort(key=lambda q: q['line'] != rid)              # the reference line is read first, plain
    model, device = _load(args)
    made = []
    for i, q in enumerate(todo, 1):
        print(f"[{i}/{len(todo)}] {q['line']}", flush=True)
        q = {k: v for k, v in q.items() if k != 'kept'}
        q['device'] = device
        if ref and q['line'] != ref['id']:
            q.update(reference=ref['id'], reference_wav=str(ref['wav']), reference_text=ref['text'])
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
