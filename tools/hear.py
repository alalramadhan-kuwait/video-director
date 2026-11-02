"""What Whisper hears in each take: `python3 tools/hear.py <voice_dir>/*.wav` (add HF_HUB_OFFLINE=1 once the model is
cached). It judges missing or added words, never pronunciation: Whisper drops the vowels and misspells Arabic."""
import os
import sys

from faster_whisper import WhisperModel


def main(paths: list[str]) -> int:
    m = WhisperModel('small', device='cpu', compute_type='int8')
    for f in sorted(paths):
        segs, _ = m.transcribe(f, language='ar', beam_size=5)
        print(os.path.basename(f), '|', ' '.join(s.text.strip() for s in segs), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
