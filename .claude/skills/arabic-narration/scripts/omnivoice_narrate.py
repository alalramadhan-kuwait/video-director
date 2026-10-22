#!/usr/bin/env python3
"""Local OmniVoice narration for review; no provider API or time stretching."""
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
    p.add_argument('--output', required=True, type=Path, help='New WAV file; existing takes are never replaced')
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
    if args.output.suffix.lower() != '.wav':
        raise ValueError('Output must be a .wav file')
    if args.steps < 1 or args.steps > 100:
        raise ValueError('Steps must be between 1 and 100')
    cfg, lex = brand_settings(args.brand)
    script = read_script(args.script)
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


def generate(args):
    req = request(args)
    if args.plan:
        return req
    meta = args.output.with_suffix('.json')
    if args.output.exists() or meta.exists():
        raise FileExistsError('Choose a new output name; existing takes are preserved')
    # Optional heavy dependencies are imported only for actual synthesis.
    import numpy as np
    import soundfile as sf
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
    print('Generating the complete narration at natural speed', flush=True)
    audio = model.generate(text=req['text'], language=req['language'],
                           instruct=req['instruct'], num_step=args.steps, speed=1.0)[0]
    audio = np.asarray(audio)
    if audio.ndim != 1 or not audio.size or not np.isfinite(audio).all():
        raise ValueError('Model returned empty or invalid audio; no take saved')
    rate = int(model.sampling_rate)
    if rate <= 0:
        raise ValueError('Invalid sample rate')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Link the complete temporary file exclusively: another process cannot be overwritten.
    fd, tmp = tempfile.mkstemp(suffix='.wav', dir=args.output.parent)
    os.close(fd)
    try:
        sf.write(tmp, audio, rate, subtype='PCM_16')
        os.link(tmp, args.output)
    finally:
        Path(tmp).unlink(missing_ok=True)
    req.update(device=device, sample_rate=rate, seconds=round(len(audio) / rate, 3),
               audio_sha256=hashlib.sha256(args.output.read_bytes()).hexdigest())
    with meta.open('x', encoding='utf-8') as f:
        json.dump(req, f, ensure_ascii=False, indent=2)
    return req


def main():
    args = parser().parse_args()
    try:
        result = generate(args)
    except (ValueError, FileExistsError, FileNotFoundError, ImportError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
