"""Import already-approved narration into the take store (read-only on the source)."""
from __future__ import annotations
import json
from pathlib import Path
from .takes import TakeStore


def import_eleven_manifest(manifest_path, audio_dir, store: TakeStore, project: str, seed=1234,
                           output_format='mp3_44100_128', by='import'):
    """tts_eleven clips.json + the matching mp3s -> approved takes. The request is rebuilt exactly as tts_eleven
    sent it (it always sends seed 1234 and mp3_44100_128), so a later plan recognises these lines as already paid for."""
    man = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    keys = []
    for line, c in man.items():
        req = {'provider': 'elevenlabs', 'voice_id': c['voice_id'], 'model': c['model'], 'settings': c['settings'],
               'seed': seed, 'output_format': output_format, 'provider_input': c['spoken']}
        audio = (Path(audio_dir) / f'{line}.mp3').read_bytes()
        keys.append(store.put(req, audio, ext='mp3', status='approved', by=by,
                              meta={'project': project, 'line': line, 'approved_text': c['text'],
                                    'seconds': c.get('seconds'), 'source': str(manifest_path)}))
    return keys
