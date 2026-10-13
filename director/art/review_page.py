"""Art review page: one place for the owner to read and decide on findings.

Sections are kept apart exactly as the report keeps them: automated checks (measured), AI judgements
(recommendations), and the blind-test evidence of how far the AI reviewer can be trusted. The owner's decisions are
stored by the page (collection `decisions`, one document per finding) and read back with artistic.decide(); nothing
on the page or behind it edits artwork.

    python -m director.art.review_page OUT_DIR
"""
from __future__ import annotations
import json, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECKS = ['frame size for the platform', 'length', 'black stretches', 'frozen stretches', 'static opening',
          'static stretches (3 s or more)', 'loudness (LUFS)', 'true peak', 'palette contamination from other projects']


def _img(src: Path, dst: Path, width: int):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists():
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(src), '-vf', f"scale='min({width},iw)':-2",
                        '-q:v', '4', str(dst)], check=True)
    return dst


def build(out_dir, pack_dir, report_path, blind_dir=None, truth_path=None, score_path=None):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    pack_dir = Path(pack_dir)
    rep = json.loads(Path(report_path).read_text(encoding='utf-8'))
    files = []

    def ev_img(ref, w):
        src = pack_dir / ref
        if not src.exists():
            return None
        rel = 'ev/' + ref.replace('/', '_')
        _img(src, out / rel, w); files.append(rel)
        return rel

    for f in rep['ai_judgement'] + rep['automated']:
        for e in f['evidence']:
            if e.get('kind') in ('still', 'strip', 'contact'):
                e['img'] = ev_img(e['ref'], 1400 if e['kind'] in ('strip', 'contact') else 300)
    blind = None
    if blind_dir and truth_path and score_path:
        truth = json.loads(Path(truth_path).read_text(encoding='utf-8'))
        sc = json.loads(Path(score_path).read_text(encoding='utf-8'))
        rows = []
        for r in sorted(sc['score']['rows'], key=lambda r: r['item']):
            rel = f"blind/{r['item']}.jpg"; _img(Path(blind_dir) / 'items' / f"{r['item']}.jpg", out / rel, 240); files.append(rel)
            fs = [f for f in sc['kept'] if f['scene'] == r['item']]
            rows.append({**r, 'img': rel, 'truth': truth[r['item']]['what'], 'kind': truth[r['item']]['kind'],
                         'findings': [{k: f[k] for k in ('severity', 'dimension', 'problem')} for f in fs]})
        blind = {'summary': {k: v for k, v in sc['score'].items() if k != 'rows'}, 'rows': rows}
    data = {'video': Path(rep['video']).name if rep.get('video') else None, 'counts': rep['counts'],
            'automated': rep['automated'], 'ai': rep['ai_judgement'], 'discarded': rep['discarded_ai'],
            'checks': CHECKS, 'contact': ev_img('contact.jpg', 1400), 'blind': blind,
            'notes': json.loads((ROOT / 'art/evidence/review_notes.json').read_text(encoding='utf-8'))}
    html = (Path(__file__).parent / 'review_template.html').read_text(encoding='utf-8')
    (out / 'index.html').write_text(html.replace('__DATA__', json.dumps(data, ensure_ascii=False)), encoding='utf-8')
    return data, sorted(set(files))


if __name__ == '__main__':
    import sys
    d, f = build(sys.argv[1], ROOT / 'var/review/ep7-final', ROOT / 'var/review/ep7-final/artistic_report.json',
                 ROOT / 'var/art_test/blind', ROOT / 'var/_truth/art_truth.json', ROOT / 'var/_truth/score.json')
    print(d['counts'], len(f), 'images')
