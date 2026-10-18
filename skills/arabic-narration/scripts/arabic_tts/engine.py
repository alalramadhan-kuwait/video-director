"""Fixed engine: Fasih-TTS-V1 (Coqui XTTS v2) + a reference voice + the series' voice settings. Not tunable on purpose:
every phase is compared with the current system on identical audio.

Configure with environment variables (set them once per project):
  ARABIC_TTS_REF       reference wav for the voice (e.g. the 14 s Bram clip). Required.
  ARABIC_TTS_WORK      project work dir: takes are cached in $ARABIC_TTS_WORK/cache (default: ./tts_work)
  ARABIC_TTS_LEXICON   the project's lexicon.yaml (default: $ARABIC_TTS_WORK/lexicon.yaml)

Takes are seeded (seed = 1000 + take index) so the current system and every phase hear identical audio for identical text.
Generated takes are cached by (text, seed, temperature) under runs/cache, so both sides share audio when their text matches.
"""
import os, hashlib, wave, json
import numpy as np

PKG = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.environ.get('ARABIC_TTS_WORK', 'tts_work'))
REF = os.environ.get('ARABIC_TTS_REF', '')
LEXICON = os.environ.get('ARABIC_TTS_LEXICON', os.path.join(ROOT, 'lexicon.yaml'))
TEMPS = [0.72, 0.62, 0.8]                                   # production cycle (fasih_lines.py)
SETTINGS = dict(repetition_penalty=2.0, speed=1.12, top_p=0.9, top_k=60, enable_text_splitting=False)
CACHE = os.path.join(ROOT, 'cache')
SR = 24000

_m = None


def model():
    global _m
    if _m is None:
        if not REF or not os.path.exists(REF):
            raise SystemExit('set ARABIC_TTS_REF to the reference voice wav')
        import torch
        from huggingface_hub import snapshot_download
        from TTS.tts.configs.xtts_config import XttsConfig
        from TTS.tts.models.xtts import Xtts
        path = snapshot_download("NightPrince/Fasih-TTS-V1"); cfg = XttsConfig(); cfg.load_json(f"{path}/config.json")
        m = Xtts.init_from_config(cfg); m.load_checkpoint(cfg, checkpoint_path=f"{path}/model.pth", vocab_path=f"{path}/vocab.json", use_deepspeed=False); m.eval()
        g, e = m.get_conditioning_latents(audio_path=[REF])
        _m = (m, g, e)
    return _m


def take_params(k):
    return 1000 + k, TEMPS[k % 3]


def synth(text, k):
    """Generate (or reuse) take k of `text`. Returns the wav path."""
    import torch
    seed, temp = take_params(k)
    key = hashlib.sha1(json.dumps([text, seed, temp, SETTINGS], ensure_ascii=False).encode()).hexdigest()[:16]
    os.makedirs(CACHE, exist_ok=True)
    fn = os.path.join(CACHE, f'{key}.wav')
    if not os.path.exists(fn):
        m, g, e = model()
        torch.manual_seed(seed); np.random.seed(seed)
        o = m.inference(text, "ar", g, e, temperature=temp, **SETTINGS)
        w = np.array(o["wav"], dtype=np.float32)
        tmp = fn + '.tmp'
        with wave.open(tmp, 'wb') as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(SR); f.writeframes((np.clip(w, -1, 1) * 32767).astype('<i2').tobytes())
        os.replace(tmp, fn)
        with open(fn + '.json', 'w') as f:
            json.dump(dict(text=text, seed=seed, temp=temp, **SETTINGS), f, ensure_ascii=False)
    return fn
