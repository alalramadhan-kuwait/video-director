"""Build a full-narration review page (word-synced text, tap a word to mark an error; marks go to the page's db).

  python -m arabic_tts.review.build OUT.html "key|label|DIR" ["key|label|DIR" ...] [--title T] [--intro I] [--reference KEY]

Each DIR comes from `python -m arabic_tts.assemble` (full.mp3 + timing.json). The first version opens by default.
`--reference` names the untouched approved version (no diacritization toggle, no «fixed» tags).
Publish OUT.html as an Artifact with capabilities {"db": {}}; read marks back from collection «marks».
"""
import json, base64, os, argparse
R = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument('out'); ap.add_argument('versions', nargs='+')
ap.add_argument('--title', default='مراجعة النطق'); ap.add_argument('--intro', default=''); ap.add_argument('--reference', default='')
a = ap.parse_args()
data = dict(versions={}, order=[], title=a.title, intro=a.intro, reference=a.reference)
for spec in a.versions:
    key, label, d = spec.split('|', 2)
    t = json.load(open(os.path.join(d, 'timing.json')))
    t['audio'] = base64.b64encode(open(os.path.join(d, 'full.mp3'), 'rb').read()).decode()
    data['versions'][key] = t; data['order'].append(dict(key=key, label=label))
html = open(os.path.join(R, 'template.html')).read().replace('__DATA__', json.dumps(data, ensure_ascii=False))
open(a.out, 'w').write(html)
print(round(len(html) / 1e6, 2), 'MB (Artifact limit 16 MB)')
