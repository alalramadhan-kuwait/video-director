"""CATT (encoder-decoder) as a second opinion. Reads a JSON list of bare texts on stdin, prints a JSON list.
Uses the isolated audit copy of CATT + onnxruntime; Arabic spans only (CATT drops other characters)."""
import sys, json, re, os
# optional: ARABIC_TTS_CATT_PATH = extra import dirs (os.pathsep-separated) holding catt_tashkeel + onnxruntime,
# for setups that keep them outside the TTS venv. Otherwise: pip install catt-tashkeel onnxruntime (CPU is fine).
for p in reversed([p for p in os.environ.get('ARABIC_TTS_CATT_PATH', '').split(os.pathsep) if p]):
    sys.path.insert(0, p)
from catt_tashkeel import CATTEncoderDecoder
m = CATTEncoderDecoder()
span = re.compile(r'[ء-يٰ ]+')
def dz(t):
    out, last = [], 0
    for mm in span.finditer(t):
        s = mm.group(0)
        if not s.strip(): continue
        out.append(t[last:mm.start()]); lead = s[:len(s) - len(s.lstrip())]; trail = s[len(s.rstrip()):]
        out.append(lead + m.do_tashkeel_batch([s.strip()], batch_size=1, verbose=False)[0] + trail); last = mm.end()
    out.append(t[last:]); return ''.join(out)
print(json.dumps([dz(t) for t in json.load(sys.stdin)], ensure_ascii=False))
