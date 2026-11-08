"""The house rules gate, by hand: python3 tools/house_check.py FILE… [--fix]

FILE is a film (.yaml: its script lines), a carousel folder or spec.json (its slides and caption.txt), or a caption
(.txt). Prints every rule a text breaks (brand/house_rules.yaml) and the lessons to confirm; with --fix, rewrites
what can be rewritten safely and saves the file. Exit 1 while anything is left to fix."""
import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from director import house  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('files', nargs='+'); ap.add_argument('--fix', action='store_true')
    a = ap.parse_args(argv)
    R, left = house.rules(), 0
    for f in map(Path, a.files):
        if f.is_dir(): f = f / 'spec.json'
        if f.suffix in ('.yaml', '.yml'):
            raw = f.read_text(encoding='utf-8')
            if a.fix: raw = house.fix(raw, R); f.write_text(raw, encoding='utf-8')
            film = yaml.safe_load(raw) or {}
            probs = house.check_lines(film.get('lines', []), R, ok=film.get('rules_ok'))
        elif f.name == 'spec.json':
            cap = f.with_name('caption.txt'); caption = cap.read_text(encoding='utf-8') if cap.exists() else ''
            raw = f.read_text(encoding='utf-8')
            if a.fix:
                raw = house.fix(raw, R); f.write_text(raw, encoding='utf-8')
                if caption: caption = house.fix(caption, R); cap.write_text(caption, encoding='utf-8')
            probs = house.check_carousel(json.loads(raw), caption, R)
        else:
            raw = f.read_text(encoding='utf-8')
            if a.fix: raw = house.fix(raw, R); f.write_text(raw, encoding='utf-8')
            probs = house.check(raw, f.name, R, caption=True)
        print(f'{f}: ' + ('clean' if not probs else f'{len(probs)} to fix'))
        for p in probs: print('  ' + p)
        left += len(probs)
    print('\nconfirm the lessons a machine cannot check:')
    for r in R.get('remember', []): print('  - ' + r)
    return 1 if left else 0


if __name__ == '__main__':
    raise SystemExit(main())
