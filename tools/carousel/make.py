"""Check and render a carousel: python3 tools/carousel/make.py carousels/<name> [--language tk|light|kuwaiti]

Reads <folder>/spec.json (and caption.txt), prints what breaks the kit's rules, renders the PNGs into <folder>/out
and a contact sheet <folder>/out/sheet.jpg to look at before sending. The language defaults to the spec's own
`language`, else Kuwaiti (the owner's carousel kit)."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from director import carousel  # noqa: E402


def sheet(files, dst):
    from PIL import Image
    ims = [Image.open(f).convert('RGB').resize((270, 338)) for f in files]
    out = Image.new('RGB', (len(ims) * 280 - 10, 338), 'white')
    for i, im in enumerate(ims): out.paste(im, (i * 280, 0))
    out.save(dst, quality=85)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('folder'); ap.add_argument('--language'); ap.add_argument('--check-only', action='store_true')
    a = ap.parse_args(argv)
    folder = Path(a.folder)
    spec, caption = carousel.load(folder)
    lang = a.language or spec.get('language') or 'kuwaiti'
    problems = carousel.check(spec, folder, lang)
    for p in problems: print('  ' + p)
    if not caption: print('  caption.txt is missing (2 lines and 3–5 hashtags, the photo credits)')
    if a.check_only: return 1 if problems else 0
    files, drawn = carousel.render_report(folder / 'spec.json', folder / 'out')
    for w in drawn: print('  ' + w)
    sheet(files, folder / 'out' / 'sheet.jpg')
    for f in files: print('FILE:' + str(f))
    print('SHEET:' + str(folder / 'out' / 'sheet.jpg'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
