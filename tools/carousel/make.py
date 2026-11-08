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
    ap.add_argument('--rules-ok', action='store_true', help='render even when a text breaks a house rule')
    a = ap.parse_args(argv)
    folder = Path(a.folder)
    spec, caption = carousel.load(folder)
    lang = a.language or spec.get('language') or 'kuwaiti'
    problems = carousel.check(spec, folder, lang)
    for p in problems: print('  ' + p)
    if not caption: print('  caption.txt is missing (two lines; no hashtags, no sources)')
    elif '#' in caption or any(w in caption for w in ('المصادر', 'المعلومات:', 'الصور:', 'Source', 'source')):
        print('  caption.txt: no hashtags and no sources or credits in a caption (the owner, 8 Nov 2026)')
    from director import house                                  # the house rules gate (brand/house_rules.yaml)
    broken = house.check_carousel(spec, caption or '')
    for p in broken: print('  house rules: ' + p)
    if a.check_only: return 1 if problems or broken else 0
    if broken and not a.rules_ok:
        print('the texts break the house rules: fix them (tools/house_check.py --fix), or --rules-ok'); return 4
    files, drawn = carousel.render_report(folder / 'spec.json', folder / 'out')
    for w in drawn: print('  ' + w)
    sheet(files, folder / 'out' / 'sheet.jpg')
    for f in files: print('FILE:' + str(f))
    print('SHEET:' + str(folder / 'out' / 'sheet.jpg'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
