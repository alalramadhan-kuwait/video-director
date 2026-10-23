#!/usr/bin/env python3
"""The film's narration as the voice reads it, one record per line:  python3 tools/voice_script.py films/panerai.yaml OUT.json
Each record is {id, text} with the line's `say` (years as words) or its `text`; the voice helper applies the brand's
watch-name pronunciation itself (--brand). OmniVoice on the owner's computer reads it with
  omnivoice_narrate.py --script OUT.json --lines-dir <dir> --brand brand/timekeeper.json
and make_film.py --voice-dir <dir> makes the film from those takes."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from director import quickfilm

if len(sys.argv) != 3: sys.exit(__doc__)
film = quickfilm.load(sys.argv[1])
recs = quickfilm.voice_script(film)
Path(sys.argv[2]).write_text(json.dumps({'film': film.get('title', ''), 'lines': recs}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print(f'{len(recs)} lines → {sys.argv[2]}')
