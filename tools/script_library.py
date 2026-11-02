"""The script library at a glance (brand/script_library.yaml).

    python3 tools/script_library.py                       # every type and language
    python3 tools/script_library.py numbers_explainer     # one type: its acts, skeleton lines and an example
    python3 tools/script_library.py numbers_explainer --language kuwaiti
    python3 tools/script_library.py --check films/<film>.yaml   # the film against its type and language, and its length
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from director import quickfilm, scripts  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('type', nargs='?'); ap.add_argument('--language'); ap.add_argument('--check')
    a = ap.parse_args(argv)
    if a.check:
        film = quickfilm.load(a.check)
        est = scripts.estimate(film)
        print(f"{scripts.language(film)} · {film.get('script_type', '(no type)')} · {est['chars']} characters ≈ {est['seconds']} s of voice")
        for m in scripts.check(film): print('  ' + m)
        return 0
    if a.type:
        print(scripts.card(a.type, a.language)); return 0
    for k, L in scripts.languages().items():
        print(f"{k:8} {L['name']}: {L['when']}")
    print()
    for k, T in scripts.types().items():
        print(f"{k:18} {T['name']} · {T['seconds'][0]}–{T['seconds'][1]} s · {', '.join(T['languages'])}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
