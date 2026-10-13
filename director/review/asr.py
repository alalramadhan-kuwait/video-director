"""Local word timings for review pages (faster-whisper on CPU, cached model, no network, audio opened read-only).

The transcript is a machine hearing used ONLY to place words on the timeline. It is never treated as proof that a
word was said right or wrong: pronunciation is confirmed by a person listening.

    HF_HUB_OFFLINE=1 python -m director.review.asr OUT_DIR AUDIO [AUDIO ...]
"""
from __future__ import annotations
import json, os, sys, hashlib
from pathlib import Path


def transcribe(paths, out_dir, model_size='medium'):
    os.environ.setdefault('HF_HUB_OFFLINE', '1')
    from faster_whisper import WhisperModel
    m = WhisperModel(model_size, device='cpu', compute_type='int8')
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    for p in map(Path, paths):
        data = p.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        dst = out_dir / f'{p.stem}.json'
        if dst.exists() and json.loads(dst.read_text())['audio_sha256'] == sha:
            continue
        segs, info = m.transcribe(str(p), language='ar', word_timestamps=True, beam_size=5, vad_filter=False,
                                  condition_on_previous_text=False)
        words = [{'w': w.word.strip(), 's': round(w.start, 3), 'e': round(w.end, 3), 'p': round(w.probability, 3)}
                 for s in segs for w in (s.words or [])]
        dst.write_text(json.dumps({'audio': p.name, 'audio_sha256': sha, 'model': f'faster-whisper-{model_size}',
                                   'duration': round(info.duration, 3), 'words': words}, ensure_ascii=False, indent=1))
        print(p.stem, len(words), flush=True)


if __name__ == '__main__':
    transcribe(sys.argv[2:], sys.argv[1])
