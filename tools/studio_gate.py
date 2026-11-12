"""The style gate, by hand: python3 tools/studio_gate.py FILM.json   (or the record on stdin: `… | studio_gate.py -`)

Run it on a film's studio record before any build or render. Exit 0 only when the record shows the owner's style pick:
`style_pick {by: 'owner', choice}` (his tap, written by the page), or his pick in chat (`flow.choice` set,
`flow.stage: 'done'` and `style_pick_chat {at, words}`, written by the back end with his own words). Otherwise it
prints why and exits 1; a record that cannot be read exits 2. There is no flag that skips it."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from director import style_gate  # noqa: E402


def main(argv=None, stdin=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('film', nargs='?', default='-', help="the film record as JSON (a path, or '-' for stdin)")
    a = ap.parse_args(argv)
    try:
        raw = (stdin or sys.stdin).read() if a.film == '-' else Path(a.film).read_text(encoding='utf-8')
        doc = json.loads(raw)
    except (OSError, ValueError) as e:
        print(f'style gate: the film record cannot be read ({e}); nothing is built'); return 2
    bad = style_gate.problems(doc)
    for b in bad: print('style gate:', b)
    if bad: return 1
    film = style_gate.record(doc)
    if style_gate.picked_on_page(film):
        print(f"style gate: open (his pick on the page: «{film['style_pick'].get('name') or film['style_pick']['choice']}»)")
    else:
        print(f"style gate: open (his pick in chat: «{film['flow']['choice']}», «{film['style_pick_chat']['words'].strip()}»)")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
